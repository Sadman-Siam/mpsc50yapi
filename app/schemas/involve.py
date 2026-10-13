from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.constants import SUBCOMMITTEE_NAMES
from app.settings import settings
from app.types import SubmissionStatus


class SubcommitteeApplicationInput(BaseModel):
    first_choice: str
    second_choice: str | None = None
    motivation: str
    availability_notes: str | None = Field(default=None, max_length=500)

    @field_validator("first_choice")
    @classmethod
    def validate_first_choice(cls, value: str) -> str:
        if value not in SUBCOMMITTEE_NAMES:
            raise ValueError("Invalid sub-committee choice")
        return value

    @field_validator("second_choice")
    @classmethod
    def validate_second_choice(cls, value: str | None) -> str | None:
        if value is not None and value not in SUBCOMMITTEE_NAMES:
            raise ValueError("Invalid sub-committee choice")
        return value

    @field_validator("motivation")
    @classmethod
    def validate_motivation(cls, value: str) -> str:
        value = value.strip()
        if not 20 <= len(value) <= 1000:
            raise ValueError("Motivation must be between 20 and 1000 characters")
        return value

    @model_validator(mode="after")
    def validate_distinct_choices(self):
        if self.second_choice == self.first_choice:
            raise ValueError("Choices must be different")
        return self


class SubcommitteeApplicationInformation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    first_choice: str
    second_choice: str | None
    motivation: str
    availability_notes: str | None
    status: SubmissionStatus
    admin_note: str | None
    created_at: datetime
    updated_at: datetime


class SponsorOfferInput(BaseModel):
    sponsor_type: Literal["individual", "company", "in_kind"]
    sponsor_name: str = Field(min_length=1, max_length=200)
    contact_person: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=5, max_length=16)
    email: EmailStr
    proposed_amount_bdt: int | None = Field(default=None, gt=0)
    in_kind_description: str | None = Field(default=None, max_length=2000)
    message: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_sponsor_fields(self):
        if self.sponsor_type == "company" and not self.sponsor_name.strip():
            raise ValueError("Company sponsorship requires a company name")
        if self.sponsor_type == "in_kind" and not (self.in_kind_description or "").strip():
            raise ValueError("In-kind sponsorship requires a description")
        if self.sponsor_type != "in_kind" and self.proposed_amount_bdt is None:
            raise ValueError("Proposed amount is required for cash sponsorship")
        return self

    @field_validator("sponsor_name", "contact_person", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class SponsorOfferInformation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    sponsor_type: Literal["individual", "company", "in_kind"]
    sponsor_name: str
    contact_person: str
    phone: str
    email: EmailStr
    proposed_amount_bdt: int | None
    in_kind_description: str | None
    message: str
    status: SubmissionStatus
    admin_note: str | None
    created_at: datetime


class OpenMicEntryInput(BaseModel):
    performance_type: Literal[
        "singer", "musician", "poet", "storyteller", "stand-up", "dancer", "other"
    ]
    title_or_description: str = Field(min_length=1, max_length=1000)
    duration_minutes: int = Field(ge=1)
    needs_equipment_or_accompaniment: bool
    equipment_notes: str | None = Field(default=None, max_length=1000)
    performance_link: str | None = Field(default=None, max_length=2048)

    @field_validator("title_or_description", "equipment_notes")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value and value == "":
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value > settings.openmic_max_duration_minutes:
            raise ValueError(
                f"Duration must not exceed {settings.openmic_max_duration_minutes} minutes"
            )
        return value

    @field_validator("performance_link")
    @classmethod
    def validate_link(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Performance link must be an http or https URL")
        return value


class OpenMicEntryInformation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    performance_type: Literal[
        "singer", "musician", "poet", "storyteller", "stand-up", "dancer", "other"
    ]
    title_or_description: str
    duration_minutes: int
    needs_equipment_or_accompaniment: bool
    equipment_notes: str | None
    performance_link: str | None
    status: SubmissionStatus
    admin_note: str | None
    scheduled_slot: str | None
    created_at: datetime
