"""
ConfigStore spec types: each Outer (InputProfile, Mapping, ...) subclasses ConfigSpecKind,
has KIND and nested Spec(TypedDict).
Typed access: store.configs.get_spec(InputProfile, name) -> InputProfile.Spec.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class ConfigSpecKind:
    """Descriptor base for ConfigStore kinds.

    Subclasses must define:
    - KIND: kind string used in ConfigStore.get_spec/put_spec
    - Spec: nested TypedDict that describes the dict shape for this kind
    """

    KIND: str = ""
    Spec: type = object  # overridden by nested class in each subclass

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if cls is ConfigSpecKind:
            return

        kind = getattr(cls, "KIND", None)
        if not isinstance(kind, str) or not kind:
            raise TypeError(f"{cls.__name__!r} must define non-empty KIND")

        spec = getattr(cls, "Spec", None)
        if spec is None or spec is object:
            raise TypeError(f"{cls.__name__!r} must define nested Spec(TypedDict)")


class KindRule(TypedDict, total=False):
    """One entry in input_profile.kind_rules."""

    pattern: str
    kind: str
    plan_name: str
    match_mode: str  # "start" (re.match) or "search" (re.search). Default "start".


class DateRule(TypedDict, total=False):
    """Optional date_rule in input_profile (sheet/cell for Excel)."""

    sheet: str
    cell: str


class InputProfile(ConfigSpecKind):
    KIND: str = "input_profile"

    class Spec(TypedDict):
        """Spec for kind='input_profile'. kind_rules required."""

        kind_rules: list[KindRule]
        date_rule: NotRequired[DateRule | dict[str, Any]]
        entity_plan_map_name: NotRequired[str]
        inspect_step_name: NotRequired[str]
        match_mode: NotRequired[str]  # "start" or "search". Profile-level default.


class Mapping(ConfigSpecKind):
    KIND: str = "mapping"

    class Spec(TypedDict):
        """Spec for kind='mapping'. ops is list of op configs."""

        ops: list[dict[str, Any]]


class ResultArtifactSpec(TypedDict):
    """One entry in result_artifacts. step and key required; label optional for UI display."""

    step: str
    key: str
    label: NotRequired[str]


class Plan(ConfigSpecKind):
    KIND: str = "plan"

    class Spec(TypedDict):
        """Spec for kind='plan'. plan is a plan config.
        result_artifacts: optional list of (step, key) paths to treat as main results.
        When present, these paths are used instead of last step's first output.
        """

        plan: dict[str, Any]
        result_artifacts: NotRequired[list[ResultArtifactSpec]]


class LookupTable(ConfigSpecKind):
    KIND: str = "lookup_table"

    class Spec(TypedDict):
        """Spec for kind='lookup_table'. artifact_key points to stored DataFrame."""

        artifact_key: str


class EntityPlanMap(ConfigSpecKind):
    KIND: str = "entity_plan_map"

    class Spec(TypedDict, total=False):
        """Spec for kind='entity_plan_map'. map: kind -> plan_name; default fallback."""

        map: dict[str, str]
        default: str | None


# Deprecated alias for backward compatibility
Routing = EntityPlanMap
