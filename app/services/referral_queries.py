from datetime import datetime
from uuid import UUID

from sqlmodel import Session, col, select

from app.models import Alumna, AlumniProfile
from app.schemas.referrals import ReferredAlumnaInformation
from app.services.referrals import counts_as_referral


def referrals_for(
    database_session: Session, alumna_uuid: UUID
) -> tuple[list[ReferredAlumnaInformation], list[datetime]]:
    rows = database_session.execute(
        select(Alumna, AlumniProfile)
        .join(AlumniProfile, AlumniProfile.alumna_uuid == Alumna.uuid)
        .where(AlumniProfile.referred_by_alumna_uuid == alumna_uuid)
        .order_by(col(AlumniProfile.registered_at), col(Alumna.uuid))
    ).all()
    referrals = [
        ReferredAlumnaInformation(
            uuid=alumna.uuid, full_name=alumna.full_name, status=alumna.status
        )
        for alumna, _ in rows
    ]
    qualifying_dates = [
        profile.registered_at
        for alumna, profile in rows
        if counts_as_referral(alumna)
    ]
    return referrals, qualifying_dates
