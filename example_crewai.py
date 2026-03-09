from pop.adapter_crewai import agent_from_persona

agent = agent_from_persona(
    "personas/marketing_manager.json",
    llm="gpt-4o"
)

print(agent)
