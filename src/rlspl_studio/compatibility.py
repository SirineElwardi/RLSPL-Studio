"""Shared capability checks for composable RLSPL components."""

from __future__ import annotations

from .descriptors import (
    AlgorithmDescriptor,
    BehaviorDescriptor,
    EnvironmentDescriptor,
    OptimizerDescriptor,
)


def environment_algorithm_reasons(
    environment: EnvironmentDescriptor,
    algorithm: AlgorithmDescriptor,
) -> tuple[str, ...]:
    reasons: list[str] = []
    capabilities = environment.capabilities
    requirements = algorithm.requirements
    if capabilities.action_kind not in requirements.action_kinds:
        reasons.append(f"{capabilities.action_kind.value} actions are not supported")
    if capabilities.observation_kind not in requirements.observation_kinds:
        reasons.append(f"{capabilities.observation_kind.value} observations are not supported")
    if requirements.requires_bounded_actions and not capabilities.action_bounded:
        reasons.append("finite action bounds are required by the algorithm")
    return tuple(reasons)


def behavior_reasons(
    environment: EnvironmentDescriptor,
    algorithm: AlgorithmDescriptor,
    behavior: BehaviorDescriptor,
) -> tuple[str, ...]:
    reasons: list[str] = []
    requirements = behavior.requirements
    interface = algorithm.composition.policy_interface
    action_kind = environment.capabilities.action_kind
    if interface not in requirements.policy_interfaces:
        reasons.append(
            f"behavior requires {', '.join(sorted(item.value for item in requirements.policy_interfaces))}; "
            f"algorithm exposes {interface.value}"
        )
    if action_kind not in requirements.action_kinds:
        reasons.append(
            f"behavior does not support {action_kind.value} actions"
        )
    if requirements.requires_bounded_actions and not environment.capabilities.action_bounded:
        reasons.append("behavior requires finite action bounds")
    if requirements.requires_perturbable_policy and not algorithm.composition.perturbable_policy:
        reasons.append("behavior requires a perturbable policy model")
    return tuple(reasons)


def composition_reasons(
    environment: EnvironmentDescriptor,
    algorithm: AlgorithmDescriptor,
    behavior: BehaviorDescriptor,
) -> tuple[str, ...]:
    return environment_algorithm_reasons(environment, algorithm) + behavior_reasons(
        environment, algorithm, behavior
    )


def optimizer_reasons(
    algorithm: AlgorithmDescriptor,
    optimizer: OptimizerDescriptor,
) -> tuple[str, ...]:
    interface = algorithm.composition.optimizer_interface
    if interface not in optimizer.requirements.interfaces:
        required = ", ".join(
            sorted(item.value for item in optimizer.requirements.interfaces)
        )
        return (
            f"optimizer requires {required}; algorithm exposes {interface.value}",
        )
    return ()


def product_reasons(
    environment: EnvironmentDescriptor,
    algorithm: AlgorithmDescriptor,
    behavior: BehaviorDescriptor,
    optimizer: OptimizerDescriptor,
) -> tuple[str, ...]:
    """Return all capability failures for one complete product selection."""

    return composition_reasons(environment, algorithm, behavior) + optimizer_reasons(
        algorithm, optimizer
    )
