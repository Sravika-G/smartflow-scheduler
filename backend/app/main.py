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
from datetime import timedelta

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

def backoff_seconds(attempt: int) -> int:
    # attempt is 1-based after the failure has been counted
    if attempt == 1:
        return 10
    if attempt == 2:
        return 30
    if attempt == 3:
        return 90
    return 300

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

    now = datetime.utcnow()
    if job.next_run_at is not None and job.next_run_at > now:
        raise HTTPException(status_code=409, detail="Job not ready to run yet")

    if not job.locked_by or not job.lock_expires_at or job.lock_expires_at <= now:
        raise HTTPException(status_code=409, detail="Job has no valid lease")

    job.status = "running"
    job.started_at = datetime.utcnow()
    job.next_run_at = None
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
    job.locked_by = None
    job.lock_expires_at = None
    job.touch()
    db.commit()

    return {"id": job.id, "status": job.status}

class FailJobRequest(BaseModel):
    error: str = Field(..., min_length=1)

@app.post("/jobs/{job_id}/fail")
def fail_job(job_id: str, req: FailJobRequest, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # only running jobs should fail
    if job.status != "running":
        raise HTTPException(status_code=400, detail=f"Job is not running (status={job.status})")

    job.attempts += 1
    job.last_error = req.error

    if job.attempts >= job.max_attempts:
        job.status = "dead"
        job.touch()
        db.commit()
        return {"id": job.id, "status": job.status, "attempts": job.attempts, "next_run_at": job.next_run_at}

    delay = backoff_seconds(job.attempts)
    job.status = "queued"
    job.next_run_at = datetime.utcnow() + timedelta(seconds=delay)
    job.locked_by = None
    job.lock_expires_at = None
    job.touch()
    db.commit()

    return {"id": job.id, "status": job.status, "attempts": job.attempts, "next_run_at": job.next_run_at}

@app.post("/jobs/requeue-ready")
def requeue_ready_jobs(limit: int = 50, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    rows = (
        db.query(JobModel)
        .filter(JobModel.status == "queued")
        .filter((JobModel.next_run_at == None) | (JobModel.next_run_at <= now))
        .order_by(JobModel.priority.desc(), JobModel.created_at.asc())
        .limit(limit)
        .all()
    )

    pushed = 0
    for job in rows:
        # Push to Redis. (Duplicate pushes are possible; we’ll guard in /start)
        rdb.rpush(QUEUE_KEY, job.id)
        pushed += 1

    return {"requeued": pushed}

class LeaseJobRequest(BaseModel):
    worker_id: str = Field(..., min_length=1)
    lease_seconds: int = Field(30, ge=5, le=300)  # lease between 5s and 5min

@app.post("/jobs/{job_id}/lease")
def lease_job(job_id: str, req: LeaseJobRequest, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Only allow leasing queued jobs that are ready
    now = datetime.utcnow()
    if job.status != "queued":
        raise HTTPException(status_code=409, detail=f"Job not leaseable (status={job.status})")

    if job.next_run_at is not None and job.next_run_at > now:
        raise HTTPException(status_code=409, detail="Job not ready yet")

    # If locked and not expired, deny
    if job.lock_expires_at is not None and job.lock_expires_at > now and job.locked_by:
        raise HTTPException(status_code=409, detail=f"Job already leased by {job.locked_by}")

    # Grant lease
    job.locked_by = req.worker_id
    job.lock_expires_at = now + timedelta(seconds=req.lease_seconds)
    job.touch()
    db.commit()

    return {
        "id": job.id,
        "locked_by": job.locked_by,
        "lock_expires_at": job.lock_expires_at
    }

@app.post("/system/reconcile")
def reconcile(limit: int = 50, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    recovered = 0
    requeued = 0
    deaded = 0

    # 1) Recover jobs that are "running" but lease expired (worker died)
    stuck = (
        db.query(JobModel)
        .filter(JobModel.status == "running")
        .filter(JobModel.lock_expires_at != None)
        .filter(JobModel.lock_expires_at <= now)
        .limit(limit)
        .all()
    )

    for job in stuck:
        # count this as a failure attempt because worker died mid-run
        job.attempts += 1
        job.last_error = "Worker lease expired (worker likely crashed)"

        # clear lock
        job.locked_by = None
        job.lock_expires_at = None

        if job.attempts >= job.max_attempts:
            job.status = "dead"
            deaded += 1
        else:
            delay = backoff_seconds(job.attempts)
            job.status = "queued"
            job.next_run_at = now + timedelta(seconds=delay)
            recovered += 1

        job.touch()

    db.commit()

    # 2) Requeue ready queued jobs into Redis
    ready = (
        db.query(JobModel)
        .filter(JobModel.status == "queued")
        .filter((JobModel.next_run_at == None) | (JobModel.next_run_at <= now))
        .order_by(JobModel.priority.desc(), JobModel.created_at.asc())
        .limit(limit)
        .all()
    )

    for job in ready:
        rdb.rpush(QUEUE_KEY, job.id)
        requeued += 1

    return {
        "recovered_running": recovered,
        "deaded": deaded,
        "requeued": requeued
    }

@app.post("/jobs/{job_id}/crash")
def crash_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # simulate worker died: keep status running, but don't complete it
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.touch()
    db.commit()
    return {"id": job.id, "status": job.status}