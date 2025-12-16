"""
Template utilities for variable interpolation, nested lookup, and safe rendering.

This file is CRITICAL for correct execution of all nodes:
- LLM templates
- HTTP request templating
- Conditional logic
- Output formatting
- Node-to-node value passing

Provides:
✔ Jinja2 rendering
✔ {{nodeId.output.key}} nested resolution
✔ {{inputs.key}} support
✔ {{context.key}} support
✔ type-safe fallback interpolation
✔ get_nested_value for OutputNode + others
"""

import re
from typing import Dict, Any, Optional
from jinja2 import Environment, TemplateSyntaxError


# =====================================================================
# Utility: Safe nested access
# =====================================================================
def get_nested_value(data: Any, path: str, default: Any = None) -> Any:
    """
    Resolve nested dictionary or object paths:
    Example:
        get_nested_value({"a": {"b": 10}}, "a.b") → 10
        get_nested_value(node_output, "output.data.text")
    """
    if data is None:
        return default

    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif hasattr(current, key):
            current = getattr(current, key)
        else:
            return default

        if current is None:
            return default

    return current


# =====================================================================
# Main interpolation engine
# =====================================================================
def interpolate_variables(
    template_str: str,
    context: Dict[str, Any],
    node_outputs: Optional[Dict[str, Any]] = None,
    inputs: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Interpolates variables in a string using:
    - workflow context (workflow variables)
    - node_inputs passed at runtime
    - node_outputs containing previous node results
    - supports deep dot-notation like {{node1.output.text}}

    Returns:
        Interpolated string (type preserved when possible)
    """

    if not isinstance(template_str, str):
        return template_str  # Do not modify non-strings

    node_outputs = node_outputs or {}
    inputs = inputs or {}

    # ================================================================
    # Build flat variable map for Jinja
    # ================================================================
    jinja_vars = {}

    # workflow-level context variables
    jinja_vars.update(context)

    # inputs available to this node
    jinja_vars["inputs"] = inputs

    # node outputs accessible as {{ nodeId }}
    # and nested attributes are resolved manually below
    for nid, out in node_outputs.items():
        jinja_vars[nid] = out

    # Jinja environment
    env = Environment()

    # Inject custom filter for nested resolution:
    # {{ node1 | get("output.value") }}
    env.filters["get"] = lambda obj, path: get_nested_value(obj, path)

    # ================================================================
    # First attempt: process with Jinja2
    # ================================================================
    try:
        template = env.from_string(template_str)
        rendered = template.render(**jinja_vars)

        # Try json parsing to preserve type
        try:
            import json
            return json.loads(rendered)
        except Exception:
            return rendered

    except TemplateSyntaxError:
        pass  # fallback below

    # ================================================================
    # Fallback manual replacement (robust)
    # ================================================================
    result = template_str

    # Match {{ something.something }}
    pattern = r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}"

    for match in re.findall(pattern, template_str):
        value = None

        # Handle dotted paths
        if "." in match:
            root, path = match.split(".", 1)
            base = jinja_vars.get(root)
            value = get_nested_value(base, path)
        else:
            value = jinja_vars.get(match)

        if value is None:
            value = ""  # safe fallback

        result = result.replace(f"{{{{{match}}}}}", str(value))

    return result


# =====================================================================
# Extract node references (debugging + workflow inspector)
# =====================================================================
def extract_node_references(text: str):
    """
    Returns list of node references:
        {{nodeId.output}}
        {{nodeId.output.key}}
    Output: list of tuples: (nodeId, "output.key")
    """
    pattern = r"\{\{\s*([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_.-]+)\s*\}\}"
    return re.findall(pattern, text)
