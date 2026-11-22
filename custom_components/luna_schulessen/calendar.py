"""Expose confirmed Luna orders as all-day calendar events."""

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import LunaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LunaCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([LunaCalendar(entry.runtime_data, entry.entry_id)])


class LunaCalendar(CoordinatorEntity[LunaCoordinator], CalendarEntity):
    _attr_name = "Luna Schulessen"

    def __init__(self, coordinator: LunaCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry_id

    def _events(self):
        for day, dish in sorted(self.coordinator.data.meals.items()):
            yield CalendarEvent(
                start=day,
                end=day + timedelta(days=1),
                summary=dish,
                uid=f"{self.unique_id}-{day.isoformat()}",
            )

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        return next((event for event in self._events() if event.start >= today), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            event for event in self._events()
            if dt_util.start_of_local_day(event.start) < end_date
            and dt_util.start_of_local_day(event.end) > start_date
        ]
