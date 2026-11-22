"""Expose whether Luna has enabled booking for the next month."""

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    async_add_entities([LunaNextMonth(entry.runtime_data, entry.entry_id)])


class LunaNextMonth(CoordinatorEntity[LunaCoordinator], BinarySensorEntity):
    _attr_name = "Luna Schulessen Nächster Monat buchbar"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: LunaCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_next_month_bookable"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.selection is not None

    @property
    def is_on(self) -> bool | None:
        status = self.coordinator.data.selection
        if status is None:
            return None
        return bool(status.next_month_bookable_days)

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        status = self.coordinator.data.selection
        if status is None:
            return None
        days = status.next_month_bookable_days
        return {
            "monat": status.next_month.strftime("%Y-%m"),
            "buchbare_tage": len(days),
            "tage_ohne_auswahl": sum(not day.selected for day in days),
        }
