"""Connector to the OIOT site"""
from datetime import datetime
import logging

import aiohttp
from homeassistant.const import CONF_API_TOKEN, CONF_CLIENT_ID, CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import OIOT_API_URL

_LOGGER = logging.getLogger(__name__)


def normalize_last_metrics_update(value):
    """Normalize various timestamp representations to datetime."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        normalized_value = value.strip()
        if not normalized_value:
            return None

        try:
            return datetime.fromisoformat(normalized_value)
        except ValueError:
            pass

        for time_format in (
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%d.%m.%Y %H:%M:%S',
            '%d.%m.%Y %H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
        ):
            try:
                return datetime.strptime(normalized_value, time_format)
            except ValueError:
                continue

    return None


class Measurement:
    """Container for the single measurement"""

    def __init__(self, title, value, dimension, date=None):
        self.title = title
        self.value = value
        self.dimension = dimension
        self.date = date


class OiotSite:
    """OIOT site connector"""

    def __init__(self, config: dict, hass: HomeAssistant) -> None:
        """Initialize."""
        self.host = OIOT_API_URL
        self.user_id = config.get(CONF_CLIENT_ID)
        self.token = config.get(CONF_API_TOKEN)
        self.device_id = config.get(CONF_DEVICE_ID)
        self.device_name = ''
        self.result = {}
        self.measurements = {}
        self.last_metrics_update = None
        self.hass = hass
        self.site_url = f'{OIOT_API_URL}?id={self.user_id}&token={self.token}'
        if self.device_id is not None:
            self.site_url = self.site_url + f'&keys[]={self.device_id}'

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the credentials provided."""
        session = async_get_clientsession(self.hass)
        resp = await session.get(self.site_url)
        responce = await resp.json()
        if 'success' in responce:
            self._parse_values(responce)
            await session.close()
            return True
        else:
            raise InvalidAuth()

    async def fetch_data(self):
        """Request all data for the specific device"""
        session = aiohttp.ClientSession()
        resp = await session.get(self.site_url)
        responce = await resp.json()
        self._parse_values(responce)
        await session.close()
        return self.measurements

    def _parse_values(self, responce: dict) -> dict:
        """Extracts measurements form the fetched values"""
        self.result = responce.get('result') or {}
        self.measurements = {}

        if not self.result:
            return self.measurements

        self.device_id = list(self.result.keys())[0]
        device_data = self.result.get(self.device_id) or {}
        self.device_name = device_data.get('TITLE')
        data_entries = device_data.get('data')
        if not isinstance(data_entries, list) or not data_entries:
            self.last_metrics_update = None
            self.measurements.update({'last_metrics_update': self.last_metrics_update})
            return self.measurements

        data = data_entries[0]
        raw_last_metrics_update = (
            data.get('date')
            or data.get('DATE')
            or data.get('date_update')
            or data.get('updated_at')
            or data.get('created_at')
        )
        self.last_metrics_update = normalize_last_metrics_update(
            raw_last_metrics_update
        )

        self.measurements.update({1: Measurement(
            device_data.get('COUNTER_NAME_1'),
            data.get('counter_1'),
            device_data.get('MEASURE_1_NAME'),
            self.last_metrics_update
        )})
        self.measurements.update({2: Measurement(
            device_data.get('COUNTER_NAME_2'),
            data.get('counter_2'),
            device_data.get('MEASURE_2_NAME'),
            self.last_metrics_update
        )})
        self.measurements.update({'last_metrics_update': self.last_metrics_update})

        return self.measurements


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
