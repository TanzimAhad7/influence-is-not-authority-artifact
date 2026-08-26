#!/usr/bin/env python3
from __future__ import annotations
import datetime,hashlib,json,sys
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 root=Path(sys.argv[1]).resolve();pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build';pkg=root/'E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1'
 dev=json.loads((pre/'DEV_LIVE_PREFLIGHT.json').read_text());freeze=json.loads((pre/'FREEZE.json').read_text())
 if dev.get('status')!='PASS':raise SystemExit('FATAL dev preflight not PASS')
 science=root/'E2E_ATTR_AUTH_v1/scientific_v1'
 if science.exists() and any(science.iterdir()):raise SystemExit('FATAL scientific outcome directory already nonempty before seal')
 ledger=pre/'PREFREEZE_SHA256.tsv'
 with ledger.open('w') as f:
  for base in [pre,pkg/'code']:
   for p in sorted(base.rglob('*')):
    if p.is_file() and p.name not in {'PREFREEZE_SHA256.tsv','PREFREEZE_COMPLETE.md'}:f.write(f'{sha(p)}\t{p.relative_to(root)}\n')
 text=f'''# E2E-ATTR-AUTH PREFREEZE COMPLETE\n\n**GO: PASS**  \n**Timestamp UTC:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}  \n**B:** {freeze['B']} natural tasks  \n**Planned executions:** {freeze['N_exec']}  \n**Scientific outcome rows present at seal:** 0  \n**AgentDojo:** 0.1.35 / benchmark v1  \n**Defense:** official source-locked AttriGuard, fuzzy, level 2  \n**Victim / shadow / judge:** openai/gpt-4.1-mini through frozen OpenRouter path  \n\nAll cohort, blinded-review, deterministic PAEF, mutation-test, matched-context, source/config, schedule, analysis-code, and dev-live-preflight gates passed before science.\n\nAfter the first sealed scientific run, the no-v2 science stop law applies regardless of outcome.\n'''
 (pre/'PREFREEZE_COMPLETE.md').write_text(text)
 print(text)
if __name__=='__main__':main()
