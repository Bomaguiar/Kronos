# Kronos Financial Forecasting

Experimental, read-only BTC, ETH and SOL forecasting using the [Kronos](https://github.com/shiyu-coder/Kronos) foundation model.

## Capabilities
- Public Binance OHLCV data for BTCUSDT, ETHUSDT and SOLUSDT
- 1 hour and 4 hour candles
- Pretrained NeoQuasar/Kronos-small with NeoQuasar/Kronos-Tokenizer-base
- Saves prediction results as JSON to the ignored `outputs/` folder
- No exchange API keys, order placement or automated trading

## Set up

Requires Python 3.10+, network access and enough RAM for the model. Optional GPU.

```bash
git clone https://github.com/Bomaguiar/Kronos.git
cd Kronos
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/shiyu-coder/Kronos.git upstream/Kronos
pip install -r upstream/Kronos/requirements.txt
python -m unittest discover -s tests
python forecast.py --symbol BTCUSDT --interval 1h --lookback 400 --pred-len 24
python forecast.py --symbol ETHUSDT --interval 4h --lookback 400 --pred-len 6
python forecast.py --symbol SOLUSDT --interval 1h --lookback 400 --pred-len 24
```

Windows PowerShell activation: `.venv\Scripts\Activate.ps1`.

## Next steps

Run rolling walk-forward backtests with no lookahead and compare against a persistence baseline. Measure MAE, RMSE and directional accuracy, accounting for fees and slippage before any real-world financial use.

Model outputs are speculative research results, not investment advice. API availability varies by region. Upstream project licensing and dependencies should be independently reviewed before deployment.
