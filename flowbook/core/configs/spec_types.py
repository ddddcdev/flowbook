"""
ConfigStore spec types: each Outer (InputProfile, Mapping, ...) subclasses ConfigSpecKind,
has CONFIG_TYPE and nested Spec(TypedDict).
Typed access: store.configs.get_spec(InputProfile, name) -> InputProfile.Spec.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class ConfigSpecKind:
    """Descriptor base for ConfigStore config types.

    Subclasses must define:
    - CONFIG_TYPE: config type string used in ConfigStore.get_spec/put_spec
    - Spec: nested TypedDict that describes the dict shape for this config type
    """

    CONFIG_TYPE: str = ""
    Spec: type = object  # overridden by nested class in each subclass

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if cls is ConfigSpecKind:
            return

        config_type = getattr(cls, "CONFIG_TYPE", None)
        if not isinstance(config_type, str) or not config_type:
            raise TypeError(f"{cls.__name__!r} must define non-empty CONFIG_TYPE")

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
    CONFIG_TYPE: str = "input_profile"

    class Spec(TypedDict):
        """Spec for config_type='input_profile'. kind_rules required."""

        kind_rules: list[KindRule]
        date_rule: NotRequired[DateRule | dict[str, Any]]
        entity_plan_map_name: NotRequired[str]
        inspect_step_name: NotRequired[str]
        match_mode: NotRequired[str]  # "start" or "search". Profile-level default.


class Mapping(ConfigSpecKind):
    CONFIG_TYPE: str = "mapping"

    class Spec(TypedDict):
        """Spec for config_type='mapping'. ops is list of op configs."""

        ops: list[dict[str, Any]]


class ResultArtifactSpec(TypedDict):
    """One entry in result_artifacts. step and key required; label optional for UI display."""

    step: str
    key: str
    label: NotRequired[str]


class Plan(ConfigSpecKind):
    CONFIG_TYPE: str = "plan"

    class Spec(TypedDict):
        """Spec for config_type='plan'. plan is a plan config.
        result_artifacts: optional list of (step, key) paths to treat as main results.
        When present, these paths are used instead of last step's first output.
        """

        plan: dict[str, Any]
        result_artifacts: NotRequired[list[ResultArtifactSpec]]


class LookupTable(ConfigSpecKind):
    CONFIG_TYPE: str = "lookup_table"

    class Spec(TypedDict):
        """Spec for config_type='lookup_table'. artifact_key points to stored DataFrame."""

        artifact_key: str


class EntityPlanMap(ConfigSpecKind):
    CONFIG_TYPE: str = "entity_plan_map"

    class Spec(TypedDict, total=False):
        """Spec for config_type='entity_plan_map'. map: kind -> plan_name; default fallback."""

        map: dict[str, str]
        default: str | None


# Registry for update_config step: config_type string -> spec_type
CONFIG_TYPE_TO_SPEC_TYPE: dict[str, type[ConfigSpecKind]] = {
    InputProfile.CONFIG_TYPE: InputProfile,
    Mapping.CONFIG_TYPE: Mapping,
    Plan.CONFIG_TYPE: Plan,
    LookupTable.CONFIG_TYPE: LookupTable,
    EntityPlanMap.CONFIG_TYPE: EntityPlanMap,
}
