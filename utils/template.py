"""Prompt templating with variable interpolation."""

import re
from typing import Dict, Any, List, Set
from jinja2 import Environment, Template, meta, TemplateSyntaxError


class TemplateError(Exception):
    """Raised when template rendering fails."""
    pass


class PromptTemplate:
    """Handle prompt templates with variable interpolation.
    
    Supports both {{variable}} and Jinja2 syntax.
    """
    
    def __init__(self, template_string: str):
        """Initialize a template.
        
        Args:
            template_string: Template string with {{variable}} placeholders
        """
        self.template_string = template_string
        self.jinja_env = Environment()
        
        try:
            self.template = self.jinja_env.from_string(template_string)
        except TemplateSyntaxError as e:
            raise TemplateError(f"Invalid template syntax: {e}")
    
    def render(self, variables: Dict[str, Any]) -> str:
        """Render the template with provided variables.
        
        Args:
            variables: Dictionary of variable values
            
        Returns:
            Rendered string
            
        Raises:
            TemplateError: If rendering fails
        """
        try:
            return self.template.render(**variables)
        except Exception as e:
            raise TemplateError(f"Failed to render template: {e}")
    
    def get_variables(self) -> Set[str]:
        """Extract all variable names from the template.
        
        Returns:
            Set of variable names
        """
        try:
            ast = self.jinja_env.parse(self.template_string)
            return meta.find_undeclared_variables(ast)
        except Exception:
            # Fallback to regex if parsing fails
            return set(re.findall(r'\{\{([^}]+)\}\}', self.template_string))
    
    def validate(self, variables: Dict[str, Any]) -> List[str]:
        """Validate that all required variables are provided.
        
        Args:
            variables: Dictionary of variable values
            
        Returns:
            List of missing variable names
        """
        required = self.get_variables()
        provided = set(variables.keys())
        missing = required - provided
        return list(missing)


def interpolate_variables(
    text: str,
    context: Dict[str, Any],
    node_outputs: Dict[str, Any] = None
) -> str:
    """Interpolate variables in text using context and node outputs.
    
    Supports multiple formats:
    - {{variable}} - from context
    - {{node_id.output}} - from node outputs
    - {{node_id.output.nested.key}} - nested access
    
    Args:
        text: Text containing variable placeholders
        context: Context dictionary with variables
        node_outputs: Dictionary of node outputs by node_id
        
    Returns:
        Text with variables replaced
    """
    if node_outputs is None:
        node_outputs = {}
    
    # Combine context and node outputs
    variables = dict(context)
    
    # Add node outputs with dot notation support
    for node_id, output in node_outputs.items():
        variables[node_id] = output
    
    # Create and render template
    try:
        template = PromptTemplate(text)
        return template.render(variables)
    except TemplateError:
        # If Jinja2 fails, try simple string replacement
        result = text
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result


def extract_node_references(text: str) -> List[tuple[str, str]]:
    """Extract node output references from text.
    
    Args:
        text: Text containing node references like {{node_id.output}}
        
    Returns:
        List of (node_id, output_key) tuples
    """
    pattern = r'\{\{([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_.-]+)\}\}'
    matches = re.findall(pattern, text)
    return matches


def get_nested_value(data: Any, path: str, default: Any = None) -> Any:
    """Get a value from nested dictionary using dot notation.
    
    Args:
        data: Dictionary or object to query
        path: Dot-separated path (e.g., 'output.data.text')
        default: Default value if path not found
        
    Returns:
        Value at path or default
    """
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif hasattr(current, key):
            current = getattr(current, key)
        else:
            return default
        
        if current is None:
            return default
    
    return current


