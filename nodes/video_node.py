"""
Video Generation Node - Supports Replicate Video Models + Google Veo
"""

from typing import Dict, Any
import os
import asyncio
from .base import BaseNode
from utils.template import interpolate_variables


class VideoGenerationNode(BaseNode):
    """Generate videos using Replicate or Google Veo."""

    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        try:
            # Interpolate the prompt
            prompt_template = self.get_config_value("prompt", "")
            prompt = interpolate_variables(prompt_template, context, inputs)

            provider = self.get_config_value("provider", None)
            model = self.get_config_value("model", None)
            duration = self.get_config_value("duration", 4)
            fps = self.get_config_value("fps", 24)

            # Auto-detect provider
            provider = provider or self._detect_provider(model)

            self.log_info(f"[VideoNode] Provider={provider}, Model={model}, Duration={duration}s")

            # Route to correct provider
            if provider == "replicate":
                result = await self._generate_replicate(prompt, model, duration, fps)

            elif provider == "google":
                result = await self._generate_google_veo(prompt, model, duration)

            else:
                return self.create_result(
                    None,
                    success=False,
                    error=f"Unsupported provider '{provider}'"
                )

            video_url = result.get("url")

            output = {
                "url": video_url,
                "output": video_url,
                "prompt_used": prompt,
                "model": model,
                "provider": provider,
                "duration": duration,
                "fps": fps,
                **result
            }

            return self.create_result(output, success=True)

        except Exception as e:
            self.log_error(f"Video generation failed: {e}")
            return self.create_result(None, success=False, error=str(e))

    # =========================================================================
    # PROVIDER 1: REPLICATE (Zeroscope, AnimateDiff, Flux Video etc.)
    # =========================================================================
    async def _generate_replicate(self, prompt, model, duration, fps):
        import replicate
        
        api_key = os.getenv("REPLICATE_API_TOKEN")
        if not api_key:
            raise ValueError("REPLICATE_API_TOKEN not set")

        os.environ["REPLICATE_API_TOKEN"] = api_key

        model_name = self._resolve_replicate_model(model)

        # Send job
        prediction = await replicate.async_run(
            model_name,
            input={
                "prompt": prompt,
                "fps": fps,
                "num_frames": duration * fps
            }
        )

        # Poll until job is complete
        url = await self._poll_replicate(prediction)

        return {"url": url}

    async def _poll_replicate(self, prediction):
        """Poll replicate until the job finishes."""
        import replicate

        prediction_id = prediction.get("id")
        if not prediction_id:
            # Some models return output directly (very rare)
            output = prediction
            if isinstance(output, list):
                return output[0]
            return output

        # Poll prediction
        for _ in range(120):  # ~2 minutes max
            pred = await replicate.predictions.async_get(prediction_id)

            if pred.status == "succeeded":
                out = pred.output
                if isinstance(out, list):
                    return out[0]
                return out

            if pred.status == "failed":
                raise RuntimeError(f"Replicate video failed: {pred.error}")

            await asyncio.sleep(2)

        raise TimeoutError("Replicate video generation timed out.")

    def _resolve_replicate_model(self, model: str):
        """Auto pick model tag for replicate."""
        m = model.lower()

        if "zeroscope" in m:
            return "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"

        if "animate" in m:
            return "lucataco/animate-diff:beecf59c4aee8d81bf04f0381033dfa10dc16e845b4ae00d281e2fa377e48a9f"

        # Flux video (optional future)
        if "flux" in m:
            return "black-forest-labs/flux-1.1-pro"

        # Default fallback
        return model

    # =========================================================================
    # PROVIDER 2: GOOGLE VEO (REAL IMPLEMENTATION)
    # =========================================================================
    async def _generate_google_veo(self, prompt, model, duration):
        """
        Google Veo API (via Gemini Video).
        Example model names:
        - "veo-1.5"
        """
        from google import genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        genai.configure(api_key=api_key)

        model_name = model or "veo-1.5"
        client = genai.GenerativeModel(model_name)

        response = client.generate_video(
            prompt=prompt,
            duration=duration,
        )

        # Google returns .videos[0].uri
        try:
            video_url = response.videos[0].uri
        except:
            raise RuntimeError("Google Veo response malformed")

        return {"url": video_url}

    # =========================================================================
    # AUTO PROVIDER DETECTION
    # =========================================================================
    def _detect_provider(self, model: str):
        if not model:
            return "replicate"

        m = model.lower()

        if "veo" in m:
            return "google"

        if "zeroscope" in m or "animate" in m:
            return "replicate"

        if "/" in m:  # full replicate tag
            return "replicate"

        return "replicate"

    # =========================================================================
    # SCHEMAS
    # =========================================================================
    @classmethod
    def get_input_schema(cls):
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
            }
        }

    @classmethod
    def get_output_schema(cls):
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "prompt_used": {"type": "string"},
                "duration": {"type": "number"},
                "fps": {"type": "number"},
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
                    "enum": ["replicate", "google"],
                    "default": "replicate"
                },
                "model": {
                    "type": "string",
                    "default": "zeroscope-v2-xl"
                },
                "prompt": {"type": "string"},
                "duration": {"type": "number", "default": 4},
                "fps": {"type": "number", "default": 24},
            },
            "required": ["prompt"]
        }
