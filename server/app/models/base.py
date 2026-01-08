"""
Base Model Classes and Mixins

Provides common functionality for all SQLAlchemy models.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class GUIDType(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses String(36) for SQLite compatibility.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(str(value)))
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


# Alias JSON for external use if needed, though we'll use sqlalchemy.types.JSON
JSON_TYPE = JSON


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class UUIDMixin:
    """Mixin that adds a UUID primary key."""
    
    id: Mapped[uuid.UUID] = mapped_column(
        GUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
