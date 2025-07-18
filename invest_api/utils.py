import uuid
from decimal import Decimal

from grpc import StatusCode
from tinkoff.invest import MoneyValue, Quotation, Candle, HistoricCandle
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from tinkoff.invest import Client
import os

__all__ = ()


def rub_currency_name() -> str:
    return "rub"


def moex_exchange_name() -> str:
    return "MOEX"


def moneyvalue_to_decimal(money_value: MoneyValue) -> Decimal:
    return quotation_to_decimal(
        Quotation(
            units=money_value.units,
            nano=money_value.nano
        )
    )


def decimal_to_moneyvalue(decimal: Decimal, currency: str = rub_currency_name()) -> MoneyValue:
    quotation = decimal_to_quotation(decimal)
    return MoneyValue(
        currency=currency,
        units=quotation.units,
        nano=quotation.nano
    )


def generate_order_id() -> str:
    return str(uuid.uuid4())


def candle_to_historiccandle(candle: Candle) -> HistoricCandle:
    return HistoricCandle(
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        time=candle.time,
        is_complete=True
    )


def invest_api_retry_status_codes() -> set[StatusCode]:
    return {StatusCode.CANCELLED, StatusCode.DEADLINE_EXCEEDED, StatusCode.RESOURCE_EXHAUSTED,
            StatusCode.FAILED_PRECONDITION, StatusCode.ABORTED, StatusCode.INTERNAL,
            StatusCode.UNAVAILABLE, StatusCode.DATA_LOSS, StatusCode.UNKNOWN}


def get_figi_by_ticker(token: str, ticker: str) -> str:
    """Возвращает FIGI по тикеру фьючерса через Tinkoff Invest API."""
    with Client(token) as client:
        response = client.instruments.futures()
        for future in response.instruments:
            if future.ticker == ticker:
                return future.figi
    return None
