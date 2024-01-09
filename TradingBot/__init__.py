import azure.functions as func

from config import TRADING_AMOUNT
from utils.utils import open_position


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Creates new trades from a POST request.
    """
    # receive alert from webhook
    if req.method == "POST":
        req_body = req.get_json()

        market = req_body.get("market")
        type = req_body.get("type")
        price = float(req_body.get("price"))

        ig_size = str(round(((TRADING_AMOUNT / price) * 100), 2))

        # open/close positions
        open_position(epic=market, direction=type, size=ig_size)

        # return 200 status code
        return func.HttpResponse(f"Success {market}, {type}, {price}", status_code=200)
