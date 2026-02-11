from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException

app = FastAPI(title="SmartFlow Scheduler")

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
def create_job(job_type: str):
    job = Job(
        id=str(uuid4()),
        type=job_type,
        status="queued",
        created_at=datetime.utcnow()
    )
    jobs.append(job)
    return job

@app.get("/jobs")
def list_jobs():
    return jobs

@app.post("/jobs/{job_id}/start")
def start_job(job_id: str):
    for idx, job in enumerate(jobs):
        if job.id == job_id:
            if job.status != "queued":
                raise HTTPException(status_code=400, detail="Job is not queued")
            jobs[idx] = job.copy(update={"status": "running"})
            return jobs[idx]
    raise HTTPException(status_code=404, detail="Job not found")


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str):
    for idx, job in enumerate(jobs):
        if job.id == job_id:
            if job.status != "running":
                raise HTTPException(status_code=400, detail="Job is not running")
            jobs[idx] = job.copy(update={"status": "completed"})
            return jobs[idx]
    raise HTTPException(status_code=404, detail="Job not found")