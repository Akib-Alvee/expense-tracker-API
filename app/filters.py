import enum
from datetime import date, timedelta

from fastapi import HTTPException, status


class Period(str, enum.Enum):
    week = "week"
    month = "month"
    three_months = "3months"


PERIOD_DAYS = {
    Period.week: 7,
    Period.month: 30,
    Period.three_months: 90,
}


def resolve_date_range(
    period: Period | None,
    start_date: date | None,
    end_date: date | None,
    today: date | None = None,
) -> tuple[date | None, date | None]:
    """Turn the query parameters into an inclusive (start, end) range.

    Either end may be None, meaning "no limit on that side".
    """
    today = today or date.today()

    if period and (start_date or end_date):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Use either 'period' or 'start_date'/'end_date', not both",
        )

    if period:
        return today - timedelta(days=PERIOD_DAYS[period]), today

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "start_date must be on or before end_date",
        )

    return start_date, end_date