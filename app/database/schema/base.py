
from sqlalchemy import (
    create_engine, Engine, Column,  ForeignKey, PrimaryKeyConstraint, 
    Integer, String, Boolean, Float, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base, DeclarativeBase, Session, sessionmaker, relationship
from typing import cast, Optional, Any, Iterable, Literal
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
import uuid
from datetime import datetime, timezone

Base: DeclarativeBase = declarative_base()

def generate_id() -> str:
    return str(uuid.uuid4())
def datetime_now() -> datetime:
    return datetime.now(timezone.utc)

def extra_data() -> dict:
    return {}