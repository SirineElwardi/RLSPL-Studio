"""Inspectable feature-model and cross-tree-constraint projections for RLSPL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .catalog import ALGORITHM_OWNED, ALGORITHM_OWNED_OPTIMIZER
from .compatibility import composition_reasons, optimizer_reasons, product_reasons
from .models import BindingMode, ResolutionResult, UserConfiguration
from .registry import ComponentRegistry


@dataclass(frozen=True)
class ConstraintSpec:
    id: str
    title: str
    category: str
    relation: str
    expression: str
    explanation: str
    issue_codes: tuple[str, ...] = ()
    issue_paths: tuple[str, ...] = ()
    scope: str = "always"
    paper_rules: tuple[str, ...] = ()

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "relation": self.relation,
            "expression": self.expression,
            "explanation": self.explanation,
            "enforcement_codes": list(self.issue_codes),
            "paper_rules": list(self.paper_rules),
        }


CONSTRAINTS = (
    ConstraintSpec(
        "FM-ENV-01", "One environment", "feature_model", "alternative",
        "card(Environment) = 1",
        "Every product selects exactly one registered environment component.",
    ),
    ConstraintSpec(
        "FM-ALG-01", "One learning algorithm", "feature_model", "alternative",
        "card(Algorithm) = 1",
        "Every product selects exactly one learning algorithm component.",
    ),
    ConstraintSpec(
        "FM-BEH-01", "One action behavior", "feature_model", "alternative",
        "card(ActionBehavior) = 1",
        "Every product resolves exactly one action-selection behavior; an omitted selection uses the algorithm's declared default.",
    ),
    ConstraintSpec(
        "FM-OPT-01", "One optimizer / update rule", "feature_model", "alternative",
        "card(Optimizer) = 1",
        "Every product resolves exactly one parameter-update component; an omitted selection uses the algorithm's declared default.",
    ),
    ConstraintSpec(
        "FM-BIND-01", "One value-assignment mode", "feature_model", "alternative",
        "Fixed(p) XOR Tunable(p)",
        "A parameter is either fixed or described by one search domain, never both.",
        paper_rules=("HC1", "HC2", "HC3"),
    ),
    ConstraintSpec(
        "CT-ACTION-01", "Action-space exclusion", "capability", "excludes",
        "not supports(Algorithm, Environment.action_kind) => excludes(Environment, Algorithm)",
        "An environment-algorithm pair is excluded when the algorithm cannot emit the required discrete or continuous action kind.",
        issue_codes=("CAP-01",),
    ),
    ConstraintSpec(
        "CT-OBS-01", "Observation compatibility", "capability", "requires",
        "Selected(Algorithm) => supports(Environment.observation_kind)",
        "The algorithm must consume the environment observation representation directly or through a declared adapter.",
        issue_codes=("CAP-02",),
    ),
    ConstraintSpec(
        "CT-BOUNDS-01", "Continuous-action bounds", "capability", "requires",
        "RequiresBoundedActions(Algorithm) => Environment.action_bounded",
        "Algorithms that scale continuous policies require finite environment action bounds.",
        issue_codes=("CAP-03",), scope="bounded_actions",
    ),
    ConstraintSpec(
        "CT-BUDGET-01", "Training-budget unit", "capability", "requires",
        "Training.budget_unit in Algorithm.supported_budget_units",
        "The selected algorithm must support episode- or timestep-based training budgets.",
        issue_codes=("CAP-04",), issue_paths=("training.budget_unit",),
    ),
    ConstraintSpec(
        "CT-BEH-01", "Policy-interface compatibility", "capability", "requires",
        "Behavior.policy_interface in Algorithm.exposed_policy_interfaces",
        "A behavior composes by contract: Q-score sampling needs Q-values, actor noise needs a continuous policy, and parameter noise needs a perturbable model.",
        issue_codes=("BEH-02",), issue_paths=("behavior.component_id",),
        scope="behavior",
    ),
    ConstraintSpec(
        "CT-BEH-02", "Behavior action-space compatibility", "capability", "requires",
        "Environment.action_kind in Behavior.supported_action_kinds",
        "The behavior must emit the environment's action kind and receive finite bounds when its transformation requires clipping.",
        issue_codes=("BEH-02",), issue_paths=("behavior.component_id",),
        scope="behavior",
    ),
    ConstraintSpec(
        "CT-OPT-01", "Optimizer-interface compatibility", "capability", "requires",
        "Optimizer.required_interface = Algorithm.optimizer_interface",
        "Tabular Q updates and gradient-based neural-network optimizers are different contracts and cannot be interchanged.",
        issue_codes=("OPT-02",), issue_paths=("optimizer.component_id",),
        scope="optimizer",
    ),
    ConstraintSpec(
        "CT-OWNER-01", "Component-owned parameters", "parameter", "requires",
        "Selected(Parameter p) => Selected(owner(p))",
        "A component-specific parameter exists only while its owning environment, algorithm, behavior, or optimizer is selected.",
        issue_codes=("PAR-02",),
    ),
    ConstraintSpec(
        "CT-BATCH-01", "Replay batch fits memory", "parameter", "numeric",
        "batch_size <= replay_capacity",
        "Every possible fixed value or search trial must fit the selected replay buffer.",
        issue_codes=("PAR-06",), scope="replay_algorithm",
    ),
    ConstraintSpec(
        "CT-BEH-SCHEDULE-01", "Behavior schedule order", "parameter", "numeric",
        "intensity_end <= intensity_start",
        "A scheduled probability, temperature, or noise scale cannot end above its initial value.",
        issue_codes=("PAR-08",), scope="behavior_schedule",
    ),
    ConstraintSpec(
        "CT-HPO-01", "Search and tunable parameters", "search", "equivalence",
        "Search <=> exists p: Tunable(p)",
        "Search is present exactly when at least one active parameter has a search domain.",
        issue_codes=("HPO-01",), scope="search_or_tunable",
        paper_rules=("HC2", "HC3"),
    ),
    ConstraintSpec(
        "CT-HPO-02", "Finite optimization budget", "search", "requires",
        "Search => (NumberOfTrials OR Timeout)",
        "An optimization configuration declares a finite trial or time budget.",
        scope="search", paper_rules=("HC4",),
    ),
    ConstraintSpec(
        "FM-HPO-03", "One optimization approach", "search", "alternative",
        "Search => exactlyOne(Random, BayesianTPE)",
        "A search configuration selects one executable sampler strategy.",
        scope="search", paper_rules=("HC5",),
    ),
    ConstraintSpec(
        "CT-HPO-04", "Measurable optimization objective", "search", "requires",
        "Search.objective in Evaluation.metrics",
        "The quantity optimized by search must also be produced by evaluation.",
        issue_codes=("HPO-05",), issue_paths=("search.objective",), scope="search",
    ),
    ConstraintSpec(
        "CT-HPO-05", "Installed search runtime", "availability", "requires",
        "Search => Installed(SearchProvider AND SearchRuntime)",
        "Random search and Bayesian TPE each select an installed runtime asset that the generator places in the product.",
        issue_codes=("HPO-02",), scope="search",
    ),
    ConstraintSpec(
        "FM-EVAL-01", "Evaluation protocol mode", "evaluation", "alternative",
        "DefaultEvaluation XOR ConfigurableEvaluation",
        "Each product has exactly one evaluation protocol mode.",
        paper_rules=("EC1",),
    ),
    ConstraintSpec(
        "CT-EVAL-BEH-01", "Evaluation action mode", "evaluation", "requires",
        "Evaluation.action_mode in Algorithm.evaluation_modes",
        "Evaluation deliberately chooses deterministic, stochastic, or training-behavior actions without silently changing the trained policy.",
        issue_codes=("BEH-03",), issue_paths=("evaluation.action_mode",),
    ),
    ConstraintSpec(
        "FM-EVAL-02", "At least one metric", "evaluation", "or_group",
        "card(Evaluation.metrics) >= 1",
        "Evaluation combines one or more registered performance or efficiency metrics.",
        issue_codes=("EVA-02",), issue_paths=("evaluation.metrics",),
        paper_rules=("EC2",),
    ),
    ConstraintSpec(
        "CT-EVAL-03", "Success-dependent metrics", "evaluation", "requires",
        "SuccessMetric => (Environment.success_signal OR success_predicate)",
        "Success rate and threshold metrics require an explicit definition of task success.",
        issue_codes=("EVA-03",), scope="success_metric",
    ),
    ConstraintSpec(
        "CT-EVAL-04", "Reward-trace consumers", "evaluation", "requires",
        "(RewardAUC OR LearningCurve OR Convergence) => RewardTrace",
        "Trace-derived metrics and plots require episode-level rewards to be collected.",
        issue_codes=("EVA-04",), scope="trace_consumer",
    ),
    ConstraintSpec(
        "CT-EVAL-05", "Replicated summaries", "evaluation", "requires",
        "DispersionSummary => card(Evaluation.seeds) >= 2",
        "Standard deviation, confidence intervals, and IQM require multiple distinct evaluation seeds.",
        issue_codes=("EVA-05",), scope="replicated_summary",
    ),
    ConstraintSpec(
        "CT-EVAL-06", "Comparative plots", "evaluation", "requires",
        "ComparativePlot => card(CompletedComparisonRuns) >= 2",
        "The revised Studio grounds comparative plots in completed runs rather than coupling them only to HPO.",
        issue_codes=("AVL-03", "EVA-06"), scope="comparative",
        paper_rules=("EC3-revised",),
    ),
    ConstraintSpec(
        "CT-EVAL-07", "Top-k comparison", "evaluation", "requires",
        "TopK => ComparativePlot AND k <= card(ComparisonRuns)",
        "A top-k report is meaningful only inside a sufficiently large comparison set.",
        issue_codes=("EVA-07",), scope="top_k", paper_rules=("EC4",),
    ),
    ConstraintSpec(
        "FM-EVAL-08", "At least one export format", "evaluation", "or_group",
        "card(ExportFormat) >= 1",
        "Every evaluation persists at least one supported result representation.",
        issue_codes=("EVA-02",), issue_paths=("evaluation.export_formats",),
        paper_rules=("EC5",),
    ),
    ConstraintSpec(
        "CT-ASSET-01", "Installed component assets", "availability", "requires",
        "Selected(Component) => Installed(RuntimeAssets(Component))",
        "A theoretically modeled component needs runtime templates before it can be generated.",
        issue_codes=("AVL-01",),
    ),
)


class SPLModel:
    """Expose SPL structure and project a configuration onto that structure."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry

    def catalog(self) -> dict[str, Any]:
        tree = self._feature_tree()
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
        public_behaviors = tuple(
            item for item in self.registry.behaviors
            if item.public or item.id in referenced_behaviors
        )
        public_optimizers = tuple(
            item for item in self.registry.optimizers
            if item.public or item.id in referenced_optimizers
        )
        pairing_matrix = [
            {
                "environment_id": environment.id,
                "environment_name": environment.display_name,
                "action_kind": environment.capabilities.action_kind.value,
                "pairings": [
                    self._pairing_projection(environment, algorithm)
                    for algorithm in self.registry.algorithms
                ],
            }
            for environment in self.registry.environments
        ]
        compatible_pairings = sum(
            pairing["compatible"]
            for row in pairing_matrix
            for pairing in row["pairings"]
        )
        behavior_matrix = [
            {
                "algorithm_id": algorithm.id,
                "algorithm_name": algorithm.display_name,
                "policy_interface": algorithm.composition.policy_interface.value,
                "behaviors": [
                    self._algorithm_behavior_projection(algorithm, behavior)
                    for behavior in public_behaviors
                ],
            }
            for algorithm in self.registry.algorithms
        ]
        compatible_algorithm_behaviors = sum(
            item["compatible"]
            for row in behavior_matrix
            for item in row["behaviors"]
        )
        optimizer_matrix = [
            {
                "algorithm_id": algorithm.id,
                "algorithm_name": algorithm.display_name,
                "optimizer_interface": algorithm.composition.optimizer_interface.value,
                "optimizers": [
                    self._algorithm_optimizer_projection(algorithm, optimizer)
                    for optimizer in public_optimizers
                ],
            }
            for algorithm in self.registry.algorithms
        ]
        compatible_algorithm_optimizers = sum(
            item["compatible"]
            for row in optimizer_matrix
            for item in row["optimizers"]
        )
        compatible_compositions = sum(
            not composition_reasons(environment, algorithm, behavior)
            for environment in self.registry.environments
            for algorithm in self.registry.algorithms
            for behavior in public_behaviors
        )
        compatible_products = sum(
            not product_reasons(environment, algorithm, behavior, optimizer)
            for environment in self.registry.environments
            for algorithm in self.registry.algorithms
            for behavior in public_behaviors
            for optimizer in public_optimizers
        )
        return {
            "schema_version": "1.0",
            "title": "Revised RLSPL feature model",
            "model_basis": (
                "Paper-derived RLSPL concepts aligned with the current extension-free "
                "registry, resolver, and generator."
            ),
            "tree": tree,
            "pairing_matrix": pairing_matrix,
            "behavior_matrix": behavior_matrix,
            "optimizer_matrix": optimizer_matrix,
            "constraints": [constraint.public() for constraint in CONSTRAINTS],
            "statistics": {
                "feature_count": self._feature_count(tree),
                "constraint_count": len(CONSTRAINTS),
                "environment_alternatives": len(self.registry.environments),
                "algorithm_alternatives": len(self.registry.algorithms),
                "behavior_alternatives": len(public_behaviors),
                "optimizer_alternatives": len(public_optimizers),
                "theoretical_component_pairs": (
                    len(self.registry.environments) * len(self.registry.algorithms)
                ),
                "capability_compatible_pairs": compatible_pairings,
                "theoretical_component_compositions": (
                    len(self.registry.environments)
                    * len(self.registry.algorithms)
                    * len(public_behaviors)
                ),
                "compatible_algorithm_behaviors": compatible_algorithm_behaviors,
                "capability_compatible_compositions": compatible_compositions,
                "theoretical_products": (
                    len(self.registry.environments)
                    * len(self.registry.algorithms)
                    * len(public_behaviors)
                    * len(public_optimizers)
                ),
                "compatible_algorithm_optimizers": compatible_algorithm_optimizers,
                "capability_compatible_products": compatible_products,
            },
            "legend": [
                {"id": "mandatory", "symbol": "M", "label": "Mandatory", "meaning": "present in every product"},
                {"id": "optional", "symbol": "O", "label": "Optional", "meaning": "may be selected"},
                {"id": "alternative", "symbol": "XOR", "label": "Alternative group", "meaning": "exactly one child"},
                {"id": "or_group", "symbol": "OR", "label": "OR group", "meaning": "one or more children"},
                {"id": "requires", "symbol": "=>", "label": "Requires", "meaning": "selection activates a dependency"},
                {"id": "excludes", "symbol": "X", "label": "Excludes", "meaning": "features cannot coexist"},
            ],
            "engineering_flow": [
                {"phase": "Domain engineering", "title": "Model commonality and variability", "detail": "Register components, feature relations, capability contracts, constraints, and reusable assets."},
                {"phase": "Application engineering", "title": "Select a configuration", "detail": "Choose one environment, algorithm, action behavior, optimizer/update rule, and values."},
                {"phase": "Application engineering", "title": "Resolve constraints", "detail": "Reject invalid combinations and materialize all active defaults."},
                {"phase": "Application engineering", "title": "Derive a product", "detail": "Compose only the assets owned by the resolved components."},
            ],
            "paper_alignment": [
                {"rules": "HC1-HC5", "status": "direct", "detail": "Represented by binding, search-activation, budget, and sampler constraints."},
                {"rules": "HC6-HC8", "status": "encapsulated", "detail": "Sampling, surrogate, acquisition, and selection internals belong to the selected search runtime; Random and TPE runtimes are currently built in."},
                {"rules": "EC1-EC2, EC4-EC5", "status": "direct", "detail": "Represented by evaluation modes, metric/export groups, and top-k dependencies."},
                {"rules": "EC3", "status": "revised", "detail": "Comparative plots require completed comparison runs; they are not restricted to HPO studies."},
                {"rules": "Execution", "status": "metadata", "detail": "Device, platform, status, timestamps, seeds, and artifacts remain outside the product feature tree."},
            ],
            "source_ids": ["foda", "feature_oriented_spl", "feature_model_analysis", "rlspl"],
        }

    def trace(
        self,
        config: UserConfiguration,
        result: ResolutionResult,
    ) -> dict[str, Any]:
        environment = self.registry.environment(config.environment.component_id)
        algorithm = self.registry.algorithm(config.algorithm.component_id)
        behavior_id = (
            config.behavior.component_id
            if config.behavior is not None
            else (
                algorithm.composition.default_behavior_id
                if algorithm is not None and algorithm.composition.default_behavior_id
                else ALGORITHM_OWNED
            )
        )
        behavior = self.registry.behavior(behavior_id)
        optimizer_id = (
            config.optimizer.component_id
            if config.optimizer is not None
            else (
                algorithm.composition.default_optimizer_id
                if algorithm is not None and algorithm.composition.default_optimizer_id
                else ALGORITHM_OWNED_OPTIMIZER
            )
        )
        optimizer = self.registry.optimizer(optimizer_id)
        selected = {
            "rlspl", "environment", "agent", "algorithm", "action_behavior", "optimizer", "hyperparameters",
            "training_parameters", "learning_parameters", "evaluation",
            f"environment:{config.environment.component_id}",
            f"algorithm:{config.algorithm.component_id}",
            f"behavior:{behavior_id}",
            f"optimizer:{optimizer_id}",
            f"evaluation_protocol:{config.evaluation.protocol.value}",
            "evaluation_metrics", "evaluation_exports",
        }
        if config.search is not None:
            selected.update({"search", f"search_sampler:{config.search.sampler}"})
        if config.evaluation.summaries:
            selected.add("evaluation_summaries")
        if config.evaluation.visualizations:
            selected.add("evaluation_visualizations")
        if behavior is not None and behavior.parameters:
            selected.add("behavior_parameters")
        if optimizer is not None and optimizer.parameters:
            selected.add("optimizer_parameters")
        if algorithm is not None and any(
            "network" in role or role in {"actor", "critic", "policy"}
            for role in algorithm.composition.architecture_roles
        ):
            selected.add("model_parameters")

        issues = tuple(result.report.issues)
        statuses: dict[str, Any] = {}
        for constraint in CONSTRAINTS:
            applies = self._constraint_applies(
                constraint.scope, config, algorithm, behavior, optimizer
            )
            relevant = [
                issue for issue in issues
                if issue.code in constraint.issue_codes
                and (
                    not constraint.issue_paths
                    or any(issue.path.startswith(path) for path in constraint.issue_paths)
                )
            ]
            if not applies:
                status = "not_applicable"
            elif any(issue.severity.value == "error" for issue in relevant):
                status = "violated"
            elif relevant:
                status = "advisory"
            else:
                status = "satisfied"
            statuses[constraint.id] = {
                "status": status,
                "issues": [issue.model_dump(mode="json") for issue in relevant],
            }

        resolved = result.resolved
        composition: dict[str, Any] = {}
        if algorithm is not None:
            composition = algorithm.composition.model_dump(mode="json")
        if behavior is not None:
            composition["behavior"] = {
                "id": behavior.id,
                "name": behavior.display_name,
                "category": behavior.category,
                "requirements": behavior.requirements.model_dump(mode="json"),
            }
        if optimizer is not None:
            composition["optimizer"] = {
                "id": optimizer.id,
                "name": optimizer.display_name,
                "category": optimizer.category,
                "requirements": optimizer.requirements.model_dump(mode="json"),
            }
        effective_parameters: list[dict[str, Any]] = []
        if resolved is not None:
            for parameter_id, binding in sorted(resolved.effective_parameters.items()):
                owner = self._parameter_owner(
                    parameter_id, environment, algorithm, behavior, optimizer
                )
                effective_parameters.append({
                    "id": parameter_id,
                    "owner": owner,
                    "mode": binding.mode.value,
                    "assignment": binding.value if binding.mode is BindingMode.FIXED else binding.domain.model_dump(mode="json"),
                })
        return {
            "valid": result.report.is_valid,
            "selected_feature_ids": sorted(selected),
            "constraint_statuses": statuses,
            "selection": {
                "environment": {
                    "id": config.environment.component_id,
                    "name": environment.display_name if environment else config.environment.component_id,
                    "origin": self.registry.origin(config.environment.component_id),
                },
                "algorithm": {
                    "id": config.algorithm.component_id,
                    "name": algorithm.display_name if algorithm else config.algorithm.component_id,
                    "origin": self.registry.origin(config.algorithm.component_id),
                },
                "behavior": {
                    "id": behavior_id,
                    "name": behavior.display_name if behavior else behavior_id,
                    "origin": self.registry.origin(behavior_id),
                },
                "optimizer": {
                    "id": optimizer_id,
                    "name": optimizer.display_name if optimizer else optimizer_id,
                    "origin": self.registry.origin(optimizer_id),
                },
                "search_enabled": config.search is not None,
                "evaluation_protocol": config.evaluation.protocol.value,
                "evaluation_metrics": list(config.evaluation.metrics),
            },
            "composition": composition,
            "effective_parameters": effective_parameters,
            "derivation": [
                {"stage": "Selection", "result": f"{config.environment.component_id} + {config.algorithm.component_id} + {behavior_id} + {optimizer_id}"},
                {"stage": "Constraint resolution", "result": "accepted" if result.report.is_valid else "blocked"},
                {"stage": "Default materialization", "result": f"{len(effective_parameters)} effective parameters" if resolved else "not available"},
                {"stage": "Asset composition", "result": ("environment adapter + algorithm runtime + behavior runtime + optimizer runtime" + (" + search runtime" if config.search is not None else "") + " + shared core") if resolved else "awaiting a valid configuration"},
            ],
        }

    def _feature_tree(self) -> dict[str, Any]:
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
        environments = [{
            "id": f"environment:{item.id}",
            "label": item.display_name,
            "relation": "alternative",
            "kind": "component",
            "description": item.description,
            "detail": f"{item.capabilities.action_kind.value} actions; {item.capabilities.observation_kind.value} observations",
            "origin": self.registry.origin(item.id),
        } for item in self.registry.environments]
        algorithms = [{
            "id": f"algorithm:{item.id}",
            "label": item.display_name,
            "relation": "alternative",
            "kind": "component",
            "description": item.description or "Registered learning-algorithm component.",
            "detail": f"{item.composition.exploration_role}; {len(item.parameters)} owned parameters",
            "origin": self.registry.origin(item.id),
        } for item in self.registry.algorithms]
        behaviors = [{
            "id": f"behavior:{item.id}",
            "label": item.display_name,
            "relation": "alternative",
            "kind": "component",
            "description": item.description,
            "detail": f"{item.category}; {len(item.parameters)} owned parameters",
            "origin": self.registry.origin(item.id),
        } for item in self.registry.behaviors if item.public or item.id in referenced_behaviors]
        optimizers = [{
            "id": f"optimizer:{item.id}",
            "label": item.display_name,
            "relation": "alternative",
            "kind": "component",
            "description": item.description,
            "detail": f"{item.category}; {len(item.parameters)} owned parameters",
            "origin": self.registry.origin(item.id),
        } for item in self.registry.optimizers if item.public or item.id in referenced_optimizers]
        return {
            "id": "rlspl", "label": "RLSPL", "relation": "root", "kind": "root",
            "description": "Family of reinforcement-learning products derived from shared assets.",
            "children": [
                {
                    "id": "environment", "label": "Environment", "relation": "mandatory", "kind": "variation_point",
                    "description": "The task and interaction contract.", "group": "alternative", "cardinality": "1..1",
                    "children": environments,
                },
                {
                    "id": "agent", "label": "Agent", "relation": "mandatory", "kind": "commonality",
                    "description": "The reusable learning-agent structure.",
                    "children": [
                        {
                            "id": "algorithm", "label": "Learning algorithm", "relation": "mandatory", "kind": "variation_point",
                            "description": "Exactly one policy-learning implementation.", "group": "alternative", "cardinality": "1..1",
                            "children": algorithms,
                        },
                        {
                            "id": "action_behavior", "label": "Action-selection behavior", "relation": "mandatory", "kind": "variation_point",
                            "description": "Exactly one compatible decision or exploration mechanism.", "group": "alternative", "cardinality": "1..1",
                            "children": behaviors,
                        },
                        {
                            "id": "optimizer", "label": "Optimizer / update rule", "relation": "mandatory", "kind": "variation_point",
                            "description": "Exactly one update implementation compatible with the algorithm's declared interface.", "group": "alternative", "cardinality": "1..1",
                            "children": optimizers,
                        },
                    ],
                },
                {
                    "id": "hyperparameters", "label": "Hyperparameters", "relation": "mandatory", "kind": "variation_point",
                    "description": "Typed values whose active set is determined by selected component owners.",
                    "children": [
                        {"id": "training_parameters", "label": "Training parameters", "relation": "mandatory", "kind": "feature_group", "description": "Budget, discount, seed, logging, and checkpoint behavior."},
                        {"id": "model_parameters", "label": "Model parameters", "relation": "optional", "kind": "feature_group", "description": "Network shape and representation settings required by deep agents."},
                        {"id": "learning_parameters", "label": "Learning and optimization parameters", "relation": "mandatory", "kind": "feature_group", "description": "Learning rates, replay, and target updates."},
                        {"id": "behavior_parameters", "label": "Behavior parameters", "relation": "optional", "kind": "feature_group", "description": "Only the selected action behavior activates its schedules and noise parameters."},
                        {"id": "optimizer_parameters", "label": "Optimizer parameters", "relation": "optional", "kind": "feature_group", "description": "Adaptive moments, momentum, numerical stability, and regularization values owned by the selected optimizer."},
                    ],
                },
                {
                    "id": "search", "label": "Hyperparameter search", "relation": "optional", "kind": "variation_point",
                    "description": "Optimization over explicitly tunable parameter domains.", "group": "alternative",
                    "children": [
                        {"id": "search_sampler:random", "label": "Random search", "relation": "alternative", "kind": "feature"},
                        {"id": "search_sampler:bayesian_tpe", "label": "Bayesian TPE", "relation": "alternative", "kind": "feature"},
                    ],
                },
                {
                    "id": "evaluation", "label": "Evaluation", "relation": "mandatory", "kind": "variation_point",
                    "description": "A declared protocol for measuring and exporting trained-agent behavior.",
                    "children": [
                        {"id": "evaluation_protocol:default", "label": "Default evaluation", "relation": "alternative", "kind": "feature"},
                        {"id": "evaluation_protocol:configurable", "label": "Configurable evaluation", "relation": "alternative", "kind": "feature"},
                        {"id": "evaluation_metrics", "label": "Metrics", "relation": "or_group", "kind": "feature_group", "description": "One or more performance or efficiency measures."},
                        {"id": "evaluation_summaries", "label": "Statistical summaries", "relation": "optional", "kind": "feature_group"},
                        {"id": "evaluation_visualizations", "label": "Visualizations", "relation": "optional", "kind": "feature_group"},
                        {"id": "evaluation_exports", "label": "Export formats", "relation": "or_group", "kind": "feature_group", "description": "One or more persistent result formats."},
                    ],
                },
            ],
        }

    @staticmethod
    def _feature_count(node: dict[str, Any]) -> int:
        return 1 + sum(SPLModel._feature_count(child) for child in node.get("children", []))

    def _pairing_projection(self, environment: Any, algorithm: Any) -> dict[str, Any]:
        reasons: list[str] = []
        if environment.capabilities.action_kind not in algorithm.requirements.action_kinds:
            reasons.append(
                f"{environment.capabilities.action_kind.value} actions are not supported"
            )
        if environment.capabilities.observation_kind not in algorithm.requirements.observation_kinds:
            reasons.append(
                f"{environment.capabilities.observation_kind.value} observations are not supported"
            )
        if (
            algorithm.requirements.requires_bounded_actions
            and not environment.capabilities.action_bounded
        ):
            reasons.append("finite action bounds are required")
        return {
            "algorithm_id": algorithm.id,
            "algorithm_name": algorithm.display_name,
            "compatible": not reasons,
            "runtime_ready": bool(
                environment.runtime_assets is not None
                and algorithm.runtime_assets is not None
            ),
            "reason": "; ".join(reasons) if reasons else "capability contracts match",
        }

    @staticmethod
    def _algorithm_behavior_projection(algorithm: Any, behavior: Any) -> dict[str, Any]:
        requirements = behavior.requirements
        reasons: list[str] = []
        if algorithm.composition.policy_interface not in requirements.policy_interfaces:
            reasons.append(
                f"needs {', '.join(sorted(item.value for item in requirements.policy_interfaces))}"
            )
        if not (algorithm.requirements.action_kinds & requirements.action_kinds):
            reasons.append("action kinds do not overlap")
        if (
            requirements.requires_perturbable_policy
            and not algorithm.composition.perturbable_policy
        ):
            reasons.append("policy model is not perturbable")
        return {
            "behavior_id": behavior.id,
            "behavior_name": behavior.display_name,
            "category": behavior.category,
            "compatible": not reasons,
            "runtime_ready": bool(
                algorithm.runtime_assets is not None
                and behavior.runtime_assets is not None
            ),
            "reason": "; ".join(reasons) if reasons else "capability contracts match",
        }

    @staticmethod
    def _algorithm_optimizer_projection(algorithm: Any, optimizer: Any) -> dict[str, Any]:
        reasons = optimizer_reasons(algorithm, optimizer)
        return {
            "optimizer_id": optimizer.id,
            "optimizer_name": optimizer.display_name,
            "category": optimizer.category,
            "compatible": not reasons,
            "runtime_ready": bool(
                algorithm.runtime_assets is not None
                and optimizer.runtime_assets is not None
            ),
            "reason": "; ".join(reasons) if reasons else "update interfaces match",
        }

    @staticmethod
    def _constraint_applies(
        scope: str,
        config: UserConfiguration,
        algorithm: Any,
        behavior: Any,
        optimizer: Any,
    ) -> bool:
        tunable = any(binding.mode is BindingMode.TUNABLE for binding in config.training.parameters.values())
        if scope == "always":
            return True
        if scope == "bounded_actions":
            return bool(algorithm and algorithm.requirements.requires_bounded_actions)
        if scope == "replay_algorithm":
            return bool(algorithm and algorithm.composition.memory_role)
        if scope == "behavior":
            return behavior is not None
        if scope == "optimizer":
            return optimizer is not None
        if scope == "behavior_schedule":
            return bool(
                behavior
                and any(
                    definition.id.endswith("_start")
                    for definition in behavior.parameters
                )
            )
        if scope == "search_or_tunable":
            return config.search is not None or tunable
        if scope == "search":
            return config.search is not None
        if scope == "success_metric":
            return bool({"success_rate", "episodes_to_threshold"} & set(config.evaluation.metrics))
        if scope == "trace_consumer":
            return bool(
                {"reward_auc"} & set(config.evaluation.metrics)
                or {"learning_curve", "convergence"} & set(config.evaluation.visualizations)
            )
        if scope == "replicated_summary":
            return bool(
                {"standard_deviation", "confidence_interval", "iqm"}
                & set(config.evaluation.summaries)
            )
        if scope == "comparative":
            return "comparative" in config.evaluation.visualizations
        if scope == "top_k":
            return config.evaluation.top_k is not None
        return True

    @staticmethod
    def _parameter_owner(
        parameter_id: str,
        environment: Any,
        algorithm: Any,
        behavior: Any,
        optimizer: Any,
    ) -> str:
        for component in (environment, algorithm, behavior, optimizer):
            if component is None:
                continue
            if any(definition.id == parameter_id for definition in component.parameters):
                return component.id
        return "core.training"
