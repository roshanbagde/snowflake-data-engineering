"""
Provider abstraction for LLM text generation.
Returns raw Markdown text — no JSON schema enforcement needed for notes.
Supported: Anthropic (Claude), OpenAI, Google Gemini, Groq, Mistral, NVIDIA NIM, Ollama (local)
"""

import os
import requests
from typing import Dict

# ── Provider registry ──────────────────────────────────────────────────────────

PROVIDERS: Dict[str, Dict] = {
    "Anthropic (Claude)": {
        "env_key":  "ANTHROPIC_API_KEY",
        "key_hint": "sk-ant-...",
        "models": [
            "claude-sonnet-4-6",
            "claude-opus-4-7",
            "claude-haiku-4-5-20251001",
        ],
        "get_key_url": "https://console.anthropic.com/settings/keys",
        "max_output": 4096,
    },
    "OpenAI": {
        "env_key":  "OPENAI_API_KEY",
        "key_hint": "sk-...",
        "models":   ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "get_key_url": "https://platform.openai.com/api-keys",
        "max_output": 4096,
    },
    "Google Gemini": {
        "env_key":  "GOOGLE_API_KEY",
        "key_hint": "AIza...",
        "models":   ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "get_key_url": "https://aistudio.google.com/app/apikey",
        "max_output": 8192,
    },
    "Groq": {
        "env_key":  "GROQ_API_KEY",
        "key_hint": "gsk_...",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
        "get_key_url": "https://console.groq.com/keys",
        "max_output": 4096,
    },
    "Mistral": {
        "env_key":  "MISTRAL_API_KEY",
        "key_hint": "...",
        "models": [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
        ],
        "get_key_url": "https://console.mistral.ai/api-keys",
        "max_output": 4096,
    },
    "NVIDIA NIM": {
        "env_key":     "NVIDIA_API_KEY",
        "key_hint":    "nvapi-...",
        "models": [
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-70b-instruct",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "deepseek-ai/deepseek-r1",
            "mistralai/mistral-large-2-instruct",
            "google/gemma-3-27b-it",
            "deepseek-ai/deepseek-v4-pro"
        ],
        "get_key_url": "https://build.nvidia.com/",
        "base_url":    "https://integrate.api.nvidia.com/v1",
        "max_output": 4096,
    },
    "Ollama (Local)": {
        "env_key":     "",
        "key_hint":    "",
        "models":      ["qwen2.5:14b", "llama3.1:8b", "mistral:7b", "llama3.2:3b","gpt-oss"],
        "get_key_url": "",
        "no_key":      True,
        "max_output": 4096,
    },
}


def get_ollama_models() -> list:
    """Return models currently installed in the local Ollama instance."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.ok:
            names = [m["name"] for m in r.json().get("models", [])]
            if names:
                return names
    except Exception:
        pass
    return PROVIDERS["Ollama (Local)"]["models"]


def env_key_for(provider: str) -> str:
    return PROVIDERS.get(provider, {}).get("env_key", "")


def default_api_key(provider: str) -> str:
    env_var = env_key_for(provider)
    return os.environ.get(env_var, "") if env_var else ""


# ── Text generation callers ────────────────────────────────────────────────────

def call_llm_text(
    provider: str,
    api_key:  str,
    model:    str,
    prompt:   str,
    max_tokens: int = 4096,
) -> str:
    """
    Call the selected provider and return raw text (Markdown).
    No JSON schema — ideal for note generation.
    """
    if provider == "Ollama (Local)":
        from openai import OpenAI
        client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    if not api_key or not api_key.strip():
        raise ValueError("API key is required. Enter it in the sidebar.")

    if provider == "Anthropic (Claude)":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    elif provider == "OpenAI":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    elif provider == "Google Gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(
            model_name=model,
            generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
        )
        resp = model_obj.generate_content(prompt)
        return resp.text.strip()

    elif provider == "Groq":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        resp = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    elif provider == "Mistral":
        from mistralai import Mistral
        client = Mistral(api_key=api_key)
        resp = client.chat.complete(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    elif provider == "NVIDIA NIM":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")
        resp = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            temperature=0.6, top_p=0.95,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    else:
        raise ValueError(f"Unknown provider: {provider!r}")
