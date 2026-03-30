# Extension Guide

This page highlights the current project shape and where future refactors may help.

## Current strengths

- very direct development flow
- easy to follow for a small team
- backend, UI, and domain logic are all close together
- fast iteration speed

## Current pressure points

### `backend/main.py` is central

A lot of logic currently lives in one file:

- models
- MQTT logic
- routes
- some migration logic

That is manageable right now, but it increases change risk as the project grows.

## Good future split candidates

If the codebase keeps growing, a natural next structure would be:

```text
backend/
  main.py
  docs_app.py
  db.py
  models.py
  mqtt.py
  routes/
    devices.py
    tags.py
    laufzettel.py
    katalog.py
    pages.py
```

## Refactor rule of thumb

Refactor when one of these starts happening regularly:

- many unrelated changes touch `main.py`
- route sections become hard to navigate
- model logic starts duplicating behavior
- test setup becomes harder than feature work

## Documentation rule of thumb

Whenever you change one of these areas, update the docs in the same PR/change set:

- UI behavior
- MQTT topic contracts
- DB schema
- startup/deploy instructions
- material pricing rules
