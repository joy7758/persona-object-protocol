from pop.adapter_crewai import export_crewai_agents_yaml

out = export_crewai_agents_yaml(
    {
        "marketing_manager": "personas/marketing_manager.json",
        "engineer": "personas/engineer.json",
        "designer": "personas/designer.json",
    },
    "personas/agents.crewai.yaml",
)

print("MULTI_AGENT_YAML_EXPORTED")
print(out)
