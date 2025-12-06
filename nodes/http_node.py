"""
HTTPRequest Node - Reliable, template-aware, retry-capable, Opal-grade HTTP node.
"""

from typing import Dict, Any, Optional
import httpx
import time
from .base import BaseNode
from utils.template import interpolate_variables


SAFE_HEADER_PREFIXES = ["authorization", "api-key", "x-api-key", "proxy-authorization"]


class HTTPRequestNode(BaseNode):
    """HTTP Request Node with:
    - retries
    - templated URL, headers, body
    - support for query params
    - auto JSON/text/bytes parsing
    - metadata output
    """

    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        try:
            method = self.get_config_value("method", "GET").upper()
            url_template = self.get_config_value("url", "")
            headers_cfg = self.get_config_value("headers", {})
            body_cfg = self.get_config_value("body", None)
            timeout = self.get_config_value("timeout", 30)
            retries = self.get_config_value("retries", 1)
            retry_delay = self.get_config_value("retry_delay", 1.5)
            parse_mode = self.get_config_value("parse", "auto")

            # ----------------------------------------
            # 1) Interpolate URL
            # ----------------------------------------
            url = interpolate_variables(url_template, context, inputs)

            # ----------------------------------------
            # 2) Build headers with interpolation
            # ----------------------------------------
            headers = {}
            for k, v in headers_cfg.items():
                if isinstance(v, str):
                    headers[k] = interpolate_variables(v, context, inputs)
                else:
                    headers[k] = v  # fallback raw

            # ----------------------------------------
            # 3) Build body (supports raw, dict, templated string)
            # ----------------------------------------
            json_body = None
            data_body = None
            raw_body = None

            if isinstance(body_cfg, dict):
                # Template each value inside dict
                json_body = {
                    key: interpolate_variables(str(val), context, inputs)
                    for key, val in body_cfg.items()
                }
            elif isinstance(body_cfg, str):
                raw_body = interpolate_variables(body_cfg, context, inputs)
            else:
                json_body = None

            # ----------------------------------------
            # 4) Execute request with retries
            # ----------------------------------------
            response = None
            error = None

            async with httpx.AsyncClient(timeout=timeout) as client:
                for attempt in range(retries + 1):
                    try:
                        start = time.time()
                        response = await client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            json=json_body,
                            content=raw_body,
                        )
                        duration = time.time() - start
                        break  # success -> stop retrying

                    except httpx.RequestError as e:
                        error = str(e)
                        if attempt < retries:
                            await asyncio.sleep(retry_delay)
                        else:
                            raise

            # ----------------------------------------
            # 5) Parse response
            # ----------------------------------------
            parsed = self._parse_response(response, parse_mode)

            # ----------------------------------------
            # 6) Success determination
            # ----------------------------------------
            success = response.status_code < 400

            # ----------------------------------------
            # 7) Exclude sensitive headers from logs
            # ----------------------------------------
            safe_headers = {
                k: ("***" if any(k.lower().startswith(p) for p in SAFE_HEADER_PREFIXES) else v)
                for k, v in headers.items()
            }

            # ----------------------------------------
            # 8) Build output
            # ----------------------------------------
            output = {
                "data": parsed,
                "output": parsed,
                "status_code": response.status_code,
                "url": str(response.url),
                "request_method": method,
                "request_headers": safe_headers,
                "response_headers": dict(response.headers),
                "raw_text": response.text,
            }

            return self.create_result(output, success=success)

        except Exception as e:
            self.log_error(f"HTTP Request failed: {e}")
            return self.create_result(None, success=False, error=str(e))

    # =========================================================================
    # RESPONSE PARSING
    # =========================================================================
    def _parse_response(self, response: httpx.Response, mode: str):
        """Return parsed response according to parse mode."""
        try:
            if mode == "json":
                return response.json()
            if mode == "text":
                return response.text
            if mode == "bytes":
                return response.content

            # AUTO MODE
            try:
                return response.json()
            except:
                return response.text

        except Exception:
            return response.text

    # =========================================================================
    # SCHEMAS
    # =========================================================================
    @classmethod
    def get_input_schema(cls):
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "body": {"type": ["object", "string"]},
            }
        }

    @classmethod
    def get_output_schema(cls):
        return {
            "type": "object",
            "properties": {
                "data": {"type": ["object", "string", "array"]},
                "output": {"type": ["object", "string", "array"]},
                "status_code": {"type": "integer"},
                "url": {"type": "string"},
                "request_method": {"type": "string"},
                "request_headers": {"type": "object"},
                "response_headers": {"type": "object"},
                "raw_text": {"type": "string"},
            },
            "required": ["data", "status_code"]
        }

    @classmethod
    def get_config_schema(cls):
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    "default": "GET"
                },
                "url": {"type": "string"},
                "headers": {"type": "object", "default": {}},
                "body": {"type": ["object", "string", "null"]},
                "timeout": {"type": "number", "default": 30},
                "retries": {"type": "integer", "default": 1},
                "retry_delay": {"type": "number", "default": 1.5},
                "parse": {
                    "type": "string",
                    "enum": ["auto", "json", "text", "bytes"],
                    "default": "auto"
                }
            },
            "required": ["url"]
        }
