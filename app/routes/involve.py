from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.constants import SUBCOMMITTEE_NAMES
from app.dependencies import CurrentAlumna, DBSession
from app.helper import now
from app.models import SponsorOffer, SubcommitteeApplication
from app.schemas.involve import (
    SubcommitteeApplicationInformation,
    SubcommitteeApplicationInput,
    SponsorOfferInformation,
    SponsorOfferInput,
)
from app.services.deadlines import ensure_open
from app.settings import settings

router = APIRouter(prefix="/involve", tags=["Get Involved"])


@router.post("/sponsor", status_code=status.HTTP_201_CREATED, response_model=SponsorOfferInformation)
def create_sponsor_offer(
    data: SponsorOfferInput, alumna: CurrentAlumna, database_session: DBSession
) -> SponsorOffer:
    ensure_open("sponsor", database_session, now=now)
    count = len(database_session.exec(
        select(SponsorOffer).where(SponsorOffer.alumna_uuid == alumna.uuid)
    ).all())
    if count >= settings.sponsor_offer_limit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sponsor offer limit reached")
    offer = SponsorOffer(alumna_uuid=alumna.uuid, **data.model_dump())
    database_session.add(offer)
    database_session.commit()
    database_session.refresh(offer)
    return offer


@router.get("/sponsor/me", response_model=list[SponsorOfferInformation])
def read_my_sponsor_offers(alumna: CurrentAlumna, database_session: DBSession) -> list[SponsorOffer]:
    return database_session.exec(
        select(SponsorOffer)
        .where(SponsorOffer.alumna_uuid == alumna.uuid)
        .order_by(SponsorOffer.created_at.desc())
    ).all()


@router.get("/subcommittee/options", response_model=list[str])
def subcommittee_options() -> list[str]:
    return SUBCOMMITTEE_NAMES


@router.post(
    "/subcommittee",
    status_code=status.HTTP_201_CREATED,
    response_model=SubcommitteeApplicationInformation,
)
def create_subcommittee_application(
    data: SubcommitteeApplicationInput,
    alumna: CurrentAlumna,
    database_session: DBSession,
) -> SubcommitteeApplication:
    ensure_open("subcommittee", database_session, now=now)
    existing = database_session.scalar(
        select(SubcommitteeApplication).where(
            SubcommitteeApplication.alumna_uuid == alumna.uuid
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sub-committee application already exists",
        )

    application = SubcommitteeApplication(
        alumna_uuid=alumna.uuid, **data.model_dump()
    )
    database_session.add(application)
    database_session.commit()
    database_session.refresh(application)
    return application


@router.get(
    "/subcommittee/me", response_model=SubcommitteeApplicationInformation
)
def read_my_subcommittee_application(
    alumna: CurrentAlumna, database_session: DBSession
) -> SubcommitteeApplication:
    application = database_session.scalar(
        select(SubcommitteeApplication).where(
            SubcommitteeApplication.alumna_uuid == alumna.uuid
        )
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-committee application not found",
        )
    return application


@router.put(
    "/subcommittee/me", response_model=SubcommitteeApplicationInformation
)
def update_my_subcommittee_application(
    data: SubcommitteeApplicationInput,
    alumna: CurrentAlumna,
    database_session: DBSession,
) -> SubcommitteeApplication:
    ensure_open("subcommittee", database_session, now=now)
    application = database_session.scalar(
        select(SubcommitteeApplication).where(
            SubcommitteeApplication.alumna_uuid == alumna.uuid
        )
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-committee application not found",
        )
    if application.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application can no longer be edited",
        )

    for field, value in data.model_dump().items():
        setattr(application, field, value)
    application.updated_at = now()
    database_session.add(application)
    database_session.commit()
    database_session.refresh(application)
    return application
