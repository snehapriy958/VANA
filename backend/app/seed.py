"""
VANA Database Seed Script
Populates the local database with initial admin, project manager, field officer,
sample projects, targets, assignments, and initial field activities.
"""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy import select
import app.models  # noqa: F401 - Register all domain models
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment, ProjectRole
from app.domains.operations.models import (
    ActivityRevision,
    ActivityStatus,
    FieldActivity,
)


async def seed():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(User).filter_by(email="admin@vana.earth"))
        if result.scalar_one_or_none():
            print("Database already contains seed users. Skipping seeding.")
            return

        print("Seeding VANA development database...")

        # 1. Users
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@vana.earth",
            hashed_password=hash_password("SecurePass123!"),
            full_name="Dr. Sunita Sharma",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        pm_user = User(
            id=uuid.uuid4(),
            email="pm.rajesh@vana.earth",
            hashed_password=hash_password("SecurePass123!"),
            full_name="Rajesh Kumar",
            role=UserRole.PROJECT_MANAGER.value,
            is_active=True,
        )
        fo_user = User(
            id=uuid.uuid4(),
            email="fo.aarav@vana.earth",
            hashed_password=hash_password("SecurePass123!"),
            full_name="Aarav Patel",
            role=UserRole.FIELD_OFFICER.value,
            is_active=True,
        )

        session.add_all([admin_user, pm_user, fo_user])
        await session.flush()

        # 2. Projects
        p1 = Project(
            id=uuid.uuid4(),
            name="Kaveri Basin Agroforestry Restoration",
            code="PRJ-KA-001",
            description="Native species reforestation and soil conservation in the upper Kaveri river basin.",
            status=ProjectStatus.ACTIVE.value,
            latitude=12.2958,
            longitude=76.6394,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.630, 12.290],
                        [76.650, 12.290],
                        [76.650, 12.305],
                        [76.630, 12.305],
                        [76.630, 12.290],
                    ]
                ],
            },
        )
        p2 = Project(
            id=uuid.uuid4(),
            name="Western Ghats High-Elevation Corridor",
            code="PRJ-MH-002",
            description="Riparian ecological buffer restoration and evergreen canopy rehabilitation.",
            status=ProjectStatus.ACTIVE.value,
            latitude=18.9220,
            longitude=73.5562,
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [
                    [
                        [73.540, 18.910],
                        [73.570, 18.910],
                        [73.570, 18.935],
                        [73.540, 18.935],
                        [73.540, 18.910],
                    ]
                ],
            },
        )

        session.add_all([p1, p2])
        await session.flush()

        # 3. Project Targets
        t1_trees = ProjectTarget(
            id=uuid.uuid4(),
            project_id=p1.id,
            metric_code="TREES_PLANTED",
            target_quantity=Decimal("10000.00"),
            target_unit="trees",
            target_date=date(2026, 12, 31),
        )
        t1_hectares = ProjectTarget(
            id=uuid.uuid4(),
            project_id=p1.id,
            metric_code="AREA_RESTORED",
            target_quantity=Decimal("50.00"),
            target_unit="hectares",
            target_date=date(2026, 12, 31),
        )
        t2_trees = ProjectTarget(
            id=uuid.uuid4(),
            project_id=p2.id,
            metric_code="TREES_PLANTED",
            target_quantity=Decimal("5000.00"),
            target_unit="trees",
            target_date=date(2027, 6, 30),
        )

        session.add_all([t1_trees, t1_hectares, t2_trees])
        await session.flush()

        # 4. Project Assignments
        assign_p1_pm = ProjectAssignment(
            id=uuid.uuid4(),
            project_id=p1.id,
            user_id=pm_user.id,
            assigned_role=ProjectRole.PROJECT_MANAGER.value,
        )
        assign_p1_fo = ProjectAssignment(
            id=uuid.uuid4(),
            project_id=p1.id,
            user_id=fo_user.id,
            assigned_role=ProjectRole.FIELD_OFFICER.value,
        )
        assign_p2_pm = ProjectAssignment(
            id=uuid.uuid4(),
            project_id=p2.id,
            user_id=pm_user.id,
            assigned_role=ProjectRole.PROJECT_MANAGER.value,
        )
        assign_p2_fo = ProjectAssignment(
            id=uuid.uuid4(),
            project_id=p2.id,
            user_id=fo_user.id,
            assigned_role=ProjectRole.FIELD_OFFICER.value,
        )

        session.add_all([assign_p1_pm, assign_p1_fo, assign_p2_pm, assign_p2_fo])
        await session.flush()

        # 5. Field Activities with Revisions
        # Activity 1: Verified (2,500 trees)
        act1 = FieldActivity(
            id=uuid.uuid4(),
            project_id=p1.id,
            created_by_id=fo_user.id,
            metric_code="TREES_PLANTED",
            unit="trees",
            is_archived=False,
        )
        session.add(act1)
        await session.flush()

        rev1 = ActivityRevision(
            id=uuid.uuid4(),
            activity_id=act1.id,
            revision_number=1,
            quantity=Decimal("2500.00"),
            activity_date=date(2026, 10, 15),
            latitude=12.2960,
            longitude=76.6400,
            gps_accuracy_meters=4.5,
            field_notes="Batch 1 native teak and sandalwood saplings planted along riparian buffer.",
            status=ActivityStatus.VERIFIED.value,
            is_active_ledger_entry=True,
            verifier_id=pm_user.id,
            verified_at=datetime.now(timezone.utc),
        )
        session.add(rev1)
        act1.current_revision_id = rev1.id
        await session.flush()

        # Activity 2: Pending (750 trees)
        act2 = FieldActivity(
            id=uuid.uuid4(),
            project_id=p1.id,
            created_by_id=fo_user.id,
            metric_code="TREES_PLANTED",
            unit="trees",
            is_archived=False,
        )
        session.add(act2)
        await session.flush()

        rev2 = ActivityRevision(
            id=uuid.uuid4(),
            activity_id=act2.id,
            revision_number=1,
            quantity=Decimal("750.00"),
            activity_date=date(2026, 11, 1),
            latitude=12.2975,
            longitude=76.6420,
            gps_accuracy_meters=5.0,
            field_notes="Batch 2 fruit-bearing and shade saplings planted in agroforestry plot.",
            status=ActivityStatus.PENDING.value,
            is_active_ledger_entry=False,
        )
        session.add(rev2)
        act2.current_revision_id = rev2.id
        await session.flush()

        # Activity 3: Verified on Project 2 (1,200 trees)
        act3 = FieldActivity(
            id=uuid.uuid4(),
            project_id=p2.id,
            created_by_id=fo_user.id,
            metric_code="TREES_PLANTED",
            unit="trees",
            is_archived=False,
        )
        session.add(act3)
        await session.flush()

        rev3 = ActivityRevision(
            id=uuid.uuid4(),
            activity_id=act3.id,
            revision_number=1,
            quantity=Decimal("1200.00"),
            activity_date=date(2026, 10, 20),
            latitude=18.9230,
            longitude=73.5570,
            gps_accuracy_meters=3.8,
            field_notes="Canopy rehabilitation saplings planted in buffer zone.",
            status=ActivityStatus.VERIFIED.value,
            is_active_ledger_entry=True,
            verifier_id=pm_user.id,
            verified_at=datetime.now(timezone.utc),
        )
        session.add(rev3)
        act3.current_revision_id = rev3.id
        await session.flush()

        await session.commit()
        print("Database seeded successfully with users, projects, targets, and activities!")


if __name__ == "__main__":
    asyncio.run(seed())
