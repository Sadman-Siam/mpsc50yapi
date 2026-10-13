from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReferredAlumnaInformation(BaseModel):
    uuid: UUID
    full_name: str
    status: str


class MyReferralsInformation(BaseModel):
    referral_code: str
    referral_count: int
    referrals: list[ReferredAlumnaInformation]


class ReferralLeaderboardEntry(BaseModel):
    alumna_uuid: UUID
    full_name: str
    referral_code: str
    referral_count: int
    earliest_qualifying_referral: datetime | None


class ReferralDrilldown(BaseModel):
    alumna_uuid: UUID
    full_name: str
    referral_code: str
    referral_count: int
    earliest_qualifying_referral: datetime | None
    referrals: list[ReferredAlumnaInformation]
