"""Collect Luna credentials directly in Home Assistant's config flow."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
from homeassistant.util import dt as dt_util

from . import DOMAIN
from .portal import LunaAuthError, LunaError, LunaPortal

_LOGGER = logging.getLogger(__name__)


class LunaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        return await self._credentials("user", user_input)

    async def async_step_reauth(self, entry_data) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        return await self._credentials("reauth_confirm", user_input)

    async def _credentials(self, step_id: str, user_input) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            data = {**user_input, CONF_USERNAME: user_input[CONF_USERNAME].strip()}
            try:
                await self.hass.async_add_executor_job(self._validate, data, dt_util.now().date())
            except LunaAuthError:
                errors["base"] = "invalid_auth"
            except LunaError as err:
                _LOGGER.warning("Could not read Luna orders during setup: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if step_id == "reauth_confirm":
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data_updates=data
                    )
                return self.async_create_entry(title="Luna Schulessen", data=data)

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): TextSelector(),
                vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            }),
            errors=errors,
        )

    @staticmethod
    def _validate(data, today) -> None:
        LunaPortal(data[CONF_USERNAME], data[CONF_PASSWORD]).orders(today)
