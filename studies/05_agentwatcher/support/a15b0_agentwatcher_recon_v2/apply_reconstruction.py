#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import shutil
import sys
import time

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: apply_reconstruction.py /path/to/AgentWatcher_runtime_worktree"
    )

repo = Path(sys.argv[1]).expanduser().resolve()
required = repo / "src/defenses/agentwatcher/defense_agentwatcher.py"
if not required.exists():
    raise SystemExit(f"Not an AgentWatcher runtime checkout: {repo}")

payload = Path(__file__).resolve().parent
core_dst = repo / "src/defenses/monitor_llm_module/core.py"
registry_dst = repo / "src/defenses/__init__.py"
adapter_dst = repo / "agents/agentdojo/src/agentdojo/agent_pipeline/piarena_defense_adapter.py"

stamp = time.strftime("%Y%m%dT%H%M%S")
backup = repo / f"A15B0_RECON_V2_BACKUP_{stamp}"
backup.mkdir()

for p in (core_dst, registry_dst, adapter_dst):
    if p.exists():
        b = backup / p.relative_to(repo)
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, b)

shutil.copy2(payload / "core.py", core_dst)
shutil.copy2(payload / "defenses_init.py", registry_dst)

text = adapter_dst.read_text()
class_pos = text.find("class PIMonitorLLMDefenseAdapter")
if class_pos < 0:
    raise RuntimeError("Could not find PIMonitorLLMDefenseAdapter")

head = text[:class_pos]
tail = text[class_pos:]

needle = (
    '        except Exception as e:\n'
    '            print(f"[PIArenaDefenseAdapter] Skipped cleaning due to error: {e}")\n'
    '            import traceback\n'
    '            traceback.print_exc()\n'
    '\n'
    '        return query, runtime, env, messages, extra_args\n'
)

replacement = (
    '        except Exception as e:\n'
    '            if self.defense_name == "agentwatcher":\n'
    '                raise RuntimeError(\n'
    '                    f"AgentWatcher defense failure; aborting scientific run: {e}"\n'
    '                ) from e\n'
    '            print(f"[PIArenaDefenseAdapter] Skipped cleaning due to error: {e}")\n'
    '            import traceback\n'
    '            traceback.print_exc()\n'
    '\n'
    '        return query, runtime, env, messages, extra_args\n'
)

if needle not in tail:
    raise RuntimeError(
        "Could not locate PIMonitorLLMDefenseAdapter silent-skip handler"
    )

tail = tail.replace(needle, replacement, 1)
adapter_dst.write_text(head + tail)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = {
    "schema": "A15B0_AGENTWATCHER_RECONSTRUCTION_v2_VLLM",
    "scientific_label": "source-faithful AgentWatcher reconstruction",
    "scientific_design_changed": False,
    "changes": [
        "restore missing monitor_llm_module/core.py as local vLLM endpoint glue",
        "isolate defense registry to AgentWatcher",
        "fail fast instead of silently continuing when AgentWatcher errors",
    ],
    "files": {
        str(core_dst.relative_to(repo)): sha(core_dst),
        str(registry_dst.relative_to(repo)): sha(registry_dst),
        str(adapter_dst.relative_to(repo)): sha(adapter_dst),
    },
    "backup_dir": str(backup),
}

manifest_path = repo / "A15B0_AGENTWATCHER_RECONSTRUCTION_v2_VLLM.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

print("RECONSTRUCTION V2 APPLY PASS")
print("repo:", repo)
print("backup:", backup)
print("manifest:", manifest_path)
for name, digest in manifest["files"].items():
    print(digest, name)
