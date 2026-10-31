# Executed verification â€” 31 October 2026

## Environment and models

- Python 3.11.15 in an isolated local virtual environment.
- PyTorch 2.8.0+cu128; CUDA available; NVIDIA GeForce RTX 3070 Ti (8 GB VRAM).
- Approximately 32 GB system RAM; disk capacity checked before installation.
- Official upstream source revision: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`.
- Official Kronos Small revision: `901c26c1332695a2a8f243eb2f37243a37bea320`.
- Official Tokenizer base revision: `0e0117387f39004a9016484a186a908917e22426`.
- Both pretrained safetensors loaded successfully. Real GPU inference completed for all six selections.
- Three samples, 256 historical input candles, three chronological 24h holdouts per selection.
- Main run used Binance public spot candles. An additional real SOL 4H inference using OKX candles also succeeded.
- Exact installed package snapshot: [requirements-lock.txt](requirements-lock.txt).

## Real published results

Prices/errors below are USDT. These are model predictions, not future realized prices. All completion timestamps are UTC on 2026-10-31.

| Asset | Interval | Completed | Historical close | Predicted final close | MAE | RMSE | Direction accuracy | Baseline MAE |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BTC | 1H | 01:49:09 | 77,568.81 | 79,776.27 | 1,273.16 | 1,554.90 | 30.56% | 674.00 |
| BTC | 4H | 01:49:12 | 77,368.77 | 77,913.69 | 1,168.22 | 1,348.50 | 44.44% | 767.56 |
| ETH | 1H | 01:49:19 | 2,250.06 | 2,280.13 | 31.33 | 39.28 | 77.78% | 23.99 |
| ETH | 4H | 01:49:21 | 2,245.54 | 2,261.26 | 27.58 | 32.68 | 33.33% | 24.75 |
| SOL | 1H | 01:49:28 | 96.80 | 98.36 | 1.85 | 2.44 | 68.06% | 1.49 |
| SOL | 4H | 01:49:30 | 96.38 | 97.68 | 1.57 | 1.85 | 55.56% | 1.66 |

The unchanged-price baseline beat the model's MAE in five of six evaluations. This short retrospective sample does not demonstrate reliable predictive skill. Directional accuracy is an observed backtest statistic, not forecast confidence.

The 1H forecasts begin at candle open 2026-10-31 01:00 UTC and end at candle close 2026-11-01 01:00 UTC. The 4H forecasts cover 2026-10-31 00:00 through 2026-11-01 00:00 UTC. Their first candle is already underway when inference completes; every input candle is fully closed.

## Executed checks

- 16 Python unit tests passed, including timestamp gaps/duplicates, nonfinite input, invalid OHLC, horizon validation, sanitization, metric verification, and chronology/no-lookahead checks.
- Six real output payloads passed the strict public JSON schema and sample-mean checks.
- Headless Chrome: all 12 combinations of asset/timeframe and desktop (1440px)/mobile (390px) passed. No JavaScript console errors. Live Binance quotes retrieved successfully. Scenario toggle, zoom reset, evaluation table and horizontal-overflow checks passed.
- Desktop and mobile screenshots inspected visually.
- JavaScript syntax check passed.
- `pip check`: no broken requirements.
- `pip-audit`: no known vulnerabilities in the final installed environment. Initial pip/setuptools findings were resolved by upgrading those isolated build tools.
- Upstream source inspected before import and locked with normalized-source SHA256 hashes. No model remote-code execution enabled.
- Only GET requests go to public exchange endpoints. No exchange authentication, orders or wallets.
- Static staging emits exactly 12 allowlisted files; excludes Python, local config, caches, model weights and logs.
- Basic secret/private-path scan passed for all 30 tracked files; all six published JSON documents passed validation.
- No inbound server, port forwarding, force push, or main merge.

## Verified deployment

- Live dashboard: https://bomaguiar.github.io/Kronos/ (HTTP 200, HTTPS enforced).
- Static deployment branch: `gh-pages`; GitHub Pages build and deployment succeeded.
- Review branch: `codex/kronos-production`; pull request: https://github.com/Bomaguiar/Kronos/pull/1.
- GitHub Actions validation passed on both the branch push and pull request.
- Repeated all 12 desktop/mobile browser combinations against the live deployment at approximately 02:01 UTC. All passed with zero console errors and working live Binance quotes.
- Main remains at `5963362b58b40cab2144e1eefa3f1f63c5eaff21`; no merge was performed.

## Operational limits

Forecast files are snapshots. Local inference and explicit publication must be repeated to refresh them. No scheduler was installed. Live quotes refresh independently every 30 seconds. The dashboard labels stale and expired forecast snapshots.

Basic secret pattern scanning and dependency auditing are useful checks, not a comprehensive security audit. The public repository should continue to receive dependency updates and code review.
