# POP Agent Runtime Profile (Draft)

## Purpose

The POP Agent Runtime Profile defines a framework-friendly runtime
binding for persona objects.

It is intended for agent frameworks that expect fields such as:

- role
- goal / goals
- backstory / system message
- tools
- communication style
- memory scope

This profile is not the POP canonical object itself.

Instead:

- POP canonical object = protocol-layer persona object
- POP Agent Runtime Profile = runtime-oriented binding for agent frameworks

## Current Field Set

- persona_id
- name
- role
- traits
- goals
- tools
- communication_style
- memory_scope

## Rationale

Frameworks such as CrewAI and AutoGen expose runtime-facing agent
attributes that differ from POP canonical fields.

This profile layer allows POP-based personas to be consumed by such
frameworks without redefining the POP core object itself.
