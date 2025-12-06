"""
Node Registry Setup
Registers all built-in workflow nodes.
"""

from core.registry import registry

# Import Node Classes
from .input_node import UserInputNode
from .llm_node import LLMTextGenerationNode
from .image_node import ImageGenerationNode
from .video_node import VideoGenerationNode
from .http_node import HTTPRequestNode
from .conditional_node import ConditionalLogicNode
from .output_node import OutputNode


def register_all_nodes():
    """Register all built-in node types with the global registry."""

    # ======================================================================
    #  INPUT / OUTPUT NODES
    # ======================================================================

    registry.register(
        type_name="user_input",
        node_class=UserInputNode,
        display_name="User Input",
        description="Capture user-provided input data",
        category="Input/Output",
        config_schema=UserInputNode.get_config_schema(),
        input_schema=UserInputNode.get_input_schema(),
        output_schema=UserInputNode.get_output_schema(),
        icon="input"
    )

    registry.register(
        type_name="output",
        node_class=OutputNode,
        display_name="Output",
        description="Return and format final workflow results",
        category="Input/Output",
        config_schema=OutputNode.get_config_schema(),
        input_schema=OutputNode.get_input_schema(),
        output_schema=OutputNode.get_output_schema(),
        icon="output"
    )

    # ======================================================================
    #  AI NODES (TEXT, IMAGE, VIDEO)
    # ======================================================================

    registry.register(
        type_name="llm_text_generation",
        node_class=LLMTextGenerationNode,
        display_name="LLM Text Generation",
        description="Generate text using LLMs (OpenAI, Claude)",
        category="AI",
        config_schema=LLMTextGenerationNode.get_config_schema(),
        input_schema=LLMTextGenerationNode.get_input_schema(),
        output_schema=LLMTextGenerationNode.get_output_schema(),
        icon="text"
    )

    registry.register(
        type_name="image_generation",
        node_class=ImageGenerationNode,
        display_name="Image Generation",
        description="Generate images using AI models (DALL·E, SDXL, Replicate)",
        category="AI",
        config_schema=ImageGenerationNode.get_config_schema(),
        input_schema=ImageGenerationNode.get_input_schema(),
        output_schema=ImageGenerationNode.get_output_schema(),
        icon="image"
    )

    registry.register(
        type_name="video_generation",
        node_class=VideoGenerationNode,
        display_name="Video Generation",
        description="Generate videos using Google Veo or Replicate video models",
        category="AI",
        config_schema=VideoGenerationNode.get_config_schema(),
        input_schema=VideoGenerationNode.get_input_schema(),
        output_schema=VideoGenerationNode.get_output_schema(),
        icon="video"
    )

    # ======================================================================
    #  LOGIC NODES
    # ======================================================================

    registry.register(
        type_name="conditional_logic",
        node_class=ConditionalLogicNode,
        display_name="Conditional Logic",
        description="If/Else branching (supports multiple conditions)",
        category="Logic",
        config_schema=ConditionalLogicNode.get_config_schema(),
        input_schema=ConditionalLogicNode.get_input_schema(),
        output_schema=ConditionalLogicNode.get_output_schema(),
        icon="branch"
    )

    # ======================================================================
    #  INTEGRATION NODES (APIs, External Services)
    # ======================================================================

    registry.register(
        type_name="http_request",
        node_class=HTTPRequestNode,
        display_name="HTTP Request",
        description="Make HTTP requests to external APIs",
        category="Integration",
        config_schema=HTTPRequestNode.get_config_schema(),
        input_schema=HTTPRequestNode.get_input_schema(),
        output_schema=HTTPRequestNode.get_output_schema(),
        icon="api"
    )


    # ======================================================================
    #  OPTIONAL PLACEHOLDER FOR FUTURE NODES
    # ======================================================================
    # registry.register(...)
    # Example: Delay Node, Loop Node, Python Code Node, etc.

    return True
