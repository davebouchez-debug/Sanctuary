"""
Pydantic models shared across routes.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid


class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class ClarityMessageCreate(BaseModel):
    session_id: str
    content: str


class ClaritySessionCreate(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    email: Optional[str] = None
    created_at: str
    session_count: int = 0


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=4096, description="Text to convert to speech")
    presence: str = Field(default="jasmine", description="Which presence voice to use")


class ClarityUploadCreate(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    filename: str
    content: str


class CanonicalUploadCreate(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    filename: str
    content: str


class FluteAnalysisCreate(BaseModel):
    user_id: Optional[str] = None
    instrument_name: str
    maker: Optional[str] = None
    year: Optional[str] = None
    toneholes: list
    notes: Optional[str] = None
    thread_reference: Optional[str] = None
