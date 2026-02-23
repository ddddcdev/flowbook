# ADR-RUN-SESSION-CONTEXT-MANAGER: Run session as context manager (with)

## Status

Accepted.

## Terminology and hierarchy

```
Engine
  └── (create) Run (run_id scope)
        └── (exec) Plan (plan_config)
              └── (exec) Step (each step in plan)
```

| Term | Role | Created / executed by |
|------|------|------------------------|
| **Engine** | Entry point. Holds store, registry, config_store. | Application setup |
| **Run** | Single execution session (run_id). Scopes artifacts. | `Engine.create_run()` |
| **Plan** | List of steps with name, op, inputs. | `RunSession.exec_plan()` or `exec_with_planner_once()` |
| **Step** | Single operation (op) with inputs/outputs. | `execute_plan()` (internal) |

- **RunSession** = the API object for a Run. Variable names may be `run` or `session`.
- One run may execute multiple plans (e.g. planner + plan in `exec_with_planner_once`).

## Context

- **RunSession** is the high-level API for a single run (run_id scope). It is created by `Engine.create_run()`.
- A run has a clear lifecycle: started when created, ended when work is done.
- Previously, there was no explicit "run ended" boundary. Plan execution completion does not define run end (one run may execute multiple plans).
- Session end is a natural place for: (1) "run ended" logging, (2) future artifact cleanup, (3) resource teardown.

## Decision

### Use context manager (`with`)

- **RunSession** implements `__enter__` and `__exit__`.
- Callers use `with engine.create_run() as session:` (or `run`) to scope the run.
- On `__exit__`: log "run ended", optionally perform cleanup (e.g., remove temporary artifacts).
- Exception handling: `__exit__` is always called, so cleanup runs even on failure.

### Usage

```python
with engine.create_run(entity_key="default") as session:
    session.put_input("name", value)
    info = session.exec_plan(plan_config=config)
```

### Rationale

1. **Explicit boundary**: Clear "run started" / "run ended" pair in logs.
2. **Resource safety**: Future cleanup (temp files, connections) guaranteed via `__exit__`.
3. **Exception safety**: `with` ensures teardown even when exceptions occur.
4. **Consistency**: All call sites follow the same pattern.

## Consequences

- All call sites (API routes, tests) use `with engine.create_run() as ...`.
- RunSession remains usable without `with` for backward compatibility, but `with` is the recommended pattern.
- Future: artifact cleanup logic can be added to `__exit__` without changing call sites.
