"""
Provider abstraction for LLM calls.
Supported: Anthropic (Claude), OpenAI, Google Gemini, Groq, Mistral, Ollama (local)
Each provider is called with the same prompt and returns the same dict shape.
"""

import json
import os
from typing import Dict, Any

# ── Provider registry ──────────────────────────────────────────────────────────

PROVIDERS: Dict[str, Dict] = {
    "Anthropic (Claude)": {
        "env_key":  "ANTHROPIC_API_KEY",
        "key_hint": "sk-ant-...",
        "models":   [
            "claude-sonnet-4-6",
            "claude-opus-4-7",
            "claude-haiku-4-5-20251001",
        ],
        "get_key_url": "https://console.anthropic.com/settings/keys",
    },
    "OpenAI": {
        "env_key":  "OPENAI_API_KEY",
        "key_hint": "sk-...",
        "models":   ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "get_key_url": "https://platform.openai.com/api-keys",
    },
    "Google Gemini": {
        "env_key":  "GOOGLE_API_KEY",
        "key_hint": "AIza...",
        "models":   ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "get_key_url": "https://aistudio.google.com/app/apikey",
    },
    "Groq": {
        "env_key":  "GROQ_API_KEY",
        "key_hint": "gsk_...",
        "models":   [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
        "get_key_url": "https://console.groq.com/keys",
    },
    "Mistral": {
        "env_key":  "MISTRAL_API_KEY",
        "key_hint": "...",
        "models":   [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
        ],
        "get_key_url": "https://console.mistral.ai/api-keys",
    },
    "NVIDIA NIM": {
        "env_key":     "NVIDIA_API_KEY",
        "key_hint":    "nvapi-...",
        "models": [
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-70b-instruct",
            "deepseek-ai/deepseek-r1",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "mistralai/mistral-large-2-instruct",
            "google/gemma-3-27b-it",
        ],
        "get_key_url": "https://build.nvidia.com/",
        "base_url":    "https://integrate.api.nvidia.com/v1",
    },
    "Ollama (Local)": {
        "env_key":     "",
        "key_hint":    "",
        "models":      ["qwen2.5:14b", "llama3.1:8b", "mistral:7b", "llama3.2:3b"],
        "get_key_url": "",
        "no_key":      True,
    },
}

# ── Shared JSON schema for structured output ───────────────────────────────────

RECOMMENDATION_SCHEMA: Dict = {
    "type": "object",
    "properties": {
        "action":             {"type": "string",  "enum": ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]},
        "confidence":         {"type": "integer", "minimum": 1, "maximum": 10},
        "target_price":       {"type": "number",  "description": "12-month price target in USD"},
        "stop_loss":          {"type": "number",  "description": "Recommended stop-loss in USD"},
        "time_horizon":       {"type": "string",  "description": "Ideal holding period e.g. '3-6 months'"},
        "risk_level":         {"type": "string",  "enum": ["LOW", "MEDIUM", "HIGH"]},
        "summary":            {"type": "string",  "description": "2-3 sentence executive summary"},
        "reasons_to_buy":     {"type": "array",   "items": {"type": "string"}},
        "reasons_to_sell":    {"type": "array",   "items": {"type": "string"}},
        "technical_outlook":  {"type": "string"},
        "fundamental_outlook":{"type": "string"},
        "news_impact":        {"type": "string"},
        "entry_strategy":     {"type": "string",  "description": "Suggested entry approach"},
    },
    "required": [
        "action", "confidence", "target_price", "stop_loss", "time_horizon",
        "risk_level", "summary", "reasons_to_buy", "reasons_to_sell",
        "technical_outlook", "fundamental_outlook", "entry_strategy",
    ],
}

_TOOL_DESCRIPTION = "Output a structured stock investment recommendation based on the provided analysis data."

# ── Provider-specific callers ──────────────────────────────────────────────────

def _call_anthropic(api_key: str, model: str, prompt: str) -> Dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        tools=[{
            "name":         "stock_recommendation",
            "description":  _TOOL_DESCRIPTION,
            "input_schema": RECOMMENDATION_SCHEMA,
        }],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "stock_recommendation":
            return block.input
    raise ValueError("Anthropic returned no tool-use block")


def _call_openai_compatible(
    api_key: str, model: str, prompt: str, base_url: str | None = None
) -> Dict:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        tools=[{
            "type": "function",
            "function": {
                "name":        "stock_recommendation",
                "description": _TOOL_DESCRIPTION,
                "parameters":  RECOMMENDATION_SCHEMA,
            },
        }],
        tool_choice={"type": "function", "function": {"name": "stock_recommendation"}},
        messages=[{"role": "user", "content": prompt}],
    )
    args = response.choices[0].message.tool_calls[0].function.arguments
    return json.loads(args)


def _call_gemini(api_key: str, model: str, prompt: str) -> Dict:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    schema_str = json.dumps(RECOMMENDATION_SCHEMA, indent=2)
    json_prompt = (
        prompt
        + f"\n\n---\nYou MUST respond with a single valid JSON object that strictly follows this schema:\n{schema_str}\n"
        + "Do not include any explanation, markdown, or extra text — only the JSON object."
    )

    model_obj = genai.GenerativeModel(
        model_name=model,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    response = model_obj.generate_content(json_prompt)
    text = response.text.strip()
    # Strip markdown fences if model adds them despite JSON mode
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _call_ollama(model: str, prompt: str) -> Dict:
    from openai import OpenAI

    client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
    schema_str = json.dumps(RECOMMENDATION_SCHEMA, indent=2)
    json_prompt = (
        prompt
        + f"\n\n---\nYou MUST respond with a single valid JSON object matching this schema exactly:\n{schema_str}\n"
        + "Return only the JSON object — no explanation, no markdown fences."
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": json_prompt}],
        response_format={"type": "json_object"},
        max_tokens=2048,
    )
    return json.loads(response.choices[0].message.content)


def _call_nvidia(api_key: str, model: str, prompt: str, schema: Dict | None = None) -> Dict:
    """
    NVIDIA NIM via OpenAI-compatible API.
    Uses JSON-mode with an inline schema prompt because tool_call support
    varies across NIM-hosted models.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
    )
    used_schema = schema if schema is not None else RECOMMENDATION_SCHEMA
    schema_str  = json.dumps(used_schema, indent=2)
    full_prompt = (
        prompt
        + f"\n\n---\nReturn ONLY a valid JSON object that strictly follows this schema:\n{schema_str}\n"
        + "No explanation, no markdown fences, no extra keys — only the JSON object."
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.6,
        top_p=0.95,
        max_tokens=4096,
    )
    text = response.choices[0].message.content.strip()
    # Strip markdown fences if the model adds them
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _call_mistral(api_key: str, model: str, prompt: str) -> Dict:
    from mistralai import Mistral

    client = Mistral(api_key=api_key)
    response = client.chat.complete(
        model=model,
        max_tokens=2048,
        tools=[{
            "type": "function",
            "function": {
                "name":        "stock_recommendation",
                "description": _TOOL_DESCRIPTION,
                "parameters":  RECOMMENDATION_SCHEMA,
            },
        }],
        tool_choice="any",
        messages=[{"role": "user", "content": prompt}],
    )
    args = response.choices[0].message.tool_calls[0].function.arguments
    return json.loads(args)


# ── Public dispatcher ──────────────────────────────────────────────────────────

def get_ollama_models() -> list:
    """Return models currently installed in the local Ollama instance."""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.ok:
            names = [m["name"] for m in r.json().get("models", [])]
            if names:
                return names
    except Exception:
        pass
    return PROVIDERS["Ollama (Local)"]["models"]


def call_llm(provider: str, api_key: str, model: str, prompt: str) -> Dict[str, Any]:
    """Route to the correct provider and return the structured recommendation dict."""
    if provider == "Ollama (Local)":
        return _call_ollama(model, prompt)

    if not api_key or not api_key.strip():
        raise ValueError("API key is required. Enter it in the sidebar.")

    if provider == "Anthropic (Claude)":
        return _call_anthropic(api_key, model, prompt)
    elif provider == "OpenAI":
        return _call_openai_compatible(api_key, model, prompt)
    elif provider == "Google Gemini":
        return _call_gemini(api_key, model, prompt)
    elif provider == "Groq":
        return _call_openai_compatible(api_key, model, prompt, base_url="https://api.groq.com/openai/v1")
    elif provider == "Mistral":
        return _call_mistral(api_key, model, prompt)
    elif provider == "NVIDIA NIM":
        return _call_nvidia(api_key, model, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider!r}")


def call_llm_schema(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    schema: Dict,
    tool_name: str = "structured_output",
    tool_description: str = "Return structured JSON output.",
) -> Dict[str, Any]:
    """Generic LLM caller with a caller-supplied JSON schema."""
    if provider == "Ollama (Local)":
        from openai import OpenAI
        client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
        schema_str = json.dumps(schema, indent=2)
        full_prompt = (
            prompt
            + f"\n\n---\nReturn ONLY a valid JSON object matching this schema exactly:\n{schema_str}\n"
            + "No explanation, no markdown fences."
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            response_format={"type": "json_object"},
            max_tokens=3000,
        )
        return json.loads(response.choices[0].message.content)

    if not api_key or not api_key.strip():
        raise ValueError("API key is required. Enter it in the sidebar.")

    if provider == "Anthropic (Claude)":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=3000,
            tools=[{"name": tool_name, "description": tool_description, "input_schema": schema}],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        raise ValueError("Anthropic returned no tool-use block")

    elif provider in ("OpenAI", "Groq"):
        from openai import OpenAI
        base_url = "https://api.groq.com/openai/v1" if provider == "Groq" else None
        client = OpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
        response = client.chat.completions.create(
            model=model,
            max_tokens=3000,
            tools=[{"type": "function", "function": {
                "name": tool_name, "description": tool_description, "parameters": schema,
            }}],
            tool_choice={"type": "function", "function": {"name": tool_name}},
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    elif provider == "Google Gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        schema_str = json.dumps(schema, indent=2)
        full_prompt = (
            prompt
            + f"\n\n---\nReturn ONLY a valid JSON object matching this schema:\n{schema_str}\n"
            + "No explanation or markdown."
        )
        model_obj = genai.GenerativeModel(
            model_name=model,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
        response = model_obj.generate_content(full_prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    elif provider == "Mistral":
        from mistralai import Mistral
        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model=model,
            max_tokens=3000,
            tools=[{"type": "function", "function": {
                "name": tool_name, "description": tool_description, "parameters": schema,
            }}],
            tool_choice="any",
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    elif provider == "NVIDIA NIM":
        return _call_nvidia(api_key, model, prompt, schema=schema)

    else:
        raise ValueError(f"Unknown provider: {provider!r}")


def env_key_for(provider: str) -> str:
    """Return the environment variable name that holds the API key for this provider."""
    return PROVIDERS.get(provider, {}).get("env_key", "")


def default_api_key(provider: str) -> str:
    """Load the API key from the environment (if set) for pre-filling the sidebar."""
    env_var = env_key_for(provider)
    return os.environ.get(env_var, "") if env_var else ""


def call_llm_chat(
    provider: str,
    api_key: str,
    model: str,
    messages: list,
    system: str = "",
) -> str:
    """
    Multi-turn chat call. `messages` is a list of {"role": "user"|"assistant", "content": str}.
    Returns the assistant reply as plain text.
    """
    if provider == "Ollama (Local)":
        from openai import OpenAI
        client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
        full_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        resp = client.chat.completions.create(
            model=model,
            messages=full_msgs,
            max_tokens=2048,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    if not api_key or not api_key.strip():
        raise ValueError("API key is required. Enter it in the sidebar.")

    if provider == "Anthropic (Claude)":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        kwargs = {"model": model, "max_tokens": 2048, "messages": messages}
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        return resp.content[0].text.strip()

    elif provider in ("OpenAI", "Groq"):
        from openai import OpenAI
        base_url = "https://api.groq.com/openai/v1" if provider == "Groq" else None
        client = OpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
        full_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        resp = client.chat.completions.create(
            model=model,
            messages=full_msgs,
            max_tokens=2048,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    elif provider == "Google Gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Convert to Gemini history format
        history = []
        for m in messages[:-1]:
            history.append({"role": "model" if m["role"] == "assistant" else "user",
                             "parts": [m["content"]]})
        system_prefix = (system + "\n\n") if system else ""
        model_obj = genai.GenerativeModel(model_name=model, system_instruction=system or None)
        chat = model_obj.start_chat(history=history)
        resp = chat.send_message(messages[-1]["content"])
        return resp.text.strip()

    elif provider == "Mistral":
        from mistralai import Mistral
        client = Mistral(api_key=api_key)
        full_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        resp = client.chat.complete(model=model, messages=full_msgs, max_tokens=2048)
        return resp.choices[0].message.content.strip()

    elif provider == "NVIDIA NIM":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")
        full_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        resp = client.chat.completions.create(
            model=model,
            messages=full_msgs,
            max_tokens=2048,
            temperature=0.6,
        )
        return resp.choices[0].message.content.strip()

    else:
        raise ValueError(f"Unknown provider: {provider!r}")
