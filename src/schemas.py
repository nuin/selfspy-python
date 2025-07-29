from datetime import datetime
from typing import List

from pydantic import BaseModel


class ActivityStats(BaseModel):
    hour: int
    window_count: int
    keystroke_count: int
    click_count: int


class ProcessStats(BaseModel):
    name: str
    window_count: int
    active_time: int
    keystroke_count: int
    click_count: int


class StatsResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    total_keystrokes: int
    total_clicks: int
    total_windows: int
    hourly_stats: List[ActivityStats]
    process_stats: List[ProcessStats]
