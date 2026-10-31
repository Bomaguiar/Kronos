"""Strict public schema. Reject malformed data; reconstruct only allowlisted fields."""
from datetime import datetime, timezone
import math
import re

SYMBOLS = ("BTCUSDT","ETHUSDT","SOLUSDT")
STEPS = {"1h":3600,"4h":14400}
def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",value):
        raise ValueError("Expected canonical UTC timestamp")
    return datetime.strptime(value,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
def number(value, low=0, high=1e9):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<high:
        raise ValueError("Invalid numeric value")
    return float(value)
def price(value):
    value=number(value)
    if value==0: raise ValueError("Price must be positive")
    return value
def candles(rows, step, length=None):
    if not isinstance(rows,list) or not 1<=len(rows)<=512 or length is not None and len(rows)!=length:
        raise ValueError("Invalid candle count")
    out=[]; previous=None
    for row in rows:
        t=timestamp(row["timestamp"])
        if t%step or previous is not None and t-previous!=step: raise ValueError("Candle timestamp gap")
        r=dict(timestamp=row["timestamp"],**{k:price(row[k]) for k in ("open","high","low","close")})
        if not r["low"]<=min(r["open"],r["close"])<=max(r["open"],r["close"])<=r["high"]: raise ValueError("Invalid OHLC")
        out.append(r); previous=t
    return out
def sanitize(p):
    if p.get("schema_version")!=2 or p.get("symbol") not in SYMBOLS or p.get("interval") not in STEPS: raise ValueError("Unknown schema or identifiers")
    step=STEPS[p["interval"]]; horizon=86400//step
    out={k:p[k] for k in ("schema_version","symbol","interval")}
    for k in ("generated_at","completed_at","history_as_of"):
        timestamp(p[k]); out[k]=p[k]
    now=datetime.now(timezone.utc).timestamp()
    if not timestamp(p["history_as_of"])+step<=timestamp(p["generated_at"])<=timestamp(p["completed_at"])<=now+60: raise ValueError("Invalid generation chronology")
    if p["source"] not in ("binance","binance-data","okx"): raise ValueError("Unknown source")
    out["source"]=p["source"]
    if p["model"]!="NeoQuasar/Kronos-small": raise ValueError("Unknown model")
    out["model"]=p["model"]
    for k in ("model_revision","tokenizer_revision","source_revision"):
        if not re.fullmatch("[0-9a-f]{40}",p[k]): raise ValueError("Invalid revision")
        out[k]=p[k]
    for k,lo,hi in (("sample_count",1,10),("lookback",2,512)):
        if type(p[k]) is not int or not lo<=p[k]<=hi: raise ValueError("Invalid count")
        out[k]=p[k]
    if p["horizon_hours"]!=24: raise ValueError("Expected 24 hours")
    out["horizon_hours"]=24
    out["history"]=candles(p["history"],step,p["lookback"])
    out["forecast"]=candles(p["forecast"],step,horizon)
    if out["history"][-1]["timestamp"]!=p["history_as_of"] or timestamp(out["forecast"][0]["timestamp"])!=timestamp(p["history_as_of"])+step: raise ValueError("Forecast origin mismatch")
    out["historical_last_close"]=price(p["historical_last_close"])
    if out["historical_last_close"]!=out["history"][-1]["close"]: raise ValueError("Last close mismatch")
    if len(p["samples"])!=p["sample_count"]: raise ValueError("Sample count mismatch")
    out["samples"]=[candles(s,step,horizon) for s in p["samples"]]
    for i,r in enumerate(out["forecast"]):
        for s in out["samples"]:
            if s[i]["timestamp"]!=r["timestamp"]: raise ValueError("Sample timestamp mismatch")
        for k in ("open","high","low","close"):
            if not math.isclose(r[k],sum(s[i][k] for s in out["samples"])/len(out["samples"]),rel_tol=1e-9): raise ValueError("Forecast is not sample mean")
    b=p["backtest"]
    if type(b["folds"]) is not int or not 1<=b["folds"]<=10 or b["count"]!=b["folds"]*horizon or len(b["rows"])!=b["count"]: raise ValueError("Invalid backtest count")
    rows=[]
    for i,r in enumerate(b["rows"]):
        t=timestamp(r["timestamp"]); origin=timestamp(r["origin_timestamp"])
        if t-origin != (i%horizon+1)*step or t>timestamp(p["history_as_of"]): raise ValueError("Backtest lookahead or horizon mismatch")
        if i and t-timestamp(rows[-1]["timestamp"])!=step: raise ValueError("Backtest timestamp gap")
        rows.append(dict(timestamp=r["timestamp"],origin_timestamp=r["origin_timestamp"],**{k:price(r[k]) for k in ("origin","actual","predicted")}))
    errors=[r["actual"]-r["predicted"] for r in rows]
    metrics=dict(mae=sum(abs(x) for x in errors)/len(rows),rmse=math.sqrt(sum(x*x for x in errors)/len(rows)),baseline_mae=sum(abs(r["actual"]-r["origin"]) for r in rows)/len(rows),directional_accuracy=sum(((r["predicted"]>r["origin"])-(r["predicted"]<r["origin"]))==((r["actual"]>r["origin"])-(r["actual"]<r["origin"])) for r in rows)/len(rows))
    for k,v in metrics.items():
        if not math.isclose(number(b[k]),v,rel_tol=1e-8,abs_tol=1e-8): raise ValueError("Backtest metric mismatch")
    out["backtest"]=dict(folds=b["folds"],count=len(rows),rows=rows,**metrics)
    out["ohlc_policy"]="Predicted wicks expanded to enclose raw OHLC; close unchanged"
    out["disclaimer"]="Experimental samples, not calibrated confidence intervals. Backtest is retrospective; pretraining overlap is unknown. Not financial advice."
    return out
