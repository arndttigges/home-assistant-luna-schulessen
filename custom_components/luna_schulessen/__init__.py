"""Luna school lunch calendar and selection status."""

from dataclasses import dataclass
from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .portal import LunaAuthError, LunaError, LunaPortal
from .selection import SelectionStatus, read_selection_status

DOMAIN = "luna_schulessen"
PLATFORMS = [Platform.CALENDAR, Platform.BINARY_SENSOR, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LunaData:
    meals: dict[date, str]
    selection: SelectionStatus | None


class LunaCoordinator(DataUpdateCoordinator[LunaData]):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, portal: LunaPortal
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Luna Schulessen",
            update_interval=timedelta(hours=2),
        )
        self.portal = portal
        self._selection_error: str | None = None

    def _read_data(self, today: date) -> LunaData:
        meals = self.portal.orders(today)
        try:
            selection = read_selection_status(self.portal, today, meals)
        except LunaError as err:
            if self._selection_error != str(err):
                _LOGGER.warning("Luna selection status is unavailable: %s", err)
            self._selection_error = str(err)
            return LunaData(meals, None)
        self._selection_error = None
        return LunaData(meals, selection)

    async def _async_update_data(self) -> LunaData:
        try:
            return await self.hass.async_add_executor_job(self._read_data, dt_util.now().date())
        except LunaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LunaError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry[LunaCoordinator]) -> bool:
    portal = await hass.async_add_executor_job(
        LunaPortal, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    coordinator = LunaCoordinator(hass, entry, portal)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry[LunaCoordinator]) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
