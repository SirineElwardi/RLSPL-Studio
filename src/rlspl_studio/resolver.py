"""Capability-aware configuration resolution and validation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .catalog import (
    ALGORITHM_OWNED,
    ALGORITHM_OWNED_OPTIMIZER,
    DETERMINISTIC,
    OU_NOISE,
    Q_LEARNING,
    RANDOM_MIXTURE,
    core_training_parameters,
)
from .compatibility import behavior_reasons, optimizer_reasons
from .descriptors import (
    AlgorithmDescriptor,
    BehaviorDescriptor,
    EnvironmentDescriptor,
    OptimizerDescriptor,
    ParameterDefinition,
)
from .models import (
    BindingMode,
    IssueSeverity,
    ParameterBinding,
    ParameterType,
    ResolutionResult,
    ResolvedConfiguration,
    SearchDomain,
    SearchDomainKind,
    UserConfiguration,
    ValidationIssue,
    ValidationReport,
)
from .registry import ComponentRegistry


SUPPORTED_METRICS = {
    "average_reward",
    "cumulative_reward",
    "success_rate",
    "reward_auc",
    "training_time",
    "environment_steps",
    "episodes_to_threshold",
}
SUPPORTED_SUMMARIES = {"mean", "median", "standard_deviation", "confidence_interval", "iqm"}
SUPPORTED_VISUALIZATIONS = {
    "learning_curve",
    "convergence",
    "reward_distribution",
    "comparative",
}


class ConfigurationResolver:
    """Resolve a user configuration against registered component contracts."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry

    def resolve(self, config: UserConfiguration) -> ResolutionResult:
        issues: list[ValidationIssue] = []
        requested_configuration_hash = self._stable_hash(config.model_dump(mode="json"))
        environment = self.registry.environment(config.environment.component_id)
        algorithm = self.registry.algorithm(config.algorithm.component_id)

        if environment is None:
            self._error(
                issues,
                "STR-02",
                "environment.component_id",
                f"environment component is not registered: {config.environment.component_id}",
                "Install or register the environment adapter before generation.",
            )
        if algorithm is None:
            self._error(
                issues,
                "STR-01",
                "algorithm.component_id",
                f"algorithm component is not registered: {config.algorithm.component_id}",
                "Select an installed algorithm component.",
            )

        if environment is None or algorithm is None:
            return ResolutionResult(report=ValidationReport(issues=tuple(issues)))

        behavior_id = (
            config.behavior.component_id
            if config.behavior is not None
            else algorithm.composition.default_behavior_id or ALGORITHM_OWNED
        )
        behavior = self.registry.behavior(behavior_id)
        if behavior is None:
            self._error(
                issues,
                "BEH-01",
                "behavior.component_id",
                f"action-selection behavior is not registered: {behavior_id}",
                "Select or install a behavior component.",
            )
            return ResolutionResult(report=ValidationReport(issues=tuple(issues)))

        optimizer_id = (
            config.optimizer.component_id
            if config.optimizer is not None
            else algorithm.composition.default_optimizer_id or ALGORITHM_OWNED_OPTIMIZER
        )
        optimizer = self.registry.optimizer(optimizer_id)
        if optimizer is None:
            self._error(
                issues,
                "OPT-01",
                "optimizer.component_id",
                f"optimizer component is not registered: {optimizer_id}",
                "Select or install an optimizer component.",
            )
            return ResolutionResult(report=ValidationReport(issues=tuple(issues)))

        self._validate_runtime_availability(
            config, environment, algorithm, behavior, optimizer, issues
        )
        self._validate_capabilities(
            config, environment, algorithm, behavior, optimizer, issues
        )
        definitions = self._collect_definitions(
            environment, algorithm, behavior, optimizer, issues
        )
        effective = self._resolve_parameters(config, behavior, definitions, issues)
        self._validate_cross_parameters(effective, issues)
        self._validate_search(config, effective, issues)
        self._validate_evaluation(config, environment, algorithm, issues)
        self._add_advisories(config, environment, algorithm, behavior, issues)
        self._add_resource_advisories(environment, algorithm, effective, issues)

        report = ValidationReport(issues=tuple(issues))
        if not report.is_valid:
            return ResolutionResult(report=report)

        composition_evidence = algorithm.composition.model_dump(mode="json")
        composition_evidence["evaluation_modes"] = sorted(
            item.value for item in algorithm.composition.evaluation_modes
        )
        behavior_requirements_evidence = {
            "policy_interfaces": sorted(
                item.value for item in behavior.requirements.policy_interfaces
            ),
            "action_kinds": sorted(
                item.value for item in behavior.requirements.action_kinds
            ),
            "requires_bounded_actions": behavior.requirements.requires_bounded_actions,
            "requires_perturbable_policy": behavior.requirements.requires_perturbable_policy,
        }
        optimizer_requirements_evidence = {
            "interfaces": sorted(
                item.value for item in optimizer.requirements.interfaces
            ),
        }
        capability_evidence = {
            "environment_action_kind": environment.capabilities.action_kind.value,
            "environment_observation_kind": environment.capabilities.observation_kind.value,
            "environment_action_bounded": environment.capabilities.action_bounded,
            "environment_success_signal": environment.capabilities.success_signal,
            "environment_success_definition": environment.capabilities.success_definition,
            "algorithm_supported_action_kinds": sorted(
                kind.value for kind in algorithm.requirements.action_kinds
            ),
            "algorithm_supported_observation_kinds": sorted(
                kind.value for kind in algorithm.requirements.observation_kinds
            ),
            "composition": composition_evidence,
            "behavior_requirements": behavior_requirements_evidence,
            "behavior_category": behavior.category,
            "optimizer_requirements": optimizer_requirements_evidence,
            "optimizer_category": optimizer.category,
            "pairing_verified": environment.id in algorithm.verified_environment_ids,
            "resource_estimates": self._resource_estimates(environment, algorithm, effective),
        }
        hash_payload = {
            "schema_version": config.schema_version,
            "name": config.name,
            "environment": {"id": environment.id, "version": environment.version},
            "algorithm": {"id": algorithm.id, "version": algorithm.version},
            "behavior": {"id": behavior.id, "version": behavior.version},
            "optimizer": {"id": optimizer.id, "version": optimizer.version},
            "training_budget_unit": config.training.budget_unit,
            "training_budget": config.training.budget,
            "checkpoint_policy": config.training.checkpoint_policy,
            "checkpoint_interval": config.training.checkpoint_interval,
            "effective_parameters": {
                key: value.model_dump(mode="json") for key, value in sorted(effective.items())
            },
            "search": config.search.model_dump(mode="json") if config.search else None,
            "evaluation": config.evaluation.model_dump(mode="json"),
        }
        resolved = ResolvedConfiguration(
            name=config.name,
            environment_id=environment.id,
            environment_version=environment.version,
            algorithm_id=algorithm.id,
            algorithm_version=algorithm.version,
            behavior_id=behavior.id,
            behavior_version=behavior.version,
            optimizer_id=optimizer.id,
            optimizer_version=optimizer.version,
            training_budget_unit=config.training.budget_unit,
            training_budget=config.training.budget,
            checkpoint_policy=config.training.checkpoint_policy,
            checkpoint_interval=config.training.checkpoint_interval,
            effective_parameters=effective,
            search=config.search,
            evaluation=config.evaluation,
            capability_evidence=capability_evidence,
            requested_configuration_hash=requested_configuration_hash,
            configuration_hash=self._stable_hash(hash_payload),
        )
        return ResolutionResult(report=report, resolved=resolved)

    def _validate_runtime_availability(
        self,
        config: UserConfiguration,
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        behavior: BehaviorDescriptor,
        optimizer: OptimizerDescriptor,
        issues: list[ValidationIssue],
    ) -> None:
        if environment.runtime_assets is None:
            self._error(
                issues,
                "AVL-01",
                "environment.component_id",
                f"environment runtime is not installed: {environment.id}",
                "Install its runtime component before selecting it in an executable product.",
            )
        if algorithm.runtime_assets is None:
            self._error(
                issues,
                "AVL-01",
                "algorithm.component_id",
                f"algorithm runtime is not installed: {algorithm.id}",
                "Install its runtime component before selecting it in an executable product.",
            )
        if behavior.runtime_assets is None:
            self._error(
                issues,
                "AVL-01",
                "behavior.component_id",
                f"behavior runtime is not installed: {behavior.id}",
                "Install its runtime component before selecting it in an executable product.",
            )
        if optimizer.runtime_assets is None:
            self._error(
                issues,
                "AVL-01",
                "optimizer.component_id",
                f"optimizer runtime is not installed: {optimizer.id}",
                "Install its runtime component before selecting it in an executable product.",
            )
        if "comparative" in config.evaluation.visualizations:
            self._error(
                issues,
                "AVL-03",
                "evaluation.visualizations",
                "comparative run loading is not installed in this milestone",
            )

    def _validate_capabilities(
        self,
        config: UserConfiguration,
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        behavior: BehaviorDescriptor,
        optimizer: OptimizerDescriptor,
        issues: list[ValidationIssue],
    ) -> None:
        capabilities = environment.capabilities
        requirements = algorithm.requirements
        if capabilities.action_kind not in requirements.action_kinds:
            self._error(
                issues,
                "CAP-01",
                "environment",
                f"{algorithm.display_name} does not support {capabilities.action_kind.value} actions",
                "Choose an algorithm supporting the selected environment action space.",
            )
        if capabilities.observation_kind not in requirements.observation_kinds:
            self._error(
                issues,
                "CAP-02",
                "environment",
                f"{algorithm.display_name} does not support {capabilities.observation_kind.value} observations",
                "Select a compatible observation adapter or algorithm.",
            )
        if (
            capabilities.action_kind in requirements.action_kinds
            and requirements.requires_bounded_actions
            and not capabilities.action_bounded
        ):
            self._error(
                issues,
                "CAP-03",
                "environment",
                f"{algorithm.display_name} requires bounded continuous actions",
                "Choose an environment adapter exposing finite action bounds.",
            )
        if config.training.budget_unit not in requirements.supports_budget_units:
            self._error(
                issues,
                "CAP-04",
                "training.budget_unit",
                f"{algorithm.display_name} does not support a {config.training.budget_unit} budget",
                f"Use one of: {', '.join(sorted(requirements.supports_budget_units))}.",
            )
        algorithm_environment_match = (
            capabilities.action_kind in requirements.action_kinds
            and capabilities.observation_kind in requirements.observation_kinds
            and (
                not requirements.requires_bounded_actions
                or capabilities.action_bounded
            )
        )
        if algorithm_environment_match:
            for reason in behavior_reasons(environment, algorithm, behavior):
                self._error(
                    issues,
                    "BEH-02",
                    "behavior.component_id",
                    f"{behavior.display_name} is incompatible: {reason}",
                    "Choose a behavior whose capability contract matches the algorithm and action space.",
                )
        for reason in optimizer_reasons(algorithm, optimizer):
            self._error(
                issues,
                "OPT-02",
                "optimizer.component_id",
                f"{optimizer.display_name} is incompatible: {reason}",
                "Choose an optimizer matching the algorithm's update interface.",
            )

    def _collect_definitions(
        self,
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        behavior: BehaviorDescriptor,
        optimizer: OptimizerDescriptor,
        issues: list[ValidationIssue],
    ) -> dict[str, ParameterDefinition]:
        definitions: dict[str, ParameterDefinition] = {}
        for definition in (
            *core_training_parameters(),
            *environment.parameters,
            *algorithm.parameters,
            *behavior.parameters,
            *optimizer.parameters,
        ):
            if definition.id in definitions:
                self._error(
                    issues,
                    "CAP-04",
                    "components",
                    f"duplicate parameter definition: {definition.id}",
                )
            definitions[definition.id] = definition
        return definitions

    def _resolve_parameters(
        self,
        config: UserConfiguration,
        behavior: BehaviorDescriptor,
        definitions: dict[str, ParameterDefinition],
        issues: list[ValidationIssue],
    ) -> dict[str, ParameterBinding]:
        requested = self._migrate_legacy_behavior_parameters(
            dict(config.training.parameters), behavior
        )
        for parameter_id, value in config.environment.parameters.items():
            if parameter_id in requested:
                self._error(
                    issues,
                    "PAR-01",
                    f"environment.parameters.{parameter_id}",
                    "parameter is assigned in both environment and training configuration",
                )
            requested[parameter_id] = ParameterBinding(mode=BindingMode.FIXED, value=value)

        for parameter_id in sorted(set(requested) - set(definitions)):
            self._error(
                issues,
                "PAR-02",
                f"training.parameters.{parameter_id}",
                f"parameter is not owned by an active component: {parameter_id}",
                "Remove it or select the component that owns it.",
            )

        effective: dict[str, ParameterBinding] = {}
        for parameter_id, definition in definitions.items():
            binding = requested.get(parameter_id)
            if binding is None:
                if definition.default is None:
                    if definition.required:
                        self._error(
                            issues,
                            "PAR-01",
                            f"training.parameters.{parameter_id}",
                            f"required parameter has no assignment: {parameter_id}",
                        )
                    continue
                binding = ParameterBinding(mode=BindingMode.FIXED, value=definition.default)

            if binding.mode is BindingMode.FIXED:
                self._validate_fixed(parameter_id, binding.value, definition, issues)
            else:
                self._validate_domain(parameter_id, binding.domain, definition, issues)
            effective[parameter_id] = binding
        return effective

    @staticmethod
    def _migrate_legacy_behavior_parameters(
        requested: dict[str, ParameterBinding],
        behavior: BehaviorDescriptor,
    ) -> dict[str, ParameterBinding]:
        """Accept v0.13 parameter IDs while resolving to strategy-owned IDs."""

        aliases: dict[str, str] = {}
        if behavior.id == RANDOM_MIXTURE:
            for prefix in ("q_learning", "dqn"):
                aliases.update({
                    f"{prefix}.epsilon_start": "behavior.random_mixture.probability_start",
                    f"{prefix}.epsilon_end": "behavior.random_mixture.probability_end",
                    f"{prefix}.epsilon_decay": "behavior.random_mixture.decay",
                })
        elif behavior.id == OU_NOISE:
            aliases = {
                "ddpg.ou_theta": "behavior.ou.theta",
                "ddpg.ou_sigma": "behavior.ou.sigma_start",
            }
        migrated = dict(requested)
        for old_id, new_id in aliases.items():
            if old_id not in migrated:
                continue
            binding = migrated.pop(old_id)
            migrated.setdefault(new_id, binding)
            if old_id == "ddpg.ou_sigma":
                migrated.setdefault("behavior.ou.sigma_end", binding)
        return migrated

    def _validate_fixed(
        self,
        parameter_id: str,
        value: Any,
        definition: ParameterDefinition,
        issues: list[ValidationIssue],
    ) -> None:
        path = f"training.parameters.{parameter_id}.value"
        if not self._value_matches_type(value, definition.type):
            self._error(
                issues,
                "PAR-03",
                path,
                f"expected {definition.type.value}, received {type(value).__name__}",
            )
            return
        if definition.type is ParameterType.CATEGORICAL and value not in definition.choices:
            self._error(issues, "PAR-03", path, f"value must be one of {definition.choices}")
        if self._is_number(value):
            if definition.minimum is not None and value < definition.minimum:
                self._error(issues, "PAR-03", path, f"value must be >= {definition.minimum}")
            if definition.maximum is not None and value > definition.maximum:
                self._error(issues, "PAR-03", path, f"value must be <= {definition.maximum}")

    def _validate_domain(
        self,
        parameter_id: str,
        domain: SearchDomain | None,
        definition: ParameterDefinition,
        issues: list[ValidationIssue],
    ) -> None:
        path = f"training.parameters.{parameter_id}.domain"
        if domain is None:
            self._error(issues, "PAR-01", path, "tunable parameter has no search domain")
            return
        if not definition.tunable:
            self._error(issues, "HPO-04", path, f"parameter is not tunable: {parameter_id}")
            return

        compatible_kinds = {
            ParameterType.INTEGER: {SearchDomainKind.INTEGER},
            ParameterType.FLOAT: {SearchDomainKind.FLOAT, SearchDomainKind.LOG_FLOAT},
            ParameterType.CATEGORICAL: {SearchDomainKind.CATEGORICAL},
            ParameterType.BOOLEAN: {SearchDomainKind.CATEGORICAL},
            ParameterType.STRING: {SearchDomainKind.CATEGORICAL},
        }[definition.type]
        if domain.kind not in compatible_kinds:
            self._error(
                issues,
                "HPO-04",
                path,
                f"{domain.kind.value} is incompatible with {definition.type.value}",
            )
            return

        if domain.kind is SearchDomainKind.CATEGORICAL:
            invalid = [value for value in domain.choices if not self._value_matches_type(value, definition.type)]
            if definition.type is ParameterType.CATEGORICAL:
                invalid.extend(value for value in domain.choices if value not in definition.choices)
            if invalid:
                self._error(issues, "HPO-04", path, f"invalid categorical choices: {invalid}")
            return

        assert domain.lower is not None and domain.upper is not None
        if domain.lower >= domain.upper:
            self._error(issues, "PAR-04", path, "lower must be strictly smaller than upper")
        if domain.kind is SearchDomainKind.LOG_FLOAT and domain.lower <= 0:
            self._error(issues, "PAR-04", path, "log-float lower bound must be > 0")
        if definition.minimum is not None and domain.lower < definition.minimum:
            self._error(issues, "HPO-04", path, f"lower bound must be >= {definition.minimum}")
        if definition.maximum is not None and domain.upper > definition.maximum:
            self._error(issues, "HPO-04", path, f"upper bound must be <= {definition.maximum}")

    def _validate_cross_parameters(
        self,
        parameters: dict[str, ParameterBinding],
        issues: list[ValidationIssue],
    ) -> None:
        for prefix in ("dqn", "ddpg", "sac"):
            self._validate_ordered_pair(
                parameters,
                f"{prefix}.batch_size",
                f"{prefix}.buffer_capacity",
                "PAR-06",
                issues,
            )
        for end_id, start_id in (
            (
                "behavior.random_mixture.probability_end",
                "behavior.random_mixture.probability_start",
            ),
            ("behavior.boltzmann.temperature_end", "behavior.boltzmann.temperature_start"),
            ("behavior.gaussian.sigma_end", "behavior.gaussian.sigma_start"),
            ("behavior.ou.sigma_end", "behavior.ou.sigma_start"),
            (
                "behavior.parameter_noise.sigma_end",
                "behavior.parameter_noise.sigma_start",
            ),
        ):
            self._validate_ordered_pair(parameters, end_id, start_id, "PAR-08", issues)

    def _validate_ordered_pair(
        self,
        parameters: dict[str, ParameterBinding],
        smaller_id: str,
        larger_id: str,
        code: str,
        issues: list[ValidationIssue],
    ) -> None:
        smaller = parameters.get(smaller_id)
        larger = parameters.get(larger_id)
        if smaller is None or larger is None:
            return
        smaller_max = self._binding_max(smaller)
        larger_min = self._binding_min(larger)
        if smaller_max is not None and larger_min is not None and smaller_max > larger_min:
            self._error(
                issues,
                code,
                f"training.parameters.{smaller_id}",
                f"the configured domain can violate {smaller_id} <= {larger_id}",
                "Adjust fixed values or bounds so every generated trial satisfies the relation.",
            )

    def _validate_search(
        self,
        config: UserConfiguration,
        parameters: dict[str, ParameterBinding],
        issues: list[ValidationIssue],
    ) -> None:
        tunable = [key for key, value in parameters.items() if value.mode is BindingMode.TUNABLE]
        if tunable and config.search is None:
            self._error(
                issues,
                "HPO-01",
                "search",
                "tunable parameters require an enabled search configuration",
            )
            return
        if config.search is not None and not tunable:
            self._error(
                issues,
                "HPO-01",
                "search",
                "search is enabled but no active parameter is tunable",
            )
        if config.search is None:
            return

        provider_id = {
            "random": "core.random",
            "bayesian_tpe": "core.bayesian_tpe",
        }.get(config.search.sampler, config.search.provider_id)
        if not provider_id or not self.registry.has_search_provider(provider_id):
            self._error(
                issues,
                "HPO-02",
                "search.sampler",
                f"search provider is not installed: {provider_id or config.search.sampler}",
            )
        if config.search.objective not in config.evaluation.metrics:
            self._error(
                issues,
                "HPO-05",
                "search.objective",
                "search objective must be emitted by the configured evaluation metrics",
                f"Add {config.search.objective} to evaluation.metrics.",
            )
        if config.search.objective == "reward_auc" and not config.evaluation.collect_reward_trace:
            self._error(
                issues,
                "HPO-05",
                "evaluation.collect_reward_trace",
                "reward_auc optimization requires reward traces",
            )

    def _validate_evaluation(
        self,
        config: UserConfiguration,
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        issues: list[ValidationIssue],
    ) -> None:
        evaluation = config.evaluation
        if evaluation.action_mode not in algorithm.composition.evaluation_modes:
            self._error(
                issues,
                "BEH-03",
                "evaluation.action_mode",
                f"{algorithm.display_name} does not expose {evaluation.action_mode.value} evaluation actions",
                "Use one of: "
                + ", ".join(sorted(item.value for item in algorithm.composition.evaluation_modes))
                + ".",
            )
        if not evaluation.metrics:
            self._error(issues, "EVA-02", "evaluation.metrics", "at least one metric is required")
        if not evaluation.export_formats:
            self._error(
                issues,
                "EVA-02",
                "evaluation.export_formats",
                "at least one export format is required",
            )
        if not evaluation.seeds:
            self._error(issues, "EVA-02", "evaluation.seeds", "at least one evaluation seed is required")

        unknown_metrics = sorted(set(evaluation.metrics) - SUPPORTED_METRICS)
        unknown_summaries = sorted(set(evaluation.summaries) - SUPPORTED_SUMMARIES)
        unknown_visualizations = sorted(set(evaluation.visualizations) - SUPPORTED_VISUALIZATIONS)
        if unknown_metrics:
            self._error(issues, "EVA-02", "evaluation.metrics", f"unregistered metrics: {unknown_metrics}")
        if unknown_summaries:
            self._error(issues, "EVA-02", "evaluation.summaries", f"unregistered summaries: {unknown_summaries}")
        if unknown_visualizations:
            self._error(
                issues,
                "EVA-02",
                "evaluation.visualizations",
                f"unregistered visualizations: {unknown_visualizations}",
            )

        success_dependent_metrics = {
            "success_rate",
            "episodes_to_threshold",
        } & set(evaluation.metrics)
        if success_dependent_metrics:
            if not environment.capabilities.success_signal and not evaluation.success_predicate:
                self._error(
                    issues,
                    "EVA-03",
                    "evaluation.success_predicate",
                    f"{sorted(success_dependent_metrics)} require an environment success signal or a success predicate",
                )
        trace_consumers = {"reward_auc"} & set(evaluation.metrics)
        trace_consumers |= {"learning_curve", "convergence"} & set(evaluation.visualizations)
        if trace_consumers and not evaluation.collect_reward_trace:
            self._error(
                issues,
                "EVA-04",
                "evaluation.collect_reward_trace",
                f"reward traces are required by: {sorted(trace_consumers)}",
            )
        replicated = {"standard_deviation", "confidence_interval", "iqm"}
        if replicated & set(evaluation.summaries) and len(set(evaluation.seeds)) < 2:
            self._error(
                issues,
                "EVA-05",
                "evaluation.seeds",
                "replicated statistical summaries require at least two distinct seeds",
            )
        comparative = "comparative" in evaluation.visualizations
        if comparative and len(set(evaluation.comparison_run_ids)) < 2:
            self._error(
                issues,
                "EVA-06",
                "evaluation.comparison_run_ids",
                "comparative visualization requires at least two distinct completed run IDs",
            )
        if evaluation.top_k is not None:
            if not comparative:
                self._error(
                    issues,
                    "EVA-07",
                    "evaluation.top_k",
                    "top_k requires comparative visualization",
                )
            elif evaluation.top_k > len(set(evaluation.comparison_run_ids)):
                self._error(
                    issues,
                    "EVA-07",
                    "evaluation.top_k",
                    "top_k cannot exceed the number of comparison runs",
                )

    def _add_advisories(
        self,
        config: UserConfiguration,
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        behavior: BehaviorDescriptor,
        issues: list[ValidationIssue],
    ) -> None:
        pairing_is_compatible = (
            environment.capabilities.action_kind in algorithm.requirements.action_kinds
            and environment.capabilities.observation_kind in algorithm.requirements.observation_kinds
            and (
                not algorithm.requirements.requires_bounded_actions
                or environment.capabilities.action_bounded
            )
        )
        if pairing_is_compatible and environment.id not in algorithm.verified_environment_ids:
            self._advisory(
                issues,
                "ADV-01",
                "environment",
                "the environment-algorithm pairing is capability-compatible but not yet verified by an integration test",
            )
        if (
            pairing_is_compatible
            and algorithm.id == Q_LEARNING
            and environment.id not in algorithm.verified_environment_ids
        ):
            self._advisory(
                issues,
                "ADV-04",
                "algorithm",
                "tabular discretization may grow exponentially with observation dimensions",
                "Inspect the derived Q-table size before a long run.",
            )
        if len(set(config.evaluation.seeds)) == 1:
            self._advisory(
                issues,
                "ADV-02",
                "evaluation.seeds",
                "single-seed evaluation cannot characterize stochastic variability",
                "Use multiple explicit evaluation seeds for comparisons.",
            )
        if config.search is not None:
            overlap = set(config.search.seeds) & set(config.evaluation.seeds)
            if overlap:
                self._advisory(
                    issues,
                    "ADV-03",
                    "evaluation.seeds",
                    f"search and final evaluation seeds overlap: {sorted(overlap)}",
                    "Use a disjoint final evaluation seed set when assessing the selected configuration.",
                )
            planned_fits = (config.search.trials or 0) * len(config.search.seeds)
            if planned_fits >= 500:
                self._advisory(
                    issues,
                    "ADV-06",
                    "search.trials",
                    f"this search can require {planned_fits:,} trial training runs before the final fit",
                    "Start with a smaller budget to verify the pipeline, then expand it deliberately.",
                )
        if behavior.id == DETERMINISTIC:
            self._advisory(
                issues,
                "ADV-05",
                "behavior.component_id",
                "training uses the deterministic actor without an external exploration mechanism",
                "This is valid, but exploration may be weak unless the environment or learning process adds stochasticity.",
            )

    def _add_resource_advisories(
        self,
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        parameters: dict[str, ParameterBinding],
        issues: list[ValidationIssue],
    ) -> None:
        estimate = self._resource_estimates(environment, algorithm, parameters)
        table_bytes = estimate.get("q_table_bytes")
        if isinstance(table_bytes, int) and table_bytes >= 256 * 1024 * 1024:
            gibibytes = table_bytes / (1024**3)
            self._advisory(
                issues,
                "RES-01",
                "training.parameters.q_learning.bins_per_dimension",
                "the selected dense discretization is estimated to require "
                f"{estimate['q_table_values']:,} Q-values ({gibibytes:.2f} GiB as float32)",
                "Generation remains allowed; reduce bins or use a sparse representation if memory is insufficient.",
            )

    @staticmethod
    def _resource_estimates(
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
        parameters: dict[str, ParameterBinding],
    ) -> dict[str, int]:
        if algorithm.id != Q_LEARNING:
            return {}
        dimensions = environment.capabilities.observation_dimensions
        actions = environment.capabilities.discrete_action_count
        bins_binding = parameters.get("q_learning.bins_per_dimension")
        if dimensions is None or actions is None or bins_binding is None:
            return {}
        bins = ConfigurationResolver._binding_max(bins_binding)
        if bins is None:
            return {}
        bins = int(bins)
        values = bins**dimensions * actions
        return {
            "q_table_states": bins**dimensions,
            "q_table_values": values,
            "q_table_bytes": values * 4,
        }

    @staticmethod
    def _binding_min(binding: ParameterBinding) -> int | float | None:
        if binding.mode is BindingMode.FIXED and ConfigurationResolver._is_number(binding.value):
            return binding.value
        if binding.domain and binding.domain.lower is not None:
            return binding.domain.lower
        return None

    @staticmethod
    def _binding_max(binding: ParameterBinding) -> int | float | None:
        if binding.mode is BindingMode.FIXED and ConfigurationResolver._is_number(binding.value):
            return binding.value
        if binding.domain and binding.domain.upper is not None:
            return binding.domain.upper
        return None

    @staticmethod
    def _value_matches_type(value: Any, type_: ParameterType) -> bool:
        if type_ is ParameterType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        if type_ is ParameterType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if type_ is ParameterType.BOOLEAN:
            return isinstance(value, bool)
        if type_ is ParameterType.STRING:
            return isinstance(value, str)
        return True

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _error(
        issues: list[ValidationIssue],
        code: str,
        path: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                code=code,
                path=path,
                message=message,
                suggestion=suggestion,
            )
        )

    @staticmethod
    def _advisory(
        issues: list[ValidationIssue],
        code: str,
        path: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ADVISORY,
                code=code,
                path=path,
                message=message,
                suggestion=suggestion,
            )
        )
