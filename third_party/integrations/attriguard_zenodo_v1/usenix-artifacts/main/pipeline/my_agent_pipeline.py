# my_agent_pipeline.py

import importlib.resources
import json
import logging
import os
from collections.abc import Iterable, Sequence
from functools import partial
from typing import Literal

import anthropic
import cohere
import openai
import requests
import yaml
from google import genai
from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import Self

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
from agentdojo.agent_pipeline.llms.anthropic_llm import AnthropicLLM
from agentdojo.agent_pipeline.llms.cohere_llm import CohereLLM
from agentdojo.agent_pipeline.llms.google_llm import GoogleLLM
from agentdojo.agent_pipeline.tool_execution import (
    ToolsExecutionLoop,
    ToolsExecutor,
    tool_result_to_str,
)
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.logging import Logger
from agentdojo.models import MODEL_PROVIDERS, ModelsEnum
from agentdojo.types import ChatMessage

from AttriGuard import AttriGuardExecutionLoop
from local_llm_compat import LocalLLM
from openai_llm_compat import OpenAILLM


DEFENSES = [
    "attriguard"
]
"""Available defenses."""

def load_system_message(system_message_name: str | None) -> str:
    package_files = importlib.resources.files("agentdojo")
    path = package_files / "data" / "system_messages.yaml"
    with importlib.resources.as_file(path) as p, p.open() as f:
        system_messages = yaml.safe_load(f)
    message = system_messages.get(system_message_name, system_messages["default"])
    return (
        message
        + " At each execution step, you must issue all tool calls whose required inputs are already available. Even if a logical order exists, tool calls must not be postponed to later steps unless they require outputs from other tools."
    )


def _get_local_model_id(port) -> str:
    url = f"http://localhost:{port}/v1/models"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    model_name = data["data"][0]["id"]
    logging.info(f"Using model: {model_name}")
    return model_name


def _get_model_provider(model: str) -> str:
    try:
        return MODEL_PROVIDERS[ModelsEnum(model)]
    except ValueError:
        if model.startswith(("gpt-", "o")):
            return "openai"
        if model.startswith("claude-"):
            return "anthropic"
        if model.startswith("gemini-"):
            return "google"
        raise ValueError(f"Unsupported model: {model}") from None


def get_llm(provider: str, model: str, model_id: str | None, tool_delimiter: str) -> BasePipelineElement:
    if provider == "openai":
        client = openai.OpenAI()
        llm = OpenAILLM(client, model)
    elif provider == "anthropic":
        client = anthropic.Anthropic()
        if "-thinking-" in model:
            elements = model.split("-thinking-")
            if len(elements) != 2:
                raise ValueError("Invalid Thinking Model Name %s", model)
            thinking_budget = int(elements[1])
            model = elements[0]
            llm = AnthropicLLM(client, model, thinking_budget_tokens=thinking_budget)
        else:
            llm = AnthropicLLM(client, model)

    elif provider == "together":
        client = openai.OpenAI(
            api_key=os.getenv("TOGETHER_API_KEY"),
            base_url="https://api.together.xyz/v1",
        )
        llm = OpenAILLM(client, model)
    elif provider == "together-prompting":
        client = openai.OpenAI(
            api_key=os.getenv("TOGETHER_API_KEY"),
            base_url="https://api.together.xyz/v1",
        )
        llm = OpenAILLM(client, model)
    elif provider == "cohere":
        client = cohere.Client()
        llm = CohereLLM(client, model)
    elif provider == "google":
        client = genai.Client(vertexai=True, project=os.getenv("GCP_PROJECT"), location=os.getenv("GCP_LOCATION"))
        llm = GoogleLLM(model, client)
    elif provider == "local":
        port = os.getenv("LOCAL_LLM_PORT", 8000)
        if model_id == "qwen3_32b_local":
            port = 8001
        elif model_id == "meta_llama_3_8b_instruct_local":
            port = 8011
        print(f"Port to {port}")

        client = openai.OpenAI(
            api_key="EMPTY",
            base_url=f"http://localhost:{port}/v1",
        )
        if model_id is None:
            model_id = _get_local_model_id(port)
        logging.info(f"Using local model: {model_id}")
        logging.info(f"Using tool delimiter: {tool_delimiter}")
        if model_id.startswith("llama_3.3_70b_instruct") or model_id.startswith("meta_llama_3_8b_instruct"):
            llm = LocalLLM(client, model_id, temperature=0.0, top_p=1.0, tool_delimiter=tool_delimiter)
        elif model_id.startswith("qwen3_32b"):
            llm = LocalLLM(client, model_id, reasoning_effort="medium", temperature=0.0, top_p=1.0, tool_delimiter=tool_delimiter)
        else:
            raise ValueError(f"Unsupported local model_id: {model_id}")
    elif provider == "vllm_parsed":
        port = os.getenv("LOCAL_LLM_PORT", 8000)
        client = openai.OpenAI(
            api_key="EMPTY",
            base_url=f"http://localhost:{port}/v1",
        )
        llm = OpenAILLM(client, _get_local_model_id(port))
    else:
        raise ValueError("Invalid provider")
    return llm


def _get_attriguard_aux_llms(tool_delimiter: str) -> tuple[BasePipelineElement, BasePipelineElement]:
    backend = os.getenv("ATTRIGUARD_BACKEND", "openai").lower()
    model_id = os.getenv("ATTRIGUARD_MODEL_ID", "gpt-4.1-mini")
    judge_model_id = os.getenv("ATTRIGUARD_JUDGE_MODEL_ID", model_id)

    if backend == "openai":
        api_key = os.getenv("ATTRIGUARD_API_KEY")
        client = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
        attenuation_llm = OpenAILLM(client, model_id, temperature=0.2, top_p=0.9)
        judge_llm = OpenAILLM(client, judge_model_id, temperature=0.2, top_p=0.9)
        return attenuation_llm, judge_llm

    if backend == "local":
        port = os.getenv("ATTRIGUARD_LOCAL_PORT", "8001")
        judge_port = os.getenv("ATTRIGUARD_LOCAL_JUDGE_PORT", port)
        client = openai.OpenAI(api_key="EMPTY", base_url=f"http://localhost:{port}/v1")
        judge_client = openai.OpenAI(api_key="EMPTY", base_url=f"http://localhost:{judge_port}/v1")
        attenuation_llm = LocalLLM(
            client,
            model_id,
            reasoning_effort="medium" if model_id.startswith("qwen3") else None,
            temperature=0.2,
            top_p=0.9,
            tool_delimiter=tool_delimiter,
        )
        judge_llm = LocalLLM(
            judge_client,
            judge_model_id,
            reasoning_effort="medium" if judge_model_id.startswith("qwen3") else None,
            temperature=0.2,
            top_p=0.9,
            tool_delimiter=tool_delimiter,
        )
        return attenuation_llm, judge_llm

    raise ValueError("ATTRIGUARD_BACKEND must be either 'openai' or 'local'")


class PipelineConfig(BaseModel):
    # to allow union type between str and BasePipelineElement
    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm: str | BasePipelineElement
    model_id: str | None
    defense: str | None
    tool_delimiter: str = "tool"
    system_message_name: str | None
    system_message: str | None
    tool_output_format: Literal["yaml", "json"] | None = None
    attack: str | None = None
    suite_name: str | None = None

    @model_validator(mode="after")
    def validate_system_message(self) -> Self:
        if self.system_message is not None:
            return self
        self.system_message = load_system_message(self.system_message_name)
        return self


class AgentPipeline(BasePipelineElement):
    """Executes a sequence of BasePipelineElements in order."""

    def __init__(self, elements: Iterable[BasePipelineElement]) -> None:
        self.elements = elements
        self.name: str | None = None

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        logger = Logger().get()

        for element in self.elements:
            query, runtime, env, messages, extra_args = element.query(query, runtime, env, messages, extra_args)
            logger.log(messages)

        return query, runtime, env, messages, extra_args

    @classmethod
    def from_config(cls, config: PipelineConfig) -> Self:
        """Creates a pipeline for a given model and defense."""
        llm = (
            get_llm(_get_model_provider(config.llm), config.llm, config.model_id, config.tool_delimiter)
            if isinstance(config.llm, str)
            else config.llm
        )
        llm_name = config.llm if isinstance(config.llm, str) else getattr(llm, "name", None)

        assert config.system_message is not None
        system_message_component = SystemMessage(config.system_message)
        init_query_component = InitQuery()

        if config.tool_output_format == "json":
            tool_output_formatter = partial(tool_result_to_str, dump_fn=json.dumps)
        else:
            tool_output_formatter = tool_result_to_str

        if config.defense is None:
            tools_loop = ToolsExecutionLoop([ToolsExecutor(tool_output_formatter), llm])
            pipeline = cls([system_message_component, init_query_component, llm, tools_loop])
            pipeline.name = f"{llm_name}-{config.model_id}-nodefense"
            return pipeline

        if config.defense == "attriguard":
            attenuation_llm, judge_llm = _get_attriguard_aux_llms(config.tool_delimiter)
            attenuation_level = int(os.getenv("ATTRIGUARD_LEVEL", "2"))
            survival_mode = os.getenv("ATTRIGUARD_SURVIVAL", "fuzzy")
            skip_empty_tool_results_audit = bool(int(os.getenv("ATTRIGUARD_SKIP_EMPTY_AUDIT", "1")))

            tools_loop = AttriGuardExecutionLoop(
                llm,
                tool_output_formatter=tool_output_formatter,
                judge_llm=judge_llm,
                attenuation_llm=attenuation_llm,
                attenuation_level=attenuation_level,
                survival_mode=survival_mode,
                skip_empty_tool_results_audit=skip_empty_tool_results_audit,
                debug=bool(int(os.getenv("ATTRIGUARD_DEBUG", "1"))),
            )
            pipeline = cls([system_message_component, init_query_component, llm, tools_loop])
            pipeline.name = f"{llm_name}-{config.model_id}-{config.defense}"
            return pipeline

        raise ValueError(f"Unsupported defense: {config.defense}")
