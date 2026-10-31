# Kronos — Market intelligence

A read-only cryptocurrency research terminal powered by real local inference using the official [Kronos Small model](https://huggingface.co/NeoQuasar/Kronos-small).

**Dashboard:** https://bomaguiar.github.io/Kronos/

- BTC/USDT, ETH/USDT and SOL/USDT; 1H and 4H candles; 24-hour forecast horizon.
- Public Binance data with Binance-data and OKX fallback; explicit source labels.
- Interactive historical candles, forecast mean, actual sampled scenario paths and live quotes.
- Chronological walk-forward backtests with MAE, RMSE, directional accuracy and a persistence baseline.
- Conditional paper signals, volatility-based stops, two profit targets, setup expiry and local-only risk sizing; see [SIGNALS.md](SIGNALS.md).
- Pinned model/tokenizer revisions, inspected source hashes, strict JSON publication, read-only CI.
- Local trusted compute; static GitHub Pages frontend; no inbound server, keys, wallets or orders.

Follow [LOCAL_SETUP.md](LOCAL_SETUP.md) for installation, inference, publication, deployment and methodology. [VERIFICATION.md](VERIFICATION.md) records the executed verification and real forecast results.

Forecasts are experimental, can be wrong and are not financial advice. The dashboard explicitly shows when the unchanged-price baseline outperforms the model. Sample paths are not confidence intervals. Published forecasts are snapshots and must be regenerated; only public market quotes refresh automatically.
