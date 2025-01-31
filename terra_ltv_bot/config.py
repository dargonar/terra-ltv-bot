import os
# import ujson
from typing import Optional


class Config:
    def __init__(
        self,
        debug: bool,
        bot_token: str,
        db_name: str,
        db_host: str,
        db_port: int,
        redis_url: str,
        lcd_url: str,
        chain_id: str,
        anchor_market_contract: str,
        anchor_overseer_contract: str,
        telegram_admin_usermames: str,
        validator_address: Optional[str],
    ) -> None:
        self.debug = debug
        self.bot_token = bot_token
        self.db_name = db_name
        self.db_host = db_host
        self.db_port = db_port
        self.redis_url = redis_url
        self.lcd_url = lcd_url
        self.chain_id = chain_id
        self.anchor_market_contract = anchor_market_contract
        self.anchor_overseer_contract = anchor_overseer_contract
        self.telegram_admin_usermames = telegram_admin_usermames
        self.validator_address = validator_address

    @classmethod
    def from_env(cls) -> "Config":
        from dotenv import load_dotenv
        load_dotenv()
        return cls(
            bool(os.getenv("DEBUG")),
            os.environ["BOT_TOKEN"],
            os.getenv("DB_NAME", "ltv"),
            os.getenv("DB_HOST", "127.0.0.1"),
            int(os.getenv("DB_PORT", "27017")),
            os.getenv("REDIS_URL", "redis://localhost"),
            os.environ["LCD_URL"],
            os.environ["CHAIN_ID"],
            os.environ["ANCHOR_MARKET_CONTRACT"],
            os.environ["ANCHOR_OVERSEER_CONTRACT"],
            os.environ["TELEGRAM_ADMIN_USERMAMES"],
            os.getenv("VALIDATOR_ADDRESS"),
        )
