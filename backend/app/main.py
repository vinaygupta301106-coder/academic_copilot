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

@app.get("/health")
@app.head("/health")
@app.get("/api/v1/health")
@app.head("/api/v1/health")
def health_check():
    """Lightweight health check endpoint for external uptime monitors."""
    import os
    import urllib.request
    from sqlalchemy import text
    from app.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    from neo4j import GraphDatabase

    status = {
        "status": "healthy",
        "service": "Academic Pathway Copilot API",
        "components": {
            "api": "online",
            "mysql": "unknown",
            "neo4j": "unknown",
            "ollama": "unknown",
        }
    }

    try:
        with mysql_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            status["components"]["mysql"] = "connected"
    except Exception as exc:
        status["components"]["mysql"] = f"error: {str(exc)[:60]}"

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
        status["components"]["neo4j"] = "connected"
    except Exception as exc:
        status["components"]["neo4j"] = f"error: {str(exc)[:60]}"

    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        req = urllib.request.Request(f"{ollama_host.rstrip('/')}/api/version", headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as r:
            if r.status in (200, 204):
                status["components"]["ollama"] = "available"
            else:
                status["components"]["ollama"] = f"status_{r.status}"
    except Exception:
        status["components"]["ollama"] = "offline_or_sleeping"

    return status
