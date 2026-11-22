"""Expose the first future date without a meal and Luna's reason, if given."""

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LunaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LunaCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([LunaNextUnselectedDay(entry.runtime_data, entry.entry_id)])


class LunaNextUnselectedDay(CoordinatorEntity[LunaCoordinator], SensorEntity):
    _attr_name = "Luna Schulessen Nächster Tag ohne Auswahl"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-question"

    def __init__(self, coordinator: LunaCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_next_unselected_day"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.selection is not None

    @property
    def native_value(self) -> date | None:
        status = self.coordinator.data.selection
        return status.next_day_without_selection if status is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, str | bool | None] | None:
        status = self.coordinator.data.selection
        if status is None:
            return None
        next_date = status.next_day_without_selection
        next_bookable = status.next_bookable_day_without_selection
        day = status.days[next_date] if next_date is not None else None
        return {
            "buchbar": day.bookable if day is not None else None,
            "ferien": day.holiday if day is not None else None,
            "luna_hinweis": day.note if day is not None else None,
            "naechster_buchbarer_tag_ohne_auswahl": (
                next_bookable.isoformat() if next_bookable is not None else None
            ),
        }
