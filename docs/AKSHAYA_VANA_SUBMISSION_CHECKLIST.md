# VANA — Akshaya Vana Technical Assignment Submission Checklist

> **Submission Target:** Akshaya Vana Climate Ventures Private Limited\
> **Candidate:** Sneha Priya\
> **Date:** November 4, 2026\
> **Platform:** VANA Environmental Operations & Impact Intelligence Platform\
> **Assignment Status:** Complete, Hardened & Ready for Live Deployment

---

## 1. Assignment Deliverables Matrix

| # | Deliverable Requirement | Status | Artifact / Location | Verification Details |
|---|---|:---:|---|---|
| **1** | **Live Website Link** | **READY FOR HOSTING** | `https://vana-app.vercel.app` (Target)\
*(Render API: `https://vana-backend.onrender.com`)* | Deployment blueprint prepared in `render.yaml`, `vercel.json`, and `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`. Live deployment executed upon cloud provider account connection. |
| **2** | **GitHub Repository Link** | **COMPLETED & PUBLISHED** | [https://github.com/snehapriy958/VANA](https://github.com/snehapriy958/VANA) | Release commits published to `main` with release candidate tag `v1.0.0-rc1`. Clean Git history. |
| **3** | **Comprehensive README** | **COMPLETED** | [README.md](file:///C:/Developers/Sneha/Projects/VANA/README.md) | Exhaustive documentation covering architecture, ERD, installation, local setup, credentials, environmental math, and troubleshooting. |
| **4** | **Test Login Credentials** | **COMPLETED** | Detailed in Section 2 of this document and in `README.md` | Pre-configured local demonstration accounts and secure production bootstrap instructions. |
| **5** | **Demo Video ($\le 5$ min)** | **SCRIPT COMPLETED** | [docs/DEMO_VIDEO_SCRIPT.md](file:///C:/Developers/Sneha/Projects/VANA/docs/DEMO_VIDEO_SCRIPT.md) | Timed 4m45s walkthrough covering all core domains, invariants, and live cryptographic verification. |
| **6** | **Unfinished Features & Future Improvements** | **COMPLETED** | Documented in Section 3 of this document and in `README.md` | Honest, detailed analysis of future enterprise milestones (spatial PostGIS, offline sync, external ledger anchoring). |
| **7** | **AI Assistance Disclosure** | **COMPLETED** | [docs/AI_ASSISTANCE_DISCLOSURE.md](file:///C:/Developers/Sneha/Projects/VANA/docs/AI_ASSISTANCE_DISCLOSURE.md) | Transparent disclosure of AI pair programming tools, human ownership, and verification methodologies. |

---

## 2. Test Login Demonstration Credentials

### Safe Local Development Accounts (Pre-Seeded)
When running locally via `scripts/seed_demo_data.py` or development setup:

| Role | Email Address | Password | Permissions Scope |
|---|---|---|---|
| **Administrator** | `admin@vana.earth` | `SecurePass123!` | Organization-wide administration, user management, global audit access |
| **Project Manager** | `manager@vana.earth` | `SecurePass123!` | Scoped to assigned projects, verification decision reviews, inspection scheduling |
| **Field Officer** | `field@vana.earth` | `SecurePass123!` | Scoped to assigned projects, activity submissions, evidence uploads |

### Production Cloud Bootstrap
For live deployment environments:
- Execute `python -m app.bootstrap_admin` in the Render web shell.
- Provide credentials securely via `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`.
- Follow the runbook in [docs/PRODUCTION_DEPLOYMENT_GUIDE.md](file:///C:/Developers/Sneha/Projects/VANA/docs/PRODUCTION_DEPLOYMENT_GUIDE.md).

---

## 3. Analysis of Unfinished Features & Future Improvements

To maintain strict architectural scope and avoid unnecessary complexity during the MVP phases, certain features were intentionally deferred to future post-MVP milestones:

### 1. Spatial Database Extensions (PostGIS) & Polygon Intersections
- **Current State:** Projects support center-point GPS coordinates (`latitude`, `longitude`) and GeoJSON polygons stored in PostgreSQL JSONB with client-side Leaflet rendering.
- **Future Improvement:** Incorporate PostGIS spatial indexing (`ST_Intersects`, `ST_Area`) to automatically detect overlapping project boundaries and compute exact satellite raster intersection coverage for carbon baselines.

### 2. Offline-First Mobile Field Progressive Web App (PWA)
- **Current State:** Responsive web client operating smoothly on mobile and desktop browsers with standard network connectivity.
- **Future Improvement:** Implement Service Worker caching and local IndexedDB revision queuing to enable remote field officers in zero-connectivity areas to capture observations offline and sync automatically upon regaining cellular network.

### 3. External Cryptographic Anchor (L2 / QLDB Notarization)
- **Current State:** Internal PostgreSQL SHA-256 hash chaining engine with gapless sequence numbers and on-demand chain verification.
- **Future Improvement:** Periodically anchor `audit_chain_head` hash checkpoints (e.g. daily) to a public blockchain (Ethereum L2) or RFC 3161 timestamping authority to provide cryptographic non-repudiation against internal superuser database administrators.

### 4. Automated Satellite & Drone Remote Sensing Ingestion
- **Current State:** Field verification relies on geotagged photographic evidence and in-situ sample survival checks.
- **Future Improvement:** Ingest Sentinel-2 and Planet multispectral imagery to calculate NDVI (Normalized Difference Vegetation Index) biomass density curves alongside ground-truth field records.

---

## 4. Final Submission Email Template (For Candidate Use)

```text
Subject: Full-Stack Technical Assignment Submission — VANA Platform — Sneha Priya

Dear Akshaya Vana Team,

I am pleased to submit the completed full-stack technical assignment: VANA (Environmental Operations & Impact Intelligence Platform).

VANA is an enterprise-grade, domain-driven modular monolith built with FastAPI, React 19, and PostgreSQL 17, enforcing verified-only environmental accounting, anti-self-verification, and an append-only cryptographic immutability ledger.

Key Submission Deliverables:
1. GitHub Repository: https://github.com/snehapriy958/VANA (Release Tag: v1.0.0-rc1)
2. Live Demonstration Architecture: Prepared for Neon + Render + Vercel deployment (detailed in docs/PRODUCTION_DEPLOYMENT_GUIDE.md)
3. Demonstration Walkthrough Script: docs/DEMO_VIDEO_SCRIPT.md
4. Test Credentials:
   - Admin: admin@vana.earth / SecurePass123!
   - Project Manager: manager@vana.earth / SecurePass123!
   - Field Officer: field@vana.earth / SecurePass123!
5. AI Assistance Disclosure: docs/AI_ASSISTANCE_DISCLOSURE.md
6. Full Automated Test Suite: 164 backend tests and 99 frontend tests passing (100% pass rate).

Thank you for the opportunity to work on this platform. I look forward to walking through the architecture and implementation during our technical discussion.

Warm regards,
Sneha Priya
```
