#!/usr/bin/env python3
from __future__ import annotations
import copy, csv, hashlib, inspect, json, os, subprocess, time, urllib.request, urllib.error, uuid, math
from pathlib import Path
from typing import Any, Sequence
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement

EXPECTED_COMPLETE_FREEZE_SHA = "0ad06fefbbc09d79eadf1e0186570d6181b4b5b22812889cbfed5476ecb0f82c"
EXPECTED_PROTOCOL_FREEZE_SHA = "611e26250e55da6d04f6d93976752078cb957c20b7dd630b225129d528f8ef27"
ATTACK_PIPELINE_NAME_ALIAS = "gemini-2.5-flash-preview-04-17"
ATTACK_MODEL_PROSE_EXPECTED = "AI model developed by Google"

class HardStop(RuntimeError):
    pass

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def stable_json(obj: Any) -> str:
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)

def obj_hash(obj: Any) -> str:
    return hashlib.sha256(stable_json(obj).encode()).hexdigest()

def write_json(path: Path,obj: Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    tmp.replace(path)

def append_jsonl(path: Path,obj: Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(obj,sort_keys=True,ensure_ascii=False,default=str)+'\n')
        f.flush(); os.fsync(f.fileno())

def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def read_csv(path: Path):
    with path.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def load_env_key(project_root: Path,name: str):
    v=os.environ.get(name)
    if v:
        return v
    p=project_root/'.env'
    if not p.exists():
        return None
    for raw in p.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        if k.strip()==name:
            v=v.strip()
            if len(v)>=2 and v[0]==v[-1] and v[0] in "'\"":
                v=v[1:-1]
            return v
    return None

def package_hashes(pkg: Path):
    return {
        str(p.relative_to(pkg)): sha256_file(p)
        for p in sorted(pkg.rglob('*'))
        if p.is_file() and p.name!='PACKAGE_SHA256.txt' and '__pycache__' not in p.parts
    }

def agentdojo_tree_hash():
    import agentdojo
    root=Path(agentdojo.__file__).resolve().parent
    rows=[(str(p.relative_to(root)),sha256_file(p)) for p in sorted(root.rglob('*.py'))]
    return obj_hash(rows),root

def verify_freeze(pkg: Path,freeze_complete: Path):
    import zipfile
    binding=json.loads((pkg/'FREEZE_BINDING.json').read_text())
    got=sha256_file(freeze_complete)
    if got!=EXPECTED_COMPLETE_FREEZE_SHA or got!=binding['author_completed_freeze_archive_sha256']:
        raise HardStop(f'completed freeze archive SHA mismatch: {got}')
    proto=json.loads((pkg/'FROZEN_INPUTS'/'P0B3_PROTOCOL_FREEZE.json').read_text())
    if proto.get('freeze_sha256')!=EXPECTED_PROTOCOL_FREEZE_SHA or proto.get('status')!='FROZEN_BEFORE_ANY_SCIENTIFIC_OUTCOME':
        raise HardStop('protocol freeze hash/status mismatch')
    for name,exp in binding['embedded_frozen_input_sha256'].items():
        p=pkg/'FROZEN_INPUTS'/name
        if not p.exists() or sha256_file(p)!=exp:
            raise HardStop(f'embedded frozen input drift: {name}')
    with zipfile.ZipFile(freeze_complete) as z:
        base='P0B3_CAUSALARMOR_CALIBRATION_FREEZE_RUN_v1/'
        for name in binding['embedded_frozen_input_sha256']:
            if z.read(base+name)!=(pkg/'FROZEN_INPUTS'/name).read_bytes():
                raise HardStop(f'author freeze archive vs embedded input mismatch: {name}')
    return proto

def verify_population(pkg: Path,proto: dict):
    import importlib.metadata
    from agentdojo.task_suite.load_suites import get_suite
    if importlib.metadata.version('agentdojo')!=proto['config']['agentdojo']['package_version']:
        raise HardStop('agentdojo package version mismatch')
    tree,root=agentdojo_tree_hash()
    if tree!=proto['config']['agentdojo']['source_tree_sha256_expected']:
        raise HardStop(f'AgentDojo source-tree mismatch: {tree}')
    benign=read_csv(pkg/'FROZEN_INPUTS'/'P0B3_BENIGN_97_TASKS.csv')
    primary=read_csv(pkg/'FROZEN_INPUTS'/'P0B3_PRIMARY_949_PAIRS.csv')
    legacy=read_csv(pkg/'FROZEN_INPUTS'/'P0B3_LEGACY_629_PAIRS.csv')
    if (len(benign),len(primary),len(legacy))!=(97,949,629):
        raise HardStop('frozen population count mismatch')
    bset={(r['suite'],r['user_task_id']) for r in benign}
    pset={(r['suite'],r['user_task_id'],r['injection_task_id']) for r in primary}
    lset={(r['suite'],r['user_task_id'],r['injection_task_id']) for r in legacy}
    if len(bset)!=97 or len(pset)!=949 or len(lset)!=629 or not lset.issubset(pset):
        raise HardStop('frozen population uniqueness/subset mismatch')
    for s in proto['config']['agentdojo']['suites']:
        suite=get_suite('v1.2.2',s)
        if {r['user_task_id'] for r in benign if r['suite']==s}!=set(suite.user_tasks):
            raise HardStop(f'{s}: benign task-set drift')
        official={(s,u,i) for u in suite.user_tasks for i in suite.injection_tasks}
        frozen={(r['suite'],r['user_task_id'],r['injection_task_id']) for r in primary if r['suite']==s}
        if frozen!=official:
            raise HardStop(f'{s}: primary cross-product drift')
    return {'benign':benign,'primary':primary,'legacy':legacy,'agentdojo_tree_sha256':tree,'agentdojo_root':str(root)}

def get_text(content) -> str:
    if content is None:
        return ''
    if isinstance(content,str):
        return content
    parts=[]
    for x in content:
        parts.append(str(x.get('content','') or '') if isinstance(x,dict) else str(x))
    return '\n'.join(parts)

def action_string(call) -> str:
    args=dict(call.args or {})
    return f"{call.function}({json.dumps(args,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)})"

def is_privileged(function_name: str,proto: dict) -> bool:
    rule=proto['config']['detector']['privileged_rule']; name=str(function_name)
    if name in set(rule['explicit']):
        return True
    if name.startswith(('get_','search_','list_')):
        return False
    return any(name.startswith(p) for p in rule['side_effect_prefixes'])

def context_serializer(messages: Sequence[dict],*,ablate_user=False,ablate_tool_message_index=None) -> str:
    """Prospectively frozen live representation of C_t.

    Uses AgentDojo history before proposed Y. First user message is U; every role=tool message is one S.
    C\\U deletes the first user message. C\\S deletes exactly the selected tool-result message.
    No matched replacement or truncation is used.
    """
    out=[]; user_deleted=False
    for idx,m in enumerate(messages):
        role=m.get('role','?')
        if role=='user' and ablate_user and not user_deleted:
            user_deleted=True; continue
        if role=='tool' and ablate_tool_message_index is not None and idx==ablate_tool_message_index:
            continue
        txt=get_text(m.get('content'))
        if role=='system':
            out += ['<SYSTEM>',txt,'</SYSTEM>']
        elif role=='user':
            out += ['<USER>',txt,'</USER>']
        elif role=='assistant':
            out += ['<ASSISTANT>',txt]
            for tc in (m.get('tool_calls') or []):
                out.append('<TOOL_CALL>'+action_string(tc)+'</TOOL_CALL>')
            out.append('</ASSISTANT>')
        elif role=='tool':
            tc=m.get('tool_call'); name=getattr(tc,'function','tool') if tc is not None else 'tool'
            out += [f'<TOOL_RESULT name="{name}">',str(m.get('error')) if m.get('error') else txt,'</TOOL_RESULT>']
        else:
            out += [f'<{str(role).upper()}>',txt,f'</{str(role).upper()}>']
    out.append('<ASSISTANT_ACTION>')
    return '\n'.join(out)+'\n'

class ProxyScorer:
    def __init__(self,base_url: str,model: str,transport: str|None=None,timeout=180):
        self.base=base_url.rstrip('/'); self.model=model; self.transport=transport; self.timeout=timeout; self.http_calls=0
    def _post(self,payload):
        req=urllib.request.Request(self.base+'/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer EMPTY','Content-Type':'application/json'},method='POST')
        self.http_calls+=1
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise HardStop(f'proxy HTTP {e.code}: {e.read().decode(errors="replace")[:1000]}') from e
    @staticmethod
    def _parse(choice,cut):
        lp=choice.get('logprobs') or {}; offs=lp.get('text_offset'); toks=lp.get('token_logprobs')
        if not isinstance(offs,list) or not isinstance(toks,list):
            raise HardStop('proxy response lacks echo text_offset/token_logprobs')
        vals=[float(v) for o,v in zip(offs,toks) if o is not None and o>=cut and v is not None]
        if not vals:
            raise HardStop('proxy could not isolate completion tokens')
        total=sum(vals)
        if not math.isfinite(total):
            raise HardStop('proxy produced non-finite completion logprob')
        return {'sum_logprob':total,'n_tokens':len(vals)}
    def score_many(self,items):
        if self.transport=='batch_echo_v1':
            d=self._post({'model':self.model,'prompt':[p+c for p,c in items],'max_tokens':0,'echo':True,'logprobs':1,'temperature':0})
            choices=d.get('choices') or []
            if len(choices)!=len(items):
                raise HardStop(f'proxy batch choice count {len(choices)} != {len(items)}')
            byidx={int(c.get('index',i)):c for i,c in enumerate(choices)}
            return [self._parse(byidx[i],len(items[i][0])) for i in range(len(items))]
        if self.transport=='scalar_echo_v1':
            out=[]
            for p,c in items:
                d=self._post({'model':self.model,'prompt':p+c,'max_tokens':0,'echo':True,'logprobs':1,'temperature':0})
                ch=d.get('choices') or []
                if len(ch)!=1:
                    raise HardStop('proxy scalar choice count != 1')
                out.append(self._parse(ch[0],len(p)))
            return out
        raise HardStop(f'unfrozen proxy transport {self.transport!r}')
    def choose_transport_preflight(self):
        items=[('System: harmless scoring test\nAssistant: ','alpha'),('System: harmless scoring test two\nAssistant: ','beta')]
        try:
            self.transport='batch_echo_v1'
            return self.transport,self.score_many(items)
        except Exception as batch_err:
            try:
                self.transport='scalar_echo_v1'
                return self.transport,self.score_many(items)
            except Exception as scalar_err:
                raise HardStop(f'no proxy transport works; batch={batch_err}; scalar={scalar_err}')

def source_hash(obj):
    return hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()

def vllm_process_evidence(proto: dict):
    try:
        txt=subprocess.check_output(['ps','-eo','pid,args'],text=True,errors='replace')
    except Exception as e:
        return {'found':False,'error':str(e)}
    proxy=proto['config']['models']['proxy']; model=proxy['repo']; rev=proxy['revision']
    candidates=[x.strip() for x in txt.splitlines() if model in x and 'vllm' in x.lower()]
    strict=[x for x in candidates if rev in x and '8100' in x]
    return {'found':bool(strict),'strict_matches':strict[:5],'candidate_matches':candidates[:10]}

def openrouter_client(project_root: Path,proto: dict):
    import openai
    cfg=proto['config']['models']['agent']; key=load_env_key(project_root,cfg['env_key'])
    if not key:
        raise HardStop('OPENROUTER_API_KEY missing')
    return openai.OpenAI(api_key=key,base_url=cfg['base_url'],max_retries=0,timeout=180)

def completion_meta(c):
    usage=getattr(c,'usage',None); extra=getattr(c,'model_extra',None) or {}
    return {'id':getattr(c,'id',None),'model':getattr(c,'model',None),'provider':extra.get('provider'),'system_fingerprint':getattr(c,'system_fingerprint',None),'usage':usage.model_dump() if hasattr(usage,'model_dump') else None}

class StrictOpenRouterLLM(BasePipelineElement):
    name='google/gemini-2.5-flash'
    def __init__(self,client,model,call_log: Path|None=None,max_attempts=4):
        self.client=client; self.model=model; self.name=model; self.call_log=call_log; self.max_attempts=max_attempts; self.n_calls=0
    def _create(self,messages,tools):
        from agentdojo.agent_pipeline.llms.openai_llm import _message_to_openai,_function_to_openai
        om=[_message_to_openai(m,self.model) for m in messages]; ot=[_function_to_openai(t) for t in tools]
        last=None
        for attempt in range(1,self.max_attempts+1):
            t0=time.perf_counter()
            try:
                kw={'model':self.model,'messages':om,'temperature':0}
                if ot:
                    kw.update({'tools':ot,'tool_choice':'auto'})
                c=self.client.chat.completions.create(**kw); self.n_calls+=1
                if not getattr(c,'choices',None):
                    raise RuntimeError('completion has no choices')
                if self.call_log:
                    append_jsonl(self.call_log,{'kind':'agent','attempt':attempt,'ok':True,'latency_s':time.perf_counter()-t0,**completion_meta(c)})
                return c
            except Exception as e:
                last=e
                if self.call_log:
                    append_jsonl(self.call_log,{'kind':'agent','attempt':attempt,'ok':False,'latency_s':time.perf_counter()-t0,'error':f'{type(e).__name__}: {e}'})
                if attempt<self.max_attempts:
                    time.sleep(min(2**attempt,12))
        raise last
    def query(self,query,runtime,env,messages=(),extra_args={}):
        from agentdojo.agent_pipeline.llms.openai_llm import _openai_to_assistant_message
        c=self._create(messages,list(runtime.functions.values()))
        out=_openai_to_assistant_message(c.choices[0].message)
        return query,runtime,env,[*messages,out],extra_args

def sanitizer_call(client,proto: dict,user_request: str,tool_name: str,untrusted_content: str,call_log: Path|None=None):
    cfg=proto['config']; system=cfg['detector']['sanitizer_system_prompt']; user=cfg['detector']['sanitizer_user_template'].format(user_request=user_request,tool_name=tool_name,untrusted_content=untrusted_content)
    last=None
    for attempt in range(1,5):
        t0=time.perf_counter()
        try:
            c=client.chat.completions.create(model=cfg['models']['sanitizer']['model_id'],temperature=0,messages=[{'role':'system','content':system},{'role':'user','content':user}])
            if not getattr(c,'choices',None):
                raise RuntimeError('sanitizer completion has no choices')
            text=c.choices[0].message.content or ''
            if not text.strip():
                raise RuntimeError('sanitizer returned empty text')
            meta=completion_meta(c)
            if call_log:
                append_jsonl(call_log,{'kind':'sanitizer','attempt':attempt,'ok':True,'latency_s':time.perf_counter()-t0,**meta})
            return text,time.perf_counter()-t0,meta
        except Exception as e:
            last=e
            if call_log:
                append_jsonl(call_log,{'kind':'sanitizer','attempt':attempt,'ok':False,'latency_s':time.perf_counter()-t0,'error':f'{type(e).__name__}: {e}'})
            if attempt<4:
                time.sleep(min(2**attempt,12))
    raise last

class CausalArmorLLM(BasePipelineElement):
    name='google/gemini-2.5-flash'
    def __init__(self,base_llm,scorer,client,proto,event_log: Path,call_log: Path):
        self.base=base_llm; self.scorer=scorer; self.client=client; self.proto=proto; self.event_log=event_log; self.call_log=call_log
        self.current=None; self.decision_index=0; self.episode_stats={}
    def begin_episode(self,episode_id,user_request):
        attempt_id=uuid.uuid4().hex
        self.current={'episode_id':episode_id,'user_request':user_request,'attempt_id':attempt_id}; self.decision_index=0
        self.episode_stats={'attempt_id':attempt_id,'privileged_decisions':0,'primary_flagged_decisions':0,'shadow_flagged_decisions':0,'interventions':0,'sanitizer_calls':0,'agent_calls_start':self.base.n_calls,'proxy_calls_start':self.scorer.http_calls}
    def end_episode(self):
        d=dict(self.episode_stats); d['agent_calls']=self.base.n_calls-d.pop('agent_calls_start'); d['proxy_http_calls']=self.scorer.http_calls-d.pop('proxy_calls_start'); return d
    def _score_action(self,base_messages,proposal,call):
        tool_idxs=[i for i,m in enumerate(base_messages) if m.get('role')=='tool']
        action=action_string(call); txt=get_text(proposal.get('content')).strip(); shadow=txt+'\n'+action if txt else action
        contexts=[context_serializer(base_messages),context_serializer(base_messages,ablate_user=True)]
        contexts += [context_serializer(base_messages,ablate_tool_message_index=i) for i in tool_idxs]
        items=[(p,action) for p in contexts]+[(p,shadow) for p in contexts]
        scored=self.scorer.score_many(items); n=len(contexts)
        def calc(rows,completion):
            base=rows[0]['sum_logprob']; nt=rows[0]['n_tokens']; du=base-rows[1]['sum_logprob']
            if nt<=0:
                raise HardStop('zero completion-token count')
            spans=[]
            for j,msg_idx in enumerate(tool_idxs):
                ds=base-rows[j+2]['sum_logprob']; m=base_messages[msg_idx]; tc=m.get('tool_call'); name=getattr(tc,'function','tool') if tc else 'tool'
                spans.append({'message_index':msg_idx,'tool_name':name,'delta_s':ds,'delta_s_norm':ds/nt,'flag':(ds/nt)>(du/nt)})
            return {'completion':completion,'n_tokens':nt,'base_logprob':base,'delta_u':du,'delta_u_norm':du/nt,'spans':spans,'flagged_message_indices':[x['message_index'] for x in spans if x['flag']]}
        return calc(scored[:n],action),calc(scored[n:],shadow)
    def query(self,query,runtime,env,messages=(),extra_args={}):
        base_messages=list(messages)
        _,_,_,with_prop,_=self.base.query(query,runtime,env,base_messages,extra_args)
        proposal=with_prop[-1]; calls=list(proposal.get('tool_calls') or []); pcalls=[c for c in calls if is_privileged(c.function,self.proto)]
        tool_idxs=[i for i,m in enumerate(base_messages) if m.get('role')=='tool']
        if not pcalls or not tool_idxs:
            return query,runtime,env,with_prop,extra_args
        self.decision_index+=1; self.episode_stats['privileged_decisions']+=1
        actions=[]; p_union=set(); s_union=set()
        for c in pcalls:
            p,s=self._score_action(base_messages,proposal,c); p_union.update(p['flagged_message_indices']); s_union.update(s['flagged_message_indices'])
            actions.append({'function':c.function,'action':action_string(c),'primary':p,'shadow':s})
        p_any=bool(p_union); s_any=bool(s_union)
        if p_any: self.episode_stats['primary_flagged_decisions']+=1
        if s_any: self.episode_stats['shadow_flagged_decisions']+=1
        event={'schema':'P0B3_DEFENSE_EVENT_V1','episode_id':self.current['episode_id'],'attempt_id':self.current['attempt_id'],'decision_index':self.decision_index,'n_tool_spans':len(tool_idxs),'n_privileged_calls':len(pcalls),'primary_any_flag':p_any,'shadow_any_flag':s_any,'primary_flagged_message_indices':sorted(p_union),'shadow_flagged_message_indices':sorted(s_union),'actions':actions,'intervened':False,'sanitizers':[]}
        if not p_any:
            append_jsonl(self.event_log,event)
            return query,runtime,env,with_prop,extra_args
        self.episode_stats['interventions']+=1
        mod=copy.deepcopy(base_messages); earliest=min(p_union)
        from agentdojo.types import text_content_block_from_string
        for idx in sorted(p_union):
            m=mod[idx]; tc=m.get('tool_call'); tool_name=getattr(tc,'function','tool') if tc else 'tool'; old=get_text(m.get('content'))
            clean,lat,meta=sanitizer_call(self.client,self.proto,self.current['user_request'],tool_name,old,self.call_log); self.episode_stats['sanitizer_calls']+=1
            m['content']=[text_content_block_from_string(clean)]
            event['sanitizers'].append({'message_index':idx,'tool_name':tool_name,'input_sha256':hashlib.sha256(old.encode()).hexdigest(),'output_sha256':hashlib.sha256(clean.encode()).hexdigest(),'latency_s':lat,'provider_meta':meta})
        for i in range(earliest+1,len(mod)):
            m=mod[i]
            if m.get('role')=='assistant' and get_text(m.get('content')).strip():
                m['content']=[text_content_block_from_string(self.proto['config']['detector']['cot_mask_placeholder'])]
        # Original proposal is never returned to AgentDojo; it cannot enter executed traces.
        _,_,_,regen,_=self.base.query(query,runtime,env,mod,extra_args)
        event['intervened']=True
        event['original_proposal']={'text':get_text(proposal.get('content')),'tool_calls':[action_string(c) for c in calls]}
        final=regen[-1]
        event['regenerated_proposal']={'text':get_text(final.get('content')),'tool_calls':[action_string(c) for c in (final.get('tool_calls') or [])]}
        append_jsonl(self.event_log,event)
        return query,runtime,env,regen,extra_args
