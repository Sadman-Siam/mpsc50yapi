from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import col, func, select

from app.dependencies import AdminSecret, DBSession
from app.models import Acquaintance, Address, Alumna, AlumniProfile, WorkProfile
from app.schemas.alumni import (
    AcquaintanceInformation,
    AddressInformation,
    AlumnaInformation,
    AlumniProfileInformation,
    WorkProfileInformation,
)
from app.types import AccountStatus

router = APIRouter(
    prefix="/admin",
    tags=["Administration Routes"],
    dependencies=[],  # auth applied per-route via AdminSecret
)


def _full_information(alumna: Alumna, database_session: DBSession) -> AlumnaInformation:
    """Admin-side projection: includes status and profile even when incomplete."""
    profile = database_session.scalar(
        select(AlumniProfile).where(AlumniProfile.alumna_uuid == alumna.uuid)
    )

    profile_information = None
    if profile:
        work_profile = (
            database_session.get(WorkProfile, profile.work_profile_uuid)
            if profile.work_profile_uuid
            else None
        )
        address = (
            database_session.get(Address, profile.address_uuid)
            if profile.address_uuid
            else None
        )

        profile_information = AlumniProfileInformation(
            uuid=profile.uuid,
            reg_code=profile.reg_code,
            student_id=profile.student_id,
            batch_year=profile.batch_year,
            tee_shirt_size=profile.tee_shirt_size,
            registered_at=profile.registered_at,
            work_profile=(
                WorkProfileInformation.model_validate(work_profile, from_attributes=True)
                if work_profile
                else None
            ),
            address=(
                AddressInformation.model_validate(address, from_attributes=True)
                if address
                else None
            ),
        )

    acquaintances = database_session.scalars(
        select(Acquaintance).where(Acquaintance.alumna_uuid == alumna.uuid)
    ).all()

    return AlumnaInformation(
        uuid=alumna.uuid,
        full_name=alumna.full_name,
        email=alumna.email,
        phone_number=alumna.phone_number,
        status=alumna.status,
        created_at=alumna.created_at,
        profile=profile_information,
        acquaintances=[
            AcquaintanceInformation.model_validate(a, from_attributes=True)
            for a in acquaintances
        ],
    )


@router.get(
    "/alumnae",
    response_model=list[AlumnaInformation],
    summary="List registered alumnae, optionally filtered by account status",
)
def list_alumnae(
    _: AdminSecret,
    database_session: DBSession,
    status_filter: AccountStatus | None = Query(
        default=None, alias="status", description="pending | confirmed | cancelled"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    statement = select(Alumna)
    if status_filter:
        statement = statement.where(Alumna.status == status_filter)

    alumnae = database_session.scalars(
        statement.order_by(col(Alumna.created_at).desc()).offset(offset).limit(limit)
    ).all()

    return [_full_information(alumna, database_session) for alumna in alumnae]


@router.get(
    "/alumnae/counts",
    summary="Count alumnae grouped by account status",
)
def count_alumnae(_: AdminSecret, database_session: DBSession) -> dict[str, int]:
    # col() is required so SQLAlchemy treats this as a SQL expression rather
    # than a model instance attribute.
    rows = database_session.execute(
        select(col(Alumna.status), func.count()).group_by(col(Alumna.status))
    ).all()

    counts = {"pending": 0, "confirmed": 0, "cancelled": 0}
    for account_status, total in rows:
        counts[str(account_status)] = int(total)

    return counts


@router.patch(
    "/alumnae/{alumna_uuid}/status",
    response_model=AlumnaInformation,
    summary="Approve, cancel or reactivate an alumna account",
)
def update_alumna_status(
    alumna_uuid: UUID,
    new_status: AccountStatus,
    _: AdminSecret,
    database_session: DBSession,
):
    alumna = database_session.get(Alumna, alumna_uuid)
    if not alumna:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alumna not found"
        )

    alumna.status = new_status
    database_session.add(alumna)
    database_session.commit()
    database_session.refresh(alumna)

    return _full_information(alumna, database_session)