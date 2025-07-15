# GigaVIDYA SMARTGuard+ strategy logic implemented in Python using pandas + pandas-ta

from trade_system.strategies.base_strategy import IStrategy
from configuration.settings import StrategySettings
from trade_system.signal import Signal
from tinkoff.invest import HistoricCandle
import pandas as pd
import pandas_ta as ta
from typing import Optional
from dataclasses import dataclass

@dataclass(frozen=True, eq=False, repr=True)
class BacktestSignal:
    figi: str = ""
    signal_type: int = 0
    take_profit_level: float = 0.0
    stop_loss_level: float = 0.0
    time: str = ""
    exit_type: str = ""

class GigaVidyaStrategy(IStrategy):
    def __init__(self, settings: Optional[StrategySettings] = None):
        self._settings = settings or StrategySettings()
        self._lot = 1
        self._short_status = False

    @property
    def settings(self) -> StrategySettings:
        return self._settings

    def update_lot_count(self, lot: int) -> None:
        self._lot = lot

    def update_short_status(self, status: bool) -> None:
        self._short_status = status

    def analyze_candles(self, candles: list[HistoricCandle]) -> Optional[Signal]:
        # TODO: реализовать преобразование свечей в DataFrame, расчёт индикаторов и генерацию сигналов
        return None

    def generate_signals(self, df: pd.DataFrame, figi: str = ""):
        # === Параметры ===
        vidya_len = 14
        rsi_len = 14
        atr_len = 14
        adx_len = 14
        min_atr_percent = 0.3
        min_sl_pct = 0.5 / 100
        max_sl_pct = 1.5 / 100
        adx_threshold = 20
        tp1_mult = 2.0
        tp2_mult = 4.0
        trail_offset_pct = 1.0 / 100
        trail_step_pct = 1.5 / 100

        # === Индикаторы ===
        df = df.copy()
        df['RSI'] = ta.rsi(df['close'], length=rsi_len)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=atr_len)
        df['ADX'] = ta.adx(df['high'], df['low'], df['close'], length=adx_len)['ADX_14']
        df['CMO'] = ta.cmo(df['close'], length=vidya_len)
        df['alpha'] = df['CMO'].abs() / 100

        # === VIDYA ===
        vidya = [df['close'].iloc[0]]
        for i in range(1, len(df)):
            prev = vidya[-1]
            a = df['alpha'].iloc[i]
            price = df['close'].iloc[i]
            vidya.append(prev + a * (price - prev))
        df['VIDYA'] = vidya

        # === Условия входа ===
        df['candle_body'] = (df['close'] - df['open']).abs()
        df['candle_range'] = df['high'] - df['low']
        df['strong_bull'] = (df['close'] > df['open']) & (df['candle_body'] / df['candle_range'] > 0.6)
        df['strong_bear'] = (df['close'] < df['open']) & (df['candle_body'] / df['candle_range'] > 0.6)
        atr_percent = df['ATR'] / df['close'] * 100

        long_signal = (
            (df['close'] > df['VIDYA']) & (df['close'].shift(1) <= df['VIDYA'].shift(1)) &
            (df['RSI'] > 50) & (df['ADX'] > adx_threshold) &
            (atr_percent > min_atr_percent) & df['strong_bull']
        )
        short_signal = (
            (df['close'] < df['VIDYA']) & (df['close'].shift(1) >= df['VIDYA'].shift(1)) &
            (df['RSI'] < 50) & (df['ADX'] > adx_threshold) &
            (atr_percent > min_atr_percent) & df['strong_bear']
        )

        from trade_system.signal import Signal, SignalType
        from decimal import Decimal
        signals = []
        # === Отладочный вывод по индикаторам ===
        print("[DEBUG] Индикаторы: NaN в RSI:", df['RSI'].isna().sum(), "ATR:", df['ATR'].isna().sum(), "ADX:", df['ADX'].isna().sum(), "CMO:", df['CMO'].isna().sum())
        print("[DEBUG] Примеры индикаторов:")
        print(df[['time','close','RSI','ATR','ADX','CMO','VIDYA']].head(20))
        # === Условия входа ===
        print("[DEBUG] Количество long сигналов:", long_signal.sum())
        print("[DEBUG] Количество short сигналов:", short_signal.sum())
        position = None
        entry_price = 0
        sl = None
        tp1 = None
        tp2 = None
        trail_sl = None
        entry_time = None
        for i in range(1, len(df)):
            row = df.iloc[i]
            ts = row['time'] if 'time' in df.columns else str(i)
            price = row['close']
            if position is None:
                if long_signal.iloc[i]:
                    position = 'long'
                    entry_price = price
                    sl = entry_price * (1 - max(min_sl_pct, min(max_sl_pct, row['ATR'] / entry_price)))
                    tp1 = entry_price + (entry_price - sl) * tp1_mult
                    tp2 = entry_price + (entry_price - sl) * tp2_mult
                    trail_sl = None
                    entry_time = ts
                    signals.append(BacktestSignal(figi=figi, signal_type=1, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="Entry"))
                elif short_signal.iloc[i]:
                    position = 'short'
                    entry_price = price
                    sl = entry_price * (1 + max(min_sl_pct, min(max_sl_pct, row['ATR'] / entry_price)))
                    tp1 = entry_price - (sl - entry_price) * tp1_mult
                    tp2 = entry_price - (sl - entry_price) * tp2_mult
                    trail_sl = None
                    entry_time = ts
                    signals.append(BacktestSignal(figi=figi, signal_type=-1, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="Entry"))
            elif position == 'long':
                if price >= tp1:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="TP1"))
                    sl = entry_price  # move to breakeven
                if price >= tp2:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="TP2"))
                    trail_sl = price - price * trail_offset_pct
                if trail_sl and price < trail_sl:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="Trailing"))
                    position = None
                elif price <= sl:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="SL"))
                    position = None
            elif position == 'short':
                if price <= tp1:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="TP1"))
                    sl = entry_price  # move to breakeven
                if price <= tp2:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="TP2"))
                    trail_sl = price + price * trail_offset_pct
                if trail_sl and price > trail_sl:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="Trailing"))
                    position = None
                elif price >= sl:
                    signals.append(BacktestSignal(figi=figi, signal_type=0, take_profit_level=price, stop_loss_level=sl, time=ts, exit_type="SL"))
                    position = None
        # После генерации сигналов:
        print(f"[DEBUG] Всего сгенерировано сигналов: {len(signals)}")
        if signals:
            print("[DEBUG] Примеры сигналов:")
            for s in signals[:5]:
                print(s)
        return signals

# Удалён procedural-блок с df = pd.read_csv("your_data.csv") и последующим кодом вне класса
