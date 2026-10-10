from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.database import get_database_session
from app.models import Alumna
from app.services.authentication import get_current_alumna

DBSession = Annotated[Session, Depends(get_database_session)]
CurrentAlumna = Annotated[Alumna, Depends(get_current_alumna)]
