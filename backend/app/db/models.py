from sqlalchemy import Column, String, DateTime, Integer, Text
from datetime import datetime
from .database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False)

    payload = Column(Text, nullable=True)          # JSON string
    priority = Column(Integer, nullable=False, default=5)

    status = Column(String, nullable=False, default="queued")

    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)

    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    def touch(self):
        self.updated_at = datetime.utcnow()