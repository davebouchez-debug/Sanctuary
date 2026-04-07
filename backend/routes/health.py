"""
Health and status endpoints.
"""
from fastapi import APIRouter
from typing import List
from datetime import datetime, timezone
import uuid

from db import db
from models import StatusCheck, StatusCheckCreate

router = APIRouter(prefix="/api")


@router.get("/")
async def root():
    return {"message": "Sanctuary Microverse V3.0 API", "status": "active"}


@router.get("/health")
async def health():
    return {"status": "healthy", "ark_status": "BUILT AND LAUNCHED"}


@router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = {
        "id": str(uuid.uuid4()),
        "client_name": input.client_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.status_checks.insert_one(status_dict)
    status_dict.pop("_id", None)
    return StatusCheck(**status_dict)


@router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks
