from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app import models  # noqa: F401  (registers all tables)
from app.database import engine
from app.routes import auth


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MPSC 50 Years Alumni API",
    version="1.0.0",
    description="Backend for the 50 years celebrations event.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://mpsc50years.docufybd.com",
        "http://mpsc50years.docufybd.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/")
def health_check():
    return {"message": "MPSC 50 Years Alumni API is running"}
