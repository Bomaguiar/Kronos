"""Publish allowlisted forecast fields to GitHub; never publish local configuration."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VALID_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
VALID_INTERVALS = {"1h", "4h"}
FIELDS = ("timestamp", "open", "high", "low", "close")


def prepare(symbol: str, interval: str) -> Path:
    if symbol not in VALID_SYMBOLS or interval not in VALID_INTERVALS:
        raise ValueError("Unsupported symbol or interval")
    src = ROOT / "outputs" / f"{symbol}_{interval}.json"
    if not src.is_file():
        raise FileNotFoundError(f"Run forecast.py first: {src}")
    payload = json.loads(src.read_text(encoding="utf-8"))
    if payload.get("symbol") != symbol or payload.get("interval") != interval:
        raise ValueError("Output identifiers do not match")
    rows = payload.get("forecast")
    if not isinstance(rows, list) or not (1 <= len(rows) <= 120):
        raise ValueError("Invalid forecast length")
    cleaned = []
    for row in rows:
        record = {key: row[key] for key in FIELDS}
        for key in FIELDS[1:]:
            price = float(record[key])
            if not (0 < price < 1e9):
                raise ValueError("Invalid forecast value")
            record[key] = price
        record["timestamp"] = str(record["timestamp"])
        cleaned.append(record)
    last = float(payload["historical_last_close"])
    if not 0 < last < 1e9:
        raise ValueError("Invalid last price")
    public = {
        "symbol": symbol,
        "interval": interval,
        "historical_last_close": last,
        "model": str(payload.get("model", "Kronos")),
        "forecast": cleaned,
        "disclaimer": "Experimental model output, not financial advice",
    }
    out = ROOT / "data" / f"{symbol}_{interval}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(public, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True, choices=sorted(VALID_SYMBOLS))
    parser.add_argument("--interval", required=True, choices=sorted(VALID_INTERVALS))
    parser.add_argument("--push", action="store_true", help="Publish to GitHub after inspection")
    args = parser.parse_args()
    out = prepare(args.symbol, args.interval)
    print(f"Prepared allowlisted public forecast: {out.relative_to(ROOT)}")
    if not args.push:
        print("Review this JSON before publishing. Add --push when ready.")
        return
    def git(*argv: str) -> str:
        return subprocess.check_output(["git", "-C", str(ROOT), *argv], text=True).strip()
    remote = git("remote", "get-url", "origin")
    if remote.rstrip("/").removesuffix(".git") not in (
        "https://github.com/Bomaguiar/Kronos",
        "git@github.com:Bomaguiar/Kronos",
    ):
        raise RuntimeError("Refusing to push to a different remote: " + remote)
    if git("branch", "--show-current") != "main":
        raise RuntimeError("Switch to main before publishing")
    git("add", "--", str(out.relative_to(ROOT)))
    if not git("diff", "--cached", "--quiet", "--", str(out.relative_to(ROOT))) if False else False:
        pass
    subprocess.run(["git", "-C", str(ROOT), "commit", "-m",
                    f"Publish {args.symbol} {args.interval} forecast", "--",
                    str(out.relative_to(ROOT))], check=False)
    subprocess.run(["git", "-C", str(ROOT), "push", "origin", "main"], check=True)
    print("Published public forecast JSON.")


if __name__ == "__main__":
    main()
