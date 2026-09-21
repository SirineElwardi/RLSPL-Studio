"""Declarative component contracts used by the registry and resolver."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .models import (
    ActionKind,
    EvaluationActionMode,
    FrozenModel,
    ObservationKind,
    OptimizerInterface,
    ParameterType,
    PolicyInterface,
)


class ParameterDefinition(FrozenModel):
    id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    type: ParameterType
    required: bool = True
    default: Any | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    choices: tuple[Any, ...] = ()
    tunable: bool = True
    description: str = ""

    @model_validator(mode="after")
    def definition_is_coherent(self) -> "ParameterDefinition":
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("minimum cannot exceed maximum")
        if self.type is ParameterType.CATEGORICAL and not self.choices:
            raise ValueError("categorical parameters require choices")
        if self.type is not ParameterType.CATEGORICAL and self.choices:
            raise ValueError("choices are only valid for categorical parameters")
        if self.required and self.default is None:
            raise ValueError("required parameters require a default")
        return self


class EnvironmentCapabilities(FrozenModel):
    action_kind: ActionKind
    observation_kind: ObservationKind
    action_bounded: bool = False
    observation_dimensions: int | None = Field(default=None, gt=0)
    discrete_action_count: int | None = Field(default=None, gt=0)
    maximum_episode_steps: int | None = Field(default=None, gt=0)
    success_signal: bool = False
    # Human-readable semantics for the boolean emitted by the generated
    # environment adapter. Optional so existing third-party 1.0 manifests
    # remain valid; built-in environments always declare it when available.
    success_definition: str | None = None


class AlgorithmRequirements(FrozenModel):
    action_kinds: frozenset[ActionKind]
    observation_kinds: frozenset[ObservationKind]
    requires_bounded_actions: bool = False
    vector_observation_adapter: str | None = None
    supports_budget_units: frozenset[str] = frozenset({"episodes"})


class AlgorithmComposition(FrozenModel):
    architecture_roles: tuple[str, ...]
    optimizer_roles: tuple[str, ...] = ()
    # Retained as a readable legacy summary for third-party 1.0 manifests.
    # Executable action selection is represented by BehaviorDescriptor.
    exploration_role: str = "algorithm_owned"
    policy_interface: PolicyInterface = PolicyInterface.ALGORITHM_OWNED
    perturbable_policy: bool = False
    default_behavior_id: str | None = None
    optimizer_interface: OptimizerInterface = OptimizerInterface.ALGORITHM_OWNED
    default_optimizer_id: str | None = None
    evaluation_modes: frozenset[EvaluationActionMode] = frozenset({
        EvaluationActionMode.DETERMINISTIC
    })
    memory_role: str | None = None
    target_update: str | None = None
    checkpoint_roles: tuple[str, ...] = ()
    conditional_roles: dict[str, str] = Field(default_factory=dict)


class ComponentDescriptor(FrozenModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = ""
    contract_version: str = "1.0"
    parameters: tuple[ParameterDefinition, ...] = ()
    dependencies: dict[str, str] = Field(default_factory=dict)


class EnvironmentRuntimeAssets(FrozenModel):
    adapter_template: str
    template_root: str | None = Field(default=None, exclude=True)


class AlgorithmRuntimeAssets(FrozenModel):
    agent_template: str
    trainer_template: str
    checkpoint_filename: str
    template_root: str | None = Field(default=None, exclude=True)


class BehaviorRequirements(FrozenModel):
    policy_interfaces: frozenset[PolicyInterface]
    action_kinds: frozenset[ActionKind]
    requires_bounded_actions: bool = False
    requires_perturbable_policy: bool = False


class BehaviorRuntimeAssets(FrozenModel):
    behavior_template: str
    template_root: str | None = Field(default=None, exclude=True)


class OptimizerRequirements(FrozenModel):
    interfaces: frozenset[OptimizerInterface]


class OptimizerRuntimeAssets(FrozenModel):
    optimizer_template: str
    template_root: str | None = Field(default=None, exclude=True)


class EnvironmentDescriptor(ComponentDescriptor):
    capabilities: EnvironmentCapabilities
    entry_point: str
    runtime_assets: EnvironmentRuntimeAssets | None = None


class AlgorithmDescriptor(ComponentDescriptor):
    requirements: AlgorithmRequirements
    composition: AlgorithmComposition
    entry_point: str
    verified_environment_ids: frozenset[str] = frozenset()
    runtime_assets: AlgorithmRuntimeAssets | None = None


class BehaviorDescriptor(ComponentDescriptor):
    """Composable action-selection behavior with a capability contract."""

    category: str = Field(min_length=1)
    public: bool = True
    requirements: BehaviorRequirements
    runtime_assets: BehaviorRuntimeAssets | None = None
    source_ids: tuple[str, ...] = ()


class OptimizerDescriptor(ComponentDescriptor):
    """Composable parameter-update rule with an explicit algorithm contract."""

    category: str = Field(min_length=1)
    public: bool = True
    requirements: OptimizerRequirements
    runtime_assets: OptimizerRuntimeAssets | None = None
    source_ids: tuple[str, ...] = ()
