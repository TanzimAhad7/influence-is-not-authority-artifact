#!/usr/bin/env python3
from __future__ import annotations
from typing import Any

class _Params:
    def __init__(self, schema: dict[str,Any]): self._schema=schema
    def model_json_schema(self): return self._schema

class _Fn:
    def __init__(self, spec: dict[str,Any]):
        self.name=spec['name']; self.description=spec.get('description',''); self.parameters=_Params(spec['input_schema'])

class SyntheticRuntime:
    def __init__(self, tool_specs: list[dict[str,Any]]):
        self.functions={x['name']:_Fn(x) for x in tool_specs}
