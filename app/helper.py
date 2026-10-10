from datetime import UTC, datetime
from uuid import uuid4


def now() -> datetime:
    return datetime.now(UTC)


def generate_reg_code() -> str:
    return uuid4().hex[:12].upper()
