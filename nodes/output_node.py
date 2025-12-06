"""Output Node - Return final workflow results."""

from typing import Dict, Any
from .base import BaseNode, NodeResult
from utils.template import interpolate_variables


class OutputNode(BaseNode):
    """Node for returning final workflow results.
    
    This node collects data from previous nodes and formats it for output.
    """
    
    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> NodeResult:
        """Execute the output node.
        
        Args:
            inputs: Input data from connected nodes
            context: Execution context
            
        Returns:
            NodeResult with formatted output
        """
        try:
            # Get configuration
            format_type = self.get_config_value("format", "auto")
            template = self.get_config_value("template", None)
            fields = self.get_config_value("fields", None)
            
            self.log_info(f"Preparing output in format: {format_type}")
            
            # Determine output based on format
            if template:
                # Use template to format output
                output = interpolate_variables(template, context, inputs)
            elif fields:
                # Select specific fields from inputs
                output = {}
                for field in fields:
                    if "." in field:
                        # Handle nested field access
                        parts = field.split(".")
                        node_id = parts[0]
                        field_path = ".".join(parts[1:])
                        if node_id in inputs:
                            from utils.template import get_nested_value
                            output[field] = get_nested_value(inputs[node_id], field_path)
                    else:
                        # Direct field access
                        if field in inputs:
                            output[field] = inputs[field]
            else:
                # Return all inputs as-is
                output = inputs
            
            # Apply format transformation
            if format_type == "json":
                formatted_output = output
            elif format_type == "text":
                if isinstance(output, dict):
                    formatted_output = "\n".join(f"{k}: {v}" for k, v in output.items())
                else:
                    formatted_output = str(output)
            elif format_type == "list":
                if isinstance(output, dict):
                    formatted_output = list(output.values())
                elif isinstance(output, list):
                    formatted_output = output
                else:
                    formatted_output = [output]
            else:  # auto
                formatted_output = output
            
            self.log_info(f"Output prepared: {type(formatted_output).__name__}")
            
            return self.create_result(
                output={
                    "output": formatted_output,
                    "result": formatted_output,
                    "format": format_type
                },
                success=True
            )
            
        except Exception as e:
            self.log_error(f"Error in output node: {e}")
            return self.create_result(
                output=None,
                success=False,
                error=str(e)
            )
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Define input schema."""
        return {
            "type": "object",
            "properties": {},
            "description": "Accepts any input from previous nodes"
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Define output schema."""
        return {
            "type": "object",
            "properties": {
                "output": {
                    "type": ["object", "string", "array", "number", "boolean"],
                    "description": "Formatted output data"
                },
                "result": {
                    "type": ["object", "string", "array", "number", "boolean"],
                    "description": "Alias for output"
                },
                "format": {
                    "type": "string",
                    "description": "Output format used"
                }
            },
            "required": ["output"]
        }
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema."""
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["auto", "json", "text", "list"],
                    "default": "auto",
                    "description": "Output format"
                },
                "template": {
                    "type": "string",
                    "description": "Optional template with {{variables}} for formatting"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific fields to include (e.g., ['node1.output', 'node2.text'])"
                }
            }
        }


