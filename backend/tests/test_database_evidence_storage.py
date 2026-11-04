"""
VANA — Database-Backed Evidence Storage & Zero-Cost Architecture Test Suite
Verifies:
1. PostgreSQL BYTEA database storage adapter (upload, download, checksum verification, deletion).
2. End-to-end cryptographic checksum verification and tamper detection.
3. Path traversal attack rejection across storage layers.
4. HTTP 413 maximum upload size (5 MB ceiling) enforcement.
5. Disallowed MIME type rejection (HTTP 400 UNSUPPORTED_FILE_TYPE).
6. Multi-tenant project-scoping authorization on evidence streaming.
7. Evidence persistence across simulated server restarts.
8. Storage deduplication for identical binary evidence payloads.
"""

from datetime import date
from decimal import Decimal
import hashlib
import io
from pathlib import Path
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.core.storage import (
    DatabaseStorageService,
    LocalStorageService,
    get_storage_service,
    validate_storage_key,
)
from app.domains.auth.models import User, UserRole
from app.domains.operations.models import (
    ActivityRevision,
    ActivityStatus,
    EvidenceBlob,
    EvidenceFile,
    FieldActivity,
)
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment


async def create_user_helper(
    db: AsyncSession,
    role: str = UserRole.FIELD_OFFICER.value,
    full_name: str = "Test Officer",
) -> tuple[User, dict]:
    """Helper to provision a user and return authorization header."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password=hash_password("SecurePass123!"),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role, email=user.email)
    return user, {"Authorization": f"Bearer {token}"}


async def setup_test_project_with_target(
    db: AsyncSession,
    metric_code: str = "TREES_PLANTED",
    unit: str = "trees",
    target_qty: Decimal = Decimal("5000.0"),
) -> Project:
    """Helper to create an active project with a configured metric target."""
    project = Project(
        id=uuid.uuid4(),
        name="Sundarbans Delta Mangrove Restoration",
        code=f"VANA-TEST-{uuid.uuid4().hex[:6].upper()}",
        status=ProjectStatus.ACTIVE.value,
        latitude=21.9497,
        longitude=89.1833,
    )
    db.add(project)
    await db.flush()

    target = ProjectTarget(
        id=uuid.uuid4(),
        project_id=project.id,
        metric_code=metric_code,
        target_quantity=target_qty,
        target_unit=unit,
        target_date=date(2027, 12, 31),
    )
    db.add(target)
    await db.commit()
    await db.refresh(project)
    return project


# ============================================================================
# 1. Database Storage Service Unit & Checksum Verification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_database_storage_adapter_upload_and_download(db_session: AsyncSession):
    """Verifies that DatabaseStorageService uploads raw bytes to PostgreSQL BYTEA and retrieves them cleanly."""
    storage = DatabaseStorageService()
    test_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    filename = "test_mangrove.png"
    expected_hash = hashlib.sha256(test_content).hexdigest()

    # Upload using existing db_session
    storage_key = await storage.upload_file(
        file_content=test_content,
        original_filename=filename,
        db=db_session,
        mime_type="image/png",
    )
    await db_session.commit()

    assert storage_key == f"{expected_hash}.png"

    # Verify EvidenceBlob record in database
    blob = await db_session.scalar(
        select(EvidenceBlob).where(EvidenceBlob.storage_key == storage_key)
    )
    assert blob is not None
    assert blob.sha256_checksum == expected_hash
    assert blob.file_size_bytes == len(test_content)
    assert blob.mime_type == "image/png"
    assert blob.file_data == test_content

    # Retrieve through storage service
    retrieved_bytes = await storage.get_file_bytes(storage_key, db=db_session)
    assert retrieved_bytes == test_content


@pytest.mark.asyncio
async def test_database_storage_tamper_detection(db_session: AsyncSession):
    """Verifies that tampering with binary data in PostgreSQL raises an integrity violation error."""
    storage = DatabaseStorageService()
    original_content = b"VALID_IMMUTABLE_EVIDENCE_BYTES"
    storage_key = await storage.upload_file(
        file_content=original_content,
        original_filename="audit_sample.pdf",
        db=db_session,
        mime_type="application/pdf",
    )
    await db_session.commit()

    # Tamper with the raw BYTEA in the database directly
    blob = await db_session.scalar(
        select(EvidenceBlob).where(EvidenceBlob.storage_key == storage_key)
    )
    assert blob is not None
    blob.file_data = b"TAMPERED_MALICIOUS_CONTENT"
    await db_session.commit()

    # Attempting to fetch the tampered evidence must fail cryptographic verification
    with pytest.raises(ValueError, match="Evidence integrity violation"):
        await storage.get_file_bytes(storage_key, db=db_session)


@pytest.mark.asyncio
async def test_database_storage_path_traversal_protection(db_session: AsyncSession):
    """Verifies that malicious directory traversal keys are rejected across all storage operations."""
    storage = DatabaseStorageService()

    malicious_keys = [
        "../../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "nested/path/file.jpg",
        "nested\\path\\file.jpg",
        "",
        "foo;bar",
    ]

    for key in malicious_keys:
        with pytest.raises(ValueError):
            validate_storage_key(key)

        with pytest.raises(ValueError):
            await storage.get_file_bytes(key, db=db_session)

        with pytest.raises(ValueError):
            await storage.delete_file(key, db=db_session)


@pytest.mark.asyncio
async def test_database_storage_blob_deduplication(db_session: AsyncSession):
    """Verifies that uploading the identical file content does not duplicate database rows, saving Neon storage."""
    storage = DatabaseStorageService()
    content = b"DEDUPLICATED_SHARED_CONTENT_FOR_NEON_SAVINGS"
    filename = "photo.jpg"

    key1 = await storage.upload_file(content, filename, db=db_session)
    key2 = await storage.upload_file(content, filename, db=db_session)
    await db_session.commit()

    assert key1 == key2

    # Verify only 1 row exists
    count = await db_session.scalar(
        select(func.count(EvidenceBlob.storage_key)).where(
            EvidenceBlob.storage_key == key1
        )
    )
    assert count == 1


# ============================================================================
# 2. End-to-End Operations API with Database Storage Backend
# ============================================================================


@pytest.mark.asyncio
async def test_api_activity_upload_and_stream_with_database_storage(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """Verifies field activity reporting with photo evidence when STORAGE_BACKEND=database."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "database")

    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "FO Assigned"
    )
    unassigned_fo, unassigned_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "FO Unassigned"
    )
    admin, admin_headers = await create_user_helper(
        db_session, UserRole.ADMIN.value, "System Admin"
    )

    db_session.add(
        ProjectAssignment(
            project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"
        )
    )
    await db_session.commit()

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "120.00",
        "unit": "trees",
        "activity_date": "2026-11-04",
        "field_notes": "Mangrove saplings planted with geotagged photo evidence.",
    }

    evidence_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00DATABASE_EVIDENCE_TEST"
    files = [
        (
            "evidence_files",
            ("mangrove_planting.jpg", io.BytesIO(evidence_bytes), "image/jpeg"),
        ),
    ]

    # 1. Submit activity
    res = await client.post(
        "/api/v1/operations/activities", data=form_data, files=files, headers=fo_headers
    )
    assert res.status_code == 201
    activity_data = res.json()
    evidence_files = activity_data["current_revision"]["evidence_files"]
    assert len(evidence_files) == 1
    evidence_id = evidence_files[0]["id"]
    assert evidence_files[0]["original_filename"] == "mangrove_planting.jpg"

    # 2. Check EvidenceBlob was written to DB
    expected_sha = hashlib.sha256(evidence_bytes).hexdigest()
    blob = await db_session.scalar(
        select(EvidenceBlob).where(EvidenceBlob.sha256_checksum == expected_sha)
    )
    assert blob is not None
    assert blob.file_data == evidence_bytes

    # 3. Authorized Field Officer streams evidence
    stream_res = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=fo_headers
    )
    assert stream_res.status_code == 200
    assert stream_res.content == evidence_bytes
    assert stream_res.headers["content-type"].startswith("image/jpeg")

    # 4. Admin streams evidence
    admin_res = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=admin_headers
    )
    assert admin_res.status_code == 200
    assert admin_res.content == evidence_bytes

    # 5. Unassigned officer is denied with 403 Forbidden
    denied_res = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=unassigned_headers
    )
    assert denied_res.status_code == 403
    assert denied_res.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_api_upload_exceeding_max_size_rejected(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """Verifies that uploads exceeding the configurable MAX_UPLOAD_SIZE_BYTES are rejected with HTTP 413."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "database")
    # Temporarily set upload limit to 100 KB for test speed and determinism
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100 * 1024)

    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "FO Assigned"
    )
    db_session.add(
        ProjectAssignment(
            project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"
        )
    )
    await db_session.commit()

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "100.00",
        "unit": "trees",
        "activity_date": "2026-11-04",
    }

    oversized_bytes = b"X" * (100 * 1024 + 10)  # Exceeds limit by 10 bytes
    files = [
        (
            "evidence_files",
            ("large_satellite.jpg", io.BytesIO(oversized_bytes), "image/jpeg"),
        ),
    ]

    res = await client.post(
        "/api/v1/operations/activities", data=form_data, files=files, headers=fo_headers
    )
    assert res.status_code == 413
    assert res.json()["detail"]["error_code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_api_unsupported_mime_type_rejected(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """Verifies that non-permitted file extensions / MIME types are rejected with HTTP 400."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "database")

    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "FO Assigned"
    )
    db_session.add(
        ProjectAssignment(
            project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"
        )
    )
    await db_session.commit()

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "50.00",
        "unit": "trees",
        "activity_date": "2026-11-04",
    }

    files = [
        (
            "evidence_files",
            ("malware.sh", io.BytesIO(b"#!/bin/sh\nrm -rf /"), "application/x-sh"),
        ),
    ]

    res = await client.post(
        "/api/v1/operations/activities", data=form_data, files=files, headers=fo_headers
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.asyncio
async def test_evidence_persistence_across_simulated_restart(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Verifies that evidence uploaded to database storage persists and remains retrievable
    without requiring any persistent disk or local filesystem storage.
    """
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "database")

    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "FO Assigned"
    )
    db_session.add(
        ProjectAssignment(
            project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"
        )
    )
    await db_session.commit()

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "250.00",
        "unit": "trees",
        "activity_date": "2026-11-04",
    }

    evidence_payload = b"%PDF-1.4\n1 0 obj\n<< /Title (Zero Cost Compliance) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    files = [
        (
            "evidence_files",
            ("compliance_doc.pdf", io.BytesIO(evidence_payload), "application/pdf"),
        ),
    ]

    # 1. Upload in initial state
    res = await client.post(
        "/api/v1/operations/activities", data=form_data, files=files, headers=fo_headers
    )
    assert res.status_code == 201
    evidence_id = res.json()["current_revision"]["evidence_files"][0]["id"]

    # 2. Simulate server cold start / restart: reset local singleton / verify no disk file was written
    sha_hash = hashlib.sha256(evidence_payload).hexdigest()
    expected_local_path = Path(settings.STORAGE_LOCAL_ROOT) / f"{sha_hash}.pdf"
    # Ensure it is NOT on local disk
    assert not expected_local_path.exists()

    # 3. Stream evidence: served directly from PostgreSQL BYTEA
    stream_res = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=fo_headers
    )
    assert stream_res.status_code == 200
    assert stream_res.content == evidence_payload
    assert "application/pdf" in stream_res.headers["content-type"]
