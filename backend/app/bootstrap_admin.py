"""
VANA — Production Administrator Bootstrap Command
Module: app.bootstrap_admin
Usage:
    python -m app.bootstrap_admin

Provisions the initial organization administrator securely in production.
Obtains credentials strictly from environment variables.
Never logs or exposes plaintext passwords.
Guarantees duplicate administrator protection and one-time provisioning.
"""

import argparse
import asyncio
import os
import re
import sys
import uuid
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 - Register all database models
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password, verify_password
from app.domains.audit.services import record_audit_log
from app.domains.auth.models import User, UserRole

# Weak or known default development passwords that are strictly prohibited in production
PROHIBITED_PASSWORDS = {
    "securepass123!",
    "password",
    "password123",
    "admin",
    "admin123",
    "changeme",
    "secret",
    "administrator",
    "12345678",
    "1234567890",
}


def validate_password_strength(password: Optional[str]) -> Tuple[bool, str]:
    """Validates that the bootstrap password satisfies production strength requirements."""
    if not password:
        return False, "Bootstrap password is required. Please set BOOTSTRAP_ADMIN_PASSWORD."
    if password.lower() in PROHIBITED_PASSWORDS:
        return False, "Insecure or known default development password is not permitted in production."
    if len(password) < 12:
        return False, "Bootstrap password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Bootstrap password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Bootstrap password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Bootstrap password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Bootstrap password must contain at least one special character."
    return True, ""


async def bootstrap_administrator(
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    password: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> Tuple[bool, str]:
    """
    Executes production administrator provisioning.
    Returns (success: bool, message: str).
    """
    admin_email = (email or os.environ.get("BOOTSTRAP_ADMIN_EMAIL") or "admin@vana.earth").strip().lower()
    admin_name = (full_name or os.environ.get("BOOTSTRAP_ADMIN_NAME") or "System Administrator").strip()
    admin_pw = password if password is not None else os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")

    # 1. Validate password strength
    is_valid, err_msg = validate_password_strength(admin_pw)
    if not is_valid:
        return False, f"VALIDATION_FAILED: {err_msg}"

    # Use supplied session or create a new session
    async def _provision(s: AsyncSession) -> Tuple[bool, str]:
        try:
            # 2. Refuse to run if a production administrator already exists in the system (even with a different email)
            existing_admin = await s.scalar(
                select(User).where(User.role == UserRole.ADMIN.value)
            )
            if existing_admin:
                return False, (
                    "BOOTSTRAP_ALREADY_COMPLETED: A production administrator already exists. "
                    "The bootstrap CLI is strictly for initial setup and cannot be used to provision additional administrators."
                )

            # 3. Check for duplicate account by email (refuse to overwrite existing account)
            existing_user = await s.scalar(
                select(User).where(User.email == admin_email)
            )
            if existing_user:
                return False, f"DUPLICATE_PROHIBITED: User with email '{admin_email}' already exists. Refusing to overwrite."

            # 4. Hash password with Argon2id (never store or log plaintext)
            hashed = hash_password(admin_pw)

            # 5. Create administrator user record
            admin_user = User(
                id=uuid.uuid4(),
                email=admin_email,
                hashed_password=hashed,
                full_name=admin_name,
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            s.add(admin_user)
            await s.flush()

            # 6. Record immutable audit event with traceable system actor
            await record_audit_log(
                db=s,
                action_type="USER_PROVISIONED",
                entity_type="user",
                entity_id=admin_user.id,
                actor_id=admin_user.id,
                new_state={
                    "email": admin_email,
                    "full_name": admin_name,
                    "role": UserRole.ADMIN.value,
                    "is_active": True,
                    "is_bootstrap": True,
                },
            )
            await s.commit()
            return True, f"SUCCESS: Production administrator '{admin_email}' provisioned successfully."
        except Exception:
            await s.rollback()
            raise

    if session:
        return await _provision(session)
    else:
        async with AsyncSessionLocal() as s:
            return await _provision(s)


def main():
    """CLI entrypoint for `python -m app.bootstrap_admin`."""
    parser = argparse.ArgumentParser(
        description="VANA Secure Production Administrator Bootstrap Command",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--email",
        type=str,
        default=os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@vana.earth"),
        help="Administrator email address",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=os.environ.get("BOOTSTRAP_ADMIN_NAME", "System Administrator"),
        help="Administrator full name",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("VANA — Production Administrator Bootstrap")
    print("=" * 70)

    try:
        success, message = asyncio.run(
            bootstrap_administrator(email=args.email, full_name=args.name)
        )
        if success:
            print(f"\n[OK] {message}")
            print("\nSECURITY INSTRUCTION:")
            print("  Please immediately remove or unset the BOOTSTRAP_ADMIN_PASSWORD environment")
            print("  variable from your hosting provider (Render Dashboard) to prevent credential leakage.")
            print("=" * 70)
            sys.exit(0)
        else:
            print(f"\n[ERROR] {message}")
            print("=" * 70)
            sys.exit(1)
    except Exception as exc:
        print(f"\n[FATAL] Bootstrap failed: {exc}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
