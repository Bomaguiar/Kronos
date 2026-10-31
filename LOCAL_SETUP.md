# Local Kronos compute and static GitHub Pages

The model runs on a trusted PC, with outbound HTTPS only. GitHub Pages serves static assets and sanitized market/forecast JSON. No local web server, exchange credentials, wallets or orders are used.

## Reproduce the tested Windows setup

Python 3.11 is recommended (tested: 3.11.15). Install Git and authenticate GitHub CLI with `gh auth login` using your normal credential manager. Never paste credentials into this repository.

```powershell
git clone --branch codex/kronos-production https://github.com/Bomaguiar/Kronos.git
cd Kronos
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
git clone https://github.com/shiyu-coder/Kronos.git upstream/Kronos
git -C upstream/Kronos checkout 67b630e67f6a18c9e9be918d9b4337c960db1e9a
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe forecast.py --all --lookback 256 --samples 3 --folds 3
.\.venv\Scripts\python.exe publish_forecast.py --all
.\.venv\Scripts\python.exe -m tests.check_public
```

For CPU replace the torch index URL with `https://download.pytorch.org/whl/cpu` and use `--device cpu`. Linux/macOS use `python3.11 -m venv .venv` and `.venv/bin/python`; choose a PyTorch build compatible with your hardware. CUDA availability is detected automatically. Check RAM, free disk and `nvidia-smi` first: the tested CUDA wheel alone downloads about 3.5 GB, and installation requires additional space.

Only the inspected upstream `model/*.py` files are imported. Their SHA256 digests are checked against `upstream-lock.json` before execution. `KRONOS_UPSTREAM` may point to an existing inspected checkout. Do not disable Git ownership/security checks.

The first model load downloads pinned `config.json` and `model.safetensors` from the official NeoQuasar repositories to ignored `.cache/huggingface/`. No remote model Python is trusted or executed. Full installed package versions are recorded in `requirements-lock.txt`; the platform-specific torch build in that snapshot requires its official CUDA index.

## Run and publish

```powershell
.\.venv\Scripts\python.exe forecast.py --symbol BTCUSDT --interval 1h
.\.venv\Scripts\python.exe forecast.py --symbol ETHUSDT --interval 4h
.\.venv\Scripts\python.exe forecast.py --all --provider okx
.\.venv\Scripts\python.exe publish_forecast.py --all
```

The horizon is always 24 hours: 24 one-hour candles or 6 four-hour candles. A manually supplied `--pred-len` must match that horizon. Copy `.env.example` to ignored `.env` for optional interval, lookback, sample count, provider and device defaults; command-line arguments take precedence. The old fixed `PRED_LEN` environment setting is deliberately replaced with an interval-derived horizon.

Providers are Binance, Binance's public-data mirror, and OKX spot USDT pairs, in that order when `--provider auto` is used. Use `--provider binance`, `binance-data` or `okx` to select one explicitly. A run uses one provider throughout its history and backtest. OKX quote turnover is used as model `amount`. Data must be finite, positive-price, nonnegative-volume, UTC-aligned, contiguous and fully closed. Missing candles are rejected, never interpolated.

Publication reconstructs a fixed public schema; extra fields never pass through. It checks timestamps, horizon, OHLC constraints, sample means, and recomputed evaluation metrics. Files are replaced atomically. Inference failures leave previous public data intact, and the dashboard labels stale/expired snapshots.

To push only prepared data:
```powershell
.\.venv\Scripts\python.exe publish_forecast.py --all --push
```
This requires `codex/kronos-production`, the exact intended remote, and an empty staging area. It never pushes main or uses force. Review through a pull request before merging.

## Deploy static assets

`python stage_site.py` builds an allowlisted `site/` with five static assets, six validated JSON files and `.nojekyll`. It rejects unexpected files. Deploy that output to the repository's `gh-pages` branch and configure GitHub Pages to use `gh-pages / (root)`. Do not upload the full working directory or virtual environment.

The initial deployment is an explicitly published static snapshot. Subsequent inference/data commits do not automatically update the deployed snapshot: rebuild `site/`, commit those files to `gh-pages` and push normally. No scheduled task was installed. Refresh the forecasts before their 24-hour horizon expires; quotes independently refresh every 30 seconds.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tests.check_public
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip install pip-audit
.\.venv\Scripts\python.exe -m pip_audit
node --check app.js
```

For browser QA install Playwright in a separate development environment and make its module available to Node. With Chrome installed, run `node tests/browser.cjs`. It routes a test HTTPS origin to local files without listening on a network port, tests six combinations at desktop/mobile widths, checks console errors, and saves ignored screenshots. Set `DASHBOARD_URL=https://bomaguiar.github.io/Kronos/` to exercise the actual deployed site.

CI uses read-only repository permissions, pinned action commits, and no model downloads or credentials. It checks unit tests, public JSON, basic secret scanning, JavaScript syntax, and the static publication bundle.

## Model and evaluation methodology

- Official source: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`.
- Kronos Small: `901c26c1332695a2a8f243eb2f37243a37bea320`.
- Tokenizer base: `0e0117387f39004a9016484a186a908917e22426`.
- Inputs: open, high, low, close, base volume, quote turnover; UTC timestamps; 256 completed candles by default.
- Sampling: temperature 1.0, top-p 0.9, top-k 0; three separate sample_count=1 calls. Live seeds 42,43,44; evaluation seeds 1000+100*fold+sample. GPU/platform differences may prevent bitwise reproducibility.
- Displayed prediction is the arithmetic mean of separately retained paths. Higher/lower terminal paths are observed model scenarios, not probabilities, quantiles or calibrated confidence bounds.
- The model decoder does not enforce candle geometry. We expand each sampled high/low to the extrema of its four raw predicted OHLC values. Open and close are unchanged; this policy is disclosed in every file and on the page.
- Three non-overlapping 24-hour historical holdouts by default. At every origin, only the preceding lookback candles enter inference and normalization. No future realized prices enter prediction.
- MAE and RMSE compare held-out closes to predicted closes. Directional accuracy compares signs of each target return relative to its own window origin (ties count as a third direction). The persistence baseline repeats the origin close.
- These are retrospective evaluations generated now, not archived forecasts claimed to have been issued in the past. Model pretraining overlap is unknown. Three windows are too few to establish predictive skill.
- `generated_at` records the start of the calculation after data retrieval, `completed_at` its completion, and `history_as_of` the last completed candle's open time. All timestamps are UTC. Forecast timestamps also label candle opens; the final close occurs one interval after its timestamp.
