# apps/cli

This directory is a placeholder for a future CLI host.

## Intent
- The CLI is a host application, same level as `apps/api`.
- It uses `flowbook` as a library and may use `adapters/common` for pure-Python mappings.
- It must not depend on `adapters/fastapi` or any HTTP-specific contracts.

## Rules
- Orchestration/state lives in the host (`apps/cli`).
- Adapters are only for shape conversion and error translation.
- `flowbook` returns `run_info` without embedding real data; data lives only in artifacts.
