import logging

import azure.functions as func

from utils.utils import close_positions, get_open_positions, send_email


def main(mytimer: func.TimerRequest) -> None:
    """
    Closes any positions which are still open at the end of the day.
    """
    logging.info("EODClose triggered.")
    open_positions = get_open_positions()
    if open_positions:
        msg = close_positions(open_positions)
        send_email(msg, status="EODClose function invoked")
    logging.info("EODClose finished.")
