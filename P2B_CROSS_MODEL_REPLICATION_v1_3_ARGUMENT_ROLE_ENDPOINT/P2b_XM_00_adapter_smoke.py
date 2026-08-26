#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import openai, requests
from canonical_json_adapter import canonicalize_history, parse_candidate_text

def served_model(base_url, api_key):
    r=requests.get(base_url.rstrip("/")+"/models",headers={"Authorization":f"Bearer {api_key}"},timeout=20)
    r.raise_for_status()
    ids=[x["id"] for x in r.json().get("data",[])]
    if len(ids)!=1:
        raise SystemExit(f"FATAL expected one served model, got {ids}")
    return ids[0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model-key",required=True)
    ap.add_argument("--base-url",default="http://localhost:8100/v1")
    ap.add_argument("--api-key",default=os.getenv("P2B_API_KEY","EMPTY"))
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--revision-lock",required=True)
    args=ap.parse_args()
    here=Path(__file__).resolve().parent
    reg=json.loads((here/"MODEL_REGISTRY.json").read_text())
    cfg=reg["models"][args.model_key]
    render_preflight=json.loads((Path(args.out_dir)/"P2B_RENDER_PREFLIGHT.json").read_text())
    if not render_preflight.get("pass") or render_preflight.get("model_key")!=args.model_key:
        raise SystemExit("FATAL missing/mismatched 26/26 live render preflight PASS")
    lock=json.loads(Path(args.revision_lock).read_text())
    if render_preflight.get("revision_lock_sha256") != lock.get("lock_sha256"):
        raise SystemExit("FATAL render preflight/revision-lock mismatch")
    model=served_model(args.base_url,args.api_key)
    if model != cfg["model_id"]:
        raise SystemExit(f"FATAL served model mismatch expected={cfg['model_id']} got={model}")
    client=openai.OpenAI(base_url=args.base_url,api_key=args.api_key)
    class _Params:
        def model_json_schema(self):
            return {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            }

    class _Fn:
        name = "lookup_code"
        description = "Return the record associated with an exact code."
        parameters = _Params()

    class _Runtime:
        functions = {"lookup_code": _Fn()}

    # This synthetic history intentionally contains the exact structural pattern that
    # broke Gemma v1: a historical tool result immediately followed by another user
    # message. canonicalize_history() must preserve both while producing alternating
    # user/assistant roles accepted by strict chat templates.
    synthetic_history = [
        {"role": "system", "content": "Synthetic adapter compatibility test."},
        {"role": "user", "content": "First inspect the old code."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "function": "lookup_code",
                    "args": {"code": "OLD1"},
                    "id": "synthetic_old_call",
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "synthetic_old_call",
            "tool_call": {"function": "lookup_code"},
            "content": "old-record",
            "error": None,
        },
        {
            "role": "user",
            "content": "Now use lookup_code with code exactly ALPHA7. Do not answer from memory.",
        },
    ]
    smoke_messages = canonicalize_history(synthetic_history, _Runtime())

    # Local shape assertion before any API call.
    conversational = [m["role"] for m in smoke_messages if m["role"] != "system"]
    if any(a == b for a, b in zip(conversational, conversational[1:])):
        raise SystemExit(f"FATAL smoke history is not alternating: {conversational}")

    results=[]
    for rep in range(3):
        c=client.chat.completions.create(
          model=model,temperature=0.0,top_p=1.0,seed=0,max_tokens=128,
          messages=smoke_messages,
        )
        text=c.choices[0].message.content or ""
        calls,err=parse_candidate_text(text)
        ok=(err is None and len(calls)==1 and calls[0]["function"]=="lookup_code"
            and calls[0]["args"]=={"code":"ALPHA7"})
        results.append({"rep":rep,"raw_text":text,"parse_error":err,"calls":calls,"pass":ok})
        print(f"SMOKE {args.model_key} rep={rep} pass={ok} text={text!r}", flush=True)
    passed=all(x["pass"] for x in results)
    outdir=Path(args.out_dir); outdir.mkdir(parents=True,exist_ok=True)
    obj={"schema":"P2B_XMODEL_ADAPTER_SMOKE_V1_3","model_key":args.model_key,
         "model_id":model,"calls":3,"scientific":False,"pass":passed,"results":results}
    (outdir/"P2B_ADAPTER_SMOKE.json").write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    print(f"ADAPTER SMOKE {'PASS' if passed else 'FAIL'}", flush=True)
    if not passed:
        raise SystemExit(5)
if __name__=="__main__": main()
