"""Read-only Kronos inference with chronological walk-forward evaluation."""
import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
UPSTREAM = Path(os.getenv("KRONOS_UPSTREAM", str(ROOT / "upstream" / "Kronos")))
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
INTERVAL_SECONDS = {"1h": 3600, "4h": 14400}
MODEL_REV = "901c26c1332695a2a8f243eb2f37243a37bea320"
TOKENIZER_REV = "0e0117387f39004a9016484a186a908917e22426"
SOURCE_REV = "67b630e67f6a18c9e9be918d9b4337c960db1e9a"
COLS = ["open", "high", "low", "close", "volume", "amount"]

def stamp(t):
    return pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ")

def validate_history(df, interval):
    if len(df) < 2 or not np.isfinite(df[COLS].to_numpy()).all():
        raise ValueError("Missing or nonfinite candles")
    if (df[COLS[:4]] <= 0).any().any() or (df[COLS[4:]] < 0).any().any():
        raise ValueError("Invalid price or volume")
    if ((df.high < df[["open","close","low"]].max(axis=1)) | (df.low > df[["open","close"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC bounds")
    step = pd.Timedelta(seconds=INTERVAL_SECONDS[interval])
    if not df.timestamps.diff().iloc[1:].eq(step).all():
        raise ValueError("Duplicate, unordered or missing candle timestamps")
    if any(int(t.timestamp()) % INTERVAL_SECONDS[interval] for t in df.timestamps):
        raise ValueError("Candle not aligned to UTC interval")
    return df

def get_history(symbol, interval, limit, provider="auto"):
    if symbol not in SYMBOLS or interval not in INTERVAL_SECONDS or not 2 <= limit <= 999:
        raise ValueError("Unsupported symbol, interval or limit")
    providers = ["binance","binance-data","okx"] if provider == "auto" else [provider]
    for name in providers:
        try:
            if name in ("binance","binance-data"):
                host = "api.binance.com" if name == "binance" else "data-api.binance.vision"
                r = requests.get(f"https://{host}/api/v3/klines", params=dict(symbol=symbol,interval=interval,limit=limit+1),timeout=30)
                r.raise_for_status()
                rows = [[x[0],*x[1:6],x[7]] for x in r.json()]
            elif name == "okx":
                rows, after = [], None
                while len(rows) < limit+1:
                    params = dict(instId=symbol.replace("USDT","-USDT"),bar=interval.upper(),limit=100)
                    if after: params["after"] = after
                    r = requests.get("https://www.okx.com/api/v5/market/history-candles",params=params,timeout=30)
                    r.raise_for_status()
                    body = r.json()
                    if body.get("code") != "0" or not body.get("data"): raise ValueError("No OKX candles")
                    batch = body["data"]
                    rows.extend([[x[0],*x[1:6],x[7]] for x in batch if x[8]=="1"])
                    after = batch[-1][0]
            else: raise ValueError("Unknown provider")
            df = pd.DataFrame(rows,columns=["time",*COLS])
            df["timestamps"] = pd.to_datetime(pd.to_numeric(df.time),unit="ms",utc=True)
            df[COLS] = df[COLS].apply(pd.to_numeric,errors="raise")
            step = pd.Timedelta(seconds=INTERVAL_SECONDS[interval])
            now = pd.Timestamp.now(tz="UTC")
            df = df.loc[df.timestamps + step <= now].sort_values("timestamps").tail(limit).reset_index(drop=True)
            if len(df) < limit or now - (df.timestamps.iloc[-1]+step) > step:
                raise ValueError("Insufficient or stale market history")
            validate_history(df,interval)
            df.attrs["provider"] = name
            return df
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
            if name == providers[-1]: raise
    raise RuntimeError("Market data unavailable")

def load_predictor(device="auto"):
    import torch
    os.environ.setdefault("HF_HOME",str(ROOT / ".cache" / "huggingface"))
    if not (UPSTREAM/"model").is_dir(): raise RuntimeError("Install pinned upstream source first")
    import hashlib
    lock = json.loads((ROOT / "upstream-lock.json").read_text())
    if lock["revision"] != SOURCE_REV:
        raise RuntimeError("Upstream revision differs from reviewed version")
    for name, digest in lock["files"].items():
        if hashlib.sha256((UPSTREAM/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != digest:
            raise RuntimeError("Upstream source differs from inspected files")
    sys.path.insert(0,str(UPSTREAM))
    from model import Kronos, KronosTokenizer, KronosPredictor
    device = ("cuda:0" if torch.cuda.is_available() else "cpu") if device=="auto" else device
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base",revision=TOKENIZER_REV)
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small",revision=MODEL_REV)
    tokenizer.eval(); model.eval()
    print(f"Loaded official Kronos Small on {device}",flush=True)
    return KronosPredictor(model,tokenizer,device=device,max_context=512)

def predict(predictor, history, interval, horizon, samples, seed):
    import torch
    future = pd.Series(pd.date_range(history.timestamps.iloc[-1],periods=horizon+1,freq=pd.Timedelta(seconds=INTERVAL_SECONDS[interval]))[1:])
    paths = []
    for i in range(samples):
        torch.manual_seed(seed+i)
        with torch.inference_mode():
            frame = predictor.predict(df=history[COLS],x_timestamp=history.timestamps.reset_index(drop=True),y_timestamp=future,pred_len=horizon,T=1.0,top_p=.9,sample_count=1,verbose=False)
        values = frame[COLS[:4]].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values<=0).any(): raise ValueError("Invalid model prices")
        # Decoder is unconstrained: expand wicks to enclose all raw OHLC values.
        low = np.min(values,axis=1)
        values[:,1] = np.max(values,axis=1)
        values[:,2] = low
        paths.append([dict(timestamp=stamp(t),**dict(zip(COLS[:4],v))) for t,v in zip(future,values)])
    return paths

def records(frame):
    return [dict(timestamp=stamp(r.timestamps),**{k:float(r[k]) for k in COLS[:4]}) for _,r in frame.iterrows()]

def forecast(symbol, interval, lookback, pred_len, samples, device, provider="auto", folds=10, predictor=None):
    if not 2<=lookback<=512 or interval not in INTERVAL_SECONDS or pred_len != 86400//INTERVAL_SECONDS[interval]:
        raise ValueError("Use lookback 2..512 and exactly a 24-hour horizon")
    if not 1<=samples<=10 or not 1<=folds<=10: raise ValueError("samples/folds must be 1..10")
    history = get_history(symbol,interval,lookback+folds*pred_len,provider)
    predictor = predictor or load_predictor(device)
    generated = stamp(pd.Timestamp.now(tz="UTC"))
    evaluations = []
    for fold in range(folds):
        cut = len(history)-(folds-fold)*pred_len
        train = history.iloc[cut-lookback:cut].reset_index(drop=True)
        target = history.iloc[cut:cut+pred_len]
        paths = predict(predictor,train,interval,pred_len,samples,1000+fold*100)
        means = np.mean([[r["close"] for r in p] for p in paths],axis=0)
        origin = float(train.close.iloc[-1])
        for (_,r),p in zip(target.iterrows(),means):
            evaluations.append(dict(timestamp=stamp(r.timestamps),origin=origin,origin_timestamp=stamp(train.timestamps.iloc[-1]),actual=float(r.close),predicted=float(p)))
    a=np.array([r["actual"] for r in evaluations]); p=np.array([r["predicted"] for r in evaluations]); o=np.array([r["origin"] for r in evaluations])
    paths = predict(predictor,history.tail(lookback).reset_index(drop=True),interval,pred_len,samples,42)
    mean = [dict(timestamp=paths[0][i]["timestamp"],**{k:float(np.mean([s[i][k] for s in paths])) for k in COLS[:4]}) for i in range(pred_len)]
    return dict(schema_version=2,symbol=symbol,interval=interval,generated_at=generated,completed_at=stamp(pd.Timestamp.now(tz="UTC")),history_as_of=stamp(history.timestamps.iloc[-1]),source=history.attrs["provider"],historical_last_close=float(history.close.iloc[-1]),model="NeoQuasar/Kronos-small",model_revision=MODEL_REV,tokenizer_revision=TOKENIZER_REV,source_revision=SOURCE_REV,sample_count=samples,lookback=lookback,horizon_hours=24,history=records(history.tail(lookback)),forecast=mean,samples=paths,backtest=dict(folds=folds,count=len(a),mae=float(np.mean(abs(a-p))),rmse=float(np.sqrt(np.mean((a-p)**2))),directional_accuracy=float(np.mean(np.sign(p-o)==np.sign(a-o))),baseline_mae=float(np.mean(abs(a-o))),rows=evaluations),ohlc_policy="Predicted wicks expanded to enclose raw OHLC; close unchanged",disclaimer="Experimental samples, not calibrated confidence intervals. Backtest is retrospective; pretraining overlap is unknown. Not financial advice.")

def main():
    load_dotenv(ROOT / ".env")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol",choices=SYMBOLS,default="BTCUSDT"); parser.add_argument("--interval",choices=tuple(INTERVAL_SECONDS),default=os.getenv("INTERVAL","1h"))
    parser.add_argument("--lookback",type=int,default=int(os.getenv("LOOKBACK","256"))); parser.add_argument("--pred-len",type=int)
    parser.add_argument("--samples",type=int,default=int(os.getenv("SAMPLE_COUNT","3"))); parser.add_argument("--folds",type=int,default=10)
    parser.add_argument("--device",default=os.getenv("DEVICE","auto")); parser.add_argument("--provider",choices=["auto","binance","binance-data","okx"],default=os.getenv("MARKET_PROVIDER","auto"))
    parser.add_argument("--all",action="store_true"); args=parser.parse_args()
    predictor=load_predictor(args.device)
    for symbol,interval in ([(s,i) for s in SYMBOLS for i in INTERVAL_SECONDS] if args.all else [(args.symbol,args.interval)]):
        result=forecast(symbol,interval,args.lookback,args.pred_len or 86400//INTERVAL_SECONDS[interval],args.samples,args.device,args.provider,args.folds,predictor)
        out=ROOT/"outputs"; out.mkdir(exist_ok=True)
        (out/f"{symbol}_{interval}.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        print(f'{symbol} {interval}: generated {result["completed_at"]}, final close {result["forecast"][-1]["close"]:.4f}',flush=True)

if __name__=="__main__": main()
