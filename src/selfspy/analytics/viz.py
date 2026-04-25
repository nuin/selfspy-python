"""Pure analytics for enhanced/visualization stats. DB I/O only; no Rich/Typer."""

from collections import namedtuple
from datetime import datetime, timedelta

from sqlalchemy import distinct, extract, func, select

from ..storage import Click, Keys, Process, Store, Window


async def get_enhanced_stats(store: Store, days: int) -> dict:
    """Get enhanced statistics data as plain data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Use subqueries to avoid cartesian product
        keystroke_subq = (
            select(Keys.process_id, func.sum(Keys.count).label("keystroke_count"))
            .where(Keys.created_at >= start_date)
            .group_by(Keys.process_id)
            .subquery()
        )

        click_subq = (
            select(Click.process_id, func.count(Click.id).label("click_count"))
            .where(Click.created_at >= start_date)
            .group_by(Click.process_id)
            .subquery()
        )

        # Enhanced process stats with more details
        process_query = (
            select(
                Process.name,
                Process.bundle_id,
                func.count(distinct(Window.id)).label("window_count"),
                func.coalesce(keystroke_subq.c.keystroke_count, 0).label(
                    "keystroke_count"
                ),
                func.coalesce(click_subq.c.click_count, 0).label("click_count"),
                func.min(Window.created_at).label("first_seen"),
                func.max(Window.created_at).label("last_seen"),
            )
            .select_from(Process)
            .join(Window, Process.id == Window.process_id)
            .outerjoin(keystroke_subq, Process.id == keystroke_subq.c.process_id)
            .outerjoin(click_subq, Process.id == click_subq.c.process_id)
            .where(Window.created_at >= start_date)
            .group_by(
                Process.name,
                Process.bundle_id,
                keystroke_subq.c.keystroke_count,
                click_subq.c.click_count,
            )
            .order_by(
                (
                    func.coalesce(keystroke_subq.c.keystroke_count, 0)
                    + func.coalesce(click_subq.c.click_count, 0)
                ).desc()
            )
        )

        process_stats = await session.execute(process_query)

        keystroke_total = await session.execute(
            select(func.coalesce(func.sum(Keys.count), 0)).where(
                Keys.created_at >= start_date
            )
        )
        total_keystrokes = keystroke_total.scalar()

        click_total = await session.execute(
            select(func.count(Click.id)).where(Click.created_at >= start_date)
        )
        total_clicks = click_total.scalar()

        window_total = await session.execute(
            select(func.count(distinct(Window.id))).where(
                Window.created_at >= start_date
            )
        )
        total_windows = window_total.scalar()

        process_total = await session.execute(
            select(func.count(distinct(Process.id)))
            .select_from(Process)
            .join(Window, Process.id == Window.process_id)
            .where(Window.created_at >= start_date)
        )
        total_processes = process_total.scalar()

        Totals = namedtuple(
            "Totals",
            ["total_keystrokes", "total_clicks", "total_windows", "total_processes"],
        )
        totals = Totals(total_keystrokes, total_clicks, total_windows, total_processes)

        return {"processes": process_stats.all(), "totals": totals}


async def get_hourly_stats(store: Store, days: int) -> dict[int, int]:
    """Get activity data by hour of day."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        hourly_query = (
            select(
                extract("hour", Keys.created_at).label("hour"),
                func.sum(Keys.count).label("keystrokes"),
            )
            .where(Keys.created_at >= start_date)
            .group_by("hour")
        )

        result = await session.execute(hourly_query)
        return {int(row.hour): int(row.keystrokes) for row in result.all()}


async def get_timeline_data(store: Store, days: int):
    """Get timeline data for activity visualization."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        timeline_query = (
            select(
                Window.created_at,
                Window.title,
                Process.name.label("process_name"),
                func.coalesce(func.sum(Keys.count), 0).label("keystrokes"),
            )
            .select_from(Window)
            .join(Process, Window.process_id == Process.id)
            .outerjoin(Keys, Keys.window_id == Window.id)
            .where(Window.created_at >= start_date)
            .group_by(Window.id)
            .order_by(Window.created_at.desc())
            .limit(50)
        )

        return await session.execute(timeline_query)
