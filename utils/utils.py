import logging
from time import sleep
from typing import List, Tuple

import requests
from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableServiceClient
from dotenv import load_dotenv

from config import (
    ACCOUNT_NAME,
    DEAL_URL,
    EMAIL_URL,
    IG_API_KEY,
    IG_IDENTIFIER,
    IG_PASSWORD,
    NOTIF_EMAILS,
    OTC_URL,
    SA_CNXN_STRING,
    STOP_LOSS,
)

load_dotenv()


def add_translations(translations):
    """
    Adds new translations to the db and returns count of how many were added.
    """
    # connect to table storage
    table = TableServiceClient.from_connection_string(
        conn_str=SA_CNXN_STRING
    ).get_table_client("translation")

    count = 0

    for epic, ins in translations.items():
        entity = {
            "PartitionKey": "ig",
            "RowKey": epic,
            "instrument_name": ins,
        }

        # create a new entity in the table
        try:
            table.create_entity(entity)
            count += 1
        except ResourceExistsError:
            pass
        except Exception as e:
            logging.error(e)
    return count


def get_profit_loss(p):
    """
    Get profit loss from a single position (p) returned from GET /positions
    """
    direction = p["position"]["direction"]
    dealsize = p["position"]["dealSize"]

    # find profit loss
    if direction == "BUY":
        price = p["market"]["bid"]
        pl = (price - p["position"]["openLevel"]) * dealsize
        logging.info(f"buy position {p}, pl = {pl}")
    elif direction == "SELL":
        price = p["market"]["offer"]
        pl = (p["position"]["openLevel"] - price) * dealsize
        logging.info(f"sell position {p}, pl = {pl}")

    return pl


def get(dict, keys: List):
    """
    Uses a list of keys to get a nested value from a dictionary.
    """
    d = dict.copy()
    for i in keys:
        d = d.get(i)
    return d


def try_req(url, body, headers, method="get", status_code=200):
    """
    Try max 2 times to do HTTP request.
    """
    for i in range(2):
        logging.info(f"Attempt {i+1} for {method} request to {url}.")
        response = getattr(requests, method)(url, json=body, headers=headers)
        if response.status_code == status_code:
            logging.info("Success")
            return response
        else:
            sleep(2)
    logging.error(f"Failed request. Status code {response.status_code}")
    return response


def get_auth_headers():
    """
    Get auth headers formatted with access token for IG API.
    """
    url = f"{DEAL_URL}/session"
    body = {"identifier": IG_IDENTIFIER, "password": IG_PASSWORD}

    headers = {"X-IG-API-KEY": IG_API_KEY, "version": "3"}
    r = try_req(url, body, headers, method="post")
    if r.status_code == 200:
        access_token = r.json()["oauthToken"]["access_token"]
        account_id = r.json()["accountId"]
        return {
            "Authorization": f"Bearer {access_token}",
            "IG-ACCOUNT-ID": account_id,
            "X-IG-API-KEY": IG_API_KEY,
        }
    else:
        return {}


def get_account(name=None):
    """
    Gets a dict of account attributes based on the given account name.
    """
    if not name:
        name = ACCOUNT_NAME
    url = f"{DEAL_URL}/accounts"

    response = try_req(url, {}, get_auth_headers())
    for i in response.json()["accounts"]:
        if i["accountId"] == name:
            logging.info(f"Raw account details: {i}")
            return {
                "account_name": i["accountName"],
                "profit_loss": i["balance"]["profitLoss"],
                "balance": i["balance"]["balance"],
            }


def pl_ratio_logic(account):
    """
    Implements logic to check profit loss ratio and invoke functions to close positions
    if profit loss ratio <= -STOP_LOSS.
    """
    try:
        pl_ratio = account.get("profit_loss") / account.get("balance")
        logging.info(f"Performing pl logic on account: {account}")
        if pl_ratio <= -STOP_LOSS:
            msg_balances = (
                f"PL: {account.get('profit_loss')}, Balance: {account.get('balance')}"
            )
            logging.info(msg_balances)
            msg_ratios = (
                f"Profit loss ratio less than - {STOP_LOSS} ({pl_ratio}). "
                "Closing positions."
            )
            logging.info(msg_ratios)
            open_positions = get_open_positions()
            msg = close_positions(open_positions)
            send_email(" ".join([msg, msg_ratios, msg_balances]))
        else:
            msg = (
                f"Profit loss ratio greater than -{STOP_LOSS} ({pl_ratio})."
                "No action required."
            )
            logging.info(msg)
    except ZeroDivisionError:
        msg = "Balance is zero. No action required."
        logging.info(msg)


def close_positions(open_positions):
    """
    Closes all given positions.
    Open positions is a list of positions from get_open_positions func.
    """
    logging.info("Closing positions.")
    close_positions = []
    for p in open_positions:
        close_positions += [
            {
                "dealId": None,
                "expiry": "DFB",
                "direction": "SELL" if p["position"]["direction"] == "BUY" else "BUY",
                "size": str(p["position"]["dealSize"]),
                "orderType": "MARKET",
                "timeInForce": "FILL_OR_KILL",
                "epic": p["market"]["epic"],
                "quoteId": None,
                "level": None,
            }
        ]

    headers = get_auth_headers()
    headers["_method"] = "DELETE"
    failed = []
    for p in close_positions:
        r = try_req(OTC_URL, p, headers, method="post")
        print(r.text)
        if r.status_code != 200:
            failed.append(r)
    n_failed = len(failed)
    n_closed = len(close_positions) - n_failed
    msg = f"{n_closed} positions closed. Failed to close {n_failed} positions."
    return msg


def get_open_positions(condition: Tuple = None):
    """
    Gets open positions. Can use a condition to filter positions.
    E.g. condition = (['market', 'epic'], 'IX.D.NASDAQ.CASH.IP')
        where condition[0] is the list of nested dictionary keys and
        condition[1] is the value.
    """
    url = f"{DEAL_URL}/positions"
    r = try_req(url, {}, get_auth_headers())
    positions = r.json()["positions"]

    if condition:
        return [i for i in positions if get(i, condition[0]) == condition[1]]
    return positions


def send_email(msg, status="Positions closed."):
    """
    Sends email by sending an HTTP request to a logic app.
    """
    payloads = [{"email": i, "status": status, "message": msg} for i in NOTIF_EMAILS]
    for payload in payloads:
        requests.post(EMAIL_URL, json=payload)


def open_position(epic: str, direction: str, size: str):
    """
    epic e.g. "IX.D.NASDAQ.CASH.IP"
    direction e.g. "BUY"
    size e.g. "1"
    """
    data = {
        "epic": epic,
        "expiry": "DFB",
        "direction": direction,
        "size": size,
        "orderType": "MARKET",
        "timeInForce": "FILL_OR_KILL",
        "level": None,
        "guaranteedStop": "false",
        "stopLevel": None,
        "stopDistance": None,
        "trailingStop": None,
        "trailingStopIncrement": None,
        "forceOpen": "false",
        "limitLevel": None,
        "limitDistance": None,
        "quoteId": None,
        "currencyCode": "GBP",
    }
    headers = get_auth_headers()
    headers["Version"] = "2"
    return try_req(OTC_URL, data, headers, method="post")
