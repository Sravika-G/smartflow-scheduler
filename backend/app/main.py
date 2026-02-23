import os
import redis
import json
from typing import Any, Optional, Dict
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

class CreateJobRequest(BaseModel):
    type: str = Field(..., min_length=1)
    payload: Optional[Dict[str, Any]] = None
    priority: int = Field(5, ge=1, le=10)
    max_attempts: int = Field(3, ge=1, le=10)

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
def create_job(req: CreateJobRequest, db: Session = Depends(get_db)):
    job_id = str(uuid4())

    payload_str = json.dumps(req.payload) if req.payload is not None else None

    job_row = JobModel(
        id=job_id,
        type=req.type,
        payload=payload_str,
        priority=req.priority,
        status="queued",
        attempts=0,
        max_attempts=req.max_attempts,
        last_error=None,
    )

    db.add(job_row)
    db.commit()
    db.refresh(job_row)

    # Push job id to Redis queue
    rdb.rpush(QUEUE_KEY, job_id)

    return {
        "id": job_row.id,
        "type": job_row.type,
        "payload": req.payload,
        "priority": job_row.priority,
        "status": job_row.status,
        "attempts": job_row.attempts,
        "max_attempts": job_row.max_attempts,
        "last_error": job_row.last_error,
        "created_at": job_row.created_at,
        "updated_at": job_row.updated_at,
        "started_at": job_row.started_at,
        "completed_at": job_row.completed_at,
    }

@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    rows = db.query(JobModel).order_by(JobModel.created_at.desc()).all()

    result = []
    for r in rows:
        payload_obj = None
        if r.payload:
            try:
                payload_obj = json.loads(r.payload)
            except Exception:
                payload_obj = {"_raw": r.payload}

        result.append({
            "id": r.id,
            "type": r.type,
            "payload": payload_obj,
            "priority": r.priority,
            "status": r.status,
            "attempts": r.attempts,
            "max_attempts": r.max_attempts,
            "last_error": r.last_error,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
        })

    return result

@app.post("/jobs/{job_id}/start")
def start_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "queued":
        raise HTTPException(status_code=400, detail=f"Job is not queued (status={job.status})")

    job.status = "running"
    job.started_at = datetime.utcnow()
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
    job.completed_at = datetime.utcnow()
    job.touch()
    db.commit()

    return {"id": job.id, "status": job.status}