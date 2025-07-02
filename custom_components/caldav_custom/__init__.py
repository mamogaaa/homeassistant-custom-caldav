"""The caldav component."""

import logging

import caldav
from caldav.lib.error import AuthorizationError, DAVError, PropfindError
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

type CalDavConfigEntry = ConfigEntry[caldav.DAVClient]

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: CalDavConfigEntry) -> bool:
    """Set up CalDAV from a config entry."""
    client = caldav.DAVClient(
        entry.data[CONF_URL],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        ssl_verify_cert=entry.data[CONF_VERIFY_SSL],
        timeout=30,
    )
    try:
        await hass.async_add_executor_job(client.principal)
    except PropfindError as err:
        _LOGGER.warning("CalDAV PropfindError during setup: %s", err)
        # PropfindError during principal() often indicates 400 Bad Request
        # Try alternative connectivity test using calendar discovery
        if "400" in str(err):
            try:
                # Alternative test: try basic HTTP connectivity to the server
                await hass.async_add_executor_job(client.request, entry.data[CONF_URL])
                _LOGGER.info("Setup proceeding with basic HTTP connectivity despite PropfindError")
            except Exception as fallback_err:
                _LOGGER.warning("Alternative setup test failed: %s", fallback_err)
                raise ConfigEntryNotReady("CalDAV server incompatible with principal discovery") from err
        else:
            raise ConfigEntryNotReady("CalDAV PropfindError during setup") from err
    except AuthorizationError as err:
        if err.reason == "Unauthorized":
            raise ConfigEntryAuthFailed("Credentials error from CalDAV server") from err
        # AuthorizationError can be raised if the url is incorrect or
        # on some other unexpected server response.
        _LOGGER.warning("Unexpected CalDAV server response: %s", err)
        return False
    except requests.ConnectionError as err:
        raise ConfigEntryNotReady("Connection error from CalDAV server") from err
    except DAVError as err:
        raise ConfigEntryNotReady("CalDAV client error") from err

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
