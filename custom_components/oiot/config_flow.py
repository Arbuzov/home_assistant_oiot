"""Config flow for oiot integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous
from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN, CONF_CLIENT_ID, CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .site import CannotConnect, InvalidAuth, OiotSite

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = voluptuous.Schema(
    {
        voluptuous.Required(CONF_API_TOKEN): str,
        voluptuous.Required(CONF_CLIENT_ID): str,
        voluptuous.Required(CONF_DEVICE_ID): str,
    }
)


async def validate_input(
        hass: HomeAssistant,
        data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.
    Data has the keys from STEP_USER_DATA_SCHEMA
    with values provided by the user.
    """
    oiot_site = OiotSite(data, hass)

    if not await oiot_site.authenticate():
        raise InvalidAuth

    return {'title': oiot_site.device_name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for oiot."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id='user', data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors['base'] = 'cannot_connect'
        except InvalidAuth:
            errors['base'] = 'invalid_auth'
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception('Unexpected exception')
            errors['base'] = 'unknown'
        else:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=info['title'], data=user_input)

        return self.async_show_form(
            step_id='user', data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
