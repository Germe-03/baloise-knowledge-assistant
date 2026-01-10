"""
KMU Knowledge Assistant - Unified LLM Provider Interface
Unterstützt Ollama (lokal), OpenAI, Anthropic, Google
"""

import httpx
import json
from abc import ABC, abstractmethod
from typing import Optional, Generator, AsyncGenerator
from dataclasses import dataclass

from app.config import config, LLMProvider


@dataclass
class LLMResponse:
    """Standardisierte LLM-Antwort"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    context_size: int = 16384  # Standard Kontextfenster
    finish_reason: Optional[str] = None

    @property
    def tokens_remaining(self) -> Optional[int]:
        """Berechnet verbleibende Tokens im Kontext"""
        if self.tokens_used is not None:
            return max(0, self.context_size - self.tokens_used)
        return None

    @property
    def usage_percent(self) -> Optional[float]:
        """Prozentuale Nutzung des Kontexts"""
        if self.tokens_used is not None:
            return min(100, (self.tokens_used / self.context_size) * 100)
        return None


class BaseLLMProvider(ABC):
    """Abstrakte Basisklasse für LLM-Provider"""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        """Generiert eine Antwort"""
        pass
    
    @abstractmethod
    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        """Streamt eine Antwort"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Prüft ob der Provider verfügbar ist"""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama (lokales LLM)"""
    
    def __init__(self):
        self.host = config.llm.ollama_host
        self.model = config.llm.ollama_model
    
    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.host}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_models(self) -> list[str]:
        """Listet verfügbare Modelle"""
        try:
            response = httpx.get(f"{self.host}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception:
            pass
        return []
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", config.llm.temperature),
                "top_p": kwargs.get("top_p", config.llm.top_p),
                "repeat_penalty": kwargs.get("repeat_penalty", config.llm.repeat_penalty),
                "num_predict": kwargs.get("max_tokens", config.llm.max_tokens or 2048),
                "num_ctx": kwargs.get("num_ctx", 16384)  # Kontextfenster 16K
            }
        }
        
        response = httpx.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=config.response_timeout_local * 10
        )
        response.raise_for_status()
        data = response.json()

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        total_tokens = prompt_tokens + completion_tokens
        context_size = payload["options"].get("num_ctx", 16384)

        return LLMResponse(
            content=data["message"]["content"],
            model=data.get("model", self.model),
            provider="ollama",
            tokens_used=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            context_size=context_size,
            finish_reason=data.get("done_reason")
        )
    
    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", config.llm.temperature),
                "top_p": kwargs.get("top_p", config.llm.top_p),
                "repeat_penalty": kwargs.get("repeat_penalty", config.llm.repeat_penalty),
                "num_predict": kwargs.get("max_tokens", config.llm.max_tokens or 2048),
                "num_ctx": kwargs.get("num_ctx", 16384)  # Kontextfenster 16K
            }
        }

        with httpx.stream(
            "POST",
            f"{self.host}/api/chat",
            json=payload,
            timeout=None
        ) as response:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API"""
    
    def __init__(self):
        self.api_key = config.llm.openai_api_key
        self.model = config.llm.openai_model
        self.base_url = "https://api.openai.com/v1"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", config.llm.temperature),
            "top_p": kwargs.get("top_p", config.llm.top_p),
            "frequency_penalty": kwargs.get("repeat_penalty", config.llm.repeat_penalty) - 1.0,  # OpenAI: 0-2 statt 1-2
            "max_tokens": kwargs.get("max_tokens", config.llm.max_tokens or 2048)
        }

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=config.response_timeout_api * 10
        )
        response.raise_for_status()
        data = response.json()

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        # OpenAI GPT-4o hat 128K Kontext
        context_size = 128000 if "gpt-4" in data.get("model", "") else 16384

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data["model"],
            provider="openai",
            tokens_used=usage.get("total_tokens"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            context_size=context_size,
            finish_reason=choice.get("finish_reason")
        )
    
    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", config.llm.temperature),
            "top_p": kwargs.get("top_p", config.llm.top_p),
            "frequency_penalty": kwargs.get("repeat_penalty", config.llm.repeat_penalty) - 1.0,
            "max_tokens": kwargs.get("max_tokens", config.llm.max_tokens or 2048),
            "stream": True
        }

        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=None
        ) as response:
            for line in response.iter_lines():
                if line.startswith("data: ") and not line.endswith("[DONE]"):
                    data = json.loads(line[6:])
                    if "choices" in data and data["choices"]:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API"""
    
    def __init__(self):
        self.api_key = config.llm.anthropic_api_key
        self.model = config.llm.anthropic_model
        self.base_url = "https://api.anthropic.com/v1"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        payload = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", config.llm.max_tokens or 2048),
            "temperature": kwargs.get("temperature", config.llm.temperature),
            "top_p": kwargs.get("top_p", config.llm.top_p),
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = httpx.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            timeout=config.response_timeout_api * 10
        )
        response.raise_for_status()
        data = response.json()

        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        # Claude hat 200K Kontext
        context_size = 200000

        return LLMResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            provider="anthropic",
            tokens_used=prompt_tokens + completion_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            context_size=context_size,
            finish_reason=data.get("stop_reason")
        )
    
    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        payload = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", config.llm.max_tokens or 2048),
            "temperature": kwargs.get("temperature", config.llm.temperature),
            "top_p": kwargs.get("top_p", config.llm.top_p),
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        if system_prompt:
            payload["system"] = system_prompt

        with httpx.stream(
            "POST",
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            timeout=None
        ) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        if "text" in delta:
                            yield delta["text"]


class GoogleProvider(BaseLLMProvider):
    """Google Gemini API"""
    
    def __init__(self):
        self.api_key = config.llm.google_api_key
        self.model = config.llm.google_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        model = kwargs.get("model", self.model)
        
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Verstanden. Ich werde diese Anweisungen befolgen."}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", config.llm.temperature),
                "topP": kwargs.get("top_p", config.llm.top_p),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": kwargs.get("max_tokens", config.llm.max_tokens or 2048)
            }
        }

        response = httpx.post(
            f"{self.base_url}/models/{model}:generateContent",
            params={"key": self.api_key},
            json=payload,
            timeout=config.response_timeout_api * 10
        )
        response.raise_for_status()
        data = response.json()

        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        # Gemini 1.5 Pro hat 1M Kontext, Flash 128K
        context_size = 1000000 if "pro" in model else 128000

        return LLMResponse(
            content=content,
            model=model,
            provider="google",
            tokens_used=usage.get("totalTokenCount"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            context_size=context_size,
            finish_reason=data["candidates"][0].get("finishReason")
        )
    
    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        model = kwargs.get("model", self.model)
        
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Verstanden."}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", config.llm.temperature),
                "topP": kwargs.get("top_p", config.llm.top_p),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": kwargs.get("max_tokens", config.llm.max_tokens or 2048)
            }
        }

        with httpx.stream(
            "POST",
            f"{self.base_url}/models/{model}:streamGenerateContent",
            params={"key": self.api_key, "alt": "sse"},
            json=payload,
            timeout=None
        ) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "candidates" in data:
                        parts = data["candidates"][0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "text" in part:
                                yield part["text"]


class UnifiedLLMProvider:
    """Unified Interface für alle LLM-Provider mit Live-Umschaltung"""
    
    def __init__(self):
        self.providers = {
            LLMProvider.OPENAI: OpenAIProvider(),
            LLMProvider.ANTHROPIC: AnthropicProvider(),
            LLMProvider.GOOGLE: GoogleProvider()
        }
        self._current_provider = config.llm.provider
    
    @property
    def current_provider(self) -> LLMProvider:
        return self._current_provider
    
    @current_provider.setter
    def current_provider(self, provider: LLMProvider):
        """Live-Wechsel des Providers ohne Neustart"""
        if provider in self.providers:
            self._current_provider = provider
        else:
            raise ValueError(f"Unbekannter Provider: {provider}")
    
    def get_provider(self) -> BaseLLMProvider:
        return self.providers[self._current_provider]
    
    def get_available_providers(self) -> list[tuple[LLMProvider, bool]]:
        """Listet alle Provider mit Verfügbarkeitsstatus"""
        return [(p, provider.is_available()) for p, provider in self.providers.items()]
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        return self.get_provider().generate(prompt, system_prompt, **kwargs)
    
    def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        return self.get_provider().stream(prompt, system_prompt, **kwargs)
    
    def is_available(self) -> bool:
        return self.get_provider().is_available()


# Globale Instanz
llm_provider = UnifiedLLMProvider()
