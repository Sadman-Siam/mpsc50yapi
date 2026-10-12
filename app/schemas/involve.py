from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.constants import SUBCOMMITTEE_NAMES
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
