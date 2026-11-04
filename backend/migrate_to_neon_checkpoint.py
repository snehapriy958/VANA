import asyncio
import argparse
import getpass
import sys
from urllib.parse import urlsplit, unquote

import asyncpg

SOURCE = {
    "host": "127.0.0.1",
    "port": 15432,
    "user": "postgres",
    "database": "vana_dev",
}

LOCAL_ADMIN_ID = "0f1299ac-0542-462f-9d19-e2ec97a22854"
NEON_ADMIN_ID = "3f669fa5-e053-4eb4-b1ad-ec205a1dc811"
ADMIN_EMAIL = "admin@vana.earth"

TABLES = [
    "users",
    "projects",
    "project_targets",
    "project_assignments",
    "field_activities",
    "activity_revisions",
    "field_inspections",
    "maintenance_tasks",
    "survival_observations",
    "evidence_files",
]

EXPECTED_SOURCE = {
    "users": 3,
    "projects": 9,
    "project_targets": 15,
    "project_assignments": 14,
    "field_activities": 18,
    "activity_revisions": 22,
    "field_inspections": 1,
    "maintenance_tasks": 1,
    "survival_observations": 2,
    "evidence_files": 4,
}

EXPECTED_TARGET = {
    "users": 1,
    "projects": 0,
    "project_targets": 0,
    "project_assignments": 0,
    "field_activities": 0,
    "activity_revisions": 0,
    "field_inspections": 0,
    "maintenance_tasks": 0,
    "survival_observations": 0,
    "evidence_files": 0,
    "evidence_blobs": 0,
    "audit_logs": 14,
    "audit_chain_head": 1,
}

def parse_neon_uri(uri):
    parsed = urlsplit(uri)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError("Expected a PostgreSQL connection URI.")
    if not parsed.hostname or not parsed.username or not parsed.path:
        raise ValueError("Incomplete PostgreSQL connection URI.")
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/"),
        "ssl": "require",
        "server_settings": {
            "application_name": "VANA-checkpoint-migration"
        },
    }

async def count_table(conn, table):
    return await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')

async def get_rows(conn, table):
    return [dict(row) for row in await conn.fetch(f'SELECT * FROM "{table}"')]

async def insert_rows(conn, table, rows, overrides=None):
    if not rows:
        return

    overrides = overrides or {}
    columns = list(rows[0].keys())
    quoted = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(
        f"${i}" for i in range(1, len(columns) + 1)
    )
    sql = f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})'

    values = []
    for row in rows:
        item = []
        for column in columns:
            value = overrides.get((str(row["id"]), column), row[column])
            item.append(value)
        values.append(tuple(item))

    await conn.executemany(sql, values)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit migration instead of rolling back dry run."
    )
    args = parser.parse_args()

    print("\nVANA checkpoint data migration")
    print("Target branch must be pre-vana-data-recovery.")
    print("Production must NOT be used here.\n")

    branch = input("Type the target branch name exactly: ").strip()
    if branch != "pre-vana-data-recovery":
        raise RuntimeError("Branch confirmation failed. No migration.")

    uri = getpass.getpass(
        "Paste the Neon CHECKPOINT PostgreSQL connection URI (hidden): "
    )
    target_config = parse_neon_uri(uri)

    if not target_config["host"].lower().endswith(".neon.tech"):
        raise RuntimeError("Target host is not a Neon hostname. Stopped.")
    if target_config["database"] != "neondb":
        raise RuntimeError("Target database is not neondb. Stopped.")

    if args.apply:
        confirmation = input(
            "Type APPLY TO pre-vana-data-recovery to commit: "
        ).strip()
        if confirmation != "APPLY TO pre-vana-data-recovery":
            raise RuntimeError("Apply confirmation failed. No migration.")

    source = await asyncpg.connect(**SOURCE)
    target = await asyncpg.connect(**target_config)

    try:
        print("\nConnected to source and target.")

        # Verify local source identity and expected counts.
        source_users = await get_rows(source, "users")
        source_user_by_email = {
            row["email"].lower(): row for row in source_users
        }

        local_admin = source_user_by_email.get(ADMIN_EMAIL)
        if not local_admin:
            raise RuntimeError("Local admin account not found.")

        if str(local_admin["id"]) != LOCAL_ADMIN_ID:
            raise RuntimeError("Unexpected local admin UUID.")

        for email in ("fo.aarav@vana.earth", "pm.rajesh@vana.earth"):
            if email not in source_user_by_email:
                raise RuntimeError(f"Missing expected source user: {email}")

        print("\nSOURCE COUNTS")
        for table, expected in EXPECTED_SOURCE.items():
            actual = await count_table(source, table)
            print(f"{table}: {actual}")
            if actual != expected:
                raise RuntimeError(
                    f"Source count mismatch for {table}: "
                    f"expected {expected}, got {actual}"
                )

        # Verify target baseline before any write.
        print("\nCHECKPOINT BASELINE")
        for table, expected in EXPECTED_TARGET.items():
            actual = await count_table(target, table)
            print(f"{table}: {actual}")
            if actual != expected:
                raise RuntimeError(
                    f"Checkpoint baseline mismatch for {table}: "
                    f"expected {expected}, got {actual}"
                )

        admin = await target.fetch(
            "SELECT id, email, role FROM users WHERE lower(email) = $1",
            ADMIN_EMAIL,
        )
        if len(admin) != 1:
            raise RuntimeError("Expected exactly one Neon admin.")
        if str(admin[0]["id"]) != NEON_ADMIN_ID or admin[0]["role"] != "ADMIN":
            raise RuntimeError("Neon admin identity mismatch.")

        # Read all source rows before opening the target transaction.
        data = {
            table: await get_rows(source, table)
            for table in TABLES
        }

        # Use the existing target admin UUID for all user references.
        # Preserve non-admin user UUIDs.
        admin_uuid = admin[0]["id"]
        for table, rows in data.items():
            for row in rows:
                for column in (
                    "id", "created_by_id", "verifier_id",
                    "assigned_to_id", "user_id"
                ):
                    if column in row and row[column] is not None:
                        if str(row[column]) == LOCAL_ADMIN_ID:
                            row[column] = admin_uuid

        # Never replace the existing Neon admin row.
        data["users"] = [
            row for row in data["users"]
            if row["email"].lower() != ADMIN_EMAIL
        ]

        # Break circular references for a safe insertion order.
        activity_current_revisions = {
            str(row["id"]): row["current_revision_id"]
            for row in data["field_activities"]
        }
        for row in data["field_activities"]:
            row["current_revision_id"] = None

        survival_superseded = {
            str(row["id"]): row["superseded_by_id"]
            for row in data["survival_observations"]
        }
        for row in data["survival_observations"]:
            row["superseded_by_id"] = None

        async with target.transaction():
            print("\nINSERTING CHECKPOINT DATA")

            for table in TABLES:
                rows = data[table]
                await insert_rows(target, table, rows)
                print(f"Inserted {len(rows)} rows into {table}")

            # Restore activity -> current revision references.
            for activity_id, revision_id in activity_current_revisions.items():
                if revision_id is not None:
                    await target.execute(
                        """
                        UPDATE field_activities
                        SET current_revision_id = $1
                        WHERE id = $2
                        """,
                        revision_id, activity_id
                    )

            # Restore survival-observation self references.
            for observation_id, superseded_id in survival_superseded.items():
                if superseded_id is not None:
                    await target.execute(
                        """
                        UPDATE survival_observations
                        SET superseded_by_id = $1
                        WHERE id = $2
                        """,
                        superseded_id, observation_id
                    )

            print("\nVALIDATING TARGET COUNTS")
            for table, expected in EXPECTED_SOURCE.items():
                expected_target = expected
                actual = await count_table(target, table)
                print(f"{table}: expected {expected_target}, actual {actual}")
                if actual != expected_target:
                    raise RuntimeError(
                        f"Post-insert count mismatch for {table}"
                    )

            # Ensure existing audit history was not modified.
            for table in ("audit_logs", "audit_chain_head", "evidence_blobs"):
                actual = await count_table(target, table)
                expected = EXPECTED_TARGET[table]
                if actual != expected:
                    raise RuntimeError(
                        f"Protected table changed: {table}"
                    )

            if args.apply:
                print("\nCOMMITTING CHECKPOINT MIGRATION")
            else:
                print("\nDRY RUN SUCCESSFUL — ROLLING BACK ALL TARGET WRITES")
                raise DryRunRollback()

    except DryRunRollback:
        print("\nDRY RUN PASSED. No checkpoint data was committed.")
    finally:
        await target.close()
        await source.close()

class DryRunRollback(Exception):
    pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except DryRunRollback:
        pass
    except Exception as exc:
        print(f"\nMIGRATION STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)
