"""
SQLAlchemy models for Selfspy using modern features and macOS support
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""

    pass


class TimestampMixin:
    """Mixin for timestamp fields"""

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )


class Process(TimestampMixin, Base):
    """Process information"""

    __tablename__ = "process"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    bundle_id: Mapped[Optional[str]] = mapped_column(
        index=True
    )  # macOS bundle identifier

    # Relationships
    windows: Mapped[list["Window"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    keys: Mapped[list["Keys"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    clicks: Mapped[list["Click"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Process '{self.name}'>"


class Window(TimestampMixin, Base):
    """Window information with macOS support"""

    __tablename__ = "window"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, index=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("process.id"), index=True)

    # macOS specific fields
    bundle_id: Mapped[Optional[str]] = mapped_column(index=True)
    is_minimized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fullscreen: Mapped[bool] = mapped_column(Boolean, default=False)

    # Window geometry
    geometry_x: Mapped[Optional[int]]
    geometry_y: Mapped[Optional[int]]
    geometry_width: Mapped[Optional[int]]
    geometry_height: Mapped[Optional[int]]

    # Screen information
    screen_width: Mapped[Optional[int]]
    screen_height: Mapped[Optional[int]]
    display_index: Mapped[Optional[int]] = mapped_column(default=0)

    # Relationships
    process: Mapped[Process] = relationship(back_populates="windows")
    keys: Mapped[list["Keys"]] = relationship(
        back_populates="window", cascade="all, delete-orphan"
    )
    clicks: Mapped[list["Click"]] = relationship(
        back_populates="window", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Window '{self.title}'>"


class Keys(TimestampMixin, Base):
    """Keystroke information"""

    __tablename__ = "keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[bytes]  # Encrypted text
    count: Mapped[int] = mapped_column(index=True)  # Number of keystrokes

    # Foreign keys
    process_id: Mapped[int] = mapped_column(ForeignKey("process.id"), index=True)
    window_id: Mapped[int] = mapped_column(ForeignKey("window.id"))

    # Relationships
    process: Mapped[Process] = relationship(back_populates="keys")
    window: Mapped[Window] = relationship(back_populates="keys")

    def decrypt_text(self, cipher=None) -> str:
        """Decrypt stored text"""
        if cipher:
            try:
                decrypted = cipher.decrypt(self.text)
                return decrypted.decode("utf-8").rstrip("\0")
            except Exception:
                return ""
        return self.text.decode("utf-8")


class Click(TimestampMixin, Base):
    """Mouse click information"""

    __tablename__ = "click"

    id: Mapped[int] = mapped_column(primary_key=True)
    button: Mapped[int]  # 1=left, 2=middle, 3=right, 4=scroll up, 5=scroll down
    x: Mapped[int]
    y: Mapped[int]

    # Mouse movement tracking
    move_distance: Mapped[int] = mapped_column(default=0)  # Total pixels moved
    move_points: Mapped[Optional[str]]  # JSON string of movement coordinates

    # Foreign keys
    process_id: Mapped[int] = mapped_column(ForeignKey("process.id"), index=True)
    window_id: Mapped[int] = mapped_column(ForeignKey("window.id"))

    # Relationships
    process: Mapped[Process] = relationship(back_populates="clicks")
    window: Mapped[Window] = relationship(back_populates="clicks")

    def __repr__(self) -> str:
        return f"<Click ({self.x}, {self.y}), button={self.button}>"


# Add indexes for common queries
Index("ix_process_name_created", Process.name, Process.created_at)
Index("ix_process_bundle", Process.bundle_id)
Index("ix_window_title_created", Window.title, Window.created_at)
Index("ix_window_geometry", Window.geometry_x, Window.geometry_y)
Index("ix_click_coords", Click.x, Click.y)
Index("ix_click_timestamp", Click.created_at)
