import logging

import azure.functions as func

from config import BANNED_TRADES
from utils.utils import close_positions, get_open_positions, send_email


def main(mytimer: func.TimerRequest) -> None:
    """
    Closes any positions which are on instruments in BANNED_INSTRUMENTS.
    """
    logging.info("PermanentBan triggered.")
    for epic in BANNED_TRADES:
        open_positions = get_open_positions(condition=(["market", "epic"], epic))
        logging.info(f"Banned open positions: {open_positions}")
        if open_positions:
            logging.info("Closing banned positions.")
            msg = close_positions(open_positions)
            send_email(msg, status=f"TradingBan function closed {epic} positions")

    logging.info("PermanentBan finished.")
