"""Build an allowlisted static site; no Python, configs, logs or model files."""
import json
import shutil
from pathlib import Path
from validation import sanitize, SYMBOLS, STEPS

ROOT=Path(__file__).resolve().parent
def main():
    target=ROOT/"site"
    target.mkdir(exist_ok=True)
    (target/"data").mkdir(exist_ok=True)
    for name in ("index.html","app.js","styles.css","lightweight-charts.js","CHART-LICENSE.txt"):
        shutil.copyfile(ROOT/name,target/name)
    for symbol in SYMBOLS:
        for interval in STEPS:
            name=f"{symbol}_{interval}.json"
            payload=sanitize(json.loads((ROOT/"data"/name).read_text()))
            if payload["symbol"]!=symbol or payload["interval"]!=interval: raise ValueError("Filename identifiers mismatch")
            (target/"data"/name).write_text(json.dumps(payload,allow_nan=False)+"\n",encoding="utf-8")
    (target/".nojekyll").write_text("")
    expected={"index.html","app.js","styles.css","lightweight-charts.js","CHART-LICENSE.txt",".nojekyll",*[f"data/{s}_{i}.json" for s in SYMBOLS for i in STEPS]}
    actual={p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    if actual!=expected: raise RuntimeError("Unexpected files in site staging directory; inspect before deployment")
    print(f"Staged {len(expected)} public files")

if __name__=="__main__": main()
