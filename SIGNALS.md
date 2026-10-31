# Conditional spot signals — research v1

The Action & risk desk converts validated Kronos forecasts into a **PAPER LONG** or **NO TRADE** screen. It never places orders, connects accounts or recommends a short position. Bearish model bias means no new spot-long setup; it is not an instruction to sell an existing holding.

## Levels and sizing

Let C be the last completed close and A the simple mean of 14 true ranges. Each true range is max(high-low, abs(high-previous close), abs(low-previous close)).

- Entry zone: C ± 0.1A. Sizing and targets assume the upper boundary E, the least favorable long entry within the zone.
- Stop S: min(C-1.5A, lowest low of the last five candles - 0.1A). Nonpositive levels are rejected.
- Per-side cost assumption c: (fee percentage + slippage percentage) / 100. Defaults: 0.1% fee and 0.05% slippage per side. These are editable assumptions, not verified exchange fees.
- Budgeted loss per unit L = E(1+c) - S(1-c).
- Target at nR: T(n) = [E(1+c)+nL]/(1-c). TP1 is 1R; TP2 is 2R.
- Model endpoint net reward/risk = [model final close(1-c)-E(1+c)]/L.
- Hypothetical quantity = min(account equity × risk fraction / L, account equity × allocation cap / [E(1+c)]), rounded down to eight decimal places. Exchange minimum lots and tick sizes are not applied; this is not an executable order ticket.
- Default illustrative risk budget is 0.5%; default allocation cap is 10%. The calculator includes assumed costs in both the risk and cash caps and never uses leverage.
- Account balance is optional and never invented. It exists only in page memory, is not persisted, and is not sent in network requests.

TP1 closes half; TP2 closes the remainder. If both fill, the blended result is 1.5R under the cost assumptions, not 2R for the whole position. Stop the remaining units if S is reached; otherwise exit any remainder at the forecast horizon. No automatic trailing stop, break-even adjustment or averaging down is implied.

## Eligibility

Every check must pass:

1. Forecast is available and the setup has not expired. New-entry expiry is the earlier of one interval after generation and two intervals after the last historical candle open. This permits entries only during the first forecast candle.
2. At least ten non-overlapping 24-hour historical evaluation windows.
3. Model MAE is at least 10% below the unchanged-price baseline.
4. Historical directional accuracy is at least 55%.
5. Forecast endpoint is above the entry and its projected gain exceeds historical MAE.
6. At least three model samples, with all sampled endpoints covering entry/exit costs.
7. Model endpoint supports at least 2:1 net reward/risk.
8. A same-exchange quote fetched within 60 seconds is available and lies inside the entry zone.

The 10%, 55%, ten-window and 2R cutoffs are explicit screening heuristics, not optimized thresholds, validated evidence of profitability or confidence percentages. Sample agreement is not a probability. The 2R screen concerns the model endpoint; partial exits at 1R/2R have the different blended outcome described above.

Failure means NO TRADE with reasons. Levels shown while blocked are hypothetical only. The UI rechecks expiry/quote age every second. Public quotes refresh every 30 seconds. A missing, stale, wrong-symbol or different-exchange quote blocks the setup.

## What has and has not been tested

The existing retrospective evaluation measures **forecast-close accuracy**, with historical-only model inputs. The new entry/stop/target strategy has **not** been backtested for fills, realized net returns, drawdowns or intrabar stop/target ordering. It should not be represented as a proven investment strategy.

Stop orders do not guarantee their trigger price; gaps and liquidity can produce larger losses. Stop-limit orders may remain unfilled. The slippage input is a budget, not a cap or guarantee. See [Investor.gov's stop-order explanation](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15). The calculator does not account for existing positions or correlated portfolio exposure.

## Executed update on 2026-10-31

- Refreshed all six forecasts with real Kronos Small GPU inference, 256 input candles, three retained samples and ten holdouts.
- Completed at 11:22:51–11:23:47 UTC using Binance completed spot candles.
- All six have model MAE worse than the persistence baseline, so every setup is currently NO TRADE regardless of quote eligibility. This is an intended rejection, not a fabricated buy signal.
- 16 new Node tests passed: ATR gaps, net targets, sizing/cash limits, invalid inputs, missing or stale quotes, source mismatch, missed entry zones, expiry, insufficient/weak evaluation, sample disagreement and bearish rejection.
- Existing 16 Python tests passed; all six refreshed JSON payloads validated.
- Desktop/mobile browser checks passed for all 12 asset/timeframe combinations, including signal display and sizing inputs; zero JavaScript console errors. Screenshots inspected.
- The static publisher now allowlists 14 files, including the two signal JavaScript modules.

Run unit checks with `node --test tests/signals.test.cjs`. Run actual inference with `python forecast.py --all --folds 10`, then validate/publish with `python publish_forecast.py --all`. Publishing new JSON to the development branch does not deploy the static site automatically; use the existing `stage_site.py`/gh-pages workflow.
