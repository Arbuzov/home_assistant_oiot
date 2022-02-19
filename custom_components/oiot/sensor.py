"""Platform for sensor integration."""
from __future__ import annotations
from datetime import timedelta

import logging

import async_timeout

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import VOLUME_CUBIC_METERS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .site import InvalidAuth, CannotConnect


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback):
    """Set up a oiot consumption sensor."""
    oiot_site = hass.data[DOMAIN][entry.unique_id]

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                return await oiot_site.fetch_data()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except CannotConnect as err:
            raise UpdateFailed(f'Error communicating with API: {err}')

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name='oiot',
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    await oiot_site.fetch_data()
    async_add_entities([
        OiotSensor(coordinator, oiot_site.device_id, oiot_site.device_name, 1),
        OiotSensor(coordinator, oiot_site.device_id, oiot_site.device_name, 2)
    ])
    return True


class OiotSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_name = 'Water consumption'
    _attr_native_unit_of_measurement = VOLUME_CUBIC_METERS
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = 'mdi:water-well'

    def __init__(
            self, coordinator, device_id='',
            device_name='New device', sensor_id=1):
        """Initialize."""
        super().__init__(coordinator)
        self.sensor_id = sensor_id
        self.device_id = device_id
        self.device_name = device_name
        self._attr_unique_id = f'{device_id}_{sensor_id}'

    @property
    def device_info(self):
        return {
            'identifiers': {
                (DOMAIN, self.device_id)
            },
            'name': self.device_name,
            'manufacturer': 'OIOT',
            'model': 'Basic'
        }

    @property
    def native_value(self):
        """Return the value reported by the sensor."""
        if self.coordinator.data is not None:
            self._attr_name = self.coordinator.data.get(self.sensor_id).title
            return self.coordinator.data.get(self.sensor_id).value
        else:
            return None
