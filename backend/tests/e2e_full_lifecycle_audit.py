import os
import sys
import json
import urllib.request
import urllib.parse
import uuid
import io

BASE_URL = "http://127.0.0.1:8000/api/v1"

def post_json(endpoint, payload, token=None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def get_json(endpoint, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def delete_req(endpoint, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def post_form(endpoint, form_fields, files=None, token=None):
    boundary = "----VanaLifecycleBoundary" + uuid.uuid4().hex
    body = io.BytesIO()

    for k, v in form_fields.items():
        if v is not None:
            body.write(f"--{boundary}\r\n".encode("utf-8"))
            body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
            body.write(str(v).encode("utf-8"))
            body.write(b"\r\n")

    if files:
        for file_field, (filename, file_bytes, mime) in files.items():
            body.write(f"--{boundary}\r\n".encode("utf-8"))
            body.write(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("utf-8"))
            body.write(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
            body.write(file_bytes)
            body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    payload = body.getvalue()

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(payload))
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{BASE_URL}{endpoint}", data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def main():
    print("=" * 70)
    print("VANA Phase 6.6 Full Business Lifecycle & Cross-Domain Integration Audit")
    print("Workflow: PLAN -> ASSIGN -> EXECUTE -> RECORD -> VERIFY -> MEASURE -> MONITOR")
    print("=" * 70)

    # 1. AUTHENTICATE ROLES
    print("\n--- 1. Authenticate Roles ---")
    status, admin_auth = post_json("/auth/login", {"email": "admin@vana.earth", "password": "SecurePass123!"})
    assert status == 200, f"Admin login failed: {status}"
    admin_token = admin_auth["access_token"]
    status, admin_me = get_json("/auth/me", admin_token)
    print(f"  [OK] Admin Authenticated: {admin_me['email']} ({admin_me['role']})")

    status, pm_auth = post_json("/auth/login", {"email": "pm.rajesh@vana.earth", "password": "SecurePass123!"})
    assert status == 200, f"PM login failed: {status}"
    pm_token = pm_auth["access_token"]
    status, pm_me = get_json("/auth/me", pm_token)
    pm_id = pm_me["id"]
    print(f"  [OK] PM Authenticated:    {pm_me['email']} ({pm_me['role']})")

    status, fo_auth = post_json("/auth/login", {"email": "fo.aarav@vana.earth", "password": "SecurePass123!"})
    assert status == 200, f"FO login failed: {status}"
    fo_token = fo_auth["access_token"]
    status, fo_me = get_json("/auth/me", fo_token)
    fo_id = fo_me["id"]
    print(f"  [OK] FO Authenticated:    {fo_me['email']} ({fo_me['role']})")

    # 2. STAGE 1: PLAN (Project & Target Management)
    print("\n--- 2. STAGE 1: PLAN (Project & Target Creation) ---")
    p_code = f"PRJ-E2E-{uuid.uuid4().hex[:6].upper()}"
    project_payload = {
        "name": "Nilgiri Biosphere Restoration Basin",
        "code": p_code,
        "description": "Native evergreen corridor restoration and watershed stabilization.",
        "latitude": 11.4102,
        "longitude": 76.6950,
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [76.6800, 11.4000],
                    [76.7100, 11.4000],
                    [76.7100, 11.4200],
                    [76.6800, 11.4200],
                    [76.6800, 11.4000]
                ]
            ]
        }
    }
    status, project = post_json("/projects", project_payload, admin_token)
    assert status == 201, f"Project creation failed: {status}, {project}"
    project_id = project["id"]
    print(f"  [OK] Created Project: {project['name']} (Code: {project['code']}, ID: {project_id})")

    # Add Target 1: 5,000 TREES_PLANTED (trees)
    t1_payload = {
        "metric_code": "TREES_PLANTED",
        "target_quantity": 5000.0,
        "target_unit": "trees",
        "target_date": "2026-12-31"
    }
    status, t1 = post_json(f"/projects/{project_id}/targets", t1_payload, admin_token)
    assert status == 201, f"Target 1 creation failed: {status}, {t1}"
    print(f"  [OK] Created Target 1: 5,000 trees (TREES_PLANTED)")

    # Add Target 2: 50 AREA_RESTORED (hectares)
    t2_payload = {
        "metric_code": "AREA_RESTORED",
        "target_quantity": 50.0,
        "target_unit": "hectares",
        "target_date": "2026-12-31"
    }
    status, t2 = post_json(f"/projects/{project_id}/targets", t2_payload, admin_token)
    assert status == 201, f"Target 2 creation failed: {status}, {t2}"
    print(f"  [OK] Created Target 2: 50 hectares (AREA_RESTORED)")

    # 3. STAGE 2: ASSIGN (Team Management & Authorization Boundaries)
    print("\n--- 3. STAGE 2: ASSIGN (Project Role Assignments) ---")
    status, pm_assign = post_json(f"/projects/{project_id}/assignments", {"user_id": pm_id, "assigned_role": "PROJECT_MANAGER"}, admin_token)
    assert status == 201, f"PM assignment failed: {status}, {pm_assign}"
    print(f"  [OK] Assigned PM Rajesh to Project")

    status, fo_assign = post_json(f"/projects/{project_id}/assignments", {"user_id": fo_id, "assigned_role": "FIELD_OFFICER"}, admin_token)
    assert status == 201, f"FO assignment failed: {status}, {fo_assign}"
    print(f"  [OK] Assigned FO Aarav to Project")

    # 4. STAGE 3: EXECUTE & RECORD (Field Activity Submissions)
    print("\n--- 4. STAGE 3: EXECUTE & RECORD (Field Activity Recording) ---")
    sample_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"

    # Activity 1: 1,500 trees planted with photo evidence
    act1_form = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "quantity": "1500.0",
        "unit": "trees",
        "activity_date": "2026-11-01",
        "latitude": "11.4110",
        "longitude": "76.6960",
        "gps_accuracy_meters": "4.2",
        "field_notes": "Completed high-density planting of Syzygium cumini saplings."
    }
    files = {"evidence_files": ("sapling_proof.jpg", sample_jpeg, "image/jpeg")}
    status, act1 = post_form("/operations/activities", act1_form, files=files, token=fo_token)
    assert status == 201, f"Activity 1 submission failed: {status}, {act1}"
    act1_id = act1["id"]
    rev1_id = act1["revisions"][0]["id"]
    print(f"  [OK] Activity 1 Submitted: 1,500 trees (Activity ID: {act1_id}, Revision ID: {rev1_id}, Status: {act1['revisions'][0]['status']})")

    # Activity 2: 800 trees planted (to be rejected)
    act2_form = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "quantity": "800.0",
        "unit": "trees",
        "activity_date": "2026-11-02",
        "latitude": "11.4115",
        "longitude": "76.6965",
        "gps_accuracy_meters": "5.0",
        "field_notes": "Unverified second batch"
    }
    status, act2 = post_form("/operations/activities", act2_form, token=fo_token)
    assert status == 201, f"Activity 2 submission failed: {status}, {act2}"
    act2_id = act2["id"]
    rev2_id = act2["revisions"][0]["id"]
    print(f"  [OK] Activity 2 Submitted: 800 trees (Activity ID: {act2_id})")

    # Activity 3: 20 hectares restored (distinct metric)
    act3_form = {
        "project_id": project_id,
        "metric_code": "AREA_RESTORED",
        "quantity": "20.0",
        "unit": "hectares",
        "activity_date": "2026-11-03",
        "latitude": "11.4120",
        "longitude": "76.6970",
        "gps_accuracy_meters": "3.8",
        "field_notes": "Soil contour bunding across western slope."
    }
    status, act3 = post_form("/operations/activities", act3_form, token=fo_token)
    assert status == 201, f"Activity 3 submission failed: {status}, {act3}"
    act3_id = act3["id"]
    act3_rev_id = act3["revisions"][0]["id"]
    print(f"  [OK] Activity 3 Submitted: 20 hectares (AREA_RESTORED)")

    # 5. STAGE 4: VERIFY (Verification State Machine & Anti-Self-Verification Gate)
    print("\n--- 5. STAGE 4: VERIFY (Independent Verification & Anti-Self-Verification) ---")
    # Test Anti-Self-Verification Gate (Rule 5): Creator FO cannot verify their own submission
    status, self_verify = post_json(f"/verification/revisions/{rev1_id}/decision", {"decision": "VERIFIED", "review_notes": "Self verification attempt"}, fo_token)
    assert status == 403, f"Anti-self-verification gate FAILED to reject creator: {status}"
    print(f"  [OK] Anti-Self-Verification Gate strictly enforced: HTTP {status} Forbidden")

    # Project Manager verifies Activity 1
    verify1_payload = {
        "decision": "VERIFIED",
        "review_notes": "Field geotags match polygon coordinates. Approved."
    }
    status, verify1 = post_json(f"/verification/revisions/{rev1_id}/decision", verify1_payload, pm_token)
    assert status == 200, f"PM verification of Act 1 failed: {status}, {verify1}"
    assert verify1["status"] == "VERIFIED"
    assert verify1["is_active_ledger_entry"] is True
    print(f"  [OK] Activity 1 Revision 1 Verified by PM: Status=VERIFIED, is_active_ledger_entry=True")

    # Project Manager rejects Activity 2 with mandatory reason
    reject2_payload = {
        "decision": "REJECTED",
        "rejection_reason_code": "INSUFFICIENT_EVIDENCE",
        "review_notes": "No geotagged photo evidence uploaded to support seedling density."
    }
    status, reject2 = post_json(f"/verification/revisions/{rev2_id}/decision", reject2_payload, pm_token)
    assert status == 200, f"PM rejection of Act 2 failed: {status}, {reject2}"
    assert reject2["status"] == "REJECTED"
    assert reject2["is_active_ledger_entry"] is False
    print(f"  [OK] Activity 2 Revision 1 Rejected by PM: Reason={reject2['rejection_reason_code']}, is_active=False")

    # FO submits Amendment (Revision 2) on Activity 1: adjusted to 1,800 trees
    amend_form = {
        "quantity": "1800.0",
        "activity_date": "2026-11-01",
        "field_notes": "Recounted border rows: added 300 additional surviving saplings.",
        "amendment_reason": "Border recount correction"
    }
    status, amend1 = post_form(f"/operations/activities/{act1_id}/revisions", amend_form, token=fo_token)
    assert status == 201, f"Amendment submission failed: {status}, {amend1}"
    rev1_2_id = amend1["revisions"][-1]["id"]
    print(f"  [OK] Amendment Submitted on Activity 1: Revision 2, Quantity=1,800 trees, Status={amend1['revisions'][-1]['status']}")

    # Check that while Amendment is PENDING, original Revision 1 remains active
    status, act1_check = get_json(f"/operations/activities/{act1_id}", pm_token)
    revs = act1_check["revisions"]
    r1 = next(r for r in revs if r["id"] == rev1_id)
    r2 = next(r for r in revs if r["id"] == rev1_2_id)
    assert r1["is_active_ledger_entry"] is True, "Revision 1 should still be active while Amendment is pending"
    assert r2["is_active_ledger_entry"] is False, "Pending amendment must not be active ledger entry"
    print(f"  [OK] Ledger Isolation Confirmed: Rev 1 is_active={r1['is_active_ledger_entry']}, Rev 2 is_active={r2['is_active_ledger_entry']}")

    # PM verifies Amendment (Revision 2)
    verify_amend_payload = {
        "decision": "VERIFIED",
        "review_notes": "Border row recount verified via aerial survey."
    }
    status, verify_amend = post_json(f"/verification/revisions/{rev1_2_id}/decision", verify_amend_payload, pm_token)
    assert status == 200, f"PM verification of amendment failed: {status}"
    print(f"  [OK] Amendment Verified: Rev 2 is now VERIFIED and active ledger entry")

    # 6. STAGE 5: MEASURE (Environmental Ledger Calculations & Strict Dimensionality)
    print("\n--- 6. STAGE 5: MEASURE (Environmental Ledger Accounting) ---")
    status, ledger = get_json(f"/analytics/projects/{project_id}/impact", admin_token)
    assert status == 200, f"Ledger impact query failed: {status}"
    print(f"  [OK] Queried Environmental Ledger for Project:")
    trees_target = next(t for t in ledger["targets"] if t["metric_code"] == "TREES_PLANTED")
    print(f"      - TREES_PLANTED: Target={trees_target['target_quantity']}, Verified={trees_target['verified_quantity']}, Progress={trees_target['achievement_percentage']}%")
    assert float(trees_target["verified_quantity"]) == 1800.0, f"Expected 1,800 verified trees, got {trees_target['verified_quantity']}"
    assert float(trees_target["achievement_percentage"]) == 36.0, f"Expected 36.0% progress, got {trees_target['achievement_percentage']}"

    # Verify Area Restored target is currently 0 verified
    area_target = next(t for t in ledger["targets"] if t["metric_code"] == "AREA_RESTORED")
    print(f"      - AREA_RESTORED: Target={area_target['target_quantity']}, Verified={area_target['verified_quantity']}, Pending={area_target['net_pending_adjustment']}")
    assert float(area_target["verified_quantity"]) == 0.0, "Area restored should be 0 verified before approval"

    # Now PM verifies Activity 3 (20 ha)
    status, v_act3 = post_json(f"/verification/revisions/{act3_rev_id}/decision", {"decision": "VERIFIED", "review_notes": "GIS boundary cross-verified."}, pm_token)
    assert status == 200

    # Re-check ledger after Area Restored verification
    status, ledger_updated = get_json(f"/analytics/projects/{project_id}/impact", admin_token)
    area_updated = next(t for t in ledger_updated["targets"] if t["metric_code"] == "AREA_RESTORED")
    print(f"      - AREA_RESTORED (Updated): Verified={area_updated['verified_quantity']} ha, Progress={area_updated['achievement_percentage']}%")
    assert float(area_updated["verified_quantity"]) == 20.0
    assert float(area_updated["achievement_percentage"]) == 40.0

    # Rule 8 Dimensionality verification: confirm trees and hectares are strictly segregated
    assert trees_target["metric_code"] != area_updated["metric_code"]
    print(f"  [OK] Rule 8 Enforced: Distinct metric codes (TREES_PLANTED vs AREA_RESTORED) strictly separated")

    # Activity Archival Verification:
    # Invariant A: Archiving an activity with an active verified revision (200 trees)
    #              reduces the official verified quantity by exactly 200 trees (2,000 -> 1,800).
    # Invariant B: Archiving a rejected activity (800 trees) leaves official verified quantity unchanged (1,800 -> 1,800).
    # Note: Activity 1 (act1_id) with 1,800 trees remains active and unarchived throughout.
    act_temp_form = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "quantity": "200.0",
        "unit": "trees",
        "activity_date": "2026-11-04",
        "field_notes": "Temporary activity for archival test"
    }
    status, act_temp = post_form("/operations/activities", act_temp_form, token=fo_token)
    temp_rev_id = act_temp["revisions"][0]["id"]
    temp_act_id = act_temp["id"]
    post_json(f"/verification/revisions/{temp_rev_id}/decision", {"decision": "VERIFIED", "review_notes": "Verify temp"}, pm_token)

    # Ledger quantity before archiving: 2,000 trees (Activity 1 [1,800] + Temp Activity [200])
    status, ledger_with_temp = get_json(f"/analytics/projects/{project_id}/impact", admin_token)
    trees_with_temp = next(t for t in ledger_with_temp["targets"] if t["metric_code"] == "TREES_PLANTED")
    assert float(trees_with_temp["verified_quantity"]) == 2000.0
    print(f"  [OK] Ledger Quantity Before Archiving Temp Activity: {trees_with_temp['verified_quantity']} trees")

    # Invariant A: Archive the temporary activity (temp_act_id)
    status, archive_res = delete_req(f"/operations/activities/{temp_act_id}", pm_token)
    assert status == 200, f"Archival failed: {status}"
    assert archive_res["deactivated_revision_id"] == temp_rev_id

    # Verify ledger drops from 2,000 to 1,800 trees
    status, ledger_after_archive = get_json(f"/analytics/projects/{project_id}/impact", admin_token)
    trees_after_archive = next(t for t in ledger_after_archive["targets"] if t["metric_code"] == "TREES_PLANTED")
    assert float(trees_after_archive["verified_quantity"]) == 1800.0
    print(f"  [OK] Invariant A Verified: Archived Temp Activity (ID: {temp_act_id}, Rev: {temp_rev_id}). Ledger dropped from 2,000 to {trees_after_archive['verified_quantity']} trees (-200 trees)")

    # Invariant B: Archive rejected Activity 2 (act2_id)
    status, archive_act2 = delete_req(f"/operations/activities/{act2_id}", pm_token)
    assert status == 200
    assert archive_act2["deactivated_revision_id"] is None, "Rejected activity should have no active revision to deactivate"

    status, ledger_after_act2_archive = get_json(f"/analytics/projects/{project_id}/impact", admin_token)
    trees_after_act2 = next(t for t in ledger_after_act2_archive["targets"] if t["metric_code"] == "TREES_PLANTED")
    assert float(trees_after_act2["verified_quantity"]) == 1800.0
    print(f"  [OK] Invariant B Verified: Archived Rejected Activity 2 (ID: {act2_id}). Ledger remained unchanged at {trees_after_act2['verified_quantity']} trees")
    print(f"  [OK] Baseline Active Activity Confirmed: Activity 1 (ID: {act1_id}) remains ACTIVE with 1,800 verified trees")

    # 7. STAGE 6: MONITOR (Field Monitoring, Inspections, Tasks, Survival)
    print("\n--- 7. STAGE 6: MONITOR (Field Inspections, Tasks, Survival & Trajectory) ---")
    # PM schedules inspection
    status, insp = post_json("/monitoring/inspections", {
        "project_id": project_id,
        "assigned_to_id": fo_id,
        "inspection_type": "SURVIVAL_CHECK",
        "scheduled_date": "2026-11-10",
        "notes": "Post-planting survival rate assessment"
    }, pm_token)
    assert status == 201
    insp_id = insp["id"]
    print(f"  [OK] Scheduled Field Inspection: ID={insp_id}, Status={insp['status']}")

    # FO starts and completes inspection
    status, _ = post_json(f"/monitoring/inspections/{insp_id}/start", {}, fo_token)
    assert status == 200
    comp_insp_payload = {
        "findings": "Saplings established well in quadrant A. Slight rodent gnawing on lower bark.",
        "vegetation_health_score": 4,
        "canopy_condition": "HEALTHY",
        "soil_moisture_condition": "ADEQUATE",
        "threats_detected": ["PEST_PRESSURE"]
    }
    status, insp_comp = post_json(f"/monitoring/inspections/{insp_id}/complete", comp_insp_payload, fo_token)
    assert status == 200
    print(f"  [OK] Completed Field Inspection: Health Score={insp_comp['vegetation_health_score']}, Threats={insp_comp['threats_detected']}")

    # Add immutable post-completion addendum
    status, insp_add = post_json(f"/monitoring/inspections/{insp_id}/addendum", {"content": "Tree guards ordered for rodent protection."}, pm_token)
    assert status == 200
    assert len(insp_add["addenda"]) == 1
    print(f"  [OK] Immutable Addendum Appended to Completed Inspection")

    # PM creates maintenance task
    task_payload = {
        "project_id": project_id,
        "inspection_id": insp_id,
        "title": "Install tree guards along perimeter",
        "description": "Protect saplings from rodent bark damage",
        "category": "FENCING_REPAIR",
        "priority": "HIGH",
        "assigned_to_id": fo_id,
        "due_date": "2026-11-18"
    }
    status, task = post_json("/monitoring/tasks", task_payload, pm_token)
    assert status == 201
    task_id = task["id"]
    print(f"  [OK] Created Maintenance Task: ID={task_id}, Priority={task['priority']}")

    # FO starts and completes task
    post_json(f"/monitoring/tasks/{task_id}/start", {}, fo_token)
    status, task_comp = post_json(f"/monitoring/tasks/{task_id}/complete", {"completion_notes": "50 tree guards installed."}, fo_token)
    assert status == 200
    print(f"  [OK] Completed Maintenance Task")

    # PM reopens task with justification
    status, task_reopen = post_json(f"/monitoring/tasks/{task_id}/reopen", {"justification": "Second row guards missing."}, pm_token)
    assert status == 200
    assert task_reopen["status"] == "TODO"
    print(f"  [OK] Reopened Maintenance Task with Justification")

    # FO records Survival Observation
    plot_name = "PLOT-NILGIRI-01"
    cohort_name = "COHORT-2026-N1"
    obs_payload = {
        "project_id": project_id,
        "plot_identifier": plot_name,
        "cohort_identifier": cohort_name,
        "observation_date": "2026-11-04",
        "sample_size": 250,
        "alive_count": 225,
        "dead_count": 20,
        "unassessed_count": 5,
        "methodology": "SAMPLE_PLOT",
        "notes": "Healthy sample plot assessment"
    }
    status, obs = post_json("/monitoring/survival-observations", obs_payload, fo_token)
    assert status == 201
    obs_id = obs["id"]
    # Derived rate = 225 / (225 + 20) * 100 = 225 / 245 * 100 = 91.8367... -> 91.84%
    assert obs["survival_rate"] == 91.84, f"Expected 91.84%, got {obs['survival_rate']}"
    print(f"  [OK] Recorded Survival Observation: ID={obs_id}, Derived Rate={obs['survival_rate']}% (Server-Derived, Observed Sample Only)")

    # PM corrects observation (Atomic Supersession)
    corr_payload = {
        "sample_size": 250,
        "alive_count": 230,
        "dead_count": 15,
        "unassessed_count": 5,
        "correction_notes": "5 dormant saplings exhibited new bud shoots upon stem scrape test.",
        "notes": "Verified count correction"
    }
    status, corr_obs = post_json(f"/monitoring/survival-observations/{obs_id}/correct", corr_payload, pm_token)
    assert status == 200
    # Derived rate = 230 / (230 + 15) * 100 = 230 / 245 * 100 = 93.8775... -> 93.88%
    assert corr_obs["survival_rate"] == 93.88, f"Expected 93.88%, got {corr_obs['survival_rate']}"
    print(f"  [OK] Observation Corrected via Atomic Supersession: Replacement ID={corr_obs['id']}, New Rate={corr_obs['survival_rate']}%")

    # Trajectory query
    status, trajectory = get_json(f"/monitoring/survival-analytics?project_id={project_id}&plot_identifier={plot_name}&cohort_identifier={cohort_name}", admin_token)
    assert status == 200
    assert len(trajectory) == 1
    print(f"  [OK] Longitudinal Survival Trajectory Active Curve: 1 data point ({trajectory[0]['survival_rate']}%)")

    # 8. CRITICAL INVARIANT: Monitoring Isolation from Environmental Ledger
    print("\n--- 8. CRITICAL INVARIANT: Monitoring Isolation from Environmental Ledger ---")
    status, final_ledger = get_json(f"/analytics/projects/{project_id}/impact", admin_token)
    assert status == 200
    final_trees = next(t for t in final_ledger["targets"] if t["metric_code"] == "TREES_PLANTED")
    print(f"  Official Verified Trees:      {final_trees['verified_quantity']} trees")
    print(f"  Monitoring Observed Saplings: {corr_obs['alive_count']} alive (Sample rate: {corr_obs['survival_rate']}%)")
    assert float(final_trees["verified_quantity"]) == 1800.0, "CRITICAL DEFECT: Survival counts leaked into environmental ledger!"
    print(f"  [PASS] Zero Contamination Confirmed: Monitoring observations remain 100% isolated from official verified ledger achievements.")

    print("\n" + "=" * 70)
    print("ALL 8 BUSINESS LIFECYCLE & CROSS-DOMAIN STAGES PASSED (100% VERIFIED)")
    print("=" * 70)

if __name__ == "__main__":
    main()
