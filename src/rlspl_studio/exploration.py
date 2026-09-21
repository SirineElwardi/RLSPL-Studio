"""Constraint-aware expansion of finite RLSPL exploration studies."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from datetime import datetime, timezone
from typing import Any, Iterable

from pydantic import ValidationError

from .catalog import (
    ALGORITHM_OWNED,
    ALGORITHM_OWNED_OPTIMIZER,
    core_training_parameters,
)
from .models import (
    DuplicateStudyCandidate,
    ExplorationStudy,
    IssueSeverity,
    ParameterBinding,
    RejectedStudyCandidate,
    StudyManifest,
    StudyPlanSummary,
    StudyVariant,
    UserConfiguration,
    ValidationIssue,
)
from .registry import ComponentRegistry
from .resolver import ConfigurationResolver


STRUCTURAL_TARGETS = frozenset({
    "environment.component_id",
    "algorithm.component_id",
    "behavior.component_id",
    "optimizer.component_id",
    "training.budget",
    "training.budget_unit",
    "training.checkpoint_policy",
    "training.checkpoint_interval",
    "evaluation.episodes_per_seed",
})
COMPONENT_TARGETS = frozenset({
    "environment.component_id",
    "algorithm.component_id",
    "behavior.component_id",
    "optimizer.component_id",
})


class StudyPlanningError(ValueError):
    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


class StudyPlanner:
    """Expand explicit axes, resolve candidates, and retain configuration lineage."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry
        self.resolver = ConfigurationResolver(registry)

    def available_axes(self) -> tuple[dict[str, Any], ...]:
        referenced_behaviors = {
            item.composition.default_behavior_id
            for item in self.registry.algorithms
            if item.composition.default_behavior_id
        }
        referenced_optimizers = {
            item.composition.default_optimizer_id
            for item in self.registry.algorithms
            if item.composition.default_optimizer_id
        }
        structural = (
            {
                "target": "environment.component_id",
                "display_name": "Environment",
                "kind": "structural",
                "type": "categorical",
                "choices": [item.id for item in self.registry.environments],
            },
            {
                "target": "algorithm.component_id",
                "display_name": "Algorithm",
                "kind": "structural",
                "type": "categorical",
                "choices": [item.id for item in self.registry.algorithms],
            },
            {
                "target": "behavior.component_id",
                "display_name": "Action-selection behavior",
                "kind": "structural",
                "type": "categorical",
                "choices": [
                    item.id for item in self.registry.behaviors
                    if item.public or item.id in referenced_behaviors
                ],
            },
            {
                "target": "optimizer.component_id",
                "display_name": "Optimizer / update rule",
                "kind": "structural",
                "type": "categorical",
                "choices": [
                    item.id for item in self.registry.optimizers
                    if item.public or item.id in referenced_optimizers
                ],
            },
            {
                "target": "training.budget",
                "display_name": "Training budget",
                "kind": "structural",
                "type": "integer",
                "default": 500,
                "minimum": 1,
            },
            {
                "target": "training.budget_unit",
                "display_name": "Budget unit",
                "kind": "structural",
                "type": "categorical",
                "default": "episodes",
                "choices": ["episodes", "timesteps"],
            },
            {
                "target": "training.checkpoint_policy",
                "display_name": "Checkpoint policy",
                "kind": "structural",
                "type": "categorical",
                "default": "best",
                "choices": ["disabled", "best", "periodic"],
            },
            {
                "target": "training.checkpoint_interval",
                "display_name": "Checkpoint interval",
                "kind": "structural",
                "type": "integer",
                "default": 100,
                "minimum": 1,
            },
            {
                "target": "evaluation.episodes_per_seed",
                "display_name": "Evaluation episodes per seed",
                "kind": "evaluation",
                "type": "integer",
                "default": 10,
                "minimum": 1,
            },
        )
        definitions: dict[str, Any] = {
            definition.id: definition for definition in core_training_parameters()
            if definition.id != "training.seed"
        }
        for environment in self.registry.environments:
            definitions.update({definition.id: definition for definition in environment.parameters})
        for algorithm in self.registry.algorithms:
            definitions.update({definition.id: definition for definition in algorithm.parameters})
        for behavior in self.registry.behaviors:
            definitions.update({definition.id: definition for definition in behavior.parameters})
        for optimizer in self.registry.optimizers:
            definitions.update({definition.id: definition for definition in optimizer.parameters})
        parameters = tuple({
            "target": definition.id,
            "display_name": definition.id,
            "kind": "parameter",
            "type": definition.type.value,
            "default": definition.default,
            "minimum": definition.minimum,
            "maximum": definition.maximum,
            "choices": list(definition.choices),
            "owner": definition.owner,
            "description": definition.description,
        } for definition in definitions.values())
        return structural + parameters

    def plan(self, study: ExplorationStudy, limit: int = 500) -> StudyManifest:
        if limit < 1:
            raise StudyPlanningError("EXP-02", "limit", "preview limit must be at least one")
        known_targets = {item["target"] for item in self.available_axes()}
        component_choices = {
            item["target"]: set(item["choices"])
            for item in self.available_axes()
            if item["target"] in COMPONENT_TARGETS
        }
        canonical_targets: set[str] = set()
        for index, axis in enumerate(study.axes):
            canonical_target = self._canonical_target(axis.target)
            if canonical_target not in known_targets:
                raise StudyPlanningError(
                    "EXP-01",
                    f"axes.{index}.target",
                    f"unknown exploration target: {axis.target}",
                )
            if canonical_target in canonical_targets:
                raise StudyPlanningError(
                    "EXP-01",
                    f"axes.{index}.target",
                    f"exploration target is repeated through an alias: {axis.target}",
                )
            canonical_targets.add(canonical_target)
            if canonical_target in COMPONENT_TARGETS and axis.when:
                raise StudyPlanningError(
                    "EXP-01",
                    f"axes.{index}.when",
                    "component-selection axes cannot be conditional",
                )
            for condition_index, condition in enumerate(axis.when):
                invalid_values = [
                    value
                    for value in condition.values
                    if value not in component_choices[condition.target]
                ]
                if invalid_values:
                    raise StudyPlanningError(
                        "EXP-01",
                        f"axes.{index}.when.{condition_index}.values",
                        f"condition references unknown components: {invalid_values}",
                    )

        candidate_count, assignments = self._candidate_assignments(study)
        assignments = itertools.islice(assignments, limit)
        variants: list[StudyVariant] = []
        rejected: list[RejectedStudyCandidate] = []
        duplicates: list[DuplicateStudyCandidate] = []
        seen: dict[str, str] = {}

        for candidate_index, assignment in enumerate(assignments):
            axis_values = {
                axis.target: assignment[self._canonical_target(axis.target)]
                for axis in study.axes
                if self._canonical_target(axis.target) in assignment
            }
            payload = self._candidate_payload(study, assignment)
            try:
                for target, value in assignment.items():
                    if target in STRUCTURAL_TARGETS:
                        self._assign(payload, target, value)
                self._prune_inactive_parameters(payload)
                for target, value in assignment.items():
                    if target not in STRUCTURAL_TARGETS:
                        self._assign(payload, target, value)
                configuration = UserConfiguration.model_validate(payload)
            except ValidationError as exc:
                rejected.append(RejectedStudyCandidate(
                    candidate_index=candidate_index,
                    axis_values=axis_values,
                    issues=self._schema_issues(exc),
                ))
                continue

            result = self.resolver.resolve(configuration)
            if not result.report.is_valid or result.resolved is None:
                rejected.append(RejectedStudyCandidate(
                    candidate_index=candidate_index,
                    axis_values=axis_values,
                    issues=result.report.errors,
                ))
                continue

            semantic_hash = self._semantic_hash(result.resolved.model_dump(mode="json"))
            configuration_id = f"cfg-{semantic_hash[:12]}"
            if semantic_hash in seen:
                duplicates.append(DuplicateStudyCandidate(
                    candidate_index=candidate_index,
                    axis_values=axis_values,
                    duplicate_of=seen[semantic_hash],
                ))
                continue
            seen[semantic_hash] = configuration_id
            variants.append(StudyVariant(
                candidate_index=candidate_index,
                configuration_id=configuration_id,
                axis_values=axis_values,
                configuration=result.resolved,
                advisories=result.report.advisories,
            ))

        evaluated = len(variants) + len(rejected) + len(duplicates)
        complete = evaluated == candidate_count
        advisories: tuple[ValidationIssue, ...] = ()
        if not complete:
            advisories = (ValidationIssue(
                severity=IssueSeverity.ADVISORY,
                code="EXP-03",
                path="axes",
                message=(
                    f"the study defines {candidate_count} candidates; "
                    f"this manifest contains the first {evaluated}"
                ),
                suggestion="Increase the preview limit to materialize more candidates.",
            ),)
        summary = StudyPlanSummary(
            candidate_count=candidate_count,
            evaluated_candidate_count=evaluated,
            valid_candidate_count=len(variants) + len(duplicates),
            invalid_candidate_count=len(rejected),
            duplicate_candidate_count=len(duplicates),
            unique_configuration_count=len(variants),
            planned_run_count=(
                len(variants) * len(study.replications.seeds)
            ),
            expansion_complete=complete,
        )
        study_hash = self._stable_hash(study.model_dump(mode="json"))
        manifest_hash = self._stable_hash({
            "study_hash": study_hash,
            "summary": summary.model_dump(mode="json"),
            "variants": [item.model_dump(mode="json") for item in variants],
            "rejected_candidates": [item.model_dump(mode="json") for item in rejected],
            "duplicate_candidates": [item.model_dump(mode="json") for item in duplicates],
            "advisories": [item.model_dump(mode="json") for item in advisories],
        })
        return StudyManifest(
            study_hash=study_hash,
            manifest_hash=manifest_hash,
            created_at=datetime.now(timezone.utc),
            study=study,
            summary=summary,
            variants=tuple(variants),
            rejected_candidates=tuple(rejected),
            duplicate_candidates=tuple(duplicates),
            advisories=advisories,
        )

    def _candidate_assignments(
        self, study: ExplorationStudy
    ) -> tuple[int, Iterable[dict[str, Any]]]:
        component_axes = tuple(
            axis
            for axis in study.axes
            if self._canonical_target(axis.target) in COMPONENT_TARGETS
        )
        other_axes = tuple(axis for axis in study.axes if axis not in component_axes)
        component_products = itertools.product(
            *(axis.values for axis in component_axes)
        )
        base_context: dict[str, Any] = {}
        if study.base_configuration is not None:
            base_algorithm = self.registry.algorithm(
                study.base_configuration.algorithm.component_id
            )
            base_context = {
                "environment.component_id": study.base_configuration.environment.component_id,
                "algorithm.component_id": study.base_configuration.algorithm.component_id,
                "behavior.component_id": (
                    study.base_configuration.behavior.component_id
                    if study.base_configuration.behavior is not None
                    else (
                        base_algorithm.composition.default_behavior_id
                        if base_algorithm is not None
                        and base_algorithm.composition.default_behavior_id
                        else ALGORITHM_OWNED
                    )
                ),
                "optimizer.component_id": (
                    study.base_configuration.optimizer.component_id
                    if study.base_configuration.optimizer is not None
                    else (
                        base_algorithm.composition.default_optimizer_id
                        if base_algorithm is not None
                        and base_algorithm.composition.default_optimizer_id
                        else ALGORITHM_OWNED_OPTIMIZER
                    )
                ),
            }
        plans: list[tuple[dict[str, Any], tuple[Any, ...]]] = []
        applicability = {axis.target: 0 for axis in other_axes}
        candidate_count = 0
        for values in component_products:
            component_assignment = {
                self._canonical_target(axis.target): value
                for axis, value in zip(component_axes, values)
            }
            context = {**base_context, **component_assignment}
            if "behavior.component_id" not in context:
                selected_algorithm = self.registry.algorithm(
                    context.get("algorithm.component_id", "")
                )
                context["behavior.component_id"] = (
                    selected_algorithm.composition.default_behavior_id
                    if selected_algorithm is not None
                    and selected_algorithm.composition.default_behavior_id
                    else ALGORITHM_OWNED
                )
            if "optimizer.component_id" not in context:
                selected_algorithm = self.registry.algorithm(
                    context.get("algorithm.component_id", "")
                )
                context["optimizer.component_id"] = (
                    selected_algorithm.composition.default_optimizer_id
                    if selected_algorithm is not None
                    and selected_algorithm.composition.default_optimizer_id
                    else ALGORITHM_OWNED_OPTIMIZER
                )
            applicable_axes = tuple(
                axis for axis in other_axes if self._conditions_match(axis.when, context)
            )
            for axis in applicable_axes:
                applicability[axis.target] += 1
            candidate_count += math.prod(len(axis.values) for axis in applicable_axes)
            plans.append((component_assignment, applicable_axes))
        for index, axis in enumerate(study.axes):
            if axis in other_axes and applicability[axis.target] == 0:
                raise StudyPlanningError(
                    "EXP-01",
                    f"axes.{index}.when",
                    f"axis conditions never match the selected component space: {axis.target}",
                )

        def generate() -> Iterable[dict[str, Any]]:
            for component_assignment, applicable_axes in plans:
                value_products = itertools.product(
                    *(axis.values for axis in applicable_axes)
                )
                for values in value_products:
                    assignment = dict(component_assignment)
                    assignment.update({
                        self._canonical_target(axis.target): value
                        for axis, value in zip(applicable_axes, values)
                    })
                    yield assignment

        return candidate_count, generate()

    def _candidate_payload(
        self,
        study: ExplorationStudy,
        assignment: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a candidate without coupling v2 studies to Configure state."""

        if study.base_configuration is not None:
            return study.base_configuration.model_dump(mode="json")
        environment_id = assignment["environment.component_id"]
        algorithm_id = assignment["algorithm.component_id"]
        environment = self.registry.environment(environment_id)
        algorithm = self.registry.algorithm(algorithm_id)
        behavior_id = assignment.get("behavior.component_id")
        if behavior_id is None:
            behavior_id = (
                algorithm.composition.default_behavior_id
                if algorithm is not None and algorithm.composition.default_behavior_id
                else ALGORITHM_OWNED
            )
        optimizer_id = assignment.get("optimizer.component_id")
        if optimizer_id is None:
            optimizer_id = (
                algorithm.composition.default_optimizer_id
                if algorithm is not None and algorithm.composition.default_optimizer_id
                else ALGORITHM_OWNED_OPTIMIZER
            )
        metrics = ["average_reward", "environment_steps"]
        if environment is not None and environment.capabilities.success_signal:
            metrics.insert(1, "success_rate")
        evaluation_summaries = ["mean"]
        if len(study.replications.evaluation_seeds) > 1:
            evaluation_summaries.extend(["standard_deviation", "confidence_interval"])
        return {
            "schema_version": "1.0",
            "name": f"{study.name}-product",
            "environment": {
                "source": "catalog",
                "component_id": environment_id,
                "parameters": {},
            },
            "algorithm": {"component_id": algorithm_id},
            "behavior": {"component_id": behavior_id},
            "optimizer": {"component_id": optimizer_id},
            "training": {
                "budget_unit": "episodes",
                "budget": 500,
                "parameters": {},
                "checkpoint_policy": "best",
                "checkpoint_interval": None,
            },
            "search": None,
            "evaluation": {
                "protocol": "configurable",
                "metrics": metrics,
                "summaries": evaluation_summaries,
                "visualizations": ["learning_curve", "reward_distribution"],
                "export_formats": ["json", "csv", "png"],
                "seeds": list(study.replications.evaluation_seeds),
                "episodes_per_seed": 10,
                "collect_reward_trace": True,
                "comparison_run_ids": [],
            },
        }

    @staticmethod
    def defaults() -> dict[str, Any]:
        """Explain the fixed defaults used when a v2 study omits an axis."""

        return {
            "training_budget_unit": "episodes",
            "training_budget": 500,
            "checkpoint_policy": "best",
            "evaluation_episodes_per_seed": 10,
            "evaluation_seeds": [100, 101, 102],
            "evaluation_metric_policy": (
                "average reward and environment steps for every environment; "
                "success rate only when the environment declares a success signal"
            ),
            "evaluation_summary_policy": (
                "mean for every study; standard deviation and confidence interval "
                "when at least two evaluation seeds are selected"
            ),
            "parameter_policy": "active component catalog defaults",
            "behavior_policy": "the selected algorithm's declared default behavior",
            "optimizer_policy": "the selected algorithm's declared default optimizer/update rule",
        }

    @staticmethod
    def _conditions_match(
        conditions: tuple[Any, ...], context: dict[str, Any]
    ) -> bool:
        return all(context[condition.target] in condition.values for condition in conditions)

    @staticmethod
    def _canonical_target(target: str) -> str:
        prefix = "training.parameters."
        return target[len(prefix):] if target.startswith(prefix) else target

    @staticmethod
    def _assign(payload: dict[str, Any], target: str, value: Any) -> None:
        if target in STRUCTURAL_TARGETS:
            section, field = target.split(".", 1)
            payload.setdefault(section, {})[field] = value
            return
        payload["training"]["parameters"][target] = ParameterBinding(
            mode="fixed", value=value
        ).model_dump(mode="json")

    def _prune_inactive_parameters(self, payload: dict[str, Any]) -> None:
        core_ids = {definition.id for definition in core_training_parameters()}
        active_ids = set(core_ids)
        known_component_ids: set[str] = set()
        for item in self.registry.environments:
            known_component_ids.update(definition.id for definition in item.parameters)
        for item in self.registry.algorithms:
            known_component_ids.update(definition.id for definition in item.parameters)
        for item in self.registry.behaviors:
            known_component_ids.update(definition.id for definition in item.parameters)
        for item in self.registry.optimizers:
            known_component_ids.update(definition.id for definition in item.parameters)
        legacy_behavior_ids = {
            "q_learning.epsilon_start",
            "q_learning.epsilon_end",
            "q_learning.epsilon_decay",
            "dqn.epsilon_start",
            "dqn.epsilon_end",
            "dqn.epsilon_decay",
            "ddpg.ou_theta",
            "ddpg.ou_sigma",
        }
        known_component_ids.update(legacy_behavior_ids)
        environment = self.registry.environment(payload["environment"]["component_id"])
        algorithm = self.registry.algorithm(payload["algorithm"]["component_id"])
        behavior_id = (payload.get("behavior") or {}).get("component_id")
        if behavior_id is None and algorithm is not None:
            behavior_id = algorithm.composition.default_behavior_id or ALGORITHM_OWNED
        behavior = self.registry.behavior(behavior_id) if behavior_id else None
        optimizer_id = (payload.get("optimizer") or {}).get("component_id")
        if optimizer_id is None and algorithm is not None:
            optimizer_id = (
                algorithm.composition.default_optimizer_id
                or ALGORITHM_OWNED_OPTIMIZER
            )
        optimizer = self.registry.optimizer(optimizer_id) if optimizer_id else None
        if environment is not None:
            active_ids.update(definition.id for definition in environment.parameters)
        if algorithm is not None:
            active_ids.update(definition.id for definition in algorithm.parameters)
        if behavior is not None:
            active_ids.update(definition.id for definition in behavior.parameters)
        if optimizer is not None:
            active_ids.update(definition.id for definition in optimizer.parameters)
        if algorithm is not None and behavior is not None:
            if behavior.id == "rlspl.behavior.random_mixture":
                active_ids.update(
                    item for item in legacy_behavior_ids
                    if (
                        item.startswith("q_learning.")
                        and algorithm.id == "rlspl.q_learning"
                    )
                    or (
                        item.startswith("dqn.")
                        and algorithm.id == "rlspl.dqn"
                    )
                )
            elif behavior.id == "rlspl.behavior.ou_noise" and algorithm.id == "rlspl.ddpg":
                active_ids.update({"ddpg.ou_theta", "ddpg.ou_sigma"})
        bindings = payload["training"]["parameters"]
        payload["training"]["parameters"] = {
            parameter_id: binding
            for parameter_id, binding in bindings.items()
            if parameter_id in active_ids or parameter_id not in known_component_ids
        }
        environment_parameters = payload["environment"].get("parameters", {})
        payload["environment"]["parameters"] = {
            parameter_id: value
            for parameter_id, value in environment_parameters.items()
            if parameter_id in active_ids or parameter_id not in known_component_ids
        }

    @staticmethod
    def _schema_issues(exc: ValidationError) -> tuple[ValidationIssue, ...]:
        return tuple(ValidationIssue(
            severity=IssueSeverity.ERROR,
            code="EXP-04",
            path=".".join(str(item) for item in error["loc"]),
            message=error["msg"],
        ) for error in exc.errors())

    @classmethod
    def _semantic_hash(cls, payload: dict[str, Any]) -> str:
        semantic = dict(payload)
        for key in (
            "name",
            "requested_configuration_hash",
            "configuration_hash",
        ):
            semantic.pop(key, None)
        return cls._stable_hash(semantic)

    @staticmethod
    def _stable_hash(payload: Any) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
