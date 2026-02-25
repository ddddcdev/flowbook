# Adding custom steps

This guide shows how to add your own steps (ops) so the engine can run them. The **minimal way** is to write a module and call its `register(registry)` once at startup—no packaging or entry points required. If you prefer to ship steps as an installable package, you can use entry points so they are discovered automatically.

**Listing steps**: `flowbook steps list` lists all registered ops. `flowbook steps show <op_name>` shows docstring, inputs (required/optional), and outputs. See [Plan from steps](steps/plan-from-steps.md) for composing plans from steps.

---

## Minimal: run your register at startup (recommended to start)

No packaging needed. Two pieces: a steps module and a single line in your app startup.

### 1. Write a steps module

Create a Python module (e.g. `my_steps.py`) in your project. Define your op(s) and expose a `register` function.

**Option: use the decorator** (good for one or more ops):

```python
# my_steps.py
from flowbook import step, register_from_steps
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase

@step("my_op")
class MyOp(BaseOp):
    class Inputs(InputsBase):
        X = "x"
        REQUIRED = (X,)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        OUT = "out"

    def __call__(self, inputs, store):
        return {self.Outputs.OUT: inputs[self.Inputs.X] * 2}

register = register_from_steps()
```

**Option: hand-written register** (if you prefer):

```python
# my_steps.py
from flowbook import Registry
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase

class MyOp(BaseOp):
    # ... same as above ...

def register(registry: Registry) -> None:
    registry.register("my_op", MyOp())
```

### 2. Call your register when building the engine

Where you create the engine (script or app startup), build the registry, load built-in steps, then call your register once:

```python
from flowbook import Engine, Registry, discover_steps, InMemoryArtifactsStore
from my_steps import register as my_register

registry = Registry()
discover_steps(registry)   # flowbook built-in steps
my_register(registry)      # your steps

engine = Engine(store=InMemoryArtifactsStore(), registry=registry)
```

That’s it. Add or change steps in `my_steps.py`; the next run will use the updated code. No extra install step.

---

## Optional: package with entry points (for distribution / reuse)

If you want your steps in an installable package and discovered automatically (no explicit `my_register(registry)` in app code), use the `flowbook.steps` entry point group.

1. **Implement steps** in your package (e.g. `my_project/steps/`) with a `register(registry)` function, as above.
2. **Declare the entry point** in your package’s `pyproject.toml`:

   ```toml
   [project.entry-points."flowbook.steps"]
   my_project = "my_project.steps:register"
   ```

3. **Install** your package in the same environment as the app (`pip install -e .` or `poetry install`).
4. **App code** only needs `discover_steps(registry)`; your steps are loaded from the entry point.

After the first install, **code changes** in your step modules are picked up on the next run (editable install). Run install again only if you **change** `pyproject.toml` (e.g. add or edit the entry point).

---

## Inputs and Outputs convention

- **Inputs**: Subclass `InputsBase`. Define key constants (e.g. `X = "x"`) and set `REQUIRED` and `OPTIONAL` tuples. Keys must be disjoint.
- **Outputs**: Subclass `OutputsBase`. Define key constants (e.g. `OUT = "out"`). Uppercase str attributes become `KEYS` automatically.
- **Docstring**: Add a class docstring; it appears in `flowbook steps show` and API `GET /steps/{op_name}`.

---

## Summary

| Approach              | Packaging / install | Entry point | What you do at runtime                          |
|-----------------------|--------------------|-------------|--------------------------------------------------|
| **Minimal (recommended)** | None               | None        | `discover_steps(registry)` then `my_register(registry)` |
| **Package + entry point** | Yes, then install  | Yes in pyproject.toml | `discover_steps(registry)` only                  |

Start with the minimal approach; move to entry points when you need a reusable, installable package.
