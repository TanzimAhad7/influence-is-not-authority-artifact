import json
from collections.abc import Sequence
from typing import overload

import openai
from openai._types import NOT_GIVEN
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionReasoningEffort,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import FunctionDefinition
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_random_exponential

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, Function, FunctionCall, FunctionsRuntime
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    ChatSystemMessage,
    ChatToolResultMessage,
    ChatUserMessage,
    MessageContentBlock,
    get_text_content_as_str,
    text_content_block_from_string,
)


def _tool_call_to_openai(tool_call: FunctionCall) -> ChatCompletionMessageToolCallParam:
    if tool_call.id is None:
        raise ValueError("`tool_call.id` is required for OpenAI")
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        type="function",
        function={
            "name": tool_call.function,
            "arguments": json.dumps(tool_call.args),
        },
    )


_REASONING_MODELS = {"o1", "o3"}


def _is_reasoning_model(model_name: str) -> bool:
    return any(model in model_name for model in _REASONING_MODELS)


@overload
def _content_blocks_to_openai_content_blocks(
    message: ChatUserMessage | ChatSystemMessage,
) -> list[ChatCompletionContentPartTextParam]: ...


@overload
def _content_blocks_to_openai_content_blocks(
    message: ChatAssistantMessage | ChatToolResultMessage,
) -> list[ChatCompletionContentPartTextParam] | None: ...


def _content_blocks_to_openai_content_blocks(
    message: ChatUserMessage | ChatAssistantMessage | ChatSystemMessage | ChatToolResultMessage,
) -> list[ChatCompletionContentPartTextParam] | None:
    if message["content"] is None:
        return None
    return [ChatCompletionContentPartTextParam(type="text", text=el["content"] or "") for el in message["content"]]


def _message_to_openai(message: ChatMessage, model_name: str) -> ChatCompletionMessageParam:
    match message["role"]:
        case "system":
            return ChatCompletionDeveloperMessageParam(
                role="system", content=_content_blocks_to_openai_content_blocks(message)
            )
        case "user":
            return ChatCompletionUserMessageParam(
                role="user", content=_content_blocks_to_openai_content_blocks(message)
            )
        case "assistant":
            if message["tool_calls"] is not None and len(message["tool_calls"]) > 0:
                tool_calls = [_tool_call_to_openai(tool_call) for tool_call in message["tool_calls"]]
                return ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=_content_blocks_to_openai_content_blocks(message),
                    tool_calls=tool_calls,
                )
            return ChatCompletionAssistantMessageParam(
                role="assistant",
                content=_content_blocks_to_openai_content_blocks(message),
            )
        case "tool":
            if message["tool_call_id"] is None:
                raise ValueError("`tool_call_id` should be specified for OpenAI.")
            return ChatCompletionToolMessageParam(
                content=message["error"] or _content_blocks_to_openai_content_blocks(message),
                tool_call_id=message["tool_call_id"],
                role="tool",
                name=message["tool_call"].function,  # type: ignore -- this is actually used, and is important!
            )
        case _:
            raise ValueError(f"Invalid message type: {message}")


def _openai_to_tool_call(tool_call: ChatCompletionMessageToolCall) -> FunctionCall:
    return FunctionCall(
        function=tool_call.function.name,
        args=json.loads(tool_call.function.arguments),
        id=tool_call.id,
    )


def _assistant_message_to_content(message: ChatCompletionMessage) -> list[MessageContentBlock] | None:
    if message.content is None:
        return None
    return [text_content_block_from_string(message.content)]


def _openai_to_assistant_message(message: ChatCompletionMessage) -> ChatAssistantMessage:
    if message.tool_calls is not None:
        tool_calls = [_openai_to_tool_call(tool_call) for tool_call in message.tool_calls]
    else:
        tool_calls = None
    return ChatAssistantMessage(role="assistant", content=_assistant_message_to_content(message), tool_calls=tool_calls)


def _function_to_openai(f: Function) -> ChatCompletionToolParam:
    function_definition = FunctionDefinition(
        name=f.name,
        description=f.description,
        parameters=f.parameters.model_json_schema(),
    )
    return ChatCompletionToolParam(type="function", function=function_definition)


def _sanitize_schema_for_gemini(schema: dict) -> dict:
    """Resolve $ref from top-level $defs and drop $defs for Gemini compatibility."""
    if not isinstance(schema, dict):
        return schema

    schema = json.loads(json.dumps(schema))  # deep copy to avoid mutating originals
    defs = schema.pop("$defs", None)

    def _walk(node: dict):
        if not isinstance(node, dict):
            return
        if "$ref" in node and defs:
            ref = node.pop("$ref")
            ref_key = ref.split("/")[-1]
            if isinstance(defs, dict) and ref_key in defs:
                ref_schema = json.loads(json.dumps(defs[ref_key]))
                node.update(ref_schema)
        if "properties" in node and isinstance(node["properties"], dict):
            for value in node["properties"].values():
                _walk(value)
        if "items" in node:
            _walk(node["items"])
        for key in ("anyOf", "oneOf", "allOf"):
            if key in node and isinstance(node[key], list):
                for item in node[key]:
                    _walk(item)

    _walk(schema)
    return schema


@retry(
    wait=wait_random_exponential(multiplier=1, max=40),
    stop=stop_after_attempt(3),
    reraise=True,
    retry=retry_if_not_exception_type((openai.BadRequestError, openai.UnprocessableEntityError)),
)
def chat_completion_request(
    client: openai.OpenAI,
    model: str,
    messages: Sequence[ChatCompletionMessageParam],
    tools: Sequence[ChatCompletionToolParam],
    reasoning_effort: ChatCompletionReasoningEffort | None,
    top_p: float | None = None,
    temperature: float | None = 0.0,
    top_k: int | None = None,
    seed: int | None = None,
    logprobs: bool | None = None,
    top_logprobs: int | None = None,
):
    # Gemini endpoints reject JSON Schema extensions like $defs/$ref; normalize share_file only.
    if model.startswith("gemini") and tools:
        sanitized_tools: list[ChatCompletionToolParam | dict] = []
        for tool in tools:
            tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else dict(tool)
            function = tool_dict.get("function")
            if isinstance(function, dict) and function.get("name") == "share_file":
                if "parameters" in function:
                    function["parameters"] = _sanitize_schema_for_gemini(function["parameters"])
                sanitized_tools.append(tool_dict)
            else:
                sanitized_tools.append(tool)
        tools = sanitized_tools  # type: ignore[assignment]2
    # print(tools)
    # print("-------------------------------------")
    # exit(0)

    params = dict(
        model=model,
        messages=messages,
        tools=tools or NOT_GIVEN,
        tool_choice="auto" if tools else NOT_GIVEN,
        temperature=temperature,
        reasoning_effort=reasoning_effort or NOT_GIVEN,
        top_p=top_p if top_p is not None else NOT_GIVEN,
        seed=seed if seed is not None else NOT_GIVEN,
        logprobs=logprobs if logprobs is not None else NOT_GIVEN,
        top_logprobs=top_logprobs if top_logprobs is not None else NOT_GIVEN,
    )
    if top_k is not None:
        model_name = str(model)
        if "gemini" in model_name:
            params["extra_body"] = {"top_k": top_k}
        elif "gpt" in model_name:
            pass
        else:
            raise ValueError(f"top_k is only supported for gemini models; got model={model!r}")

    debug_params = dict(params)
    if "messages" in debug_params:
        debug_params["messages"] = "<omitted>"
    if "tools" in debug_params:
        debug_params["tools"] = "<omitted>"
    print("[debug] chat_completion_request params:")
    print(json.dumps(debug_params, ensure_ascii=True, indent=2, default=str))
    return client.chat.completions.create(**params)


class OpenAILLM(BasePipelineElement):
    """LLM pipeline element that uses OpenAI's API.

    Args:
        client: The OpenAI client.
        model: The model name.
        temperature: The temperature to use for generation.
    """

    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        reasoning_effort: ChatCompletionReasoningEffort | None = None,
        top_p: float | None = None,
        temperature: float | None = 0.0,
        top_k: int | None = None,
        seed: int | None = None,
        logprobs: bool | None = None,
        top_logprobs: int | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.top_p: float | None = top_p
        self.top_k: int | None = top_k
        self.seed: int | None = seed
        self.logprobs: bool | None = logprobs
        self.top_logprobs: int | None = top_logprobs
        self.reasoning_effort: ChatCompletionReasoningEffort | None = reasoning_effort

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        logprobs = extra_args.get("logprobs", self.logprobs) if isinstance(extra_args, dict) else self.logprobs
        top_logprobs = (
            extra_args.get("top_logprobs", self.top_logprobs) if isinstance(extra_args, dict) else self.top_logprobs
        )
        openai_messages = [_message_to_openai(message, self.model) for message in messages]
        openai_tools = [_function_to_openai(tool) for tool in runtime.functions.values()]
        completion = chat_completion_request(
            self.client,
            self.model,
            openai_messages,
            openai_tools,
            self.reasoning_effort,
            self.top_p,
            self.temperature,
            self.top_k,
            self.seed,
            logprobs,
            top_logprobs,
        )
        logprobs_data = getattr(completion.choices[0], "logprobs", None)
        if logprobs_data is not None:
            # surface logprobs to caller via extra_args without mutating input dict
            extra_args = {**extra_args, "logprobs": logprobs_data}
        output = _openai_to_assistant_message(completion.choices[0].message)
        messages = [*messages, output]
        return query, runtime, env, messages, extra_args


class OpenAILLMToolFilter(BasePipelineElement):
    def __init__(
        self,
        prompt: str,
        client: openai.OpenAI,
        model: str,
        temperature: float | None = 0.0,
        top_k: int | None = None,
        seed: int | None = None,
    ) -> None:
        self.prompt = prompt
        self.client = client
        self.model = model
        self.temperature = temperature
        self.top_k = top_k
        self.seed = seed

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        messages = [*messages, ChatUserMessage(role="user", content=[text_content_block_from_string(self.prompt)])]
        openai_messages = [_message_to_openai(message, self.model) for message in messages]
        openai_tools = [_function_to_openai(tool) for tool in runtime.functions.values()]
        params = dict(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools or NOT_GIVEN,
            tool_choice="none",
            temperature=self.temperature,
            seed=self.seed if self.seed is not None else NOT_GIVEN,
        )
        if self.top_k is not None:
            params["extra_body"] = {"top_k": self.top_k}
        completion = self.client.chat.completions.create(**params)
        output = _openai_to_assistant_message(completion.choices[0].message)

        new_tools = {}
        for tool_name, tool in runtime.functions.items():
            if output["content"] is not None and tool_name in get_text_content_as_str(output["content"]):
                new_tools[tool_name] = tool

        runtime.update_functions(new_tools)

        messages = [*messages, output]
        return query, runtime, env, messages, extra_args
