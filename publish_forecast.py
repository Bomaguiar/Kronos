"""Publish only validated public JSON, optionally to a reviewed development branch."""
import argparse
import json
from pathlib import Path
import subprocess
from validation import sanitize, SYMBOLS, STEPS

ROOT=Path(__file__).resolve().parent
def prepare(symbol,interval):
    if symbol not in SYMBOLS or interval not in STEPS: raise ValueError("Unsupported identifiers")
    payload=json.loads((ROOT/"outputs"/f"{symbol}_{interval}.json").read_text(encoding="utf-8"))
    if payload.get("symbol")!=symbol or payload.get("interval")!=interval: raise ValueError("Identifier mismatch")
    public=sanitize(payload)
    out=ROOT/"data"/f"{symbol}_{interval}.json"
    out.parent.mkdir(exist_ok=True)
    temp=out.with_suffix(".tmp")
    temp.write_text(json.dumps(public,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    temp.replace(out)
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol",choices=SYMBOLS); parser.add_argument("--interval",choices=tuple(STEPS))
    parser.add_argument("--all",action="store_true"); parser.add_argument("--push",action="store_true")
    args=parser.parse_args()
    if not args.all and not (args.symbol and args.interval): parser.error("Use --all or --symbol and --interval")
    paths=[prepare(s,i) for s,i in ([(s,i) for s in SYMBOLS for i in STEPS] if args.all else [(args.symbol,args.interval)])]
    print(f"Validated {len(paths)} public forecast files")
    if not args.push: return
    def git(*argv):
        return subprocess.check_output(["git","-C",str(ROOT),*argv],text=True).strip()
    if git("remote","get-url","origin").rstrip("/").removesuffix(".git") not in ("https://github.com/Bomaguiar/Kronos","git@github.com:Bomaguiar/Kronos"): raise RuntimeError("Wrong remote")
    branch=git("branch","--show-current")
    if branch!="codex/kronos-production": raise RuntimeError("Publishing requires codex/kronos-production; open a PR for review")
    if git("diff","--cached","--name-only"): raise RuntimeError("Commit or unstage existing staged changes first")
    files=[p.relative_to(ROOT).as_posix() for p in paths]
    git("add","--",*files)
    if git("diff","--cached","--name-only"):
        git("commit","-m","Publish validated Kronos forecasts","--",*files)
    git("push","origin",branch)

if __name__=="__main__": main()
