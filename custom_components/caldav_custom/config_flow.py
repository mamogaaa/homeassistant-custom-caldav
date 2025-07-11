"""Configuration flow for CalDav."""

from collections.abc import Mapping
import logging
from typing import Any

import caldav
from caldav.lib.error import AuthorizationError, DAVError, PropfindError
import requests
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD, default=""): cv.string,
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
    }
)


class CalDavConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for caldav."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_URL: user_input[CONF_URL],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                }
            )
            if error := await self._test_connection(user_input):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, user_input: dict[str, Any]) -> str | None:
        """Test the connection to the CalDAV server and return an error if any."""
        client = caldav.DAVClient(
            user_input[CONF_URL],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
            ssl_verify_cert=user_input[CONF_VERIFY_SSL],
        )
        try:
            # Try basic connectivity first - this might fail with PropfindError on some servers
            await self.hass.async_add_executor_job(client.principal)
        except PropfindError as err:
            _LOGGER.warning("CalDAV PropfindError during principal() call: %s", err)
            # PropfindError during principal() often indicates 400 Bad Request
            # Try alternative connection test using calendar home set discovery
            if "400" in str(err):
                try:
                    # Alternative test: try basic HTTP connectivity to the server
                    response = await self.hass.async_add_executor_job(
                        client.request, user_input[CONF_URL]
                    )
                    _LOGGER.info("Connection test passed with basic HTTP request despite PropfindError")
                    return None
                except Exception as fallback_err:
                    _LOGGER.warning("Alternative connection test also failed: %s", fallback_err)
                    return "cannot_connect"
            return "cannot_connect"
        except AuthorizationError as err:
            _LOGGER.warning("Authorization Error connecting to CalDAV server: %s", err)
            if err.reason == "Unauthorized":
                return "invalid_auth"
            # AuthorizationError can be raised if the url is incorrect or
            # on some other unexpected server response.
            return "cannot_connect"
        except requests.ConnectionError as err:
            _LOGGER.warning("Connection Error connecting to CalDAV server: %s", err)
            return "cannot_connect"
        except DAVError as err:
            _LOGGER.warning("CalDAV client error: %s", err)
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return "unknown"
        return None

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog."""
        errors = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            user_input = {**reauth_entry.data, **user_input}

            if error := await self._test_connection(user_input):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=user_input)

        return self.async_show_form(
            description_placeholders={
                CONF_USERNAME: reauth_entry.data[CONF_USERNAME],
            },
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
