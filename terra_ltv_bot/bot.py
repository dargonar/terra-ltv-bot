import aioredis
import motor
import logging
from aiogram import Bot as TelegramBot
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from beanie import init_beanie
from terra_sdk.client.lcd.lcdclient import AsyncLCDClient

from .config import Config
from .handlers import Handlers
from .models import all_models
from .tasks import Tasks
from .terra import Terra

log = logging.getLogger(__name__)


class Bot:
    def __init__(self, config: Config) -> None:
        self.bot = TelegramBot(token=config.bot_token, parse_mode=types.ParseMode.HTML)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.terra = Terra(
            AsyncLCDClient(url=config.lcd_url, chain_id=config.chain_id),
            anchor_market_contract=config.anchor_market_contract,
            anchor_overseer_contract=config.anchor_overseer_contract,
        )
        log.info(f"Bot::__init__() {config.db_host}:{config.db_port}")
        self.db = motor.motor_asyncio.AsyncIOMotorClient(
            host=config.db_host, port=config.db_port
        )[config.db_name]
        self.redis = aioredis.from_url(config.redis_url)
        self.config = config

    async def on_startup(self, dp: Dispatcher):
        log.info(f"Bot::on_startup() #1")
        await init_beanie(
            database=self.db,
            document_models=all_models,
        )
        log.info(f"Bot::on_startup() #2")
        x = Handlers(dp=dp, terra=self.terra, redis=self.redis, config=self.config)
        await x.init_hack()
        Tasks(dp, self.bot, self.terra, self.redis)

    async def on_shutdown(self, _: Dispatcher):
        pass

    def run(self) -> None:
        executor.start_polling(
            self.dp,
            on_startup=self.on_startup,
            on_shutdown=self.on_shutdown,
        )
