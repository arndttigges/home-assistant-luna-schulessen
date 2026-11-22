"""Read booking availability and closing days from the Luna calendar."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from .portal import Document, LunaError, LunaPortal, normalize, order_months


@dataclass
class DaySelection:
    bookable: bool = False
    selected: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def note(self) -> str | None:
        return " / ".join(self.notes) or None

    @property
    def holiday(self) -> bool:
        return any("ferien" in note.casefold() for note in self.notes)


@dataclass(frozen=True)
class SelectionStatus:
    today: date
    next_month: date
    days: dict[date, DaySelection]

    @property
    def next_month_bookable_days(self) -> list[DaySelection]:
        return [
            day for when, day in self.days.items()
            if when.replace(day=1) == self.next_month and day.bookable
        ]

    @property
    def next_day_without_selection(self) -> date | None:
        return min(
            (when for when, day in self.days.items()
             if when > self.today and not day.selected and (day.bookable or day.note)),
            default=None,
        )

    @property
    def next_bookable_day_without_selection(self) -> date | None:
        return min(
            (when for when, day in self.days.items()
             if when > self.today and day.bookable and not day.selected),
            default=None,
        )


def _flag(value: object) -> bool:
    if value in (True, 1, "1", False, 0, "0"):
        return value in (True, 1, "1")
    raise LunaError("Luna returned an unknown booking flag.")


def _event_date(value: str) -> date:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        raise LunaError("Luna calendar data contains an invalid date.") from None


def _add_closing_period(
    days: dict[date, DaySelection], month: date, start: date, event: dict
) -> None:
    label = event.get("title")
    note = normalize(Document(label).root.text) if isinstance(label, str) else ""
    if not note:
        return

    after_start = start + timedelta(days=1)
    end = event.get("end")
    # FullCalendar represents an event's last day as an exclusive boundary.
    until = max(_event_date(end), after_start) if isinstance(end, str) and end else after_start
    first = max(month, start)
    last_exclusive = min(order_months(month)[1], until)
    for delta in range((last_exclusive - first).days):
        when = first + timedelta(days=delta)
        if when.weekday() >= 5:
            continue
        day = days.setdefault(when, DaySelection())
        if note not in day.notes:
            day.notes.append(note)


def parse_selection_month(payload: object, month: date) -> dict[date, DaySelection]:
    """Parse FullCalendar events, using Luna's own flags and closing text."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise LunaError("Luna returned an unexpected calendar data format.")

    days: dict[date, DaySelection] = {}
    for event in payload["data"]:
        if not isinstance(event, dict) or not isinstance(start := event.get("start"), str):
            raise LunaError("Luna calendar data contains an event without a date.")
        when = _event_date(start)
        properties = event.get("extendedProps", event)
        if not isinstance(properties, dict):
            raise LunaError("Luna returned unexpected calendar event properties.")
        if _flag(properties.get("isClosing")):
            _add_closing_period(days, month, when, event)
            continue
        if when.replace(day=1) != month or properties.get("dishType") in (2, "2"):
            continue
        day = days.setdefault(when, DaySelection())
        bookable = not _flag(properties.get("isDisabled"))
        selected = _flag(properties.get("isOrdered"))
        day.bookable = day.bookable or bookable
        day.selected = day.selected or selected
    return days


def read_selection_status(
    portal: LunaPortal, today: date, confirmed: dict[date, str]
) -> SelectionStatus:
    current, following = order_months(today)
    days = {
        when: day
        for month in (current, following)
        for when, day in parse_selection_month(portal.selection_month(month), month).items()
    }
    for when in confirmed:
        if when in days:
            days[when].selected = True
    return SelectionStatus(today, following, days)
