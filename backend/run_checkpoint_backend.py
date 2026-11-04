"""
VANA — Local Checkpoint Database Test Launcher
Runs the VANA FastAPI application targeting a Neon branch checkpoint (e.g. pre-vana-data-recovery)
on local port 8001 without altering .env, production settings, or the primary database.
"""

import getpass
import os
import sys
from urllib.parse import urlsplit


def validate_neon_uri(uri: str) -> str:
    """
    Validates the connection URI according to strict security and architectural requirements:
    1. Rejects empty or whitespace-only inputs.
    2. Scheme must be 'postgresql' or 'postgres'.
    3. Host must end with '.neon.tech'.
    4. Database path must be '/neondb'.

    Returns the stripped URI if valid.
    Raises ValueError with a sanitized error message (never exposing credentials) if invalid.
    """
    if not uri or not isinstance(uri, str):
        raise ValueError("Connection URI cannot be empty.")

    clean_uri = uri.strip()
    if not clean_uri:
        raise ValueError("Connection URI cannot be blank.")

    try:
        parsed = urlsplit(clean_uri)
    except Exception as exc:
        raise ValueError(f"Malformed connection URI syntax: {exc}")

    # 1. Scheme validation: must be postgresql or postgres
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("postgresql", "postgres"):
        raise ValueError(
            f"Invalid URI scheme '{scheme}'. Scheme must be 'postgresql' or 'postgres'."
        )

    # 2. Host validation: must end with .neon.tech
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Connection URI is missing a hostname.")
    if not hostname.endswith(".neon.tech"):
        raise ValueError(
            "Invalid host. Host must target a Neon branch ending with '.neon.tech'."
        )

    # 3. Database path validation: must be /neondb
    path = (parsed.path or "").strip()
    if path.rstrip("/") != "/neondb":
        raise ValueError(
            f"Invalid database path '{path}'. Database path must be '/neondb'."
        )

    return clean_uri


def main() -> None:
    print("=" * 70)
    print(" VANA — Neon Checkpoint Database Local Launcher")
    print(" Target Branch: pre-vana-data-recovery")
    print(" Target Port:   http://127.0.0.1:8001")
    print("=" * 70)
    print()

    # 1. Prompt securely using getpass (never echoes input, never logs credentials)
    try:
        raw_uri = getpass.getpass("Enter Neon PostgreSQL connection URI (hidden): ")
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Operation cancelled by user.")
        sys.exit(0)

    # 2. Validate URI against required rules
    try:
        validated_uri = validate_neon_uri(raw_uri)
    except ValueError as err:
        print(f"\n[ERROR] Validation failed: {err}")
        print("[HINT] Expected format: postgresql://user:pass@ep-branch-xyz.region.aws.neon.tech/neondb?sslmode=require")
        sys.exit(1)

    # 3. Set process-isolated environment variables
    os.environ["DATABASE_URL"] = validated_uri
    os.environ["ENVIRONMENT"] = "development"
    os.environ["CORS_ORIGINS"] = '["http://localhost:5173","http://127.0.0.1:5173"]'

    # Ensure backend directory is in sys.path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    print("\n[INFO] Connection URI validated successfully (*.neon.tech / neondb).")
    print("[INFO] ENVIRONMENT set to 'development'.")
    print("[INFO] CORS_ORIGINS configured: ['http://localhost:5173', 'http://127.0.0.1:5173'].")
    print("[INFO] Starting FastAPI application on http://127.0.0.1:8001...")
    print("[INFO] Press CTRL+C to terminate.")
    print("-" * 70)

    # 4. Start existing application using uvicorn
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="info")


if __name__ == "__main__":
    main()
