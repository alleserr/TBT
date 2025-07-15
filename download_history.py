import os
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from tinkoff.invest import Client, CandleInterval
from invest_api.utils import get_figi_by_ticker

# === Параметры выгрузки ===
TICKERS = ["IMOEXF", "RIU5"]  # Заменён RTS на RIU5 (фьючерс на индекс РТС)
TIMEFRAMES = {
    "H1": CandleInterval.CANDLE_INTERVAL_HOUR,
    "H2": CandleInterval.CANDLE_INTERVAL_2_HOUR
}
DATA_DIR = "./data"
START_DATE = datetime(2023, 11, 1, tzinfo=timezone.utc)
END_DATE = datetime(2024, 6, 1, tzinfo=timezone.utc)

load_dotenv()
token = os.getenv("TINKOFF_API_TOKEN")
os.makedirs(DATA_DIR, exist_ok=True)

def download_candles(ticker, interval, tf_name, start_date, end_date, filename):
    figi = get_figi_by_ticker(token, ticker)
    if not figi:
        print(f"FIGI не найден для тикера {ticker}")
        return
    candles = []
    with Client(token) as client:
        for candle in client.get_all_candles(
            figi=figi,
            from_=start_date,
            to=end_date,
            interval=interval
        ):
            candles.append({
                "time": candle.time.isoformat(),
                "open": float(candle.open.units) + candle.open.nano / 1e9,
                "high": float(candle.high.units) + candle.high.nano / 1e9,
                "low": float(candle.low.units) + candle.low.nano / 1e9,
                "close": float(candle.close.units) + candle.close.nano / 1e9,
                "volume": candle.volume
            })
    df = pd.DataFrame(candles)
    df.to_csv(filename, index=False)
    print(f"Сохранено {len(df)} свечей в {filename}")

for ticker in TICKERS:
    for tf_name, interval in TIMEFRAMES.items():
        filename = os.path.join(DATA_DIR, f"{ticker}_{tf_name}.csv")
        print(f"Выгружаю {ticker} {tf_name}...")
        download_candles(ticker, interval, tf_name, START_DATE, END_DATE, filename) 