"""Define automations to call services in specific scenarios."""
from typing import Union

import voluptuous as vol

from const import (
    CONF_ENTITY_IDS,
    CONF_EVENT,
    CONF_EVENT_DATA,
    CONF_PROPERTIES,
    CONF_TARGET_ENTITY_ID,
)
from core import APP_SCHEMA, Base
from helpers import config_validation as cv

CONF_RUN_ON_DAYS = "run_on_days"
CONF_SCHEDULE_TIME = "schedule_time"

CONF_SERVICE = "service"
CONF_SERVICE_DATA = "service_data"

CONF_DELAY = "delay"
CONF_OPPOSITE = "opposite"
CONF_TARGET_STATE = "target_state"

SERVICE_CALL_SCHEMA = APP_SCHEMA.extend(
    {vol.Required(CONF_SERVICE): str, vol.Required(CONF_SERVICE_DATA): dict}
)


class ServiceBase(Base):  # pylint: disable=too-few-public-methods
    """Define a base automation for calling services."""

    def call_service_with_data(self) -> None:
        """Call the service with the provided service data."""
        self.call_service(self.args[CONF_SERVICE], **self.args[CONF_SERVICE_DATA])

    def service_callback(self, kwargs: dict) -> None:
        """Define a AppDaemon runtime callback to call the service with its data."""
        self.call_service_with_data()


class ServiceOnEvent(ServiceBase):  # pylint: disable=too-few-public-methods
    """Define an automation to call a service upon seeing an specific event/payload."""

    APP_SCHEMA = SERVICE_CALL_SCHEMA.extend(
        {
            CONF_PROPERTIES: vol.Schema(
                {vol.Required(CONF_EVENT): str, vol.Optional(CONF_EVENT_DATA): dict},
                extra=vol.ALLOW_EXTRA,
            )
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.listen_event(
            self.service_callback,
            self.properties[CONF_EVENT],
            **self.properties.get(CONF_EVENT_DATA, {}),
            constrain_enabled=True,
        )


class ServiceOnState(ServiceBase):
    """Define a feature to toggle the switch when an entity enters a state."""

    APP_SCHEMA = SERVICE_CALL_SCHEMA.extend(
        {
            CONF_ENTITY_IDS: vol.Schema(
                {vol.Required(CONF_TARGET_ENTITY_ID): cv.entity_id},
                extra=vol.ALLOW_EXTRA,
            ),
            CONF_PROPERTIES: vol.Schema(
                {
                    vol.Required(CONF_TARGET_STATE): str,
                    vol.Optional(CONF_OPPOSITE): bool,
                    vol.Optional(CONF_DELAY): int,
                },
                extra=vol.ALLOW_EXTRA,
            ),
        }
    )

    def configure(self) -> None:
        """Configure."""
        kwargs = {"constrain_enabled": True, "auto_constraints": True}

        if self.properties[CONF_OPPOSITE]:
            kwargs["old"] = self.properties[CONF_TARGET_STATE]
        else:
            kwargs["new"] = self.properties[CONF_TARGET_STATE]

        if self.properties[CONF_DELAY]:
            kwargs["duration"] = self.properties[CONF_DELAY]

        self.listen_state(
            self._on_target_state_observed,
            self.entity_ids[CONF_TARGET_ENTITY_ID],
            **kwargs,
        )

    async def _on_target_state_observed(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Call the service when the target state is observed."""
        self.call_service_with_data()


class ServiceOnTime(ServiceBase):  # pylint: disable=too-few-public-methods
    """Define an automation to call a service at a specific time."""

    APP_SCHEMA = SERVICE_CALL_SCHEMA.extend(
        {
            CONF_PROPERTIES: vol.Schema(
                {vol.Required(CONF_SCHEDULE_TIME): str}, extra=vol.ALLOW_EXTRA,
            )
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.run_daily(
            self.service_callback,
            self.parse_time(self.properties[CONF_SCHEDULE_TIME]),
            constrain_enabled=True,
            auto_constraints=True,
        )
