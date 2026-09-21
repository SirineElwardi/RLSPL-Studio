"""Versioned domain and persistence models for RLSPL Studio."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)


class FrozenModel(BaseModel):
    """Base model for immutable resolved and descriptor objects."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class StrictModel(BaseModel):
    """Base model for validated user input."""

    model_config = ConfigDict(extra="forbid")


class StringEnum(str, Enum):
    """Python 3.10-compatible equivalent of Python 3.11's StrEnum."""

    def __str__(self) -> str:
        return self.value


class ActionKind(StringEnum):
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"


class ObservationKind(StringEnum):
    DISCRETE = "discrete"
    VECTOR = "vector"


class PolicyInterface(StringEnum):
    """Action-decision interface exposed by an algorithm runtime."""

    Q_VALUES = "q_values"
    DETERMINISTIC_ACTOR = "deterministic_actor"
    STOCHASTIC_POLICY = "stochastic_policy"
    ALGORITHM_OWNED = "algorithm_owned"


class OptimizerInterface(StringEnum):
    """Parameter-update interface exposed by an algorithm runtime."""

    TABULAR_UPDATE = "tabular_update"
    TORCH_GRADIENT = "torch_gradient"
    ALGORITHM_OWNED = "algorithm_owned"


class EvaluationActionMode(StringEnum):
    """How a trained policy chooses actions during evaluation."""

    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"
    TRAINING_BEHAVIOR = "training_behavior"


class ParameterType(StringEnum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    CATEGORICAL = "categorical"


class BindingMode(StringEnum):
    FIXED = "fixed"
    TUNABLE = "tunable"


class SearchDomainKind(StringEnum):
    INTEGER = "integer"
    FLOAT = "float"
    LOG_FLOAT = "log_float"
    CATEGORICAL = "categorical"


class IssueSeverity(StringEnum):
    ERROR = "error"
    ADVISORY = "advisory"


class StudyExecutionStatus(StringEnum):
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class StudyRunStatus(StringEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class EnvironmentSource(StringEnum):
    CATALOG = "catalog"
    CUSTOM = "custom"


class EvaluationProtocol(StringEnum):
    DEFAULT = "default"
    CONFIGURABLE = "configurable"


class SearchDomain(StrictModel):
    kind: SearchDomainKind
    lower: int | float | None = None
    upper: int | float | None = None
    choices: tuple[Any, ...] = ()

    @model_validator(mode="after")
    def shape_matches_kind(self) -> "SearchDomain":
        numeric = {
            SearchDomainKind.INTEGER,
            SearchDomainKind.FLOAT,
            SearchDomainKind.LOG_FLOAT,
        }
        if self.kind in numeric:
            if self.lower is None or self.upper is None:
                raise ValueError("numeric search domains require lower and upper")
            if self.choices:
                raise ValueError("numeric search domains cannot define choices")
        else:
            if len(self.choices) < 2:
                raise ValueError("categorical search domains require at least two choices")
            if self.lower is not None or self.upper is not None:
                raise ValueError("categorical search domains cannot define bounds")
        return self


class ParameterBinding(StrictModel):
    mode: BindingMode
    value: Any | None = None
    domain: SearchDomain | None = None

    @model_validator(mode="after")
    def exactly_one_payload(self) -> "ParameterBinding":
        if self.mode is BindingMode.FIXED:
            if self.value is None or self.domain is not None:
                raise ValueError("fixed bindings require value and forbid domain")
        elif self.value is not None or self.domain is None:
            raise ValueError("tunable bindings require domain and forbid value")
        return self


class EnvironmentSelection(StrictModel):
    source: EnvironmentSource = EnvironmentSource.CATALOG
    component_id: str = Field(min_length=1)
    entry_point: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def custom_requires_entry_point(self) -> "EnvironmentSelection":
        if self.source is EnvironmentSource.CUSTOM and not self.entry_point:
            raise ValueError("custom environments require entry_point")
        if self.source is EnvironmentSource.CATALOG and self.entry_point is not None:
            raise ValueError("catalog environments cannot override entry_point")
        return self


class AlgorithmSelection(StrictModel):
    component_id: str = Field(min_length=1)


class BehaviorSelection(StrictModel):
    """Selected action-selection/exploration component."""

    component_id: str = Field(min_length=1)


class OptimizerSelection(StrictModel):
    """Selected parameter-update component."""

    component_id: str = Field(min_length=1)


class TrainingConfiguration(StrictModel):
    budget_unit: Literal["episodes", "timesteps"] = "episodes"
    budget: int = Field(gt=0)
    parameters: dict[str, ParameterBinding] = Field(default_factory=dict)
    checkpoint_policy: Literal["disabled", "periodic", "best"] = "best"
    checkpoint_interval: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def periodic_checkpoint_has_interval(self) -> "TrainingConfiguration":
        if self.checkpoint_policy == "periodic" and self.checkpoint_interval is None:
            raise ValueError("periodic checkpoint policy requires checkpoint_interval")
        if self.checkpoint_policy != "periodic" and self.checkpoint_interval is not None:
            raise ValueError("checkpoint_interval is only valid for periodic checkpoints")
        return self


class SearchConfiguration(StrictModel):
    sampler: Literal["random", "bayesian_tpe"]
    objective: Literal["average_reward", "cumulative_reward", "reward_auc"]
    trials: int | None = Field(default=None, gt=0)
    timeout_seconds: int | None = Field(default=None, gt=0)
    seeds: tuple[int, ...] = (0,)
    sampler_seed: int = 0
    aggregation: Literal["mean", "median", "iqm"] = "mean"
    top_k: int = Field(default=5, ge=1, le=5)
    provider_id: str | None = None

    @field_validator("seeds")
    @classmethod
    def seeds_are_distinct(cls, seeds: tuple[int, ...]) -> tuple[int, ...]:
        if len(seeds) != len(set(seeds)):
            raise ValueError("search seeds must be distinct")
        return seeds

    @model_validator(mode="after")
    def has_budget_and_seeds(self) -> "SearchConfiguration":
        if self.trials is None and self.timeout_seconds is None:
            raise ValueError("search requires trials, timeout_seconds, or both")
        if not self.seeds:
            raise ValueError("search requires at least one seed")
        return self


class EvaluationConfiguration(StrictModel):
    protocol: EvaluationProtocol = EvaluationProtocol.DEFAULT
    metrics: tuple[str, ...] = ("average_reward",)
    summaries: tuple[str, ...] = ("mean",)
    visualizations: tuple[str, ...] = ("learning_curve",)
    export_formats: tuple[Literal["json", "csv", "png"], ...] = ("json",)
    seeds: tuple[int, ...] = (0,)
    episodes_per_seed: int = Field(default=10, gt=0)
    collect_reward_trace: bool = True
    success_predicate: str | None = None
    comparison_run_ids: tuple[str, ...] = ()
    top_k: int | None = Field(default=None, gt=0)
    action_mode: EvaluationActionMode = EvaluationActionMode.DETERMINISTIC


class UserConfiguration(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(min_length=1)
    environment: EnvironmentSelection
    algorithm: AlgorithmSelection
    # Optional on input for backward compatibility. The resolver materializes
    # the selected algorithm's declared default into every resolved product.
    behavior: BehaviorSelection | None = None
    # Optional for backward compatibility; resolution freezes the algorithm's
    # declared default into the generated product and study manifest.
    optimizer: OptimizerSelection | None = None
    training: TrainingConfiguration
    search: SearchConfiguration | None = None
    evaluation: EvaluationConfiguration = Field(default_factory=EvaluationConfiguration)


def _distinct_json_values(values: tuple[Any, ...], owner: str) -> tuple[Any, ...]:
    try:
        encoded = [
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            for value in values
        ]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{owner} values must be finite JSON values") from exc
    if len(encoded) != len(set(encoded)):
        raise ValueError(f"{owner} values must be distinct")
    return values


class ExplorationCondition(StrictModel):
    """A finite applicability predicate for an exploration axis."""

    target: Literal[
        "environment.component_id",
        "algorithm.component_id",
        "behavior.component_id",
        "optimizer.component_id",
    ]
    values: tuple[Any, ...] = Field(min_length=1)

    @field_validator("values")
    @classmethod
    def values_are_distinct_json(cls, values: tuple[Any, ...]) -> tuple[Any, ...]:
        return _distinct_json_values(values, "condition")


class ExplorationAxis(StrictModel):
    """One finite structural selection or parametric dimension in a study."""

    target: str = Field(min_length=1)
    values: tuple[Any, ...] = Field(min_length=1)
    label: str | None = None
    when: tuple[ExplorationCondition, ...] = ()

    @field_validator("target")
    @classmethod
    def target_is_trimmed(cls, value: str) -> str:
        if value != value.strip() or any(character.isspace() for character in value):
            raise ValueError("axis target cannot contain whitespace")
        return value

    @field_validator("values")
    @classmethod
    def values_are_distinct(cls, values: tuple[Any, ...]) -> tuple[Any, ...]:
        return _distinct_json_values(values, "axis")

    @model_validator(mode="after")
    def conditions_are_unique(self) -> "ExplorationAxis":
        targets = [condition.target for condition in self.when]
        if len(targets) != len(set(targets)):
            raise ValueError("an axis condition target can appear only once")
        if self.target in targets:
            raise ValueError("an axis cannot be conditional on its own target")
        return self


class StudyReplications(StrictModel):
    """Training and evaluation repetitions kept outside product variability."""

    seeds: tuple[int, ...] = (0,)
    evaluation_seeds: tuple[int, ...] = (100, 101, 102)

    @field_validator("seeds")
    @classmethod
    def seeds_are_nonempty_and_distinct(cls, seeds: tuple[int, ...]) -> tuple[int, ...]:
        if not seeds:
            raise ValueError("a study requires at least one training seed")
        if len(seeds) != len(set(seeds)):
            raise ValueError("study training seeds must be distinct")
        return seeds

    @field_validator("evaluation_seeds")
    @classmethod
    def evaluation_seeds_are_nonempty_and_distinct(
        cls, seeds: tuple[int, ...]
    ) -> tuple[int, ...]:
        if not seeds:
            raise ValueError("a study requires at least one evaluation seed")
        if len(seeds) != len(set(seeds)):
            raise ValueError("study evaluation seeds must be distinct")
        return seeds


class ExplorationStudy(StrictModel):
    """A reproducible finite exploration assembled from explicit selections."""

    schema_version: Literal["1.0", "2.0"] = "2.0"
    name: str = Field(min_length=1)
    # Retained only so frozen v1 manifests remain readable. New v2 studies are
    # deliberately independent from the Configure workspace.
    base_configuration: UserConfiguration | None = None
    axes: tuple[ExplorationAxis, ...] = Field(min_length=1)
    replications: StudyReplications = Field(default_factory=StudyReplications)

    @model_validator(mode="after")
    def shape_matches_schema_version(self) -> "ExplorationStudy":
        targets = [axis.target for axis in self.axes]
        if len(targets) != len(set(targets)):
            raise ValueError("an exploration target can appear in only one axis")
        if self.schema_version == "1.0":
            if self.base_configuration is None:
                raise ValueError("v1 studies require base_configuration")
            return self
        if self.base_configuration is not None:
            raise ValueError("v2 studies do not use base_configuration")
        required = {"environment.component_id", "algorithm.component_id"}
        missing = sorted(required - set(targets))
        if missing:
            raise ValueError(
                "v2 studies require explicit environment and algorithm selections: "
                + ", ".join(missing)
            )
        return self

    @model_serializer(mode="wrap")
    def omit_legacy_base_from_v2(self, handler: Any) -> dict[str, Any]:
        payload = handler(self)
        if self.schema_version == "2.0":
            payload.pop("base_configuration", None)
        return payload


class ValidationIssue(FrozenModel):
    severity: IssueSeverity
    code: str
    path: str
    message: str
    suggestion: str | None = None


class ValidationReport(FrozenModel):
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is IssueSeverity.ERROR)

    @property
    def advisories(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity is IssueSeverity.ADVISORY)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class ResolvedConfiguration(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str
    environment_id: str
    environment_version: str
    algorithm_id: str
    algorithm_version: str
    behavior_id: str
    behavior_version: str
    optimizer_id: str
    optimizer_version: str
    training_budget_unit: Literal["episodes", "timesteps"]
    training_budget: int
    checkpoint_policy: Literal["disabled", "periodic", "best"]
    checkpoint_interval: int | None
    effective_parameters: dict[str, ParameterBinding]
    search: SearchConfiguration | None
    evaluation: EvaluationConfiguration
    capability_evidence: dict[str, Any]
    requested_configuration_hash: str
    configuration_hash: str

    @model_validator(mode="before")
    @classmethod
    def migrate_pre_optimizer_manifests(cls, payload: Any) -> Any:
        """Keep v0.13 generated products and study manifests monitorable."""

        if not isinstance(payload, dict) or payload.get("optimizer_id") is not None:
            return payload
        migrated = dict(payload)
        algorithm_id = migrated.get("algorithm_id")
        migrated["optimizer_id"] = (
            "rlspl.optimizer.direct_update"
            if algorithm_id == "rlspl.q_learning"
            else "rlspl.optimizer.adam"
            if algorithm_id in {"rlspl.dqn", "rlspl.ddpg", "rlspl.sac"}
            else "rlspl.optimizer.algorithm_owned"
        )
        migrated["optimizer_version"] = "1.0.0"
        return migrated


class ResolutionResult(FrozenModel):
    report: ValidationReport
    resolved: ResolvedConfiguration | None = None


class StudyVariant(FrozenModel):
    candidate_index: int
    configuration_id: str
    axis_values: dict[str, Any]
    configuration: ResolvedConfiguration
    advisories: tuple[ValidationIssue, ...] = ()


class RejectedStudyCandidate(FrozenModel):
    candidate_index: int
    axis_values: dict[str, Any]
    issues: tuple[ValidationIssue, ...]


class DuplicateStudyCandidate(FrozenModel):
    candidate_index: int
    axis_values: dict[str, Any]
    duplicate_of: str


class StudyPlanSummary(FrozenModel):
    candidate_count: int
    evaluated_candidate_count: int
    valid_candidate_count: int
    invalid_candidate_count: int
    duplicate_candidate_count: int
    unique_configuration_count: int
    planned_run_count: int
    expansion_complete: bool


class StudyManifest(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    study_hash: str
    manifest_hash: str
    created_at: datetime
    study: ExplorationStudy
    summary: StudyPlanSummary
    variants: tuple[StudyVariant, ...]
    rejected_candidates: tuple[RejectedStudyCandidate, ...] = ()
    duplicate_candidates: tuple[DuplicateStudyCandidate, ...] = ()
    advisories: tuple[ValidationIssue, ...] = ()


class StudyRunRecord(FrozenModel):
    run_id: str
    configuration_id: str
    training_seed: int
    resolved_configuration_hash: str
    status: StudyRunStatus = StudyRunStatus.PENDING
    attempt: int = Field(default=0, ge=0)
    product_path: str
    configuration_path: str
    attempt_path: str | None = None
    log_path: str | None = None
    artifact_path: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    return_code: int | None = None
    error: str | None = None


class StudyExecutionState(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    execution_id: str
    study_hash: str
    manifest_hash: str
    status: StudyExecutionStatus
    workspace: str
    jobs: int = Field(gt=0)
    dependencies: tuple[str, ...]
    python_executable: str
    environment_snapshot_path: str | None = None
    created_at: datetime
    updated_at: datetime
    runs: tuple[StudyRunRecord, ...]
    error: str | None = None


class StudyRunContext(FrozenModel):
    """Links one product artifact to its study without creating variability."""

    execution_id: str
    study_hash: str
    manifest_hash: str
    configuration_id: str
    study_run_id: str
    attempt: int = Field(gt=0)
    training_seed: int


class HPORunMetadata(FrozenModel):
    """Compact HPO provenance stored with the final selected-agent run."""

    sampler: str
    objective: str
    aggregation: str
    trial_budget: int | None
    completed_trials: int = Field(ge=0)
    failed_trials: int = Field(ge=0)
    best_trial_number: int = Field(ge=0)
    best_objective_value: float
    best_parameters: dict[str, Any]
    best_configuration_hash: str
    search_seeds: tuple[int, ...]
    sampler_seed: int


class RunMetadata(FrozenModel):
    """Cross-cutting execution record; deliberately not a feature branch."""

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    status: Literal["completed"] = "completed"
    requested_configuration_hash: str
    resolved_configuration_hash: str
    component_versions: dict[str, str]
    started_at: datetime
    ended_at: datetime | None = None
    effective_device: str
    python_version: str
    platform: str
    effective_seeds: tuple[int, ...]
    artifacts: dict[str, str] = Field(default_factory=dict)
    execution_mode: Literal["single", "hpo"] = "single"
    hpo: HPORunMetadata | None = None
    study: StudyRunContext | None = None

    @model_validator(mode="after")
    def hpo_evidence_matches_execution_mode(self) -> "RunMetadata":
        if self.execution_mode == "hpo" and self.hpo is None:
            raise ValueError("HPO execution metadata requires an HPO provenance record")
        if self.execution_mode == "single" and self.hpo is not None:
            raise ValueError("single execution metadata cannot contain HPO provenance")
        return self
