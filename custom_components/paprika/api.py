import gzip
import json
import logging
from datetime import date, datetime
from typing import NewType, Optional, TypedDict, cast

import aiohttp

_LOGGER = logging.getLogger(__name__)

START_DATE_FILTER = date(
    2025, 1, 1
)  # Only process meals after this date (see issue #13)

MealId = NewType("MealId", str)
RecipeID = NewType("RecipeID", str)


class MealType(TypedDict):
    uid: str
    name: str
    order_flag: int
    color: str
    export_all_day: bool
    export_time: int
    original_type: int


class PlannedMeal(TypedDict):
    uid: MealId
    recipe_uid: RecipeID
    date: date
    type: MealType
    name: str
    order_flag: int
    type_uid: str
    scale: int | None
    is_ingredient: bool


class GroceryListItem(TypedDict):
    uid: str
    recipe_uid: RecipeID | None
    name: str
    order_flag: int
    purchased: bool
    aisle: Optional[str]
    ingredient: Optional[str]
    recipe: Optional[str]
    instruction: Optional[str]
    quantity: Optional[str]
    separate: bool
    aisle_uid: Optional[str]
    list_uid: Optional[str]
    deleted: bool


class PaprikaError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class PaprikaApi:
    base_url: str
    user_agent: str

    def __del__(self):
        # TODO: verify this works as expected when erroring during setup.
        self.session.close()

    def __init__(self, token: str):
        _LOGGER.info("Setting up client")
        self.access_token = token
        self.base_url = "https://www.paprikaapp.com/api/v2"
        self.user_agent = "Paprika 3/3.8.2 (com.hindsightlabs.paprika.ios.v3; build:71; iOS 18.1.1) Alamofire/5.2.2"
        self.session = aiohttp.ClientSession("https://www.paprikaapp.com/api/v2/")
        self.session.headers["authorization"] = f"Bearer {self.access_token}"
        self.session.headers["user-agent"] = self.user_agent

    @classmethod
    async def login(cls, email: str, password: str):
        """Use a username and password to get a token that can be used to initialise the client for other calls."""
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                "https://paprikaapp.com/api/v1/account/login",
                data={"email": email, "password": password},
            )
            json_response = await response.json()

            if json_response.get("error"):
                _LOGGER.error(
                    f"Error from authentication endpoint: {json_response['error']['message']}"
                )
                raise PaprikaError(json_response["error"]["message"])

            return json_response["result"]["token"]

    async def get_meal_types(self) -> list[MealType]:
        response = await self.session.get("sync/mealtypes")
        response.raise_for_status()
        response_json = await response.json()
        return [cast("MealType", item) for item in response_json["result"]]

    async def get_meals(self, meal_types: list[MealType]) -> list[PlannedMeal]:
        meal_types_by_id = {mt["uid"]: mt for mt in meal_types}
        response = await self.session.get("sync/meals")
        response.raise_for_status()
        response_json = await response.json()
        meals: list[PlannedMeal] = []
        for meal in response_json["result"]:
            meal_date = datetime.strptime(meal["date"][:10], "%Y-%m-%d").date()
            # Skip meals before START_DATE_FILTER to avoid processing old data with bad ids (see issue #13)
            if meal_date < START_DATE_FILTER:
                _LOGGER.debug("Skipping meal with date before cutoff: %s", meal)
                continue
            meal["date"] = meal_date
            meal["type"] = meal_types_by_id[meal["type_uid"]]
            meals.append(cast("PlannedMeal", meal))
        _LOGGER.debug("Got %s meals from API", len(meals))
        return meals

    async def get_groceries(self) -> list[GroceryListItem]:
        """Get grocery list items, for all lists."""
        response = await self.session.get("sync/groceries")
        response.raise_for_status()
        response_json = await response.json()
        return [cast("GroceryListItem", item) for item in response_json["result"]]

    async def post_groceries(self, groceries: list[GroceryListItem]) -> None:
        data = gzip.compress(json.dumps(list(groceries)).encode("utf8"))

        form = aiohttp.FormData()

        form.add_field(
            name="data", value=data, filename="data.gz", content_type="application/gzip"
        )

        async with self.session.post(
            f"{self.base_url}/sync/groceries/", data=form
        ) as response:
            response.raise_for_status()
            json_response = await response.json()
            if json_response.get("result", False) is False:
                raise PaprikaError(
                    message=f"Error from groceries endpoint: {json.dumps(response.json())}"
                )

        # response = await self.session.post(
        #     f"{self.base_url}/sync/groceries/",
        #     files={"data": data},
        # )
        # response.raise_for_status()
        # if response.json().get("result", False) is False:
        #     raise PaprikaError(
        #         message=f"Error from groceries endpoint: {json.dumps(response.json())}"
        #     )
