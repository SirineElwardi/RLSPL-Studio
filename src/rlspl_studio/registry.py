"""In-memory registry for declarative RLSPL components."""

from __future__ import annotations

from .descriptors import (
    AlgorithmDescriptor,
    BehaviorDescriptor,
    EnvironmentDescriptor,
    OptimizerDescriptor,
)
from .models import OptimizerInterface, PolicyInterface, ValidationIssue


class ComponentRegistry:
    def __init__(self) -> None:
        self._environments: dict[str, EnvironmentDescriptor] = {}
        self._algorithms: dict[str, AlgorithmDescriptor] = {}
        self._behaviors: dict[str, BehaviorDescriptor] = {}
        self._optimizers: dict[str, OptimizerDescriptor] = {}
        self._search_providers: set[str] = {"core.random", "core.bayesian_tpe"}
        self._origins: dict[str, str] = {}
        self._plugin_diagnostics: list[ValidationIssue] = []

    def register_environment(
        self, descriptor: EnvironmentDescriptor, *, origin: str = "builtin"
    ) -> None:
        self._register_unique(self._environments, descriptor.id, descriptor)
        self._origins[descriptor.id] = origin

    def register_algorithm(
        self, descriptor: AlgorithmDescriptor, *, origin: str = "builtin"
    ) -> None:
        composition_updates: dict[str, str] = {}
        if (
            descriptor.composition.policy_interface is PolicyInterface.ALGORITHM_OWNED
            and descriptor.composition.default_behavior_id is None
        ):
            composition_updates["default_behavior_id"] = "rlspl.behavior.algorithm_owned"
        if (
            descriptor.composition.optimizer_interface
            is OptimizerInterface.ALGORITHM_OWNED
            and descriptor.composition.default_optimizer_id is None
        ):
            composition_updates["default_optimizer_id"] = "rlspl.optimizer.algorithm_owned"
        if composition_updates:
            descriptor = descriptor.model_copy(update={
                "composition": descriptor.composition.model_copy(
                    update=composition_updates
                )
            })
        self._register_unique(self._algorithms, descriptor.id, descriptor)
        self._origins[descriptor.id] = origin

    def register_behavior(
        self, descriptor: BehaviorDescriptor, *, origin: str = "builtin"
    ) -> None:
        self._register_unique(self._behaviors, descriptor.id, descriptor)
        self._origins[descriptor.id] = origin

    def register_optimizer(
        self, descriptor: OptimizerDescriptor, *, origin: str = "builtin"
    ) -> None:
        self._register_unique(self._optimizers, descriptor.id, descriptor)
        self._origins[descriptor.id] = origin

    def register_search_provider(self, provider_id: str) -> None:
        if not provider_id:
            raise ValueError("provider_id cannot be empty")
        self._search_providers.add(provider_id)

    def environment(self, component_id: str) -> EnvironmentDescriptor | None:
        return self._environments.get(component_id)

    def algorithm(self, component_id: str) -> AlgorithmDescriptor | None:
        return self._algorithms.get(component_id)

    def behavior(self, component_id: str) -> BehaviorDescriptor | None:
        return self._behaviors.get(component_id)

    def optimizer(self, component_id: str) -> OptimizerDescriptor | None:
        return self._optimizers.get(component_id)

    def has_search_provider(self, provider_id: str) -> bool:
        return provider_id in self._search_providers

    def origin(self, component_id: str) -> str:
        return self._origins.get(component_id, "unknown")

    def add_plugin_diagnostic(self, diagnostic: ValidationIssue) -> None:
        self._plugin_diagnostics.append(diagnostic)

    @property
    def environments(self) -> tuple[EnvironmentDescriptor, ...]:
        return tuple(self._environments.values())

    @property
    def algorithms(self) -> tuple[AlgorithmDescriptor, ...]:
        return tuple(self._algorithms.values())

    @property
    def behaviors(self) -> tuple[BehaviorDescriptor, ...]:
        return tuple(self._behaviors.values())

    @property
    def optimizers(self) -> tuple[OptimizerDescriptor, ...]:
        return tuple(self._optimizers.values())

    @property
    def plugin_diagnostics(self) -> tuple[ValidationIssue, ...]:
        return tuple(self._plugin_diagnostics)

    @staticmethod
    def _register_unique(store: dict[str, object], key: str, value: object) -> None:
        if key in store:
            raise ValueError(f"component already registered: {key}")
        store[key] = value
