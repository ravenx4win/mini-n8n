"""
Image Generation Node - OpenAI DALL·E / Replicate SDXL / Future: Google Imagen
"""

from typing import Dict, Any
import os
from .base import BaseNode
from utils.template import interpolate_variables
import asyncio


class ImageGenerationNode(BaseNode):
    """Generate images using multiple providers."""

    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        try:
            # Merge prompt
            prompt_template = self.get_config_value("prompt", "")
            prompt = interpolate_variables(prompt_template, context, inputs)

            provider = self.get_config_value("provider", None)
            model = self.get_config_value("model", None)
            size = self.get_config_value("size", "1024x1024")
            quality = self.get_config_value("quality", "standard")

            # Auto-detect provider if missing
            provider = provider or self._detect_provider(model)

            self.log_info(f"[ImageNode] Provider={provider}, Model={model}, Size={size}")

            # Route to provider
            if provider == "openai":
                result = await self._generate_openai(prompt, model, size, quality)

            elif provider == "replicate":
                result = await self._generate_replicate(prompt, model)

            elif provider == "google":
                result = await self._generate_google(prompt, model, size)

            else:
                return self.create_result(
                    None,
                    success=False,
                    error=f"Unsupported provider '{provider}'"
                )

            # Build output metadata
            output = {
                "url": result.get("url"),
                "output": result.get("url"),
                "prompt": prompt,
                "model": model,
                "provider": provider,
                "revised_prompt": result.get("revised_prompt"),
                "resolution": size,
            }

            return self.create_result(output, success=True)

        except Exception as e:
            self.log_error(f"Image generation failed: {e}")
            return self.create_result(None, success=False, error=str(e))

    # =========================================================================
    # PROVIDERS
    # =========================================================================

    async def _generate_openai(self, prompt, model, size, quality):
        """Generate using OpenAI DALL·E."""
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")

            client = AsyncOpenAI(api_key=api_key)

            response = await client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )

            img = response.data[0]
            return {
                "url": img.url,
                "revised_prompt": getattr(img, "revised_prompt", None)
            }

        except Exception as e:
            raise RuntimeError(f"OpenAI error: {e}")

    async def _generate_replicate(self, prompt, model):
        """Generate using Replicate SDXL/Flux/etc."""
        try:
            import replicate

            api_key = os.getenv("REPLICATE_API_TOKEN")
            if not api_key:
                raise ValueError("REPLICATE_API_TOKEN not set")

            os.environ["REPLICATE_API_TOKEN"] = api_key

            # Auto-detect model variants
            model_resolved = self._resolve_replicate_model(model)

            output = await replicate.async_run(
                model_resolved,
                input={"prompt": prompt}
            )

            # Replicate returns list, string, or dict depending on model
            if isinstance(output, list):
                url = output[0] if output else None
            elif isinstance(output, dict):
                url = output.get("url")
            else:
                url = output

            return {"url": url}

        except Exception as e:
            raise RuntimeError(f"Replicate error: {e}")

    async def _generate_google(self, prompt, model, size):
        """Future support for Google Imagen/Gemini image models."""
        from google import genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        try:
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(model_name=model)

            response = client.generate_image(
                prompt=prompt,
                size=size
            )

            return {"url": response.image.url}

        except Exception as e:
            raise RuntimeError(f"Google Imagen error: {e}")

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _detect_provider(self, model: str):
        """Auto-detect provider from model name."""
        if not model:
            return "openai"

        model_l = model.lower()

        if "dall" in model_l or "gpt" in model_l:
            return "openai"

        if "sdxl" in model_l or "stable-diffusion" in model_l or "/" in model_l:
            return "replicate"

        if "imagen" in model_l or "gemini" in model_l:
            return "google"

        return "openai"

    def _resolve_replicate_model(self, model: str) -> str:
        """Clean model resolution for Replicate."""
        if not model:
            return "stability-ai/sdxl:latest"

        if "/" in model:
            return model  # full model tag

        if "flux" in model.lower():
            return "black-forest-labs/flux-1.1-pro"

        if "sdxl" in model.lower():
            return "stability-ai/sdxl:latest"

        return "stability-ai/sdxl:latest"

    # =========================================================================
    # SCHEMAS
    # =========================================================================

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
                "url": {"type": "string", "description": "Generated image URL"},
                "prompt": {"type": "string"},
                "model": {"type": "string"},
                "provider": {"type": "string"},
                "revised_prompt": {"type": "string"},
                "resolution": {"type": "string"}
            },
            "required": ["url"]
        }

    @classmethod
    def get_config_schema(cls):
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "enum": ["openai", "replicate", "google"],
                    "default": "openai"
                },
                "model": {
                    "type": "string",
                    "default": "dall-e-3",
                },
                "prompt": {
                    "type": "string",
                    "description": "Prompt with {{variables}}",
                    "ui:widget": "textarea"
                },
                "size": {
                    "type": "string",
                    "enum": ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"],
                    "default": "1024x1024"
                },
                "quality": {
                    "type": "string",
                    "enum": ["standard", "hd"],
                    "default": "standard"
                }
            },
            "required": ["prompt"]
        }
