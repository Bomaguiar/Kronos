# Run Kronos securely on your own computer

The public dashboard is `index.html`, hosted using GitHub Pages. The machine learning model runs only on your PC. There is **no web server on your PC** and no incoming port forwarding.

## Prerequisites

Install Python 3.10+, Git and the official GitHub CLI (gh). Run `gh auth login` and choose GitHub.com and HTTPS. Do not paste GitHub tokens or passwords into scripts or chat.

> Review the official Kronos repository, its license, model weights and third party packages before running them. Use an isolated Python environment and keep your system patched.

## Local installation

### macOS / Linux
```bash
git clone https://github.com/Bomaguiar/Kronos.git
cd Kronos
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
git clone https://github.com/shiyu-coder/Kronos.git upstream/Kronos
pip install -r upstream/Kronos/requirements.txt
python -m unittest discover -s tests
python forecast.py --symbol BTCUSDT --interval 1h
python publish_forecast.py --symbol BTCUSDT --interval 1h
```

### Windows PowerShell
```powershell
git clone https://github.com/Bomaguiar/Kronos.git
cd Kronos
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
git clone https://github.com/shiyu-coder/Kronos.git upstream/Kronos
.\.venv\Scripts\python.exe -m pip install -r upstream/Kronos/requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe forecast.py --symbol BTCUSDT --interval 1h
.\.venv\Scripts\python.exe publish_forecast.py --symbol BTCUSDT --interval 1h
```

If model dependencies require a different supported Python/PyTorch version, follow the upstream Kronos compatibility instructions.

## Publish a verified forecast

First inspect the generated `data/BTCUSDT_1h.json` file. It contains only symbol, interval, historical close, model label and OHLC predictions. Then execute:

```bash
python publish_forecast.py --symbol BTCUSDT --interval 1h --push
```

For ETH or SOL change `--symbol`. For four hour candles use `--interval 4h`. This action is **opt in**. It pushes a new commit to your public repository; the data becomes public. If a manual process is preferable, upload only the generated JSON via GitHub's website.

You can schedule the **same commands** using Windows Task Scheduler or macOS launchd after verifying that manual runs work. Avoid scheduled publishing until Git authentication and code have been tested. Never store login credentials in your code.

## Enable your website

Open repository **Settings → Pages → Build and deployment → Deploy from a branch → main / (root) → Save**.

Once GitHub Pages publishes it, the URL will be:
https://bomaguiar.github.io/Kronos/

Without output files the dashboard deliberately shows "Awaiting model data" rather than simulated forecasts.

## Security model

* GitHub Pages only reads `data/*.json` files and cannot access localhost.
* Python uses only a public market data endpoint and model downloads. No wallet keys or trading permissions are needed.
* The publisher checks the remote repository URL and limits exported JSON to a fixed schema.
* The repository is public. Never commit `.env`, `.venv`, API keys, private trades, account details or PC paths.
* This is an early experimental integration. Perform isolated validation and backtesting before treating predictions as useful financial signals.
