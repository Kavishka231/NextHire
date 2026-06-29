from pydantic import BaseModel
from typing import Optional


class StatusCount(BaseModel):
    status: str
    label:  str
    color:  str
    count:  int


class WeeklyActivity(BaseModel):
    week:  str   # "Mon", "Tue" … or date string
    count: int


class TopCompany(BaseModel):
    company: str
    count:   int


class StatsResponse(BaseModel):
    total_saved:       int
    total_applied:     int
    total_interviews:  int
    total_offers:      int
    total_rejected:    int
    response_rate:     float          # interviews / applied * 100
    offer_rate:        float          # offers / applied * 100
    status_counts:     list[StatusCount]
    weekly_activity:   list[WeeklyActivity]
    top_companies:     list[TopCompany]
    avg_salary_min:    Optional[float]
    avg_salary_max:    Optional[float]
