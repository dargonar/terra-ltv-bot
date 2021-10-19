import logging

from . import __name__ as __root_name__
from . import __version__ as version
from .bot import Bot
from .config import Config

log = logging.getLogger(__name__)


def entrypoint() -> None:
    log.info(f"starting terra-ltv-bot v{version}")
    config = Config.from_env()
    if config.debug:
        logging.getLogger(__root_name__).setLevel(logging.DEBUG)
    # log.info(f"starting #2")
    bot = Bot(config)
    # log.info(f"starting #3")
    bot.run()
    # log.info(f"starting #4")
