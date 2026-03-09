from pop.adapter_crewai import export_crewai_agent_yaml, persona_to_crewai_config

config = persona_to_crewai_config("personas/marketing_manager.json")
print("CONFIG_OK")
print(config)

out = export_crewai_agent_yaml(
    "personas/marketing_manager.json",
    "personas/marketing_manager.crewai.yaml",
)
print("YAML_EXPORTED")
print(out)
