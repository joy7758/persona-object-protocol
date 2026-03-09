from pop.loader import validate_persona
from pop.registry import list_personas, load_persona_by_id, resolve_persona

print("LIST_PERSONAS")
print(list_personas())

print("RESOLVE_PERSONA")
print(resolve_persona("marketing_manager_v1"))

print("LOAD_BY_ID")
print(load_persona_by_id("marketing_manager_v1"))

print("VALIDATE")
print(validate_persona("personas/marketing_manager.json"))
