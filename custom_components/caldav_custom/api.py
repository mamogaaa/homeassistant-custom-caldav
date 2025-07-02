"""Library for working with CalDAV api."""

import logging

import caldav
from caldav.lib.error import PropfindError

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_get_calendars(
    hass: HomeAssistant, client: caldav.DAVClient, component: str
) -> list[caldav.Calendar]:
    """Get all calendars that support the specified component."""

    def _get_calendars() -> list[caldav.Calendar]:
        try:
            # Try standard principal-based calendar discovery
            return [
                calendar
                for calendar in client.principal().calendars()
                if component in calendar.get_supported_components()
            ]
        except PropfindError as err:
            _LOGGER.warning("Principal-based calendar discovery failed: %s", err)
            if "400" in str(err):
                # Fallback for servers like calendar.mail.ru that don't support principal discovery
                return _get_calendars_fallback(client, component)
            raise
        except Exception as err:
            _LOGGER.warning("Calendar discovery failed: %s", err)
            # Try fallback approach
            return _get_calendars_fallback(client, component)

    return await hass.async_add_executor_job(_get_calendars)


def _get_calendars_fallback(client: caldav.DAVClient, component: str) -> list[caldav.Calendar]:
    """Fallback calendar discovery for servers that don't support principal discovery."""
    _LOGGER.info("Attempting fallback calendar discovery")
    
    calendars = []
    
    # Try common CalDAV URL patterns
    base_url = str(client.url).rstrip('/')
    username = client.username
    
    # Common calendar URL patterns for various servers
    patterns = [
        f"{base_url}/dav/{username}/calendar/",
        f"{base_url}/caldav/{username}/",
        f"{base_url}/dav/{username}/",
        f"{base_url}/calendar/dav/{username}/",
        f"{base_url}/calendars/{username}/",
        f"{base_url}/remote.php/dav/calendars/{username}/",  # Nextcloud/ownCloud
        f"{base_url}/dav/calendars/{username}/",
    ]
    
    for pattern in patterns:
        try:
            _LOGGER.debug("Trying calendar pattern: %s", pattern)
            calendar_home = caldav.CalendarSet(client, url=pattern)
            found_calendars = calendar_home.calendars()
            
            if found_calendars:
                _LOGGER.info("Found %d calendars at %s", len(found_calendars), pattern)
                
                # Filter calendars by supported components
                for calendar in found_calendars:
                    try:
                        supported_components = calendar.get_supported_components()
                        if component in supported_components:
                            calendars.append(calendar)
                            _LOGGER.debug("Added calendar %s (supports %s)", calendar.url, component)
                    except Exception as comp_err:
                        # If we can't get supported components, assume it supports the component
                        _LOGGER.debug("Could not check components for %s, assuming supported: %s", calendar.url, comp_err)
                        calendars.append(calendar)
                
                break  # Stop on first successful pattern
                
        except Exception as pattern_err:
            _LOGGER.debug("Pattern %s failed: %s", pattern, pattern_err)
            continue
    
    if calendars:
        _LOGGER.info("Fallback discovery found %d calendars supporting %s", len(calendars), component)
    else:
        _LOGGER.warning("Fallback discovery found no calendars supporting %s", component)
    
    return calendars


def get_attr_value(obj: caldav.CalendarObjectResource, attribute: str) -> str | None:
    """Return the value of the CalDav object attribute if defined."""
    if hasattr(obj, attribute):
        return getattr(obj, attribute).value
    return None
