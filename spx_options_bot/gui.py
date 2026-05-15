from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from .app import BotRunResult, run_once
from .broker_ibkr import IbkrConnectionError
from .config import BotConfig


ENV_PATH = Path(".env")
BG = "#f5f7fa"
CARD = "#ffffff"
TEXT = "#17202a"
MUTED = "#5b6673"
DARK = "#0f1720"
LOG_TEXT = "#e7edf3"
BORDER = "#d6dbe1"
BLUE = "#1677ff"


class GuiLogHandler(logging.Handler):
    def __init__(self, messages: queue.Queue[tuple[str, object]]) -> None:
        super().__init__()
        self.messages = messages

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.messages.put(("log", self.format(record)))
        except Exception:
            pass


class BotGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SPX 0DTE Iron Condor Bot")
        self.geometry("980x720")
        self.minsize(920, 650)

        self.config_model = BotConfig.from_env()
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.fields: dict[str, tk.StringVar] = {}
        self.checks: dict[str, tk.BooleanVar] = {}

        self._build_style()
        self._build_layout()
        self._load_fields()
        self._install_log_handler()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_messages)

    def _build_style(self) -> None:
        self.configure(bg=BG)

    def _build_layout(self) -> None:
        root = tk.Frame(self, bg=BG, padx=16, pady=16)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        header = tk.Frame(root, bg=BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        tk.Label(
            header,
            text="SPX 0DTE Iron Condor Bot",
            bg=BG,
            fg=TEXT,
            font=("Helvetica", 20, "bold"),
        ).grid(
            row=0, column=0, sticky="w"
        )
        header.columnconfigure(0, weight=1)

        actions = tk.Frame(header, bg=BG)
        actions.grid(row=0, column=1, sticky="e")
        self.run_button = self._button(actions, "Check starten", self._run_check, primary=True)
        self.run_button.grid(row=0, column=0, padx=(0, 8))
        self._button(actions, "Speichern", self._save_env).grid(row=0, column=1)

        left = tk.Frame(root, bg=BG)
        right = tk.Frame(root, bg=BG)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        right.grid(row=1, column=1, sticky="nsew")
        root.columnconfigure(0, weight=1, minsize=360)
        root.columnconfigure(1, weight=2, minsize=500)
        root.rowconfigure(1, weight=1)

        self._build_settings(left)
        self._build_status(right)

    def _build_settings(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=CARD, padx=14, pady=14, highlightthickness=1)
        card.configure(highlightbackground="#d6dbe1", highlightcolor="#d6dbe1")
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Einstellungen", bg=CARD, fg=TEXT, font=("Helvetica", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        self._entry(card, "IB Host", "ib_host")
        self._entry(card, "IB Port", "ib_port")
        self._entry(card, "Client ID", "ib_client_id")
        self._entry(card, "Account ID", "account_id")
        self._check(card, "Dry Run", "dry_run")
        self._check(card, "Live Trading", "live_trading")
        self._check(card, "Verzoegerte Marktdaten", "use_delayed_market_data")

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=12)

        self._entry(card, "Kontrakte", "contracts")
        self._entry(card, "Max. Trades pro Tag", "max_daily_trades")
        self._entry(card, "Max. VIX", "max_vix")
        self._entry(card, "Max. Overnight Gap", "max_overnight_gap_pct")
        self._entry(card, "Min. Short-Abstand %", "min_otm_distance_pct")
        self._entry(card, "Max. Short-Abstand %", "max_otm_distance_pct")
        self._entry(card, "Put-Fluegel Punkte", "put_spread_width")
        self._entry(card, "Call-Fluegel Punkte", "call_spread_width")
        self._entry(card, "Take Profit % Praemie", "take_profit_pct")
        self._entry(card, "Stop Loss % Praemie", "stop_loss_pct")

    def _build_status(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=CARD, padx=14, pady=14, highlightthickness=1)
        card.configure(highlightbackground="#d6dbe1", highlightcolor="#d6dbe1")
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Status", bg=CARD, fg=TEXT, font=("Helvetica", 12, "bold")).pack(anchor="w")

        grid = tk.Frame(card, bg=CARD)
        grid.pack(fill="x", pady=12)
        self.status_vars = {
            "price": tk.StringVar(value="SPX: -"),
            "vix": tk.StringVar(value="VIX: -"),
            "gap": tk.StringVar(value="Gap: -"),
            "decision": tk.StringVar(value="Entscheidung: -"),
        }
        for idx, key in enumerate(("price", "vix", "gap", "decision")):
            label = tk.Label(
                grid,
                textvariable=self.status_vars[key],
                bg=CARD,
                fg=TEXT,
                font=("Helvetica", 11, "bold"),
                anchor="w",
            )
            label.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=8, pady=8)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        tk.Label(card, text="Log", bg=CARD, fg=TEXT, font=("Helvetica", 12, "bold")).pack(
            anchor="w", pady=(8, 6)
        )
        self.log = tk.Text(card, height=24, wrap="word", bg=DARK, fg=LOG_TEXT)
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

    def _entry(self, parent: tk.Frame, label: str, key: str) -> None:
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=CARD, fg=MUTED, width=24, anchor="w").pack(side="left")
        var = tk.StringVar()
        self.fields[key] = var
        tk.Entry(
            row,
            textvariable=var,
            bg="#ffffff",
            fg=TEXT,
            relief="solid",
            borderwidth=1,
            insertbackground=TEXT,
            font=("Helvetica", 13),
        ).pack(side="right", fill="x", expand=True, ipady=5)

    def _check(self, parent: tk.Frame, label: str, key: str) -> None:
        var = tk.BooleanVar()
        self.checks[key] = var
        tk.Checkbutton(
            parent,
            text=label,
            variable=var,
            bg=CARD,
            fg=TEXT,
            activebackground=CARD,
            anchor="w",
        ).pack(anchor="w", pady=3)

    def _button(
        self,
        parent: tk.Frame,
        text: str,
        command: Callable[[], None],
        primary: bool = False,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=BLUE if primary else "#ffffff",
            fg="#ffffff" if primary else TEXT,
            activebackground="#0f63d8" if primary else "#eef2f6",
            activeforeground="#ffffff" if primary else TEXT,
            relief="solid",
            borderwidth=1,
            padx=14,
            pady=8,
            font=("Helvetica", 12, "bold" if primary else "normal"),
            cursor="hand2",
        )

    def _load_fields(self) -> None:
        for key, var in self.fields.items():
            value = getattr(self.config_model, key)
            var.set("" if value is None else str(value))
        for key, var in self.checks.items():
            var.set(bool(getattr(self.config_model, key)))

    def _config_from_fields(self) -> BotConfig:
        current = self.config_model
        values = {
            "ib_host": self.fields["ib_host"].get().strip(),
            "ib_port": int(self.fields["ib_port"].get()),
            "ib_client_id": int(self.fields["ib_client_id"].get()),
            "account_id": self.fields["account_id"].get().strip() or None,
            "dry_run": self.checks["dry_run"].get(),
            "live_trading": self.checks["live_trading"].get(),
            "use_delayed_market_data": self.checks["use_delayed_market_data"].get(),
            "contracts": int(self.fields["contracts"].get()),
            "max_daily_trades": int(self.fields["max_daily_trades"].get()),
            "max_vix": float(self.fields["max_vix"].get()),
            "max_overnight_gap_pct": float(self.fields["max_overnight_gap_pct"].get()),
            "min_otm_distance_pct": float(self.fields["min_otm_distance_pct"].get()),
            "max_otm_distance_pct": float(self.fields["max_otm_distance_pct"].get()),
            "put_spread_width": float(self.fields["put_spread_width"].get()),
            "call_spread_width": float(self.fields["call_spread_width"].get()),
            "take_profit_pct": float(self.fields["take_profit_pct"].get()),
            "stop_loss_pct": float(self.fields["stop_loss_pct"].get()),
        }
        return replace(current, **values)

    def _run_check(self) -> None:
        try:
            config = self._config_from_fields()
        except ValueError as exc:
            messagebox.showerror("Eingabe pruefen", f"Eine Einstellung ist ungueltig: {exc}")
            return

        self.config_model = config
        self.run_button.configure(state="disabled")
        self._append_log("Check gestartet...\n")
        worker = threading.Thread(target=self._run_worker, args=(config,), daemon=True)
        worker.start()

    def _run_worker(self, config: BotConfig) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = run_once(config)
            self.messages.put(("result", result))
        except IbkrConnectionError as exc:
            self.messages.put(("error", str(exc)))
        except Exception as exc:
            self.messages.put(("error", f"{type(exc).__name__}: {exc}"))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
            self.messages.put(("done", None))

    def _poll_messages(self) -> None:
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "result":
                self._show_result(payload)  # type: ignore[arg-type]
            elif kind == "error":
                self._append_log(f"Fehler: {payload}\n")
            elif kind == "log":
                self._append_log(f"{payload}\n")
            elif kind == "done":
                self.run_button.configure(state="normal")
        self.after(100, self._poll_messages)

    def _show_result(self, result: BotRunResult) -> None:
        snapshot = result.snapshot
        signal = result.signal
        decision = result.decision

        self.status_vars["price"].set(f"SPX: {self._money(snapshot.underlying_price)}")
        self.status_vars["vix"].set(f"VIX: {self._money(snapshot.vix_price)}")
        gap = "-" if snapshot.overnight_gap_pct is None else f"{snapshot.overnight_gap_pct:.2%}"
        self.status_vars["gap"].set(f"Gap: {gap}")
        self.status_vars["decision"].set(
            "Entscheidung: freigegeben" if decision.approved else "Entscheidung: blockiert"
        )

        self._append_log(
            "Snapshot: "
            f"SPX {self._money(snapshot.underlying_price)}, "
            f"VIX {self._money(snapshot.vix_price)}, "
            f"Gap {gap}, offene SPX-Positionen {snapshot.open_positions}\n"
        )
        self._append_log(f"Signal: {signal.action.value} - {signal.reason}\n")
        self._append_log(f"Risiko: {decision.reason}\n")
        if signal.legs:
            self._append_log(f"Legs: {signal.legs}\n")

    def _save_env(self) -> None:
        try:
            config = self._config_from_fields()
        except ValueError as exc:
            messagebox.showerror("Eingabe pruefen", f"Eine Einstellung ist ungueltig: {exc}")
            return

        self.config_model = config
        ENV_PATH.write_text(self._env_text(config), encoding="utf-8")
        self._append_log(".env gespeichert.\n")

    def _env_text(self, config: BotConfig) -> str:
        lines = [
            "# IBKR connection",
            f"IB_HOST={config.ib_host}",
            f"IB_PORT={config.ib_port}",
            f"IB_CLIENT_ID={config.ib_client_id}",
            f"USE_DELAYED_MARKET_DATA={self._bool_text(config.use_delayed_market_data)}",
            "",
            "# Trading controls",
            f"DRY_RUN={self._bool_text(config.dry_run)}",
            f"LIVE_TRADING={self._bool_text(config.live_trading)}",
            "",
            "# Account/risk controls",
            f"ACCOUNT_ID={config.account_id or ''}",
            f"ACCOUNT_SIZE_USD={config.account_size_usd}",
            f"MAX_RISK_PER_TRADE_USD={config.max_risk_per_trade_usd}",
            f"MAX_DAILY_LOSS_USD={config.max_daily_loss_usd}",
            f"MAX_OPEN_POSITIONS={config.max_open_positions}",
            "",
            "# SPX option settings",
            f"UNDERLYING={config.underlying}",
            f"EXCHANGE={config.exchange}",
            f"CURRENCY={config.currency}",
            "",
            "# Strategy",
            f"STRATEGY={config.strategy}",
            f"TARGET_DTE={config.target_dte}",
            f"SHORT_DELTA={config.short_delta}",
            f"SPREAD_WIDTH={config.spread_width}",
            f"PUT_SPREAD_WIDTH={config.put_spread_width}",
            f"CALL_SPREAD_WIDTH={config.call_spread_width}",
            f"TAKE_PROFIT_PCT={config.take_profit_pct}",
            f"STOP_LOSS_MULTIPLE={config.stop_loss_multiple}",
            f"STOP_LOSS_PCT={config.stop_loss_pct}",
            "",
            "# 0DTE SPX Iron Condor rules",
            f"CONTRACTS={config.contracts}",
            f"MAX_DAILY_TRADES={config.max_daily_trades}",
            f"MIN_OTM_DISTANCE_PCT={config.min_otm_distance_pct}",
            f"MAX_OTM_DISTANCE_PCT={config.max_otm_distance_pct}",
            f"MAX_VIX={config.max_vix}",
            f"MAX_OVERNIGHT_GAP_PCT={config.max_overnight_gap_pct}",
            f"ENTRY_AFTER_MINUTES={config.entry_after_minutes}",
            f"FORCE_CLOSE_BEFORE_MINUTES={config.force_close_before_minutes}",
            f"MARKET_TIMEZONE={config.market_timezone}",
            "",
        ]
        return "\n".join(lines)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _install_log_handler(self) -> None:
        self.log_handler = GuiLogHandler(self.messages)
        self.log_handler.setLevel(logging.INFO)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.INFO)

        logging.getLogger("ib_insync.wrapper").setLevel(logging.INFO)
        logging.getLogger("ib_insync.client").setLevel(logging.INFO)

    def _on_close(self) -> None:
        if hasattr(self, "log_handler"):
            logging.getLogger().removeHandler(self.log_handler)
        self.destroy()

    @staticmethod
    def _money(value: Optional[float]) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}"

    @staticmethod
    def _bool_text(value: bool) -> str:
        return "true" if value else "false"


def main() -> None:
    os.chdir(Path(__file__).resolve().parents[1])
    app = BotGui()
    app.mainloop()


if __name__ == "__main__":
    main()
