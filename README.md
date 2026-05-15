# SPX Options Bot for IBKR

Ein sicherer Startpunkt fuer einen Bot, der SPX-Indexoptionen ueber Interactive Brokers handeln kann.

Der Bot ist absichtlich defensiv gebaut:

- Standard ist `DRY_RUN=true`, also keine echten Orders.
- Live-Trading braucht zusaetzlich `LIVE_TRADING=true`.
- Risikoregeln pruefen Positionsanzahl und Dry-Run/Live-Status.
- Die Strategie ist modular und startet als No-Op, bis du eine konkrete Regel aktivierst.

## Voraussetzungen

1. Interactive Brokers TWS oder IB Gateway starten.
2. API aktivieren:
   - TWS: `Settings > API > Settings > Enable ActiveX and Socket Clients`
   - Paper-Trading empfohlen.
3. Python 3.11+ verwenden.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Windows Installation

Auf dem Windows-Laptop:

1. Python 3 installieren: https://www.python.org/downloads/windows/
2. Beim Installer `Add python.exe to PATH` aktivieren.
3. Projektordner auf den Windows-Laptop kopieren.
4. `setup_windows.bat` per Doppelklick starten.
5. Danach `start_web_gui_windows.bat` per Doppelklick starten.

## Windows als normale App ohne Python beim Nutzer

Wenn der eigentliche Nutzer kein Python installieren soll, gibt es zwei Phasen:

1. Einmalig auf einem Windows-Rechner bauen.
2. Danach nur noch den fertigen `dist`-Ordner oder einen Installer weitergeben.

Build auf Windows:

```text
setup_windows.bat
build_windows_exe.bat
```

Danach liegt die App hier:

```text
dist\SPXBot.exe
```

Der Nutzer braucht dann kein Python mehr. Er startet einfach `SPXBot.exe`. Die App öffnet lokal die Browser-Oberfläche unter:

```text
http://127.0.0.1:8765
```

Wichtig: Die `.env` muss neben `SPXBot.exe` im `dist`-Ordner liegen, damit Host, Port, Account und Risikowerte gespeichert werden koennen.

Fuer einen richtigen Windows-Installer empfehle ich danach Inno Setup oder NSIS. Der Installer sollte mindestens diese Dateien installieren:

- `SPXBot.exe`
- `.env`

und optional eine Desktop-Verknuepfung fuer `SPXBot.exe` anlegen.

## Alternative ohne signiertes EXE

Wenn Windows Smart App Control die unsignierte `SPXBot.exe` blockiert und du kein Code-Signing-Zertifikat hast, nutze die portable Variante:

```text
build_windows_portable.bat
```

Das erstellt:

```text
dist_portable\SPXBot
```

Der Nutzer startet dann:

```text
Start SPXBot.bat
```

Dabei wird keine eigene unsignierte `.exe` gestartet. Stattdessen nutzt die App die offizielle Python-Runtime von python.org im Ordner.

Wenn TWS oder IB Gateway auf demselben Windows-Laptop laeuft:

```env
IB_HOST=127.0.0.1
IB_PORT=7497
```

Wenn du TWS Paper nutzt, ist `7497` meistens korrekt. Bei IB Gateway Paper ist es meistens `4002`.

## Start

```bash
source .venv/bin/activate
python -m spx_options_bot
```

## GUI starten

```bash
source .venv/bin/activate
python -m spx_options_bot.gui
```

## Browser-GUI starten

Empfohlen auf macOS, wenn Tkinter nicht sauber rendert:

```bash
source .venv/bin/activate
python -m spx_options_bot.web_gui
```

Dann im Browser öffnen:

```text
http://127.0.0.1:8765
```

Auf Windows kannst du stattdessen auch einfach starten:

```text
start_web_gui_windows.bat
```

Die GUI kann:

- IBKR-Verbindungsdaten bearbeiten
- Dry-Run, Live-Trading und verzögerte Marktdaten setzen
- Risiko- und Strategieparameter anpassen
- `.env` speichern
- einen einzelnen Checklauf starten und das Ergebnis kompakt anzeigen

Wenn du `Connection refused` siehst, ist TWS oder IB Gateway nicht auf dem eingestellten Port erreichbar.

Wenn du `Connection reset by peer` oder einen Timeout nach kurzem `Connected` siehst, erreicht der Bot den Laptop, aber TWS akzeptiert die API-Session nicht vollstaendig.

Checkliste:

- TWS oder IB Gateway ist gestartet und eingeloggt
- Paper- oder Live-Modus passt zu deinem Port
- API ist aktiviert: `Enable ActiveX and Socket Clients`
- `Read-Only API` ist fuer Dry-Run/Paper okay
- Bei Remote-Zugriff: `Allow connections from localhost only` deaktivieren
- Die IP des Bot-Macs als `Trusted IP` eintragen
- Auf dem TWS-Laptop eine eventuell sichtbare API-Verbindungsabfrage bestaetigen
- Firewall auf dem TWS-Laptop fuer den API-Port erlauben
- `127.0.0.1` ist nur korrekt, wenn Bot und TWS auf demselben Rechner laufen
- `.env` enthaelt den passenden `IB_PORT`

## Wichtige Einstellungen

Siehe `.env.example`.

Fuer IBKR Paper-Trading ist haeufig:

- TWS Paper: Port `7497`
- TWS Live: Port `7496`
- IB Gateway Paper: Port `4002`
- IB Gateway Live: Port `4001`

## Aktive Strategie

`STRATEGY=spx_0dte_iron_condor`

Regeln:

- Underlying: SPX
- Laufzeit: 0DTE
- Struktur: Iron Condor
- Short-Strikes: ca. 1,7% bis 2,0% vom aktuellen SPX-Kurs entfernt
- Eingabe der Short-Strike-Abstaende erfolgt als ganze Prozentzahl, z. B. `1.7` fuer 1,7%
- Put- und Call-Fluegel koennen getrennt in Punkten eingestellt werden
- VIX muss unter `MAX_VIX=25` liegen
- Overnight-Gap muss kleiner als `MAX_OVERNIGHT_GAP_PCT=0.005` sein
- Einstieg fruehestens 60 Minuten nach US-Handelsstart
- Kein Einstieg spaeter als 60 Minuten vor US-Handelsschluss
- Take Profit in Prozent der erhaltenen Praemie, z. B. `TAKE_PROFIT_PCT=70`
- Stop Loss in Prozent der erhaltenen Praemie, z. B. `STOP_LOSS_PCT=300`
- Skalierung ueber `CONTRACTS` und `MAX_DAILY_TRADES`

Wichtige Strategieparameter:

```env
MIN_OTM_DISTANCE_PCT=1.7
MAX_OTM_DISTANCE_PCT=2.0
PUT_SPREAD_WIDTH=5
CALL_SPREAD_WIDTH=5
TAKE_PROFIT_PCT=70
STOP_LOSS_PCT=300
```

Die Browser-GUI zeigt zusaetzlich optische Statusflaechen fuer:

- TWS Verbindung
- Bot wartet auf Einstieg
- Trade ausgefuehrt
- Ausstiegsorders angehaengt

Da Order-Routing noch nicht implementiert ist, bleiben `Trade ausgefuehrt` und `Ausstiegsorders angehaengt` aktuell bewusst auf `nein`.

Der Bot erzeugt aktuell ein Signal und prueft Risiko. Echte Order-Platzierung und Positionsmanagement sollten erst nach einem Paper-Testlauf aktiviert werden.

## Empfohlene Umgebung

Start:

- Mac lokal laufen lassen
- IB Gateway oder TWS Paper-Trading
- `DRY_RUN=true`
- Log-Ausgaben beobachten

Nach stabiler Paper-Phase:

- kleiner VPS oder dauerhaft laufender Mini-PC
- IB Gateway statt TWS
- separater IBKR Paper-/Live-Account
- Prozessmanager wie `systemd`, `pm2` oder `launchd`
- taeglicher Health-Check und Log-Archiv

## Naechster Schritt

Als naechstes sollte Order-Routing fuer den Iron Condor gebaut werden:

- Combo-Order an IBKR
- Limit-Preis anhand der Mid-Preise
- Bracket/OCA-Logik fuer Take Profit und Stop Loss
- Zwangsschliessung 60 Minuten vor Handelsende
- Persistenz, damit `MAX_DAILY_TRADES` auch nach Neustart korrekt bleibt
