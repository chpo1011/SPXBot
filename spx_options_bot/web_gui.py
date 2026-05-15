from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
import threading
import webbrowser
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

from .app import run_once
from .config import BotConfig


HOST = "127.0.0.1"
PORT = 8765


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


ENV_PATH = app_dir() / ".env"


HTML = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SPX 0DTE Iron Condor Bot</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --panel: #ffffff;
      --text: #111827;
      --muted: #5b6472;
      --border: #d8dee6;
      --blue: #1668e8;
      --green: #0f8f5f;
      --red: #c93636;
      --dark: #101722;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
    }
    header {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 22px;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
    }
    h1 {
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }
    main {
      display: grid;
      grid-template-columns: minmax(360px, 440px) minmax(520px, 1fr);
      gap: 16px;
      padding: 16px;
      min-height: calc(100vh - 64px);
    }
    section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 15px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 5px;
    }
    input {
      width: 100%;
      height: 36px;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0 10px;
      font-size: 14px;
      background: #fff;
      color: var(--text);
    }
    .checks {
      display: grid;
      gap: 8px;
      margin: 12px 0 16px;
    }
    .check {
      display: flex;
      align-items: center;
      gap: 9px;
      color: var(--text);
    }
    .check input {
      width: 18px;
      height: 18px;
    }
    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    button {
      height: 38px;
      border: 1px solid var(--border);
      border-radius: 7px;
      background: #fff;
      color: var(--text);
      padding: 0 14px;
      font-size: 14px;
      cursor: pointer;
    }
    button.primary {
      background: var(--blue);
      color: #fff;
      border-color: var(--blue);
      font-weight: 700;
    }
    button:disabled {
      opacity: 0.55;
      cursor: wait;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .metric {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      min-height: 72px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }
    .metric strong {
      font-size: 20px;
      letter-spacing: 0;
    }
    .signals {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .signal-tile {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 11px;
      min-height: 78px;
      background: #f8fafc;
    }
    .signal-tile span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 7px;
    }
    .signal-tile strong {
      font-size: 15px;
    }
    .signal-tile.on {
      border-color: #a8dbc4;
      background: #effaf5;
    }
    .signal-tile.off {
      border-color: #e6c2c2;
      background: #fff7f7;
    }
    .decision {
      margin-bottom: 14px;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #f8fafc;
    }
    .decision.good { border-color: #a8dbc4; background: #effaf5; }
    .decision.bad { border-color: #efb5b5; background: #fff4f4; }
    pre {
      height: calc(100vh - 286px);
      min-height: 360px;
      margin: 0;
      padding: 14px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      border-radius: 8px;
      background: var(--dark);
      color: #e8eef6;
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .wide { grid-column: 1 / -1; }
    @media (max-width: 920px) {
      main { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr 1fr; }
      .signals { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>SPX 0DTE Iron Condor Bot</h1>
    <div class="actions">
      <button class="primary" id="run">Check starten</button>
      <button id="save">Speichern</button>
    </div>
  </header>
  <main>
    <section>
      <h2>Einstellungen</h2>
      <div class="grid" id="fields"></div>
      <div class="checks">
        <label class="check"><input id="dry_run" type="checkbox"> Dry Run</label>
        <label class="check"><input id="live_trading" type="checkbox"> Live Trading</label>
        <label class="check"><input id="use_delayed_market_data" type="checkbox"> Verzögerte Marktdaten</label>
      </div>
    </section>
    <section>
      <h2>Status</h2>
      <div class="metrics">
        <div class="metric"><span>SPX</span><strong id="spx">-</strong></div>
        <div class="metric"><span>VIX</span><strong id="vix">-</strong></div>
        <div class="metric"><span>Overnight Gap</span><strong id="gap">-</strong></div>
        <div class="metric"><span>Offene SPX-Positionen</span><strong id="positions">-</strong></div>
      </div>
      <div class="decision" id="decision">Noch kein Checklauf.</div>
      <div class="signals">
        <div class="signal-tile off" id="tile_tws"><span>TWS Verbindung</span><strong>-</strong></div>
        <div class="signal-tile off" id="tile_waiting"><span>Wartet auf Einstieg</span><strong>-</strong></div>
        <div class="signal-tile off" id="tile_trade"><span>Trade ausgeführt</span><strong>-</strong></div>
        <div class="signal-tile off" id="tile_exits"><span>Ausstiegsorders angehängt</span><strong>-</strong></div>
      </div>
      <h2>Log</h2>
      <pre id="log"></pre>
    </section>
  </main>
  <script>
    const fieldDefs = [
      ["ib_host", "IB Host"], ["ib_port", "IB Port"], ["ib_client_id", "Client ID"],
      ["account_id", "Account ID"], ["contracts", "Kontrakte"], ["max_daily_trades", "Max. Trades pro Tag"],
      ["max_vix", "Max. VIX"], ["max_overnight_gap_pct", "Max. Overnight Gap"],
      ["min_otm_distance_pct", "Min. Short-Abstand %"], ["max_otm_distance_pct", "Max. Short-Abstand %"],
      ["put_spread_width", "Put-Flügel Punkte"], ["call_spread_width", "Call-Flügel Punkte"],
      ["take_profit_pct", "Take Profit % Prämie"], ["stop_loss_pct", "Stop Loss % Prämie"]
    ];
    const fields = document.getElementById("fields");
    for (const [key, label] of fieldDefs) {
      const wrap = document.createElement("div");
      wrap.innerHTML = `<label for="${key}">${label}</label><input id="${key}">`;
      fields.appendChild(wrap);
    }
    const log = document.getElementById("log");
    function append(message) {
      log.textContent += message + "\\n";
      log.scrollTop = log.scrollHeight;
    }
    function value(key) {
      const el = document.getElementById(key);
      return el.type === "checkbox" ? el.checked : el.value;
    }
    function payload() {
      const data = {};
      for (const [key] of fieldDefs) data[key] = value(key);
      for (const key of ["dry_run", "live_trading", "use_delayed_market_data"]) data[key] = value(key);
      return data;
    }
    function setDecision(approved, text) {
      const box = document.getElementById("decision");
      box.className = "decision " + (approved ? "good" : "bad");
      box.textContent = text;
    }
    function setTile(id, on, text) {
      const tile = document.getElementById(id);
      tile.className = "signal-tile " + (on ? "on" : "off");
      tile.querySelector("strong").textContent = text;
    }
    async function loadConfig() {
      const res = await fetch("/api/config");
      const data = await res.json();
      for (const [key] of fieldDefs) document.getElementById(key).value = data[key] ?? "";
      for (const key of ["dry_run", "live_trading", "use_delayed_market_data"]) {
        document.getElementById(key).checked = Boolean(data[key]);
      }
      append("Konfiguration geladen.");
    }
    async function saveConfig() {
      const res = await fetch("/api/config", {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload())
      });
      const data = await res.json();
      append(data.ok ? ".env gespeichert." : "Fehler: " + data.error);
    }
    async function runCheck() {
      const run = document.getElementById("run");
      run.disabled = true;
      append("Check gestartet...");
      try {
        const res = await fetch("/api/run", {
          method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload())
        });
        const data = await res.json();
        if (!data.ok) {
          append("Fehler: " + data.error);
          setDecision(false, data.error);
          return;
        }
        document.getElementById("spx").textContent = data.snapshot.underlying_price ?? "-";
        document.getElementById("vix").textContent = data.snapshot.vix_price ?? "-";
        document.getElementById("gap").textContent = data.snapshot.overnight_gap_pct ?? "-";
        document.getElementById("positions").textContent = data.snapshot.open_positions;
        setDecision(data.decision.approved, data.decision.reason);
        setTile("tile_tws", data.status.tws_connected, data.status.tws_connected ? "verbunden" : "getrennt");
        setTile("tile_waiting", data.status.waiting_for_entry, data.status.waiting_for_entry ? "aktiv" : "nein");
        setTile("tile_trade", data.status.trade_executed, data.status.trade_executed ? "ja" : "nein");
        setTile("tile_exits", data.status.exit_orders_attached, data.status.exit_orders_attached ? "ja" : "nein");
        append("Signal: " + data.signal.action + " - " + data.signal.reason);
        append("Risiko: " + data.decision.reason);
        if (data.logs) append(data.logs);
      } finally {
        run.disabled = false;
      }
    }
    document.getElementById("save").addEventListener("click", saveConfig);
    document.getElementById("run").addEventListener("click", runCheck);
    loadConfig();
  </script>
</body>
</html>
"""


def config_to_dict(config: BotConfig) -> dict[str, Any]:
    return {
        "ib_host": config.ib_host,
        "ib_port": config.ib_port,
        "ib_client_id": config.ib_client_id,
        "account_id": config.account_id or "",
        "dry_run": config.dry_run,
        "live_trading": config.live_trading,
        "use_delayed_market_data": config.use_delayed_market_data,
        "contracts": config.contracts,
        "max_daily_trades": config.max_daily_trades,
        "max_vix": config.max_vix,
        "max_overnight_gap_pct": config.max_overnight_gap_pct,
        "min_otm_distance_pct": config.min_otm_distance_pct,
        "max_otm_distance_pct": config.max_otm_distance_pct,
        "put_spread_width": config.put_spread_width,
        "call_spread_width": config.call_spread_width,
        "take_profit_pct": config.take_profit_pct,
        "stop_loss_pct": config.stop_loss_pct,
    }


def config_from_payload(payload: dict[str, Any]) -> BotConfig:
    current = BotConfig.from_env()
    return replace(
        current,
        ib_host=str(payload["ib_host"]).strip(),
        ib_port=int(payload["ib_port"]),
        ib_client_id=int(payload["ib_client_id"]),
        account_id=str(payload.get("account_id", "")).strip() or None,
        dry_run=bool(payload["dry_run"]),
        live_trading=bool(payload["live_trading"]),
        use_delayed_market_data=bool(payload["use_delayed_market_data"]),
        contracts=int(payload["contracts"]),
        max_daily_trades=int(payload["max_daily_trades"]),
        max_vix=float(payload["max_vix"]),
        max_overnight_gap_pct=float(payload["max_overnight_gap_pct"]),
        min_otm_distance_pct=float(payload["min_otm_distance_pct"]),
        max_otm_distance_pct=float(payload["max_otm_distance_pct"]),
        put_spread_width=float(payload["put_spread_width"]),
        call_spread_width=float(payload["call_spread_width"]),
        take_profit_pct=float(payload["take_profit_pct"]),
        stop_loss_pct=float(payload["stop_loss_pct"]),
    )


def env_text(config: BotConfig) -> str:
    def bool_text(value: bool) -> str:
        return "true" if value else "false"

    return "\n".join(
        [
            "# IBKR connection",
            f"IB_HOST={config.ib_host}",
            f"IB_PORT={config.ib_port}",
            f"IB_CLIENT_ID={config.ib_client_id}",
            f"USE_DELAYED_MARKET_DATA={bool_text(config.use_delayed_market_data)}",
            "",
            "# Trading controls",
            f"DRY_RUN={bool_text(config.dry_run)}",
            f"LIVE_TRADING={bool_text(config.live_trading)}",
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
    )


def run_to_dict(config: BotConfig) -> dict[str, Any]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        result = run_once(config)
        snapshot = result.snapshot
        return {
            "ok": True,
            "snapshot": {
                "underlying_price": fmt(snapshot.underlying_price),
                "vix_price": fmt(snapshot.vix_price),
                "overnight_gap_pct": None
                if snapshot.overnight_gap_pct is None
                else f"{snapshot.overnight_gap_pct:.2%}",
                "open_positions": snapshot.open_positions,
            },
            "signal": {
                "action": result.signal.action.value,
                "reason": result.signal.reason,
                "legs": [leg.__dict__ for leg in result.signal.legs],
            },
            "decision": {
                "approved": result.decision.approved,
                "reason": result.decision.reason,
            },
            "status": {
                "tws_connected": True,
                "waiting_for_entry": not result.decision.approved,
                "trade_executed": False,
                "exit_orders_attached": False,
            },
            "logs": log_stream.getvalue().strip(),
        }
    finally:
        root_logger.removeHandler(handler)
        loop.close()
        asyncio.set_event_loop(None)


def fmt(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return f"{value:.2f}"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self.send_text(HTML, "text/html")
        elif self.path == "/api/config":
            self.send_json(config_to_dict(BotConfig.from_env()))
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        try:
            payload = self.read_json()
            config = config_from_payload(payload)
            if self.path == "/api/config":
                ENV_PATH.write_text(env_text(config), encoding="utf-8")
                self.send_json({"ok": True})
            elif self.path == "/api/run":
                self.send_json(run_to_dict(config))
            else:
                self.send_error(404)
        except Exception as exc:
            self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, content_type: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    os.chdir(app_dir())
    server = None
    port = PORT
    for candidate in range(PORT, PORT + 20):
        try:
            server = ThreadingHTTPServer((HOST, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        raise RuntimeError(f"Could not start local server on ports {PORT}-{PORT + 19}.")

    url = f"http://{HOST}:{port}"
    print(f"Web-GUI laeuft auf {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
