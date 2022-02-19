"""Connector to the OIOT site"""
import logging

import aiohttp

from homeassistant.const import CONF_API_TOKEN, CONF_CLIENT_ID, CONF_DEVICE_ID
from homeassistant.exceptions import HomeAssistantError

from .const import OIOT_API_URL


_LOGGER = logging.getLogger(__name__)


class Measurement:
    """Container for the single measurement"""

    def __init__(self, title, value, dimension, date=None):
        self.title = title
        self.value = value
        self.dimension = dimension
        self.date = date


class OiotSite:
    """OIOT site connector"""

    def __init__(self, config: dict) -> None:
        """Initialize."""
        self.host = OIOT_API_URL
        self.user_id = config.get(CONF_CLIENT_ID)
        self.token = config.get(CONF_API_TOKEN)
        self.device_id = config.get(CONF_DEVICE_ID)
        self.device_name = ''
        self.result = {}
        self.measurements = {}
        self.site_url = f'{OIOT_API_URL}?id={self.user_id}&token={self.token}'
        if self.device_id is not None:
            self.site_url = self.site_url + f'&keys[]={self.device_id}'

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the credentials provided."""
        session = aiohttp.ClientSession()
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
        self.result = responce.get('result')
        self.device_id = list(self.result.keys())[0]
        self.device_name = self.result.get(self.device_id).get('TITLE')
        self.measurements.update({1: Measurement(
            self.result.get(self.device_id).get('COUNTER_NAME_1'),
            self.result.get(self.device_id).get('data')[0].get('counter_1'),
            self.result.get(self.device_id).get('MEASURE_1_NAME')
        )})
        self.measurements.update({2: Measurement(
            self.result.get(self.device_id).get('COUNTER_NAME_2'),
            self.result.get(self.device_id).get('data')[0].get('counter_2'),
            self.result.get(self.device_id).get('MEASURE_2_NAME')
        )})
        return


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
