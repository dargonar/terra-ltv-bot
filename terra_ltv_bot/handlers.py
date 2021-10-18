import asyncio
import logging

from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.exceptions import Throttled
from aioredis import Redis
from pymongo.errors import DuplicateKeyError

from functools import wraps
from typing import Callable

from .config import Config
from .models import Address, Subscription, User
from .terra import FINDER_URL, Terra

log = logging.getLogger(__name__)

_admins_cache_key = 'telegram:admins'

def is_admin(f: Callable) -> Callable:
    async def inner(self, message: types.Message):
        user = message.from_user
        if user is None: 
            await message.reply('suck it!')
            return False
        if user.username not in self.telegram_admins:
            await message.reply('suck it!')
            return False
        
        return await f(self, message=message)

    return inner


def in_role(f: Callable) -> Callable:
    @wraps(f)
    async def wrapper(self, message: types.Message):
        user = message.from_user
        if user is None: 
            await message.reply('suck it!')
            return False
        admins = await self.redis.get(_admins_cache_key)
        admins = admins.decode() if admins is not None else ''
        log.info(f"is_admin: admins list: {admins}")
        # admins = '' if admins is None else admins
        admins_list = str(admins).split(',')
        admins_list = [*self.telegram_admins, *admins_list]
        log.info(f"is_admin: admins list array: {admins_list}")
        username = user.username
        if username not in admins_list: 
            await message.reply('suck it!')
            return False
        
        await f(self, message=message)

    return wrapper


class Handlers:
    def __init__(self, dp: Dispatcher, terra: Terra, redis: Redis, config: Config) -> None:
        self.dp = dp
        self.terra = terra
        self.redis = redis
        self.config = config
        self.telegram_admins = self.config.telegram_admin_usermames.split(',')
        dp.register_message_handler(self.start, commands=["start", "help"])
        dp.register_message_handler(self.subscribe, commands=["subscribe"])
        dp.register_message_handler(self.list_, commands=["list"])
        dp.register_message_handler(self.unsubscribe, commands=["unsubscribe"])
        dp.register_message_handler(self.ltv, commands=["ltv"])
        dp.register_message_handler(self.list_users, commands=["users"])
        dp.register_message_handler(self.add_user, commands=["add_user"])
        dp.register_message_handler(self.remove_user, commands=["rem_user"])

    async def init_hack(self):
        users = await User.all().to_list()
        names = [user.telegram_user for user in users]
        names = ','.join(names)
        await self.redis.set(_admins_cache_key, names)

    async def start(self, message: types.Message) -> None:
        log.info(f"@{message.from_user.username} {message.get_args()}")
        await message.reply(
            "<u>Terra LTV bot</u>\n"
            "\n"
            "This bot lets you subscribe to Terra addresses and receive "
            "alerts when they are close to liquidation on a spcific protocol.\n"
            "\n"
            "<u>Supported protocols:</u>\n"
            "\n"
            " - <a href='https://anchorprotocol.com'>Anchor borrow</a>, "
            "default safe threshold: 45%\n"
            "\n"
            "<u>Commands:</u>\n"
            "\n"
            "/help\nDisplay this message.\n"
            "\n"
            "/subscribe address (threshold)\n"
            "<pre>/subscribe terra1[...] 55</pre>\n"
            "<pre>/subscribe terra1[...]</pre>\n"
            "Subscribe to an address LTV alerts.\n"
            "Whe not specified, the alert threshold defaults to "
            "the protocol safe value.\n"
            "\n"
            "/list\nList all subscribed addresses and their current LTV.\n"
            "\n"
            "/unsubscribe address\n"
            "<pre>/unsubscribe terra1[...]</pre>\n"
            "Unsubscribe from an address LTV alerts.\n"
            "\n"
            "/ltv address\n"
            "<pre>/ltv terra1[...]</pre>\n"
            "Retreive LTV for an arbitrary address.\n"
            "\n"
            "/users\nList all users that can configure alerts.\n"
            "\n"
            "/add_user telegram_user_name\n"
            "<pre>/add_user telegram_user_name</pre>\n"
            "Enables telegram user to create and remove its alerts.\n"
            "\n"
            "/rem_user telegram_user_name\n"
            "<pre>/rem_user telegram_user_name</pre>\n"
            "Disables telegram user from creating and removing its alerts.\n"
            "\n"
            "made with ♥ by Stratton "
            "<a href='https://github.com/dargonar/terra-ltv-bot'>project source</a>"
        )

    @in_role
    async def subscribe(self, message: types.Message) -> None:
        try:
            await self.dp.throttle("add", rate=1)
        except Throttled:
            await message.reply("too many requests")
        else:
            user_id = message.from_user.id
            user_name = message.from_user.username
            args = message.get_args().split(" ")
            account_address = args[0] if 0 < len(args) else None
            alert_threshold = args[1] if 1 < len(args) else None
            log.info(f"{user_id} {user_name} {args}")
            if account_address:
                try:
                    address = await Address.find_one(
                        Address.account_address == account_address
                    )
                    if not address:
                        address = Address(account_address=account_address)
                        await address.insert()
                    subscription = await Subscription.find_one(
                        Subscription.address_id == address.id,
                        Subscription.protocol == "anchor",
                        Subscription.telegram_id == user_id,
                    )
                    if subscription:
                        if alert_threshold != subscription.alert_threshold:
                            subscription.alert_threshold = alert_threshold
                            await self.redis.delete(
                                f"{account_address}:anchor:{subscription.telegram_id}"
                            )
                    else:
                        subscription = Subscription(
                            address_id=address.id,
                            protocol="anchor",
                            alert_threshold=alert_threshold,
                            telegram_id=user_id,
                            telegram_name=user_name
                        )
                    await subscription.save()
                    await message.reply(
                        "subscribed to "
                        "<a href='{}{}/address/{}'>{}...{}</a>".format(
                            FINDER_URL,
                            self.terra.lcd.chain_id,
                            address.account_address,
                            address.account_address[:13],
                            address.account_address[-5:],
                        )
                    )
                except ValueError:
                    await message.reply("invalid parameters")
                except DuplicateKeyError:
                    await message.reply(
                        "already subscribed to "
                        "<a href='{}{}/address/{}'>{}...{}</a>".format(
                            FINDER_URL,
                            self.terra.lcd.chain_id,
                            address.account_address,
                            address.account_address[:13],
                            address.account_address[-5:],
                        )
                    )
            else:
                await message.reply("invalid format, missing account address")

    @in_role
    async def list_(self, message: types.Message) -> None:
        try:
            await self.dp.throttle("add", rate=1)
        except Throttled:
            await message.reply("too many requests")
        else:
            user_id = message.from_user.id
            user_name = message.from_user.username
            args = message.get_args().split(" ")
            log.info(f"{user_id} {user_name} {args}")
            subscriptions = await Subscription.find(
                Subscription.telegram_id == user_id
            ).to_list()
            addresses = [
                await Address.get(subscription.address_id)
                for subscription in subscriptions
            ]
            ltvs = await asyncio.gather(
                *[self.terra.ltv(address.account_address) for address in addresses]
            )
            reply = ""
            for index, address in enumerate(addresses):
                url = "{}{}/address/{}".format(
                    FINDER_URL,
                    self.terra.lcd.chain_id,
                    address.account_address,
                )
                subscription = subscriptions[index]
                ltv = ltvs[index]
                threshold = subscription.alert_threshold or 45
                reply += "{} <a href='{}'>{}...{}</a> {}/{}%\n".format(
                    "🔴" if ltv >= threshold else "🟢",
                    url,
                    address.account_address[:13],
                    address.account_address[-5:],
                    ltv,
                    threshold,
                )
            await message.reply(reply or "not subscribed to any address")

    @in_role
    async def unsubscribe(self, message: types.Message) -> None:
        try:
            await self.dp.throttle("add", rate=1)
        except Throttled:
            await message.reply("too many requests")
        else:
            user_id = message.from_user.id
            user_name = message.from_user.username
            args = message.get_args().split(" ")
            account_address = args[0] if 0 < len(args) else None
            log.info(f"{user_id} {user_name} {args}")
            if account_address:
                address = await Address.find_one(
                    Address.account_address == account_address
                )
                subscription = (
                    await Subscription.find_one(
                        Subscription.address_id == address.id,
                        Subscription.protocol == "anchor",
                        Subscription.telegram_id == user_id,
                    )
                    if address
                    else None
                )
                if subscription:
                    await subscription.delete()
                    await message.reply(
                        "unsubscribed from "
                        "<a href='{}{}/address/{}'>{}...{}</a>".format(
                            FINDER_URL,
                            self.terra.lcd.chain_id,
                            address.account_address,
                            address.account_address[:13],
                            address.account_address[-5:],
                        )
                    )
                else:
                    await message.reply("subscription not found")
            else:
                await message.reply("invalid format, missing account address")

    @in_role
    async def ltv(self, message: types.Message) -> None:
        try:
            await self.dp.throttle("add", rate=1)
        except Throttled:
            await message.reply("too many requests")
        else:
            user_id = message.from_user.id
            user_name = message.from_user.username
            args = message.get_args().split(" ")
            account_address = args[0] if 0 < len(args) else None
            log.info(f"{user_id} {user_name} {args}")
            if account_address:
                ltv = await self.terra.ltv(account_address)
                await message.reply(f"{ltv}%" if ltv else "no loan found")
            else:
                await message.reply("invalid format, missing account address")

    @is_admin
    async def list_users(self, message: types.Message) -> None:
        try:
            await self.dp.throttle("add", rate=1)
        except Throttled:
            await message.reply("too many requests")
            return
        
        reply = ""
        for index, user in enumerate(self.telegram_admins):
            _index = index + 1
            reply += "{} {}\n".format(
                _index,
                user
            )
        users = await User.all().to_list()
        for index, user in enumerate(users):
            _index = index + len(self.telegram_admins) + 1
            reply += "{} {}\n".format(
                _index,
                user.telegram_user
            )
        await message.reply(reply or "no users added")
                
    @is_admin
    async def add_user(self, message: types.Message) -> None:
        user_id = message.from_user.id
        user_name = message.from_user.username
        args = message.get_args().split(" ")
        new_user = args[0] if 0 < len(args) else None
        if new_user in self.telegram_admins:
            await message.reply(f'{new_user} is already an admin!')
            return

        reply = ''
        try:
            user = await User.find_one(
                User.telegram_user == new_user
            )
            if not user:
                user = User(telegram_user=new_user)
                await user.insert()
                await self.init_hack()
                reply = f'User {new_user} can now add alerts.'
            else:
                reply = f'User {new_user} already exists!'
        except Exception as ex:
            await message.reply(str(ex))
            return

        await message.reply(reply)
    
    @is_admin
    async def remove_user(self, message: types.Message) -> None:
        args = message.get_args().split(" ")
        new_user = args[0] if 0 < len(args) else None
        if new_user in self.telegram_admins:
            await message.reply(f'Cant remove an admin!')
            return

        reply = ''
        try:
            log.info(f"remove_user#0")
            user = await User.find_one(
                User.telegram_user == new_user
            )
            if user is None:
                await message.reply('User does not exists!')
                return                
            await user.delete()
            log.info(f"remove_user#1")
            subscriptions = await Subscription.find(
                Subscription.telegram_name == new_user
            ).to_list()
            log.info(f"remove_user#2")
            for subscription in enumerate(subscriptions):
                address = await Address.find_one(
                    Address.id == subscription.address_id
                )
                log.info(f"remove_user#3")
                if address is not None:
                    reply += f"Address {address.account_address} ({str(address.id)}) removed\n"
                    address.delete()
                log.info(f"remove_user#4")
                reply += f"Subscription {str(subscription.address_id)} removed\n"
                subscription.delete()

        except Exception as ex:
            log.info(f"remove_user {str(ex)}")
            await message.reply(str(ex))
            return

        await self.init_hack()

        await message.reply(f'User {new_user} removed!')
