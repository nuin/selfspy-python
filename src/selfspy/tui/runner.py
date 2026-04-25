"""TUI runner — drives the SelfspyApp from a running Monitor."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from .app import SelfspyApp
from .tabs.apps import AppData

if TYPE_CHECKING:
    from ..core.monitor import Monitor

logger = structlog.get_logger()


async def run_tui(monitor: Monitor) -> None:
    """Run the Textual TUI bound to the given monitor."""
    app = SelfspyApp()

    async def update_loop() -> None:
        while monitor.running and not monitor._shutdown_event.is_set():
            try:
                await monitor._check_active_window()
                await monitor._flush_buffer()
                monitor._update_metrics()

                state = monitor.get_current_state()

                app.update_live_metrics(
                    keystrokes=state["keystrokes"],
                    clicks=state["clicks"],
                    keys_per_min=state["keys_per_min"],
                    clicks_per_min=state["clicks_per_min"],
                    current_window=state["current_window"],
                    status=state["status"],
                    session_duration=state["session_duration"],
                )

                if state["keystroke_history"]:
                    app.add_activity_samples(
                        state["keystroke_history"][-1]
                        if state["keystroke_history"]
                        else 0,
                        state["click_history"][-1] if state["click_history"] else 0,
                    )

                apps = [
                    AppData(
                        name=a["name"],
                        keystrokes=a["keystrokes"],
                        clicks=a["clicks"],
                        activity_percent=a["activity_percent"],
                    )
                    for a in state["apps"]
                ]
                app.update_apps(apps)

                app.update_summary(
                    session_duration=state["session_duration"],
                    active_time=state["active_time"],
                    active_percent=state["active_percent"],
                    idle_time=state["idle_time"],
                    idle_percent=state["idle_percent"],
                    total_keystrokes=state["keystrokes"],
                    total_clicks=state["clicks"],
                    windows_switched=state["windows_switched"],
                    yesterday_diff=state["yesterday_diff"],
                    more_active=state["more_active"],
                )

                await asyncio.sleep(1)
            except Exception as e:
                logger.error("TUI update error", error=str(e))
                await asyncio.sleep(1)

    update_task = asyncio.create_task(update_loop())
    try:
        await app.run_async()
    finally:
        monitor.running = False
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass
