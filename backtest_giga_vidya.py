import pandas as pd
from trade_system.strategies.strategy_factory import StrategyFactory
import os
from decimal import Decimal
import numpy as np
from datetime import datetime, timezone

# === Импортируем BacktestSignal ===
from trade_system.strategies.giga_vidya_strategy import BacktestSignal

# === Параметры теста ===
TICKERS = ["IMOEXF"]  # Тестируем только IMOEXF
TIMEFRAMES = ["H1", "H2"]
DATA_DIR = "./data"  # Папка с CSV-файлами: {ticker}_{tf}.csv
START_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)

# === Метрики для сбора ===
RESULT_COLUMNS = [
    "ticker", "timeframe", "total_trades", "winrate", "avg_pnl", "gross_profit", "gross_loss", "net_pnl",
    "max_profit", "max_loss", "profit_factor", "expectancy", "avg_win", "avg_loss", "win_loss_ratio",
    "max_drawdown", "TP1_count", "TP2_count", "Trailing_count", "SL_count", "SmartExit_count", "avg_bars_in_trade"
]
results = []

for ticker in TICKERS:
    for tf in TIMEFRAMES:
        csv_path = os.path.join(DATA_DIR, f"{ticker}_{tf}.csv")
        if not os.path.exists(csv_path):
            print(f"Нет данных: {csv_path}")
            continue
        df = pd.read_csv(csv_path)
        # Фильтруем по периоду
        df["time"] = pd.to_datetime(df["time"])
        df = df[(df["time"] >= START_DATE) & (df["time"] < END_DATE)].reset_index(drop=True)
        if df.empty:
            print(f"Нет данных в периоде для {ticker} {tf}")
            continue
        strategy = StrategyFactory.new_factory("giga_vidya")
        signals = strategy.generate_signals(df, figi=ticker)

        # === Собираем сделки ===
        trades = []  # [dict: entry_time, exit_time, entry_price, exit_price, pnl, bars, exit_type]
        entry = None
        entry_idx = None
        for idx, sig in enumerate(signals):
            if sig.exit_type == "Entry":
                entry = sig
                entry_idx = idx
            elif sig.exit_type in ["TP1", "TP2", "SL", "Trailing", "SmartExit"] and entry is not None:
                entry_price = float(entry.take_profit_level) if entry.take_profit_level is not None else 0.0
                exit_price = float(sig.take_profit_level) if sig.take_profit_level is not None else 0.0
                pnl = exit_price - entry_price if entry.signal_type == 1 else entry_price - exit_price
                bars = idx - entry_idx
                trades.append({
                    "entry_time": entry.time,
                    "exit_time": sig.time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "bars": bars,
                    "exit_type": sig.exit_type
                })
                entry = None
                entry_idx = None

        if not trades:
            results.append({col: 0 for col in RESULT_COLUMNS} | {"ticker": ticker, "timeframe": tf})
            continue

        # === Метрики ===
        pnls = [t["pnl"] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        total_trades = len(trades)
        winrate = len(wins) / total_trades if total_trades else 0
        avg_pnl = np.mean(pnls) if pnls else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        net_pnl = gross_profit - gross_loss
        max_profit = max(wins) if wins else 0
        max_loss = min(losses) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss else 0
        expectancy = avg_pnl * winrate - (np.mean(losses) if losses else 0) * (1 - winrate)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        win_loss_ratio = avg_win / abs(avg_loss) if avg_loss else 0
        # Max drawdown (капитальная кривая)
        equity = np.cumsum(pnls)
        drawdown = np.maximum.accumulate(equity) - equity
        max_drawdown = np.max(drawdown) if len(drawdown) else 0
        # Exit type counts
        TP1_count = sum(1 for t in trades if t["exit_type"] == "TP1")
        TP2_count = sum(1 for t in trades if t["exit_type"] == "TP2")
        Trailing_count = sum(1 for t in trades if t["exit_type"] == "Trailing")
        SL_count = sum(1 for t in trades if t["exit_type"] == "SL")
        SmartExit_count = sum(1 for t in trades if t["exit_type"] == "SmartExit")
        avg_bars_in_trade = np.mean([t["bars"] for t in trades]) if trades else 0

        results.append({
            "ticker": ticker,
            "timeframe": tf,
            "total_trades": total_trades,
            "winrate": round(winrate, 3),
            "avg_pnl": round(avg_pnl, 3),
            "gross_profit": round(gross_profit, 3),
            "gross_loss": round(gross_loss, 3),
            "net_pnl": round(net_pnl, 3),
            "max_profit": round(max_profit, 3),
            "max_loss": round(max_loss, 3),
            "profit_factor": round(profit_factor, 3),
            "expectancy": round(expectancy, 3),
            "avg_win": round(avg_win, 3),
            "avg_loss": round(avg_loss, 3),
            "win_loss_ratio": round(win_loss_ratio, 3),
            "max_drawdown": round(max_drawdown, 3),
            "TP1_count": TP1_count,
            "TP2_count": TP2_count,
            "Trailing_count": Trailing_count,
            "SL_count": SL_count,
            "SmartExit_count": SmartExit_count,
            "avg_bars_in_trade": round(avg_bars_in_trade, 2)
        })

# === Выводим таблицу результатов ===
results_df = pd.DataFrame(results, columns=RESULT_COLUMNS)
print("\nРезультаты бэктеста:")
print(results_df.to_string(index=False)) 