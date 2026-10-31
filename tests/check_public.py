"""Basic tracked-file secret scan and real public schema verification."""
import json
import re
import subprocess
from pathlib import Path
from validation import sanitize, SYMBOLS, STEPS

ROOT=Path(__file__).resolve().parents[1]
patterns=[
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"gh[pousr]_[A-Za-z0-9]{30,}",
    rb"github_pat_[A-Za-z0-9_]{30,}",
    rb"AKIA[A-Z0-9]{16}",
    rb"[A-Za-z]:[\\/]+Users[\\/]+",
    rb"(?i)(?:api_key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_/-]{20,}['\"]",
]
files=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()
for name in files:
    if name==".env" or any(part in {".venv",".cache","outputs","upstream","node_modules"} for part in Path(name).parts):
        raise SystemExit("Private runtime file tracked: "+name)
    if name=="tests/check_public.py": continue
    content=(ROOT/name).read_bytes()
    for pattern in patterns:
        if re.search(pattern,content): raise SystemExit("Potential secret or private path in "+name)
for symbol in SYMBOLS:
    for interval in STEPS:
        p=ROOT/"data"/f"{symbol}_{interval}.json"
        value=json.loads(p.read_text())
        assert sanitize(value)==value
        assert value["symbol"]==symbol and value["interval"]==interval
print(f"PASS: {len(files)} tracked files scanned; six real public forecast schemas validated")
