"""Pure analytics for basic activity stats. DB I/O only; no Rich/Typer."""

from collections import namedtuple
from datetime import datetime, timedelta

from sqlalchemy import distinct, func, select

from ..storage import Click, Keys, Process, Store, Window


async def get_stats(store: Store, days: int) -> dict:
    """Get activity statistics for the last N days as plain data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    async with store.async_session() as session:
        # Subquery for keystrokes
        keystroke_subq = (
            select(Keys.process_id, func.sum(Keys.count).label("keystroke_count"))
            .where(Keys.created_at >= start_date)
            .group_by(Keys.process_id)
            .subquery()
        )

        # Subquery for clicks
        click_subq = (
            select(Click.process_id, func.count(Click.id).label("click_count"))
            .where(Click.created_at >= start_date)
            .group_by(Click.process_id)
            .subquery()
        )

        # Main query with proper joins
        process_query = (
            select(
                Process.name,
                func.count(distinct(Window.id)).label("window_count"),
                func.coalesce(keystroke_subq.c.keystroke_count, 0).label(
                    "keystroke_count"
                ),
                func.coalesce(click_subq.c.click_count, 0).label("click_count"),
            )
            .select_from(Process)
            .join(Window, Process.id == Window.process_id)
            .outerjoin(keystroke_subq, Process.id == keystroke_subq.c.process_id)
            .outerjoin(click_subq, Process.id == click_subq.c.process_id)
            .where(Window.created_at >= start_date)
            .group_by(
                Process.name,
                keystroke_subq.c.keystroke_count,
                click_subq.c.click_count,
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

        daily_keys = await session.execute(
            select(
                func.date(Keys.created_at).label("date"),
                func.sum(Keys.count).label("count"),
            )
            .where(Keys.created_at >= start_date)
            .group_by(func.date(Keys.created_at))
            .order_by(func.date(Keys.created_at))
        )

        daily_clicks = await session.execute(
            select(
                func.date(Click.created_at).label("date"),
                func.count(Click.id).label("count"),
            )
            .where(Click.created_at >= start_date)
            .group_by(func.date(Click.created_at))
            .order_by(func.date(Click.created_at))
        )

        Totals = namedtuple(
            "Totals", ["total_keystrokes", "total_clicks", "total_windows"]
        )
        totals = Totals(total_keystrokes, total_clicks, total_windows)

        return {
            "processes": process_stats.all(),
            "totals": totals,
            "daily_keys": {str(row.date): row.count for row in daily_keys.all()},
            "daily_clicks": {str(row.date): row.count for row in daily_clicks.all()},
            "days": days,
            "start_date": start_date,
            "end_date": end_date,
        }
