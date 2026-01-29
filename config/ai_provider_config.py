"""
AI Provider Configuration
Contains base URLs and default models for various AI providers
"""

AI_PROVIDERS_CONFIG = {
    "openai": {
        "name": "🔴 OpenAI",
        "base_url": "https://api.openai.com/v1",
        "description": "OpenAI's GPT models (GPT-4, GPT-3.5-turbo, etc.)",
        "default_models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "api_key_format": "sk-*",
        "docs_url": "https://platform.openai.com/api-keys",
        "requires_load": True  # Needs to fetch models from API
    },
    "google": {
        "name": "🔵 Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "description": "Google's Generative AI (Gemini models)",
        "default_models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "api_key_format": "AIza*",
        "docs_url": "https://aistudio.google.com/app/apikey",
        "requires_load": False  # Known models, no need to fetch
    },
    "groq": {
        "name": "⚡ Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "description": "Groq's fast inference API",
        "default_models": ["mixtral-8x7b-32768", "llama2-70b-4096", "gemma-7b-it"],
        "api_key_format": "gsk-*",
        "docs_url": "https://console.groq.com/keys",
        "requires_load": True
    },
    "anthropic": {
        "name": "🤖 Anthropic Claude",
        "base_url": "https://api.anthropic.com",
        "description": "Anthropic's Claude models",
        "default_models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
        "api_key_format": "sk-ant-*",
        "docs_url": "https://console.anthropic.com/",
        "requires_load": False
    },
    "cohere": {
        "name": "🟢 Cohere",
        "base_url": "https://api.cohere.ai",
        "description": "Cohere's Command models",
        "default_models": ["command-r-plus", "command-r", "command"],
        "api_key_format": "*",
        "docs_url": "https://dashboard.cohere.com/api-keys",
        "requires_load": False
    },
    "mistral": {
        "name": "🟠 Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "description": "Mistral's open-source models",
        "default_models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
        "api_key_format": "*",
        "docs_url": "https://console.mistral.ai/api-keys/",
        "requires_load": True
    },
    "huggingface": {
        "name": "🤗 HuggingFace",
        "base_url": "https://api-inference.huggingface.co/models",
        "description": "HuggingFace inference API",
        "default_models": ["meta-llama/Llama-2-70b-chat-hf", "mistralai/Mistral-7B-Instruct-v0.1"],
        "api_key_format": "hf_*",
        "docs_url": "https://huggingface.co/settings/tokens",
        "requires_load": False
    },
    "together": {
        "name": "🔗 Together AI",
        "base_url": "https://api.together.xyz/v1",
        "description": "Together AI inference service",
        "default_models": ["meta-llama/Llama-2-70b-chat-hf", "mistralai/Mistral-7B-Instruct-v0.2"],
        "api_key_format": "*",
        "docs_url": "https://www.together.ai/settings/api-keys",
        "requires_load": True
    },
    "replicate": {
        "name": "🔴 Replicate",
        "base_url": "https://api.replicate.com/v1",
        "description": "Replicate API for various models",
        "default_models": ["meta/llama-2-70b-chat", "mistral-community/mistral-7b-instruct-v0.2"],
        "api_key_format": "*",
        "docs_url": "https://replicate.com/account/api-tokens",
        "requires_load": False
    },
    "custom": {
        "name": "⚙️ Custom/Local",
        "base_url": "http://localhost:8000/v1",
        "description": "Custom OpenAI-compatible endpoint (vLLM, Ollama, etc.)",
        "default_models": ["custom-model", "llama-2", "mistral"],
        "api_key_format": "optional",
        "docs_url": "https://github.com/vllm-project/vllm",
        "requires_load": False
    }
}

# Models for specific use cases
SPECIALIZED_MODELS = {
    "highlight_finder": {
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "google": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        "groq": ["mixtral-8x7b-32768", "llama2-70b-4096"],
        "anthropic": ["claude-3-5-sonnet-20241022"],
        "cohere": ["command-r-plus", "command-r"],
        "mistral": ["mistral-large-latest"],
    },
    "caption_maker": {
        "openai": ["whisper-1"],  # Special case for whisper
        "google": [],  # Gemini doesn't have whisper equivalent
        "groq": [],
    },
    "hook_maker": {
        "openai": ["tts-1-hd", "tts-1"],  # TTS models
        "google": [],  # Gemini doesn't have TTS built-in
        "anthropic": [],
    },
    "youtube_title_maker": {
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "google": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        "groq": ["mixtral-8x7b-32768"],
        "anthropic": ["claude-3-5-sonnet-20241022"],
    }
}


def get_provider_name(provider_key: str) -> str:
    """Get display name for provider"""
    return AI_PROVIDERS_CONFIG.get(provider_key, {}).get("name", provider_key)


def get_provider_base_url(provider_key: str) -> str:
    """Get base URL for provider"""
    return AI_PROVIDERS_CONFIG.get(provider_key, {}).get("base_url", "")


def get_provider_default_models(provider_key: str) -> list:
    """Get default models for provider"""
    return AI_PROVIDERS_CONFIG.get(provider_key, {}).get("default_models", [])


def get_all_providers() -> list:
    """Get list of all available providers"""
    return list(AI_PROVIDERS_CONFIG.keys())


def get_provider_display_list() -> list:
    """Get list of providers with display names for dropdown"""
    return [
        (AI_PROVIDERS_CONFIG[key]["name"], key)
        for key in sorted(AI_PROVIDERS_CONFIG.keys())
    ]


def requires_model_load(provider_key: str) -> bool:
    """Check if provider requires loading models from API"""
    return AI_PROVIDERS_CONFIG.get(provider_key, {}).get("requires_load", False)


def get_provider_description(provider_key: str) -> str:
    """Get description for provider"""
    return AI_PROVIDERS_CONFIG.get(provider_key, {}).get("description", "")


def get_provider_docs_url(provider_key: str) -> str:
    """Get documentation URL for provider"""
    return AI_PROVIDERS_CONFIG.get(provider_key, {}).get("docs_url", "")


def get_specialized_models(task: str, provider_key: str) -> list:
    """Get specialized models for a specific task and provider"""
    return SPECIALIZED_MODELS.get(task, {}).get(provider_key, [])
