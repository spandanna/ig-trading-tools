import logging

import azure.functions as func

from utils.utils import get_account, pl_ratio_logic


def main(mytimer: func.TimerRequest) -> None:
    """
    Closes all positions if the overall loss on the account is great than STOP_LOSS.
    """

    logging.info("AccountStopLoss triggered.")
    account = get_account()
    pl_ratio_logic(account)
    logging.info("AccountStopLoss finished.")
