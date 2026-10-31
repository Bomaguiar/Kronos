"""Synthetic fixtures exercise safeguards only; never used as dashboard/model data."""
import copy
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from forecast import validate_history, forecast, stamp, COLS
from validation import sanitize

def history(n=32):
    df=pd.DataFrame({k:np.full(n,100.0) for k in COLS})
    df["high"]=101.;df["low"]=99.
    df["timestamps"]=pd.date_range("2026-01-01",periods=n,freq="4h",tz="UTC")
    df.attrs["provider"]="binance"
    return df

class PipelineTests(unittest.TestCase):
    def test_gap_rejected(self):
        with self.assertRaises(ValueError): validate_history(history().drop(4),"4h")
    def test_duplicate_rejected(self):
        h=history();h.loc[4,"timestamps"]=h.loc[3,"timestamps"]
        with self.assertRaises(ValueError): validate_history(h,"4h")
    def test_invalid_ohlc_rejected(self):
        h=history();h.loc[1,"high"]=90
        with self.assertRaises(ValueError): validate_history(h,"4h")
    def test_nan_volume_rejected(self):
        h=history();h.loc[1,"volume"]=float("nan")
        with self.assertRaises(ValueError): validate_history(h,"4h")
    def make_payload(self):
        h=history(20);self.inputs=[]
        def fake(predictor,train,interval,horizon,samples,seed):
            self.inputs.append(train.timestamps.tolist())
            future=pd.date_range(train.timestamps.iloc[-1],periods=horizon+1,freq="4h")[1:]
            return [[dict(timestamp=stamp(t),open=100.,high=102.,low=99.,close=101.) for t in future] for _ in range(samples)]
        with patch("forecast.get_history",return_value=h),patch("forecast.predict",side_effect=fake):
            return forecast("BTCUSDT","4h",8,6,2,"cpu",folds=2,predictor=object())
    def test_no_lookahead_and_known_metrics(self):
        p=self.make_payload()
        self.assertEqual(len(self.inputs),3)
        for i,train in enumerate(self.inputs[:2]):
            first=p["backtest"]["rows"][i*6]
            self.assertLess(train[-1],pd.Timestamp(first["timestamp"]))
            self.assertEqual(len(train),8)
        self.assertEqual(p["backtest"]["mae"],1)
        self.assertEqual(p["backtest"]["rmse"],1)
        self.assertEqual(p["backtest"]["baseline_mae"],0)
        self.assertEqual(p["backtest"]["directional_accuracy"],0)
        sanitize(p)
    def test_private_fields_removed(self):
        p=self.make_payload();p["private"]="PRIVATE";p["forecast"][0]["secret"]="PRIVATE";p["backtest"]["rows"][0]["local_path"]="PRIVATE"
        self.assertNotIn("PRIVATE",str(sanitize(p)))
    def test_bad_metric_rejected(self):
        p=self.make_payload();p["backtest"]["mae"]=0
        with self.assertRaises(ValueError): sanitize(p)
    def test_nonfinite_rejected(self):
        p=self.make_payload();p["forecast"][0]["close"]=float("nan")
        with self.assertRaises(ValueError): sanitize(p)
    def test_future_origin_rejected(self):
        p=self.make_payload();p["backtest"]["rows"][0]["origin_timestamp"]=p["forecast"][0]["timestamp"]
        with self.assertRaises(ValueError): sanitize(p)
    def test_injected_timestamp_rejected(self):
        p=self.make_payload();p["forecast"][0]["timestamp"]="<script>bad</script>"
        with self.assertRaises(ValueError): sanitize(p)
    def test_sample_mean_mismatch_rejected(self):
        p=self.make_payload();p["forecast"][0]["close"]=100.5
        with self.assertRaises(ValueError): sanitize(p)
    def test_4h_24_candles_rejected(self):
        with self.assertRaises(ValueError): forecast("BTCUSDT","4h",8,24,1,"cpu")

if __name__=="__main__": unittest.main()
