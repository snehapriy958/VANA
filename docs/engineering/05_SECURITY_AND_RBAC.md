# VANA — Security Architecture & RBAC Specification

This document details the authentication protocols, cryptographic standards, Role-Based Access Control (RBAC), and security gates enforced in VANA.

---

## 1. Authentication & Token Management

### 1.1 Password Hashing: Argon2
User passwords are encrypted using the **Argon2id** algorithm (`argon2-cffi`), conforming to OWASP recommendations:
* **Algorithm:** Argon2id (v=19)
* **Time Cost (iterations):** 3
* **Memory Cost:** 64 MB (`65536` KiB)
* **Parallelism:** 4 lanes
* Plaintext passwords are never logged, persisted, or returned in API responses.

### 1.2 JWT Token Mechanics
VANA utilizes stateless JSON Web Tokens for API session management:
* **Access Token:**
  * **Lifespan:** 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES = 60`).
  * **Claims Payload:** `sub` (User UUID), `email`, `role`, `exp` (Expiry UTC), `iat` (Issued At UTC).
  * **Signing Algorithm:** HMAC-SHA256 (`HS256`) using an environment-configured 256-bit secret.
* **Refresh Token:**
  * **Lifespan:** 7 days (`REFRESH_TOKEN_EXPIRE_DAYS = 7`).
  * **Claims Payload:** `sub` (User UUID), `token_type: "refresh"`, `exp`, `jti` (Unique Token ID).
  * Exchanged at `/api/v1/auth/refresh` to issue a fresh access token without user credentials.

---

## 2. Granular Role-Based Access Control (RBAC)

The platform partitions user privileges into three discrete operational roles:

```
┌────────────────────────────────────────────────────────┐
│  ADMIN (Organization-Wide Scope)                       │
│  └── PROJECT_MANAGER (Assigned Projects Scope)        │
│      └── FIELD_OFFICER (Assigned Projects Scope)       │
└────────────────────────────────────────────────────────┘
```

### 2.1 Capability Permission Matrix

| Operation | ADMIN | PROJECT_MANAGER | FIELD_OFFICER |
|---|:---:|:---:|:---:|
| User Provisioning & Role Modification | **ALLOW** | DENY (403) | DENY (403) |
| Project Creation & Deletion | **ALLOW** | DENY (403) | DENY (403) |
| Update Project Targets & Metadata | **ALLOW** | ALLOW (Assigned Only) | DENY (403) |
| Assign Personnel to Projects | **ALLOW** | ALLOW (Assigned Only) | DENY (403) |
| Submit Field Activity Reports | **ALLOW** | ALLOW (Assigned Only) | ALLOW (Assigned Only) |
| Verify / Reject Field Activities | **ALLOW** (Non-Self) | ALLOW (Assigned & Non-Self) | DENY (403) |
| View System Audit History | **ALLOW** | DENY (403) | DENY (403) |

---

## 3. Independent Backend Authorization Implementation

Frontend UI button states and route guards are strictly for user experience. The FastAPI backend validates authentication, roles, and project ownership independently via Python dependencies.

```python
# Conceptual FastAPI Dependency Implementation
async def require_project_manager_access(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> None:
    if current_user.role == "ADMIN":
        return  # Admins possess organization-wide authority

    if current_user.role != "PROJECT_MANAGER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "INSUFFICIENT_ROLE", "message": "Project Manager role required."}
        )

    # Verify project assignment
    assignment = await db.scalar(
        select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == current_user.id
        )
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "PROJECT_NOT_ASSIGNED", "message": "You are not assigned to this project."}
        )
```

---

## 4. The Anti-Self-Verification Gate

A critical compliance invariant in VANA is that **no user may verify their own submission**, preventing collusion and conflict of interest.

```python
async def enforce_anti_self_verification(
    activity: FieldActivity,
    current_user: User
) -> None:
    if activity.created_by_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "SELF_VERIFICATION_PROHIBITED",
                "message": "Policy Violation: You cannot verify an activity submission you authored."
            }
        )
```

---

## 5. Evidence File Upload Security & Access Control

1. **Storage Path Virtualization:**
   * User-submitted filenames are discarded. Files are stored using cryptographic SHA-256 hashes of content: `/uploads/{sha256_hash}.{ext}`.
2. **MIME Type Whitelisting:**
   * Only validated image MIME types are permitted: `image/jpeg`, `image/png`, `image/webp`. Executables and SVG files are rejected.
3. **Payload Size Bounds:**
   * Maximum upload size per file is capped at $10\text{ MB}$.
4. **Access Control:**
   * File endpoints verify that the requesting user is authenticated and holds project assignment rights before streaming image bytes.
