import logging
from typing import TYPE_CHECKING

from homeassistant.components.todo import TodoItem, TodoListEntity
from homeassistant.components.todo.const import TodoItemStatus
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PaprikaCoordinator
    from .data import PaprikaConfigEntry

LOGGER = logging.getLogger(__name__)


class PaprikaGroceryList(TodoListEntity, CoordinatorEntity["PaprikaCoordinator"]):

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: "PaprikaCoordinator",
        entry: "PaprikaConfigEntry",
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.title}_groceries_list"
        self._attr_has_entity_name = False

    @property
    def name(self) -> str:
        return "Paprika Grocery List"

    @property
    def todo_items(self) -> list[TodoItem] | None:
        if not self.coordinator.data.groceries:
            return None
        return [
            TodoItem(
                uid=item["uid"],
                summary=item["name"],
                status=(
                    TodoItemStatus.COMPLETED
                    if item["purchased"]
                    else TodoItemStatus.NEEDS_ACTION
                ),
            )
            for item in sorted(
                self.coordinator.data.groceries, key=lambda i: i["order_flag"]
            )
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new grocery item in Paprika."""
        LOGGER.debug(
            f"Creating new grocery item in Paprika list. UID: {item.uid}",
        )
        # list_id = self._gkeep_list_id
        # text = item.summary

        # try:
        #     # Create the new item in the specified list
        #     await self.api.async_create_todo_item(list_id, text)
        #     LOGGER.debug("Successfully created new item '%s' in Google Keep.", text)

        # except Exception as e:
        #     LOGGER.error("Failed to create new item '%s' in Google Keep: %s", text, e)

        # finally:
        #     # Request refresh to synchronize with Google Keep
        #     await self.coordinator.async_refresh()
        #     LOGGER.debug("Requested data refresh after item creation.")

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a grocery item in Paprika."""
        LOGGER.debug("Updating todo item: %s in Paprika grocery list.", item.uid)


async def async_setup_entry(
    hass: "HomeAssistant",  # noqa: ARG001 Unused function argument: `hass`
    entry: "PaprikaConfigEntry",
    async_add_entities: "AddEntitiesCallback",
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        [
            # TODO: split by list name?
            PaprikaGroceryList(
                coordinator=entry.runtime_data.coordinator,
                entry=entry,
            ),
        ]
    )
