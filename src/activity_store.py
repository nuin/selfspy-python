"""
Activity data storage implementation
"""

import asyncio
from pathlib import Path
from typing import Optional, Tuple

import structlog
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from .config import Settings
from .encryption import check_password, create_cipher
from .models import Base, Click, Keys, Process, Window

logger = structlog.get_logger()


class ActivityStore:
    """Asynchronous activity data store"""

    def __init__(self, settings: Settings, password: Optional[str] = None):
        """Initialize activity store (sync only - call initialize() to complete setup)"""
        self.settings = settings
        self.password = password

        # Initialize SQLAlchemy engine
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{settings.database_path}",
            echo=settings.debug,
            pool_pre_ping=True,  # Enable connection health checks
        )

        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create cipher with installation-specific salt
        self.cipher = create_cipher(password, settings.data_dir) if password else None
        self.current_window_id: Optional[int] = None
        self.current_process_id: Optional[int] = None
        self._initialized = False

    def _run_migrations(self):
        """Run Alembic migrations to upgrade database schema"""
        try:
            # Find the alembic.ini file
            project_root = Path(__file__).parent.parent
            alembic_cfg_path = project_root / "alembic.ini"

            if not alembic_cfg_path.exists():
                logger.warning("No alembic.ini found, skipping migrations")
                return

            # Configure Alembic
            alembic_cfg = Config(str(alembic_cfg_path))
            alembic_cfg.set_main_option("sqlalchemy.url", str(self.settings.database_path).replace("sqlite:///", "sqlite:///"))

            # Run migrations to head
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations completed successfully")

        except Exception as e:
            logger.warning(f"Migration failed, will use create_all fallback: {e}")
            # Fallback to create_all if migrations fail
            raise

    async def initialize(self):
        """Initialize database and verify encryption password"""
        if self._initialized:
            return

        # Try to run migrations first
        try:
            await asyncio.to_thread(self._run_migrations)
        except Exception as e:
            logger.info(f"Migrations not available or failed ({e}), using create_all")
            # Fallback: Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        # Verify encryption password if encryption is enabled
        if self.settings.encryption_enabled:
            password_valid = await check_password(
                self.settings.data_dir, self.cipher, self.settings.read_only
            )
            if not password_valid:
                raise ValueError("Invalid encryption password")

        self._initialized = True
        logger.info("Activity store initialized successfully")

    async def update_window_info(
        self,
        process_name: str,
        window_title: str,
        bundle: str,
        geometry: Optional[Tuple[int, int, int, int]] = None,
    ):
        """Update current window information"""
        async with self.async_session() as session:
            async with session.begin():
                # Get or create process
                process = await session.scalar(
                    select(Process).where(Process.name == process_name)
                )
                if not process:
                    process = Process(name=process_name, bundle_id=bundle)
                    session.add(process)
                    await session.flush()

                # Update current process ID
                self.current_process_id = process.id

                # Create window record
                window = Window(title=window_title, process_id=process.id)

                # Add geometry if provided
                if geometry:
                    x, y, width, height = geometry
                    window.x = x
                    window.y = y
                    window.width = width
                    window.height = height

                session.add(window)
                await session.flush()

                # Update current window ID
                self.current_window_id = window.id

    async def store_keys(self, text: str):
        """Store keystroke data"""
        if not self.current_process_id or not self.current_window_id:
            return

        encrypted_text = self._encrypt_text(text)

        async with self.async_session() as session:
            async with session.begin():
                keys = Keys(
                    text=encrypted_text,
                    count=len(text),
                    process_id=self.current_process_id,
                    window_id=self.current_window_id,
                )
                session.add(keys)

    async def store_click(self, button: int, x: int, y: int):
        """Store mouse click data"""
        if not self.current_process_id or not self.current_window_id:
            return

        async with self.async_session() as session:
            async with session.begin():
                click = Click(
                    button=button,
                    x=x,
                    y=y,
                    process_id=self.current_process_id,
                    window_id=self.current_window_id,
                )
                session.add(click)

    def _encrypt_text(self, text: str) -> bytes:
        """Encrypt text data"""
        if not self.cipher:
            return text.encode()

        padding = 8 - (len(text) % 8)
        padded_text = text + "\0" * padding
        return self.cipher.encrypt(padded_text.encode())

    async def close(self):
        """Clean up database connection"""
        await self.engine.dispose()
