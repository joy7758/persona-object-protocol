"""
AutoGen-aligned POP prototype example.

This example follows the AutoGen quickstart shape:
- AssistantAgent
- model_client
- tools
- system_message

If AutoGen is not installed, or no model_client is provided,
the script prints a safe preview config instead of raising.
"""

from pop.adapter_autogen import (
    assistant_agent_from_persona,
    persona_to_autogen_config,
)

cfg = persona_to_autogen_config("personas/marketing_manager.json", model="gpt-4o")
print("AUTOGEN_CONFIG")
print(cfg)

agent = assistant_agent_from_persona(
    "personas/marketing_manager.json",
    model_client=None,
)
print("AUTOGEN_AGENT")
print(agent)
