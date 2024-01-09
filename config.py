import os

from dotenv import load_dotenv

load_dotenv()

# IG API setup
IG_API_URL = os.getenv("IG_API_URL")
DEAL_URL = f"{IG_API_URL}/gateway/deal"
OTC_URL = f"{DEAL_URL}/positions/otc"
IG_API_KEY = os.getenv("IG_API_KEY")
IG_IDENTIFIER = os.getenv("IG_IDENTIFIER")
IG_PASSWORD = os.getenv("IG_PASSWORD")
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME")

# Notifications
# getting up to 9 notification email addresses
NOTIF_EMAILS = [
    os.getenv(f"NOTIF_EMAIL_{i}")
    for i in range(9)
    if os.getenv(f"NOTIF_EMAIL_{i}") is not None
]
EMAIL_URL = os.getenv("EMAIL_URL")

# Trading parameters
STOP_LOSS = float(os.getenv("STOP_LOSS", 0))
TRADING_AMOUNT = int(os.getenv("TRADING_AMOUNT", 0))
BANNED_TRADES = [
    "CS.D.GBPUSD.TODAY.IP",
    "IX.D.DAX.DAILY.IP",
    "IX.D.NASDAQ.CASH.IP",
    "IX.D.FTSE.DAILY.IP",
    "IX.D.SPTRD.DAILY.IP",
    "IX.D.DOW.DAILY.IP",
    "IX.D.HANGSENG.DAILY.IP",
    "IX.D.HSCHIN.DFB.IP",
    "IX.D.XINHUA.DFB.IP",
    "IX.D.HSTECH.DAILY.IP",
    "IX.D.ASX.MONTH1.IP",
    "IX.D.MIB.CASH.IP",
    "IX.D.CAC.DAILY.IP",
    "IX.D.NIKKEI.DAILY.IP",
    "IX.D.IBEX.CASH.IP",
]

# Azure storage account credentials
SA_KEY = os.getenv("SA_KEY")
SA_NAME = os.getenv("SA_NAME")
SA_CNXN_STRING = (
    f"DefaultEndpointsProtocol=https;AccountName={SA_NAME};"
    "AccountKey={SA_KEY};EndpointSuffix=core.windows.net"
)
