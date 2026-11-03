"""
VANA — Environmental Ledger & Impact Intelligence Service
Implements official environmental ledger aggregation, role-based portfolio scoping,
project impact analytics, and activity trend intelligence.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.auth.models import User, UserRole
from app.domains.operations.models import ActivityRevision, ActivityStatus, FieldActivity
from app.domains.projects.metrics import (
    APPROVED_METRIC_CATALOG,
    convert_between_units,
    convert_to_canonical,
    validate_metric_and_unit,
)
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment
from app.domains.analytics.schemas import (
    AttentionProjectItem,
    DashboardOverviewResponse,
    DashboardProjectsResponse,
    MetricCatalogSummaryItem,
    MetricProgressSummary,
    ProjectImpactDetailResponse,
    ProjectProgressItem,
    ProjectTrendPoint,
    ProjectTrendsResponse,
    RecentActivityItem,
    TargetProgressItem,
)


class EnvironmentalLedgerService:
    """
    Authoritative Environmental Ledger aggregation and analytics computation engine.
    Strictly follows 06_ENVIRONMENTAL_IMPACT_LOGIC.md and ADR-003, ADR-004, ADR-011.
    """

    @staticmethod
    async def get_authorized_project_ids(
        db: AsyncSession, current_user: User
    ) -> Optional[List[uuid.UUID]]:
        """
        Determines the list of project UUIDs the user is authorized to view.
        Returns None if ADMIN (indicating global portfolio-wide access).
        Returns list of assigned project IDs for PROJECT_MANAGER and FIELD_OFFICER.
        """
        if current_user.role == UserRole.ADMIN.value:
            return None

        stmt = select(ProjectAssignment.project_id).where(
            ProjectAssignment.user_id == current_user.id
        )
        result = await db.scalars(stmt)
        return list(result.all())

    @staticmethod
    async def verify_project_access(
        db: AsyncSession, project_id: uuid.UUID, current_user: User
    ) -> Project:
        """
        Validates that a project exists and that the current user has authorization to view it.
        Raises 404 if not found, or 403 if user lacks project assignment.
        """
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.targets),
                selectinload(Project.activities).selectinload(FieldActivity.revisions),
            )
        )
        project = await db.scalar(stmt)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PROJECT_NOT_FOUND",
                    "message": f"Project with ID '{project_id}' not found.",
                },
            )

        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "PROJECT_ACCESS_DENIED",
                        "message": "You are not assigned to this project.",
                    },
                )

        return project

    @staticmethod
    def _calculate_project_target_progress(
        project: Project, non_archived_activities: List[FieldActivity]
    ) -> Tuple[List[TargetProgressItem], Optional[float], int]:
        """
        Calculates verified achievement, net pending adjustment, and progress percentage
        for all targets defined on a project.
        Returns: (targets_progress, overall_achievement_percentage, pending_revisions_count)
        """
        # Map active verified quantity and net pending adjustment by metric_code (in canonical base unit)
        verified_canonical_by_metric: Dict[str, Decimal] = {}
        pending_canonical_by_metric: Dict[str, Decimal] = {}
        total_pending_revisions = 0

        for activity in non_archived_activities:
            metric_code = activity.metric_code
            if metric_code not in verified_canonical_by_metric:
                verified_canonical_by_metric[metric_code] = Decimal("0.0")
                pending_canonical_by_metric[metric_code] = Decimal("0.0")

            # 1. Active ledger entry (official verified quantity)
            active_rev = next(
                (r for r in activity.revisions if r.is_active_ledger_entry), None
            )
            if active_rev:
                verified_canonical_by_metric[metric_code] += convert_to_canonical(
                    metric_code, active_rev.quantity, activity.unit
                )

            # 2. Current revision (pending adjustments)
            current_rev = next(
                (r for r in activity.revisions if r.id == activity.current_revision_id),
                None,
            )
            if not current_rev and activity.revisions:
                current_rev = sorted(activity.revisions, key=lambda r: r.revision_number)[-1]

            if current_rev and current_rev.status == ActivityStatus.PENDING.value:
                total_pending_revisions += 1
                if active_rev:
                    delta = current_rev.quantity - active_rev.quantity
                else:
                    delta = current_rev.quantity
                pending_canonical_by_metric[metric_code] += convert_to_canonical(
                    metric_code, delta, activity.unit
                )

        # Build TargetProgressItem for each configured target
        target_items: List[TargetProgressItem] = []
        achievement_percentages: List[float] = []

        for target in project.targets:
            metric_code = target.metric_code
            catalog_def = APPROVED_METRIC_CATALOG.get(metric_code)
            metric_name = catalog_def.display_name if catalog_def else metric_code
            canonical_unit = catalog_def.canonical_unit if catalog_def else target.target_unit

            # Total verified in target unit
            verified_canonical = verified_canonical_by_metric.get(metric_code, Decimal("0.0"))
            verified_in_target = convert_between_units(
                metric_code, verified_canonical, canonical_unit, target.target_unit
            )

            # Net pending in target unit
            pending_canonical = pending_canonical_by_metric.get(metric_code, Decimal("0.0"))
            pending_in_target = convert_between_units(
                metric_code, pending_canonical, canonical_unit, target.target_unit
            )

            target_qty = target.target_quantity
            remaining = max(Decimal("0.0"), target_qty - verified_in_target)

            if target_qty > 0:
                pct = float(round((verified_in_target / target_qty) * 100, 2))
            else:
                pct = 0.0

            achievement_percentages.append(pct)

            target_items.append(
                TargetProgressItem(
                    target_id=target.id,
                    metric_code=metric_code,
                    metric_name=metric_name,
                    target_quantity=target_qty,
                    target_unit=target.target_unit,
                    verified_quantity=round(verified_in_target, 2),
                    net_pending_adjustment=round(pending_in_target, 2),
                    remaining_quantity=round(remaining, 2),
                    achievement_percentage=pct,
                    target_date=target.target_date,
                    milestone_id=target.milestone_id,
                )
            )

        overall_pct: Optional[float] = None
        if achievement_percentages:
            # Safe composite indicator: average capped at 100 per target for portfolio pacing
            overall_pct = float(
                round(sum(min(100.0, p) for p in achievement_percentages) / len(achievement_percentages), 2)
            )

        return target_items, overall_pct, total_pending_revisions

    @staticmethod
    async def get_dashboard_overview(
        db: AsyncSession, current_user: User
    ) -> DashboardOverviewResponse:
        """
        Assembles high-level KPI cards, metric-by-metric verified achievements,
        attention projects, and pending verifications count scoped to user permissions.
        """
        authorized_ids = await EnvironmentalLedgerService.get_authorized_project_ids(
            db, current_user
        )

        # Fetch projects matching scope
        stmt = (
            select(Project)
            .where(Project.status != ProjectStatus.ARCHIVED.value)
            .options(
                selectinload(Project.targets),
                selectinload(Project.activities).selectinload(FieldActivity.revisions),
            )
        )
        if authorized_ids is not None:
            stmt = stmt.where(Project.id.in_(authorized_ids))

        projects = list((await db.scalars(stmt)).all())

        # Project status counters
        total_projects = len(projects)
        active_projects = sum(1 for p in projects if p.status == ProjectStatus.ACTIVE.value)
        completed_projects = sum(1 for p in projects if p.status == ProjectStatus.COMPLETED.value)
        draft_projects = sum(1 for p in projects if p.status == ProjectStatus.DRAFT.value)

        # Environmental Ledger Aggregations across authorized projects
        metric_verified_totals: Dict[str, Decimal] = {}
        metric_pending_totals: Dict[str, Decimal] = {}
        metric_target_totals: Dict[str, Decimal] = {}
        metric_active_projects: Dict[str, Set[uuid.UUID]] = {}
        metric_activities_count: Dict[str, int] = {}
        total_pending_verifications = 0
        attention_projects: List[AttentionProjectItem] = []
        today = date.today()

        for project in projects:
            non_archived_activities = [a for a in project.activities if not a.is_archived]
            target_items, overall_pct, proj_pending_count = (
                EnvironmentalLedgerService._calculate_project_target_progress(
                    project, non_archived_activities
                )
            )
            total_pending_verifications += proj_pending_count

            # Track targets in canonical units
            for target in project.targets:
                m_code = target.metric_code
                cat_def = APPROVED_METRIC_CATALOG.get(m_code)
                if cat_def:
                    c_unit = cat_def.canonical_unit
                    t_canonical = convert_between_units(
                        m_code, target.target_quantity, target.target_unit, c_unit
                    )
                    metric_target_totals[m_code] = (
                        metric_target_totals.get(m_code, Decimal("0.0")) + t_canonical
                    )

            # Track verified and pending achievements in canonical units
            for act in non_archived_activities:
                m_code = act.metric_code
                if m_code not in metric_verified_totals:
                    metric_verified_totals[m_code] = Decimal("0.0")
                    metric_pending_totals[m_code] = Decimal("0.0")
                    metric_active_projects[m_code] = set()
                    metric_activities_count[m_code] = 0

                metric_active_projects[m_code].add(project.id)
                metric_activities_count[m_code] += 1

                # Active ledger revision
                active_rev = next((r for r in act.revisions if r.is_active_ledger_entry), None)
                if active_rev:
                    metric_verified_totals[m_code] += convert_to_canonical(
                        m_code, active_rev.quantity, act.unit
                    )

                # Current pending revision
                current_rev = next(
                    (r for r in act.revisions if r.id == act.current_revision_id), None
                )
                if not current_rev and act.revisions:
                    current_rev = sorted(act.revisions, key=lambda r: r.revision_number)[-1]

                if current_rev and current_rev.status == ActivityStatus.PENDING.value:
                    if active_rev:
                        delta = current_rev.quantity - active_rev.quantity
                    else:
                        delta = current_rev.quantity
                    metric_pending_totals[m_code] += convert_to_canonical(
                        m_code, delta, act.unit
                    )

            # Evaluate Attention Rules for project
            if project.status == ProjectStatus.ACTIVE.value:
                # Rule 1: Pending verifications backlog
                if proj_pending_count >= 1:
                    attention_projects.append(
                        AttentionProjectItem(
                            project_id=project.id,
                            project_name=project.name,
                            project_code=project.code,
                            status=project.status,
                            reason=f"{proj_pending_count} activity revision(s) awaiting verification review.",
                            severity="HIGH" if proj_pending_count >= 4 else "MEDIUM",
                            pending_verifications_count=proj_pending_count,
                            lowest_target_achievement_percentage=overall_pct,
                        )
                    )
                # Rule 2: Target approaching deadline with low progress (<50%)
                for ti in target_items:
                    days_left = (ti.target_date - today).days
                    if ti.achievement_percentage < 50.0:
                        if days_left < 0:
                            attention_projects.append(
                                AttentionProjectItem(
                                    project_id=project.id,
                                    project_name=project.name,
                                    project_code=project.code,
                                    status=project.status,
                                    reason=f"Target for {ti.metric_name} is overdue ({abs(days_left)} days past deadline) with only {ti.achievement_percentage}% achievement.",
                                    severity="HIGH",
                                    pending_verifications_count=proj_pending_count,
                                    days_until_deadline=days_left,
                                    lowest_target_achievement_percentage=ti.achievement_percentage,
                                )
                            )
                            break
                        elif days_left <= 30:
                            attention_projects.append(
                                AttentionProjectItem(
                                    project_id=project.id,
                                    project_name=project.name,
                                    project_code=project.code,
                                    status=project.status,
                                    reason=f"Target deadline for {ti.metric_name} approaching in {days_left} days with only {ti.achievement_percentage}% achievement.",
                                    severity="HIGH",
                                    pending_verifications_count=proj_pending_count,
                                    days_until_deadline=days_left,
                                    lowest_target_achievement_percentage=ti.achievement_percentage,
                                )
                            )
                            break
                # Rule 3: Active with targets but zero verified activities
                if target_items and overall_pct == 0.0 and proj_pending_count == 0:
                    attention_projects.append(
                        AttentionProjectItem(
                            project_id=project.id,
                            project_name=project.name,
                            project_code=project.code,
                            status=project.status,
                            reason="Project is active with targets defined but zero verified activities recorded.",
                            severity="LOW",
                            pending_verifications_count=0,
                            lowest_target_achievement_percentage=0.0,
                        )
                    )

        # Build metric progress summaries for catalog
        metric_achievements: List[MetricProgressSummary] = []
        for m_code, cat_def in APPROVED_METRIC_CATALOG.items():
            verified_qty = metric_verified_totals.get(m_code, Decimal("0.0"))
            pending_qty = metric_pending_totals.get(m_code, Decimal("0.0"))
            target_qty = metric_target_totals.get(m_code)
            active_proj_count = len(metric_active_projects.get(m_code, set()))
            act_count = metric_activities_count.get(m_code, 0)

            # Only include metrics that have either targets or recorded activities
            if target_qty is not None or verified_qty > 0 or pending_qty != 0:
                achieve_pct: Optional[float] = None
                if target_qty and target_qty > 0:
                    achieve_pct = float(round((verified_qty / target_qty) * 100, 2))

                metric_achievements.append(
                    MetricProgressSummary(
                        metric_code=m_code,
                        display_name=cat_def.display_name,
                        category=cat_def.category,
                        canonical_unit=cat_def.canonical_unit,
                        total_verified_quantity=round(verified_qty, 2),
                        total_pending_adjustment=round(pending_qty, 2),
                        total_target_quantity=round(target_qty, 2) if target_qty else None,
                        overall_achievement_percentage=achieve_pct,
                        active_projects_count=active_proj_count,
                        activities_count=act_count,
                    )
                )

        return DashboardOverviewResponse(
            total_projects=total_projects,
            active_projects=active_projects,
            completed_projects=completed_projects,
            draft_projects=draft_projects,
            total_pending_verifications=total_pending_verifications,
            metric_achievements=metric_achievements,
            attention_projects=attention_projects[:10],  # Cap top 10 attention items
            user_role=current_user.role,
            is_portfolio_wide=(authorized_ids is None),
        )

    @staticmethod
    async def get_dashboard_projects(
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> DashboardProjectsResponse:
        """
        Lists projects with their verified target progress, pending revisions, and coordinates.
        Scoped to user's assigned projects for non-admin roles.
        """
        authorized_ids = await EnvironmentalLedgerService.get_authorized_project_ids(
            db, current_user
        )

        stmt = (
            select(Project)
            .where(Project.status != ProjectStatus.ARCHIVED.value)
            .order_by(desc(Project.created_at))
            .options(
                selectinload(Project.targets),
                selectinload(Project.activities).selectinload(FieldActivity.revisions),
            )
        )
        if authorized_ids is not None:
            stmt = stmt.where(Project.id.in_(authorized_ids))

        if status_filter:
            stmt = stmt.where(Project.status == status_filter.strip().upper())

        projects = list((await db.scalars(stmt)).all())

        if search and search.strip():
            query = search.strip().lower()
            projects = [
                p
                for p in projects
                if query in p.name.lower()
                or query in p.code.lower()
                or query in (p.description or "").lower()
            ]

        project_items: List[ProjectProgressItem] = []
        for p in projects:
            non_archived = [a for a in p.activities if not a.is_archived]
            target_items, overall_pct, pending_count = (
                EnvironmentalLedgerService._calculate_project_target_progress(p, non_archived)
            )

            # Determine latest activity date
            all_dates = [
                r.activity_date
                for a in non_archived
                for r in a.revisions
                if r.activity_date is not None
            ]
            last_date = max(all_dates) if all_dates else None

            has_coords = bool(
                p.latitude is not None
                and p.longitude is not None
                and not (p.latitude == 0.0 and p.longitude == 0.0)
            )

            project_items.append(
                ProjectProgressItem(
                    id=p.id,
                    name=p.name,
                    code=p.code,
                    status=p.status,
                    description=p.description,
                    latitude=p.latitude,
                    longitude=p.longitude,
                    targets=target_items,
                    overall_achievement_percentage=overall_pct,
                    pending_verifications_count=pending_count,
                    last_activity_date=last_date,
                    has_coordinates=has_coords,
                )
            )

        return DashboardProjectsResponse(total=len(project_items), projects=project_items)

    @staticmethod
    async def get_recent_activity(
        db: AsyncSession, current_user: User, limit: int = 15
    ) -> List[RecentActivityItem]:
        """
        Retrieves real-time operational events (submissions, verifications, rejections, amendments).
        Scoped to projects the user is authorized to view.
        """
        authorized_ids = await EnvironmentalLedgerService.get_authorized_project_ids(
            db, current_user
        )

        # Query recent activity revisions
        stmt = (
            select(ActivityRevision)
            .join(FieldActivity, FieldActivity.id == ActivityRevision.activity_id)
            .join(Project, Project.id == FieldActivity.project_id)
            .where(FieldActivity.is_archived == False)
            .order_by(desc(ActivityRevision.created_at))
            .limit(limit)
            .options(
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.project),
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.created_by),
                selectinload(ActivityRevision.verifier),
            )
        )
        if authorized_ids is not None:
            stmt = stmt.where(FieldActivity.project_id.in_(authorized_ids))

        revisions = list((await db.scalars(stmt)).all())

        items: List[RecentActivityItem] = []
        for r in revisions:
            activity = r.activity
            project = activity.project
            creator = activity.created_by
            verifier = r.verifier

            cat_def = APPROVED_METRIC_CATALOG.get(activity.metric_code)
            m_name = cat_def.display_name if cat_def else activity.metric_code

            if r.status == ActivityStatus.VERIFIED.value:
                ev_type = "VERIFICATION"
                title = f"Activity Verified: {r.quantity:g} {activity.unit} of {m_name}"
                desc_text = (
                    f"Verified by {verifier.full_name if verifier else 'Reviewer'} "
                    f"for project {project.name} ({project.code})."
                )
                ts = r.verified_at or r.created_at
                actor_id = r.verifier_id
                actor_name = verifier.full_name if verifier else None
            elif r.status == ActivityStatus.REJECTED.value:
                ev_type = "REJECTION"
                title = f"Activity Submission Rejected: {r.quantity:g} {activity.unit}"
                reason_clean = (r.rejection_reason_code or "Unspecified").replace("_", " ").title()
                desc_text = f"Rejected ({reason_clean}): {r.review_notes or 'No notes provided.'}"
                ts = r.verified_at or r.created_at
                actor_id = r.verifier_id
                actor_name = verifier.full_name if verifier else None
            else:
                is_amendment = r.revision_number > 1
                ev_type = "AMENDMENT" if is_amendment else "SUBMISSION"
                action_word = "Amendment submitted" if is_amendment else "Activity reported"
                title = f"{action_word}: {r.quantity:g} {activity.unit} of {m_name}"
                desc_text = f"Reported by {creator.full_name if creator else 'Field Officer'} on site."
                ts = r.created_at
                actor_id = activity.created_by_id
                actor_name = creator.full_name if creator else None

            items.append(
                RecentActivityItem(
                    id=r.id,
                    event_type=ev_type,
                    title=title,
                    description=desc_text,
                    timestamp=ts,
                    actor_id=actor_id,
                    actor_name=actor_name,
                    project_id=project.id,
                    project_name=project.name,
                    project_code=project.code,
                    metric_code=activity.metric_code,
                    quantity=r.quantity,
                    unit=activity.unit,
                    status=r.status,
                )
            )

        return items

    @staticmethod
    async def get_project_impact_detail(
        db: AsyncSession, project_id: uuid.UUID, current_user: User
    ) -> ProjectImpactDetailResponse:
        """
        Deep-dive environmental impact balance sheet for an individual project.
        Reconciles targets, verified quantities, pending adjustments, and historical rejections.
        """
        project = await EnvironmentalLedgerService.verify_project_access(
            db, project_id, current_user
        )

        non_archived = [a for a in project.activities if not a.is_archived]
        target_items, overall_pct, pending_count = (
            EnvironmentalLedgerService._calculate_project_target_progress(project, non_archived)
        )

        all_revisions = [r for a in non_archived for r in a.revisions]
        verified_revisions = [r for r in all_revisions if r.is_active_ledger_entry]
        historical_rejections = [r for r in all_revisions if r.status == ActivityStatus.REJECTED.value]

        all_dates = [r.activity_date for r in all_revisions if r.activity_date is not None]
        last_date = max(all_dates) if all_dates else None

        activities_summary = {
            "total_activities_count": len(non_archived),
            "verified_active_revisions_count": len(verified_revisions),
            "pending_revisions_count": pending_count,
            "current_rejected_revisions_count": len(historical_rejections),
            "archived_activities_count": sum(1 for a in project.activities if a.is_archived),
        }

        return ProjectImpactDetailResponse(
            project_id=project.id,
            project_name=project.name,
            project_code=project.code,
            project_status=project.status,
            description=project.description,
            latitude=project.latitude,
            longitude=project.longitude,
            boundary_geojson=project.boundary_geojson,
            targets=target_items,
            overall_achievement_percentage=overall_pct,
            activities_summary=activities_summary,
            historical_rejected_count=len(historical_rejections),
            last_activity_date=last_date,
        )

    @staticmethod
    async def get_project_trends(
        db: AsyncSession,
        project_id: uuid.UUID,
        current_user: User,
        metric_code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ProjectTrendsResponse:
        """
        Generates time-series data points of verified activities for chart visualizations.
        Maintains cumulative running totals and discrete daily quantities.
        """
        project = await EnvironmentalLedgerService.verify_project_access(
            db, project_id, current_user
        )

        # Validate date filters if both provided
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_DATE_RANGE",
                    "message": "start_date cannot be greater than end_date.",
                },
            )

        # Fetch all active verified revisions for this project
        stmt = (
            select(ActivityRevision)
            .join(FieldActivity, FieldActivity.id == ActivityRevision.activity_id)
            .where(
                FieldActivity.project_id == project_id,
                FieldActivity.is_archived == False,
                ActivityRevision.is_active_ledger_entry == True,
            )
            .order_by(ActivityRevision.activity_date.asc(), ActivityRevision.created_at.asc())
            .options(selectinload(ActivityRevision.activity))
        )

        if metric_code:
            valid_m = metric_code.strip().upper()
            stmt = stmt.where(FieldActivity.metric_code == valid_m)

        if start_date:
            stmt = stmt.where(ActivityRevision.activity_date >= start_date)
        if end_date:
            stmt = stmt.where(ActivityRevision.activity_date <= end_date)

        revisions = list((await db.scalars(stmt)).all())

        # Collect available metrics for this project
        all_metrics_stmt = (
            select(FieldActivity.metric_code)
            .where(FieldActivity.project_id == project_id, FieldActivity.is_archived == False)
            .distinct()
        )
        available_metrics = list((await db.scalars(all_metrics_stmt)).all())

        # Group by (activity_date, metric_code)
        grouped_quantities: Dict[Tuple[date, str], Decimal] = {}
        grouped_counts: Dict[Tuple[date, str], int] = {}
        distinct_metrics: Set[str] = set()

        for r in revisions:
            act = r.activity
            m_code = act.metric_code
            distinct_metrics.add(m_code)
            d = r.activity_date

            # Convert to canonical unit
            qty_canonical = convert_to_canonical(m_code, r.quantity, act.unit)

            key = (d, m_code)
            grouped_quantities[key] = grouped_quantities.get(key, Decimal("0.0")) + qty_canonical
            grouped_counts[key] = grouped_counts.get(key, 0) + 1

        # Sort chronological dates
        sorted_keys = sorted(grouped_quantities.keys(), key=lambda k: (k[0], k[1]))

        # Calculate cumulative running total per metric code
        cumulative_totals: Dict[str, Decimal] = {m: Decimal("0.0") for m in distinct_metrics}
        trend_points: List[ProjectTrendPoint] = []

        for d, m_code in sorted_keys:
            cat_def = APPROVED_METRIC_CATALOG.get(m_code)
            m_name = cat_def.display_name if cat_def else m_code
            c_unit = cat_def.canonical_unit if cat_def else "units"

            period_qty = grouped_quantities[(d, m_code)]
            cumulative_totals[m_code] += period_qty

            trend_points.append(
                ProjectTrendPoint(
                    date=d.isoformat(),
                    metric_code=m_code,
                    metric_name=m_name,
                    unit=c_unit,
                    period_quantity=round(period_qty, 2),
                    cumulative_quantity=round(cumulative_totals[m_code], 2),
                    activities_count=grouped_counts[(d, m_code)],
                )
            )

        return ProjectTrendsResponse(
            project_id=project.id,
            project_name=project.name,
            trends=trend_points,
            available_metrics=available_metrics,
        )

    @staticmethod
    async def get_metrics_catalog_summary(
        db: AsyncSession, current_user: User
    ) -> List[MetricCatalogSummaryItem]:
        """
        Retrieves active metrics catalog with scoped portfolio achievements and target totals.
        """
        overview = await EnvironmentalLedgerService.get_dashboard_overview(db, current_user)
        achievements_map = {m.metric_code: m for m in overview.metric_achievements}

        items: List[MetricCatalogSummaryItem] = []
        for m_code, cat_def in APPROVED_METRIC_CATALOG.items():
            summary = achievements_map.get(m_code)
            verified_qty = summary.total_verified_quantity if summary else Decimal("0.0")
            pending_qty = summary.total_pending_adjustment if summary else Decimal("0.0")
            target_qty = summary.total_target_quantity if summary else None
            achieve_pct = summary.overall_achievement_percentage if summary else None
            proj_count = summary.active_projects_count if summary else 0

            items.append(
                MetricCatalogSummaryItem(
                    metric_code=m_code,
                    display_name=cat_def.display_name,
                    category=cat_def.category,
                    canonical_unit=cat_def.canonical_unit,
                    supported_units=cat_def.supported_units,
                    total_verified_quantity=verified_qty,
                    total_pending_adjustment=pending_qty,
                    total_target_quantity=target_qty,
                    overall_achievement_percentage=achieve_pct,
                    projects_count=proj_count,
                )
            )

        return items
