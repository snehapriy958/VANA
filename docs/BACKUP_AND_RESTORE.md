# VANA — Database and Evidence Backup & Disaster Recovery Guide

> **Platform:** VANA Environmental Operations Platform\
> **Authoritative System of Record:** PostgreSQL 17 (Neon Cloud / Self-Hosted)\
> **Storage Layer:** Content-Addressed File Storage (Persistent Disk / S3 Object Storage)\
> **Date:** November 4, 2026

---

## 1. Overview & Recovery Objectives

VANA maintains an immutable environmental achievement ledger and a cryptographically chained audit log. Disaster recovery must satisfy:
- **RPO (Recovery Point Objective):** $\le 1$ hour for application transactions.
- **RTO (Recovery Time Objective):** $\le 30$ minutes to restore service.
- **Cryptographic Continuity:** Ledger chain sequence numbers and SHA-256 hashes must remain gapless post-recovery.

---

## 2. Neon PostgreSQL Backup & Branching

Neon provides automated continuous backups and instant branching:

### 2.1 Automated Continuous Backups
- Neon automatically creates continuous point-in-time backups (PITR) with retention based on project tier (up to 30 days on paid tiers).
- Any point in time can be restored within seconds by creating a new database branch.

### 2.2 Point-in-Time Restoration via Branching
1. In the Neon Console, navigate to **Branches**.
2. Click **Create Branch**.
3. Choose **Point in Time** and select the timestamp immediately preceding the disaster event.
4. Name the recovery branch: `vana-recovery-YYYYMMDD`.
5. Update `DATABASE_URL` and `ALEMBIC_DATABASE_URL` in Render environment variables to point to the new branch endpoint.
6. Trigger Render service restart.

### 2.3 Manual Logical Database Backup (`pg_dump`)
For periodic offline archive snapshots:

```bash
# Dump the complete database schema and data in compressed directory format
pg_dump "postgresql://vana_user:SECRET@ep-direct-xyz.neon.tech/neondb?sslmode=require" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file=vana_backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup archive integrity
pg_restore --list vana_backup_*.dump > /dev/null
echo "Backup verification complete."
```

### 2.4 Logical Database Restore (`pg_restore`)
To restore a logical backup to a clean PostgreSQL instance:

```bash
# Restore schema and data into target database
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="postgresql://vana_user:SECRET@ep-direct-xyz.neon.tech/neondb?sslmode=require" \
  vana_backup_20261104_120000.dump
```

---

## 3. Render Persistent Disk & Evidence Backup

Photo evidence files are stored with content-addressed SHA-256 filenames under `/var/data/uploads`.

### 3.1 Persistent Disk Snapshotting
1. In Render Dashboard, navigate to **Disks** $\to$ `vana-evidence-disk`.
2. Render automatically maintains daily snapshots of attached disks.
3. To recover an accidental file deletion, mount the latest disk snapshot to a staging web service.

### 3.2 Evidence File Archival via Render Shell
To archive evidence files to secure cloud object storage (e.g., AWS S3):

```bash
# Execute from Render Web Shell
tar -czvf /tmp/vana_evidence_$(date +%Y%m%d).tar.gz /var/data/uploads

# Upload archive to private AWS S3 bucket (if AWS CLI configured)
# aws s3 cp /tmp/vana_evidence_*.tar.gz s3://vana-backups-archive/
```

### 3.3 Evidence Restoration
```bash
# Extract archive back to upload directory
tar -xzvf vana_evidence_20261104.tar.gz -C /var/data/
```

---

## 4. Post-Restoration Integrity Verification Runbook

Immediately after restoring database or disk state:

1. **Verify Database Connection:**
   ```bash
   curl -s https://vana-backend.onrender.com/health | jq .
   ```
   Must return `{"status": "healthy", "database": "connected"}`.

2. **Verify Alembic Revision:**
   ```bash
   alembic current
   ```
   Must match `0003_audit_immutability_ledger (head)`.

3. **Execute Full Cryptographic Ledger Verification:**
   - Run verification via REST API or Frontend Console (`/audit` $\to$ **Integrity Console**).
   - Alternatively, execute backend verification script:
     ```python
     python -c "
     import asyncio
     from app.core.database import AsyncSessionLocal
     from app.domains.audit.services import verify_audit_chain
     async def check():
         async with AsyncSessionLocal() as db:
             res = await verify_audit_chain(db)
             print('Verification Status:', res.status, 'Total Events:', res.total_events)
     asyncio.run(check())
     "
     ```
   - Must output: `Verification Status: VALID`.
