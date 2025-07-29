# src/platform/screen_capture.py
"""
Enhanced screen capture functionality for macOS with periodic and smart capture modes
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import aiofiles
import structlog

logger = structlog.get_logger()


class MacScreenCapture:
    """
    Enhanced macOS screen capture with periodic and smart capture capabilities
    """

    def __init__(
        self,
        output_dir: Union[str, Path] = "./screenshots",
        periodic_interval: int = 300,  # 5 minutes
        max_daily_captures: int = 100,
        min_window_duration: int = 10,  # seconds
        excluded_apps: Optional[List[str]] = None,
    ):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.periodic_interval = periodic_interval
        self.max_daily_captures = max_daily_captures
        self.min_window_duration = min_window_duration
        self.excluded_apps = set(excluded_apps or [])

        # State tracking
        self.last_capture = datetime.now()
        self.daily_captures = 0
        self.last_reset_date = datetime.now().date()
        self.capture_history: Set[str] = set()  # Track unique window titles
        self.current_window: Optional[Dict] = None
        self.window_start_time: Optional[datetime] = None

        # Background task handle
        self.periodic_task: Optional[asyncio.Task] = None
        self.running = False

    async def start_periodic_capture(self):
        """Start periodic screen capture"""
        if self.periodic_task and not self.periodic_task.done():
            return

        self.running = True
        self.periodic_task = asyncio.create_task(self._periodic_capture_loop())
        logger.info("Started periodic screen capture", interval=self.periodic_interval)

    async def stop_periodic_capture(self):
        """Stop periodic screen capture"""
        self.running = False
        if self.periodic_task and not self.periodic_task.done():
            self.periodic_task.cancel()
            try:
                await self.periodic_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped periodic screen capture")

    async def _periodic_capture_loop(self):
        """Background loop for periodic captures"""
        while self.running:
            try:
                # Reset daily counter if needed
                current_date = datetime.now().date()
                if current_date != self.last_reset_date:
                    self.daily_captures = 0
                    self.last_reset_date = current_date
                    self.capture_history.clear()

                # Check if we should capture
                if (
                    self.daily_captures < self.max_daily_captures
                    and (datetime.now() - self.last_capture).seconds
                    >= self.periodic_interval
                ):
                    await self.smart_capture()

            except Exception as e:
                logger.error("Periodic capture error", error=str(e))

            await asyncio.sleep(min(60, self.periodic_interval))

    async def update_window_info(self, window_info: Dict):
        """Update current window information and trigger smart capture"""
        if window_info != self.current_window:
            # Check if previous window meets duration threshold
            if (
                self.current_window
                and self.window_start_time
                and (datetime.now() - self.window_start_time).seconds
                >= self.min_window_duration
            ):
                await self.smart_capture()

            self.current_window = window_info
            self.window_start_time = datetime.now()

    async def smart_capture(self):
        """Smart capture based on window context and history"""
        if not self.current_window:
            return

        app_name = self.current_window.get("process", "")
        window_title = self.current_window.get("title", "")

        # Skip if app is excluded
        if app_name in self.excluded_apps:
            return

        # Generate unique key for this window state
        window_key = f"{app_name}:{window_title}"

        # Only capture if we haven't seen this window before today
        if (
            window_key not in self.capture_history
            and self.daily_captures < self.max_daily_captures
        ):
            screenshot_path = await self.capture(
                window=True, filename=self._generate_filename(app_name, window_title)
            )

            if screenshot_path and screenshot_path.exists():
                self.capture_history.add(window_key)
                self.daily_captures += 1
                self.last_capture = datetime.now()

                # Save metadata
                await self._save_metadata(screenshot_path, self.current_window)

                logger.info(
                    "Smart capture successful",
                    app=app_name,
                    captures_today=self.daily_captures,
                )

    async def capture(
        self,
        filename: Optional[str] = None,
        window: bool = False,
        interactive: bool = False,
        screen: Optional[int] = None,
        clipboard: bool = False,
        no_shadow: bool = False,
    ) -> Optional[Path]:
        """
        Capture screen or window using native macOS screencapture command.
        """
        # Build command
        cmd = ["screencapture"]

        if interactive:
            cmd.append("-i")
        if window:
            cmd.append("-w")
        if clipboard:
            cmd.append("-c")
        if screen is not None:
            cmd.extend(["-D", str(screen)])
        if no_shadow:
            cmd.append("-o")

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"

        output_path = self.output_dir / filename
        cmd.append(str(output_path))

        # Execute capture
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and output_path.exists():
                return output_path
            else:
                logger.error(
                    "Capture failed",
                    returncode=process.returncode,
                    stderr=stderr.decode() if stderr else None,
                )
                return None

        except Exception as e:
            logger.error("Capture error", error=str(e))
            return None

    def _generate_filename(self, app_name: str, window_title: str) -> str:
        """Generate filename for screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean up app name and window title for filename
        app_name = "".join(c for c in app_name if c.isalnum() or c in (" ", "-", "_"))
        window_title = "".join(
            c for c in window_title[:50] if c.isalnum() or c in (" ", "-", "_")
        )
        return f"{timestamp}_{app_name}_{window_title}.png"

    async def _save_metadata(self, screenshot_path: Path, window_info: Dict):
        """Save metadata for screenshot"""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "app_name": window_info.get("process"),
            "window_title": window_info.get("title"),
            "bundle_id": window_info.get("bundle"),
        }

        metadata_path = screenshot_path.with_suffix(".json")
        try:
            async with aiofiles.open(metadata_path, "w") as f:
                await f.write(json.dumps(metadata, indent=2))
        except Exception as e:
            logger.error("Failed to save metadata", error=str(e))

    async def cleanup_old_captures(self, max_age_days: int = 30):
        """Clean up old captures and metadata"""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            for file_path in self.output_dir.glob("*"):
                if file_path.is_file():
                    file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_date < cutoff_date:
                        file_path.unlink()
                        # Remove corresponding metadata if it exists
                        metadata_path = file_path.with_suffix(".json")
                        if metadata_path.exists():
                            metadata_path.unlink()

            logger.info("Cleaned up old captures", max_age_days=max_age_days)

        except Exception as e:
            logger.error("Cleanup error", error=str(e))

    def get_capture_stats(self) -> Dict:
        """Get capture statistics"""
        return {
            "daily_captures": self.daily_captures,
            "max_daily_captures": self.max_daily_captures,
            "unique_windows_captured": len(self.capture_history),
            "last_capture": self.last_capture.isoformat(),
            "periodic_interval": self.periodic_interval,
            "excluded_apps": list(self.excluded_apps),
        }
