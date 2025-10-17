import logging
from typing import TYPE_CHECKING, cast

from homeassistant.components.todo import TodoItem, TodoListEntity
from homeassistant.components.todo.const import TodoItemStatus, TodoListEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GroceryListItem
from .coordinator import PaprikaCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

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

    # async def async_create_todo_item(self, item: TodoItem) -> None:
    #     """Create a new grocery item in Paprika."""
    #     LOGGER.debug("Creating todo item: %s in Paprika grocery list.", item.summary)

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

    # def test_get_replacement_name(self, item: TodoItem, originalName: str) -> str:
    #     LOGGER.debug(
    #         "Updating name of todo item: %s in Paprika grocery list with %s.",
    #         item.summary,
    #         originalName,
    #     )
    #     return item.summary if item.summary else ""

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a grocery item in Paprika."""
        LOGGER.debug("Updating todo item: %s in Paprika grocery list.", item.summary)

        try:
            updatedGroceryList: list[GroceryListItem] = [
                cast(
                    GroceryListItem,
                    {
                        **grocery,
                        "name": (
                            grocery["name"]
                            if grocery["uid"] != item.uid
                            else item.summary
                        ),
                        "purchased": (
                            grocery["purchased"]
                            if grocery["uid"] != item.uid
                            else (
                                True
                                if item.status == TodoItemStatus.COMPLETED
                                else False
                            )
                        ),
                    },
                )
                for grocery in sorted(
                    self.coordinator.data.groceries, key=lambda i: i["order_flag"]
                )
            ]

            await self.coordinator.api.post_groceries(updatedGroceryList)

            self.coordinator.data.groceries = updatedGroceryList

            LOGGER.debug("Successfully updated item %s in Paprika.", item.summary)

        except Exception as e:
            LOGGER.error("Failed to update item %s in Paprika: %s", item.summary, e)

        finally:
            # Resync data with Paprika
            await self.coordinator._async_update_data()
            LOGGER.debug("Requested data refresh after update.")

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add a grocery item in Paprika."""
        LOGGER.debug("Creating new item: %s in Paprika grocery list.", item.summary)

        try:

            newItem: GroceryListItem | None = (
                {
                    "uid": item.uid,
                    "recipe_uid": None,
                    "name": item.summary if item.summary else "New Item",
                    "recipe_uid": None,
                    "order_flag": (
                        len(self.coordinator.data.groceries)
                        if self.coordinator.data.groceries
                        else 1
                    ),
                    "purchased": item.status == TodoItemStatus.COMPLETED,
                    "aisle": None,
                    "ingredient": None,
                    "recipe": None,
                    "instruction": None,
                    "quantity": None,
                    "separate": False,
                    "aisle_uid": None,
                    "list_uid": (
                        self.coordinator.data.groceries[0]["list_uid"]
                        if (
                            self.coordinator.data.groceries
                            and len(self.coordinator.data.groceries) > 0
                        )
                        else None
                    ),
                    "deleted": False,
                }
                if item.uid
                else None
            )

            updatedGroceryList: list[GroceryListItem] = sorted(
                self.coordinator.data.groceries, key=lambda i: i["order_flag"]
            )

            if newItem:
                updatedGroceryList.append(newItem)

            await self.coordinator.api.post_groceries(updatedGroceryList)

            self.coordinator.data.groceries = updatedGroceryList

            LOGGER.debug("Successfully added item %s in Paprika.", item.summary)

        except Exception as e:
            LOGGER.error("Failed to add item %s in Paprika: %s", item.summary, e)

        finally:
            # Resync data with Paprika
            await self.coordinator._async_update_data()
            LOGGER.debug("Requested data refresh after update.")


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
