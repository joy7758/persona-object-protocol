from pop.registry import (
    list_persona_ids,
    list_personas,
    load_persona_by_id,
    normalize_persona_ref,
    resolve_persona,
)


def main():
    print("LIST_PERSONAS")
    print(list_personas())

    print("LIST_PERSONA_IDS")
    print(list_persona_ids())

    print("NORMALIZE")
    print(normalize_persona_ref("pop:marketing_manager_v1"))

    print("RESOLVE_PERSONA")
    print(resolve_persona("pop:marketing_manager_v1"))

    print("LOAD_BY_ID")
    print(load_persona_by_id("pop:marketing_manager_v1"))


if __name__ == "__main__":
    main()
