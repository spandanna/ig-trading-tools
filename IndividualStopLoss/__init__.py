import logging

import azure.functions as func

from utils.utils import (
    add_translations,
    close_positions,
    get_account,
    get_open_positions,
    get_profit_loss,
    send_email,
)


def main(mytimer: func.TimerRequest) -> None:
    """
    If a single instrument has a loss greater than 10%, close all positions on that
    instrument.

    This function also adds to the translations table since the IG API endpoint it
    uses gives the epic name and the instrument name. The translations table is needed
    for a different function which needs the epic name but only has access to the
    instrument name.
    """
    logging.info("IndividualStopLoss triggered.")

    # summed is a dictionary of epics aggregated on their profit loss
    # {'epic_name': profit loss value}
    summed = {}
    translations = {}

    # loop through all open positions and and aggregate on 'epic' and SUM of profit loss
    for position in get_open_positions():

        epic = position["market"]["epic"]
        instrument_name = position["market"]["instrumentName"]
        pl = get_profit_loss(position)

        # if epic is already in the summed dictionary, add profit loss to existing
        # profit loss for epic otherwise add it in with the pl
        summed[epic] = (
            {
                "pl": summed[epic]["pl"] + pl,
                "positions": summed[epic]["positions"] + [position],
            }
            if summed.get(epic)
            else {"pl": pl, "positions": [position]}
        )

        # add new epic and instrument name to the translations dictionary
        if not translations.get(epic):
            translations[epic] = instrument_name

    logging.info(f"summed dict: {summed}")
    balance = get_account()["balance"]

    # go through all the epics in summed and add to to_close if pl <-0.1
    to_close = []
    for epic, pl in summed.items():
        pl_ratio = pl["pl"] / balance
        logging.info(f"pl ratio for {epic} is {pl_ratio}")
        if pl_ratio <= -0.1:
            to_close += pl["positions"]

    if to_close:
        logging.info(f"closing positions: {to_close}")
        msg = close_positions(to_close)
        send_email(msg, status="IndividualStopLoss function invoked.")

    # updating the translations table with any newly found translations
    logging.info(f"translations: {translations}")
    add_translations(translations)

    logging.info("IndividualStopLoss finished.")
