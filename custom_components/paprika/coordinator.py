from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from datetime import timedelta
from logging import Logger
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.typing import UNDEFINED, UndefinedType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from .api import PaprikaApi, GroceryListItem, MealType, PlannedMeal
    from .data import PaprikaConfigEntry


@dataclass
class PaprikaData:
    meals: list["PlannedMeal"]
    groceries: list["GroceryListItem"]
    meal_types: list["MealType"]


class PaprikaCoordinator(DataUpdateCoordinator[PaprikaData]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        name: str,
        api: PaprikaApi,
        update_interval: timedelta | None = None,
    ) -> None:
        super().__init__(hass, logger, name=name, update_interval=update_interval)

        self.api = api

    config_entry: "PaprikaConfigEntry"

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        meal_types = await self.config_entry.runtime_data.client.get_meal_types()
        meals = await self.config_entry.runtime_data.client.get_meals(meal_types)
        groceries = await self.config_entry.runtime_data.client.get_groceries()
        return PaprikaData(meal_types=meal_types, meals=meals, groceries=groceries)
