"""Artifact key format: {run_id}/{entity_key}/{path}.

- Outputs: run_id/entity_key/step/out (path = step/out, entity_key may contain slashes)
- Inputs (run-level): run_id//input/name (entity_key is empty string)
"""


def parse_artifact_key(key: str) -> tuple[str, str, str]:
    """Parse key into (run_id, entity_key, path). Raises ValueError if invalid.
    - 3 segments: run_id/entity_key/path (path is single segment)
    - 4+ segments: run_id/entity_key/step/out (path = last two; entity_key may contain slashes)
    - Empty entity_key: run_id//path
    """
    parts = key.split("/")
    if len(parts) < 3:
        raise ValueError(f"invalid artifact key format (expected run_id/entity_key/path): {key}")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    run_id = parts[0]
    if parts[1] == "":
        entity_key = ""
        path = "/".join(parts[2:])
    else:
        entity_key = "/".join(parts[1:-2])
        path = "/".join(parts[-2:])
    return run_id, entity_key, path


def build_artifact_key(run_id: str, entity_key: str, path: str) -> str:
    """Build key from components."""
    return f"{run_id}/{entity_key}/{path}"
