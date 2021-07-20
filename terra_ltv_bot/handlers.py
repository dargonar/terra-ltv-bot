from aiogram import types
from aiogram.dispatcher import Dispatcher
from beanie.operators import All

from .models import Address
from .terra import Terra
from .utils import is_account_address


class Handlers:
    def __init__(self, dp: Dispatcher, terra: Terra) -> None:
        self.terra = terra
        dp.register_message_handler(self.start, commands=["start"])
        dp.register_message_handler(self.add, commands=["add"])
        dp.register_message_handler(self.list_, commands=["list"])
        dp.register_message_handler(self.remove, commands=["remove"])

    async def start(self, message: types.Message) -> None:
        await message.reply("todo")

    async def add(self, message: types.Message) -> None:
        account_address = message.get_args().split(" ")[0]
        user_id = message.from_user.id
        if account_address:
            if is_account_address(account_address):
                address = await Address.get_or_create(account_address)
                if user_id in address.subscribers:
                    await message.reply(f"already subscribed to:\n`{account_address}`")
                else:
                    address.subscribers.append(user_id)
                    await address.save()
                    await message.reply(f"subscribed to:\n`{account_address}`")
            else:
                await message.reply(f"invalid account address:\n`{account_address}`")
        else:
            await message.reply("invalid format")

    async def list_(self, message: types.Message) -> None:
        user_id = message.from_user.id
        reply = ""
        async for result in Address.find(All(Address.subscribers, [user_id])):
            reply += f"`{result.account_address}`\n"
        await message.reply(reply or "not subscribed to any address")

    async def remove(self, message: types.Message) -> None:
        account_address = message.get_args().split(" ")[0]
        user_id = message.from_user.id
        if account_address:
            if is_account_address(account_address):
                address = await Address.get_or_create(account_address)
                if user_id in address.subscribers:
                    address.subscribers.remove(user_id)
                    await address.save()
                    await message.reply(f"unsubscribed from:\n`{account_address}`")
                else:
                    await message.reply(f"not subscribed to:\n`{account_address}`")
            else:
                await message.reply(f"invalid account address:\n`{account_address}`")
        else:
            await message.reply("invalid format")
