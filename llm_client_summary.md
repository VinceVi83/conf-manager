# Analysis of `llm_client.py`

## Overview

`llm_client.py` is a Python client layer designed to centralize calls to a large language model (LLM). It exposes a common interface, primarily `llm_call(system_prompt, user_prompt, model=None, options=None)`, while being able to route requests to two infrastructures:

1. **LLMGateway**: a remote HTTP server, potentially woken on demand via Wake-on-LAN (WOL);
2. **Ollama**: a local instance and, optionally, a WAN-accessible instance, with automatic selection based on availability.

The module normalizes responses to Python dictionaries and provides both synchronous and asynchronous variants. It relies on the global configuration imported from `config.conf_manager` (`cfg`).

> **Important note on the three requested modes**: the file does not declare any class, function or constant named `instruct`, `summarizer` or `creative`. These modes are therefore not technical modes implemented by this module. They can be obtained by calling the same interface with different system/user prompts and options, but the file does not provide predefined profiles or specific validation for them.

## Architecture

### 1. Normalization of prompts and configuration

`LLMRequest` encapsulates a request:

- chooses the explicit model provided by the caller, otherwise `cfg.llm.default_model`;
- stores Ollama options in a dictionary;
- converts prompts into messages compatible with the chat API:
  - `system` message for behavior instructions;
  - `user` message for the user request.

`get_payload()` produces an object of the form:

```python
{
    "model": "model-name",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "options": {"temperature": 0.7}
}
```

### 2. Processing results

The `_process_llm_result()` pipeline:

1. retrieves `response.message.content`;
2. removes surrounding spaces;
3. looks for the first `{` character and the last `}`;
4. attempts to parse the portion between these two characters as JSON;
5. if the JSON is a dictionary, returns its keys converted to lowercase strings;
6. otherwise returns `{"content": raw_content}`.

This strategy allows retrieving a JSON object even if the model surrounds it with an explanation, but it remains deliberately simple: it does not correctly handle all nested JSON, complex Markdown blocks, or root JSON responses that are not objects.

### 3. Direct access to Ollama

`OllamaService` is the synchronous client. It receives a LAN URL and optionally a WAN URL. A daemon thread executes `_monitor_loop()` and periodically checks `/api/version`:

- WAN availability: every 10 minutes when everything is fine;
- accelerated monitoring at 1 minute if LAN or WAN is unavailable;
- `is_ready` indicates LAN status;
- `wan_available` indicates WAN status.

`generate()` chooses WAN when it is available and a WAN client exists; otherwise it uses LAN. If no model is defined in the request, it tries to use `default_model_wan` or `default_model_lan`. In case of WAN failure, it retries with `fallback_model_wan`, but only on the WAN client. A LAN error is propagated to the caller.

`OllamaServiceAsync` uses `AsyncClient` and provides the same call idea asynchronously. Exceptions are transformed into dictionaries containing `content` and `error`, unlike the synchronous Ollama path which can re-raise the exception after failure.

### 4. Access via LLMGateway and machine wake-up

`LLMGatewayClient` encapsulates an HTTP API exposing notably:

- `POST /call-llm` to execute the call;
- `POST /wol-ack` to notify wakeup;
- a dedicated TCP port to know if the server is reachable.

Before the call, `_tcp_check()` attempts a TCP connection. If it fails:

1. `_send_wol()` builds and broadcasts a magic WOL packet to the broadcast address on UDP port 9;
2. `_wait_for_wakeup()` waits up to 60 seconds, checking the TCP port every second;
3. `_notify_wol_success()` calls `/wol-ack`;
4. the LLM request is sent with `generate()`.

The HTTP payload translates the two chat messages into `system_prompt` and `prompt`, then transmits the model and options. The expected response is a JSON containing `result`, which is returned in the form `{"content": ...}` without passing through `_process_llm_result()`.

`LLMGatewayClientAsync` reuses the synchronous client in a thread via `asyncio.to_thread()`. It thus maintains an asynchronous API without implementing a separate asynchronous HTTP client.

### 5. Initialization and backend selection

`init_llm_service(cfg)` first tries to build:

- a `LLMGatewayClient`;
- a `LLMGatewayClientAsync`;
- the gateway base URL.

In case of exception, it falls back to `OllamaService` and `OllamaServiceAsync`. The module then immediately initializes the global variables:

```python
llm, llm_async, base_url = init_llm_service(cfg)
```

## The three usage modes

Once again, the code does not implement them as a named feature. They correspond to three **application prompt profiles** that can all use `llm.llm_call()` or `await llm_async.llm_call()`.

### Mode `instruct`

Objective: obtain a precise response that executes an instruction.

- The system prompt defines the role, constraints and expected format.
- The user prompt describes the action to perform.
- A low temperature is generally suitable to promote stability, but this value is not imposed by the file.

Conceptual example:

```python
result = llm.llm_call(
    system_prompt="You are a technical assistant. Respond with numbered steps.",
    user_prompt="Explain how to test this function.",
    options={"temperature": 0.2}
)
```

### Mode `summarizer`

Objective: condense a text while preserving important information.

The behavior depends entirely on the prompt: the module does not truncate text, count tokens, or verify the faithfulness of the summary. It is recommended to specify length, audience, language and output structure.

```python
result = llm.llm_call(
    system_prompt="You are a faithful summarizer. Do not add any information not present in the text.",
    user_prompt="Summarize the following text in five points:\n\n" + text,
    options={"temperature": 0.2}
)
```

### Mode `creative`

Objective: produce variants, ideas or stylistically freer text.

The prompt can define tone, audience, forbidden elements and number of proposals. A higher temperature can be requested via `options`, but the module does not set a specific default value for this mode.

```python
result = llm.llm_call(
    system_prompt="You are a creative writer. Propose three distinct, concrete and memorable concepts.",
    user_prompt="Imagine a campaign for an ecological product.",
    options={"temperature": 0.9}
)
```

For a maintainable application, these profiles should be added in a separate module, for example as functions `call_instruct`, `call_summarizer` and `call_creative`, in order to centralize their prompts and options without mixing product policy with LLM transport.

## Use in a project

### Prerequisites

The project must provide the following dependencies and configuration elements:

- the Python package `ollama`;
- `requests`;
- `config.conf_manager` with a `cfg` object containing at least the LLM or gateway parameters used;
- an Ollama server or a reachable LLMGateway;
- for WOL: a valid MAC address, allowed network broadcast and an accessible TCP wake-up port.

The expected configuration varies depending on the path used. The gateway uses notably `cfg.llm_gateway.server_ip`, `port`, `server_mac`, `wakeup_port` and `default_model`. The Ollama fallback looks for `cfg.llm.lan_url.local_url`, possibly `cfg.llm.wan_url.wan_url`, as well as model names such as `default_model_lan`, `default_model_wan` and `fallback_model_wan`.

### Synchronous call

```python
from llm_client import llm

result = llm.llm_call(
    system_prompt="You are a concise assistant.",
    user_prompt="Give three benefits of unit tests.",
    model="qwen2.5:7b",       # optional
    options={"temperature": 0.4}  # optional
)

print(result.get("content"))
```

The result can also be a dictionary from the JSON generated by the model, with keys normalized to lowercase. Therefore, both a structured response and a response containing only `content` must be processed.

### Asynchronous call

```python
from llm_client import llm_async

result = await llm_async.llm_call(
    system_prompt="You are a synthesis assistant.",
    user_prompt="Summarize this document..."
)
```

In an asynchronous application, this form avoids blocking the loop when using the asynchronous Ollama client. For the gateway, the implementation still defers the synchronous call to a thread.

### Recommended integration

- Import the client behind an application layer rather than scattering prompts throughout the application.
- Check for the presence of `error` before using the result.
- Define timeouts, size limits and retry policies at the product level.
- Use prompts requesting strict JSON if the application depends on a structure, then validate this JSON with a schema.
- Avoid making test calls or network calls when importing the module.

## Main design decisions

1. **Uniform interface**: backends share `generate()` and `llm_call()`, which allows replacing the transport without changing the callers.
2. **Automatic degradation**: gateway is prioritized, then Ollama serves as a fallback.
3. **LAN/WAN routing**: availability is monitored in the background rather than tested on each request.
4. **On-demand wake-up**: WOL avoids keeping the remote LLM machine powered on permanently.
5. **Sync/async support**: consumers can choose according to their execution architecture.
6. **Options pass-through**: generation parameters are passed to the Ollama client without imposing a catalog of options.
7. **Tolerance for unstructured outputs**: a JSON response is extracted when possible, otherwise raw text is preserved.
8. **External configuration**: URLs and models are centralized in `cfg`, rather than hardcoded in business calls.

## Points of vigilance and observed limits

- **Side effects on import**: after the class definitions, the module makes a `GET {base_url}/models` request, executes `test_llm_call()` and launches `asyncio.run(test_llm_call_async())`. Importing this file therefore triggers network calls and LLM generations. These lines should be placed under `if __name__ == "__main__":` or removed from library modules.
- **Unconditional test calls**: the `/models` request and its `r.json()` can fail before the calling application can handle the error.
- **Monitoring thread stop**: `_interrupt_monitor` is created and waited, but the loop is `while True` and no public method signals the stop. The daemon thread only disappears with the process.
- **Likely bug in Ollama model choice**: `LLMRequest.__init__` already fills `self.model` with `cfg.llm.default_model`. The test `if not payload['model']` will therefore generally be false; the dedicated LAN/WAN values will not be chosen if the global default model is defined.
- **Incomplete WAN fallback**: if the first WAN call fails, the second call with `fallback_model_wan` is not protected by a second `try/except` and can raise an exception.
- **Heterogeneous error handling**: the gateway and async Ollama service return error dictionaries, while the sync Ollama service can raise the exception on the LAN side.
- **Fragile JSON normalization**: extraction by first brace and last brace can select an invalid substring or the wrong object. JSON content is not validated by schema.
- **Implicit dependency on Ollama responses**: `_process_llm_result()` assumes the presence of `response.message.content`, which ties the code to the Ollama SDK response form.
- **Two `json` imports**: the import is duplicated; this does not affect behavior, but indicates possible cleanup.
- **Potentially sensitive logging**: `logger.debug(response)` and some logs may expose prompts or responses; log level and confidentiality must be controlled.
- **Network security**: the code uses HTTP and broadcasts WOL packet; no authentication, TLS encryption or certificate validation is handled in this file. Protections must be ensured by the network or the gateway.
- **Async gateway not fully native**: `asyncio.to_thread()` avoids blocking the loop, but consumes a thread and does not make HTTP truly asynchronous.
- **Potentially inconsistent configuration**: `init_llm_service` receives a `cfg` parameter but the classes and `LLMRequest` also read the global `cfg` imported. This makes testing and configuration injection less predictable.

## Conclusion

The file is a relatively complete LLM transport adapter: it unifies local/WAN Ollama and a WOL-wakeable gateway, offers synchronous and asynchronous APIs, and provides minimal response normalization. However, `instruct`, `summarizer` and `creative` modes are not coded as distinct features: today they depend on how the caller builds its prompts and options. Before using as a production library, priority should be to remove calls executed on import, clarify configuration injection, harmonize errors and make model selection and JSON parsing more reliable.

