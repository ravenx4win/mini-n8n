"""
LLM Text Generation Node - Multi-provider (OpenAI, Anthropic, Google Gemini)
"""

from typing import Dict, Any
import os
from .base import BaseNode, NodeResult
from utils.template import interpolate_variables
import inspect


class LLMTextGenerationNode(BaseNode):
    """Generate text using LLMs (OpenAI, Anthropic, Google Gemini)."""

    # ----------------------------------------
    # MAIN RUN METHOD
    # ----------------------------------------
    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> NodeResult:
        try:
            # Merge prompt with upstream inputs
            prompt_template = self.get_config_value("prompt", "")
            provider = self.get_config_value("provider", None)
            model = self.get_config_value("model", None)
            temperature = self.get_config_value("temperature", 0.7)
            max_tokens = self.get_config_value("max_tokens", 2000)

            # Interpolate variables from inputs + context
            prompt = interpolate_variables(prompt_template, context, inputs)

            # Auto-detect provider if missing
            provider = provider or self._detect_provider(model)

            if provider not in ("openai", "anthropic", "google"):
                return self.create_result(
                    None,
                    success=False,
                    error=f"Unsupported provider '{provider}'"
                )

            self.log_info(f"LLM request via {provider}/{model}")

            # Provider routing
            if provider == "openai":
                text, tokens = await self._generate_openai(prompt, model, temperature, max_tokens)

            elif provider == "anthropic":
                text, tokens = await self._generate_anthropic(prompt, model, temperature, max_tokens)

            elif provider == "google":
                text, tokens = await self._generate_google(prompt, model, temperature, max_tokens)

            else:
                raise ValueError(f"Unknown provider: {provider}")

            # Build response
            output = {
                "text": text,
                "output": text,
                "prompt_used": prompt,
                "provider": provider,
                "model": model,
                "tokens_used": tokens
            }

            return self.create_result(output, success=True)

        except Exception as e:
            self.log_error(f"LLM node error: {e}")
            return self.create_result(None, success=False, error=str(e))

    # ----------------------------------------
    # PROVIDER: OPENAI
    # ----------------------------------------
    async def _generate_openai(self, prompt, model, temperature, max_tokens):
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            text = response.choices[0].message.content
            tokens = response.usage.total_tokens if hasattr(response, "usage") else None

            return text, tokens

        except Exception as e:
            raise ValueError(f"OpenAI Error: {e}")

    # ----------------------------------------
    # PROVIDER: ANTHROPIC
    # ----------------------------------------
    async def _generate_anthropic(self, prompt, model, temperature, max_tokens):
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            response = await client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            text = response.content[0].text
            tokens = response.usage.output_tokens if hasattr(response, "usage") else None

            return text, tokens

        except Exception as e:
            raise ValueError(f"Anthropic Error: {e}")

    # ----------------------------------------
    # PROVIDER: GOOGLE GEMINI
    # ----------------------------------------
    async def _generate_google(self, prompt, model, temperature, max_tokens):
        try:
            from google import genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

            client = genai.GenerativeModel(model_name=model)

            response = client.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )

            text = response.text
            tokens = None  # Gemini API does not always return usage tokens

            return text, tokens

        except Exception as e:
            raise ValueError(f"Google Gemini Error: {e}")

    # ----------------------------------------
    # AUTO PROVIDER DETECTION
    # ----------------------------------------
    def _detect_provider(self, model: str) -> str:
        """Automatically determine provider based on model name."""
        if not model:
            return "openai"

        model = model.lower()

        if model.startswith(("gpt", "o1", "o-")):
            return "openai"

        if "claude" in model:
            return "anthropic"

        if "gemini" in model:
            return "google"

        return "openai"

    # ----------------------------------------
    # SCHEMAS
    # ----------------------------------------
    @classmethod
    def get_input_schema(cls):
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"}
            }
        }

    @classmethod
    def get_output_schema(cls):
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "output": {"type": "string"},
                "prompt_used": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "tokens_used": {"type": ["number", "null"]}
            },
            "required": ["text", "output"]
        }

    @classmethod
    def get_config_schema(cls):
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "enum": ["openai", "anthropic", "google"],
                    "default": "openai"
                },
                "model": {
                    "type": "string",
                    "default": os.getenv("DEFAULT_TEXT_MODEL", "gpt-4.1")
                },
                "prompt": {
                    "type": "string",
                    "description": "Prompt template with {{variables}}",
                    "ui:widget": "textarea"
                },
                "temperature": {"type": "number", "default": 0.7},
                "max_tokens": {"type": "integer", "default": 2000}
            },
            "required": ["prompt"]
        }
