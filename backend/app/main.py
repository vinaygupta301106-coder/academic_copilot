from fastapi import FastAPI, Request
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from app.config import MYSQL_DATABASE_URL
from app.routers import courses, students, copilot, advisor, auth

app = FastAPI(title="Policy-Aware Academic Pathway Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses.router)
app.include_router(students.router)
app.include_router(copilot.router)
app.include_router(advisor.router)
app.include_router(auth.router)

mysql_engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True)

@app.on_event("startup")
def startup():
    students.init_student_storage()
    copilot.init_copilot_usage_storage()
    advisor.init_advisor_storage()

@app.get("/")
def home():
    return {"message": "Academic Pathway Copilot API is active!"}
