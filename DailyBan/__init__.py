import datetime as dt
import logging

import azure.functions as func
import requests
from azure.data.tables import TableServiceClient

from config import DEAL_URL, SA_CNXN_STRING
from utils.utils import (
    close_positions,
    get_account,
    get_auth_headers,
    get_open_positions,
    send_email,
)


def main(mytimer: func.TimerRequest) -> None:
    """
    If an instrument has made a loss greater than 10% over the past week,
    close open positions.

    """
    # get transactions for the past week
    today = dt.date.today().isoformat()
    start_date = (today - dt.timedelta(days=7)).isoformat()
    url = (
        f"{DEAL_URL}/history/transactions?type=ALL_DEAL&from={start_date}&pageSize=900"
    )
    logging.info(url)
    headers = get_auth_headers()
    headers["version"] = "2"
    resp = requests.get(url, headers=headers)

    balance = get_account()["balance"]
    summed = {}

    # sum up the balance for each instrument across all transactions
    for transaction in resp.json()["transactions"]:
        instrument_name = transaction["instrumentName"]
        pl = float(transaction["profitAndLoss"][1:])
        summed[instrument_name] = (
            summed[instrument_name] + pl if summed.get(instrument_name) else pl
        )

    # if the balance for an instrument is a 10% loss, add the instrument to the list
    instruments_to_close = []
    for instrument_name, instrument_balance in summed.items():
        pl_ratio = instrument_balance / balance
        if pl_ratio <= -0.1:
            instruments_to_close.append(
                {
                    "instrument_name": instrument_name,
                    "pl_ratio": pl_ratio,
                    "balance": instrument_balance,
                }
            )

    # get the epic name from the translations table
    translations_table = TableServiceClient.from_connection_string(
        conn_str=SA_CNXN_STRING
    ).get_table_client("translation")

    for instrument in instruments_to_close:
        translations = [
            i
            for i in translations_table.query_entities(
                query_filter=f"instrument_name eq '{instrument['instrument_name']}'"
            )
        ]
        if len(translations) == 1:
            instrument["epic"] = translations[0][
                "RowKey"
            ]  # get the epic name from the translation results
        elif len(translations) == 0:
            send_email(
                f"No epic found for instrument {instrument['instrument_name']}",
                "Missing epic / instrument name translation.",
            )
        else:
            logging.info(
                f"""Multiple translations found for the same instrument {instrument}.
                Translations: {translations}"""
            )

    # close any open positions
    for condition in [
        (["market", "epic"], instrument["epic"]) for instrument in instruments_to_close
    ]:
        positions = get_open_positions(condition)
        if len(positions) > 0:
            msg = close_positions(positions)
            send_email(msg, status=f"7 Day Ban - closed {condition[1]} positions.")
