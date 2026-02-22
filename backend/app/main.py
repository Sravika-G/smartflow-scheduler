import os
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from app.db.database import Base, SessionLocal, engine
from app.db.models import Job as JobModel  # noqa: E402 - register model with Base
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="SmartFlow Scheduler")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
rdb = redis.from_url(REDIS_URL, decode_responses=True)
QUEUE_KEY = "smartflow:queue"

class Job(BaseModel):
    id: str
    type: str
    status: str
    created_at: datetime

jobs = []

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(job_type: str, db: Session = Depends(get_db)):
    job_id = str(uuid4())

    job_row = JobModel(
        id=job_id,
        type=job_type,
        status="queued"
    )
    db.add(job_row)
    db.commit()

    # push job id into Redis queue
    rdb.rpush(QUEUE_KEY, job_id)

    return {
        "id": job_id,
        "type": job_type,
        "status": "queued",
        "created_at": job_row.created_at
    }

@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    rows = db.query(JobModel).order_by(JobModel.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "type": r.type,
            "status": r.status,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]

@app.post("/jobs/{job_id}/start")
def start_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "queued":
        raise HTTPException(status_code=400, detail=f"Job is not queued (status={job.status})")

    job.status = "running"
    job.touch()
    db.commit()

    return {"id": job.id, "status": job.status}


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "running":
        raise HTTPException(status_code=400, detail=f"Job is not running (status={job.status})")

    job.status = "completed"
    job.touch()
    db.commit()

    return {"id": job.id, "status": job.status}