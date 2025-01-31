from typing import Any, Optional

from beanie import Document, Indexed
from beanie.odm.fields import PydanticObjectId
from pydantic import validator
from pymongo import ASCENDING, IndexModel

from .terra import is_account_address


class Address(Document):
    account_address: Indexed(str, unique=True)  # type: ignore
    is_staker: bool = False

    class Config:
        validate_assignment = True

    @validator("account_address", always=True)
    def account_address_should_be_a_terra_address(cls, v: str):
        if not is_account_address(v):
            raise ValueError("invalid account address")
        return v


class Subscription(Document):
    address_id: PydanticObjectId
    protocol: str
    alert_threshold: Optional[float]
    telegram_id: int
    telegram_name: str

    class Collection:
        indexes = [
            IndexModel(
                [
                    ("address_id", ASCENDING),
                    ("protocol", ASCENDING),
                    ("telegram_id", ASCENDING),
                ],
                unique=True,
            )
        ]

    class Config:
        validate_assignment = True

    @validator("alert_threshold", always=True)
    def alert_threshold_is_percentage(cls, v: Any) -> Optional[float]:
        if v is None:
            return v
        try:
            threshold = float(v)
        except ValueError:
            raise ValueError("alert threshold is not a float")
        if not 0 <= threshold <= 100:
            raise ValueError("alert threshold is not a percentage")
        return threshold


class User(Document):
    telegram_user: Indexed(str, unique=True)  # type: ignore

    class Config:
        validate_assignment = True

    @validator("telegram_user", always=True)
    def telegram_user_should_be_a_telegram_account(cls, v: str):
        return v


all_models = [Address, Subscription, User]
