"""Convert resolved configurations into explicit product-generation plans."""

from __future__ import annotations

from pydantic import Field

from .compatibility import (
    behavior_reasons,
    environment_algorithm_reasons,
    optimizer_reasons,
)
from .descriptors import AlgorithmDescriptor, EnvironmentDescriptor
from .models import FrozenModel, ResolvedConfiguration
from .registry import ComponentRegistry


class ProductPlanningError(ValueError):
    """Raised when a valid configuration has no executable implementation yet."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PlannedFile(FrozenModel):
    path: str
    role: str
    source_component_id: str


class ProductPlan(FrozenModel):
    schema_version: str = "1.0"
    product_name: str
    configuration_hash: str
    environment_id: str
    algorithm_id: str
    behavior_id: str
    optimizer_id: str
    hpo_enabled: bool = False
    dependencies: tuple[str, ...]
    files: tuple[PlannedFile, ...]
    checkpoint_filename: str
    environment_template: str
    agent_template: str
    trainer_template: str
    behavior_template: str
    optimizer_template: str
    environment_template_root: str | None = Field(default=None, exclude=True)
    algorithm_template_root: str | None = Field(default=None, exclude=True)
    behavior_template_root: str | None = Field(default=None, exclude=True)
    optimizer_template_root: str | None = Field(default=None, exclude=True)
    entry_command: str = "python3 run.py"


class ProductPlanner:
    """Plan only combinations backed by complete runtime implementations."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry

    def plan(self, resolved: ResolvedConfiguration) -> ProductPlan:
        environment = self.registry.environment(resolved.environment_id)
        algorithm = self.registry.algorithm(resolved.algorithm_id)
        behavior = self.registry.behavior(resolved.behavior_id)
        optimizer = self.registry.optimizer(resolved.optimizer_id)
        if (
            environment is None
            or algorithm is None
            or behavior is None
            or optimizer is None
        ):
            raise ProductPlanningError("GEN-03", "resolved components disappeared from the registry")
        if (
            environment.runtime_assets is None
            or algorithm.runtime_assets is None
            or behavior.runtime_assets is None
            or optimizer.runtime_assets is None
        ):
            raise ProductPlanningError(
                "GEN-03", "a resolved component has no installed runtime assets"
            )

        dependencies = {
            f"{name}{constraint}" for name, constraint in environment.dependencies.items()
        }
        dependencies.update(
            f"{name}{constraint}" for name, constraint in algorithm.dependencies.items()
        )
        dependencies.update(
            f"{name}{constraint}" for name, constraint in behavior.dependencies.items()
        )
        dependencies.update(
            f"{name}{constraint}" for name, constraint in optimizer.dependencies.items()
        )
        if resolved.evaluation.visualizations or "png" in resolved.evaluation.export_formats:
            dependencies.add("matplotlib>=3.7,<4")

        common = (
            PlannedFile(path="README.md", role="documentation", source_component_id="core"),
            PlannedFile(path="pyproject.toml", role="packaging", source_component_id="core"),
            PlannedFile(path="run.py", role="launcher", source_component_id="core"),
            PlannedFile(path="config.json", role="resolved_configuration", source_component_id="core"),
            PlannedFile(path="generation-manifest.json", role="manifest", source_component_id="core"),
            PlannedFile(path="src/rlspl_product/__init__.py", role="package", source_component_id="core"),
            PlannedFile(path="src/rlspl_product/__main__.py", role="entrypoint", source_component_id="core"),
            PlannedFile(path="src/rlspl_product/main.py", role="orchestration", source_component_id="core"),
            PlannedFile(
                path="src/rlspl_product/trainer.py",
                role="training",
                source_component_id=resolved.algorithm_id,
            ),
            PlannedFile(
                path="src/rlspl_product/behavior.py",
                role="action_selection",
                source_component_id=resolved.behavior_id,
            ),
            PlannedFile(
                path="src/rlspl_product/optimizer.py",
                role="parameter_update",
                source_component_id=resolved.optimizer_id,
            ),
            PlannedFile(path="src/rlspl_product/evaluation.py", role="evaluation", source_component_id="core"),
        )
        selected = (
            PlannedFile(
                path="src/rlspl_product/environment.py",
                role="environment_adapter",
                source_component_id=resolved.environment_id,
            ),
            PlannedFile(
                path="src/rlspl_product/agent.py",
                role="algorithm",
                source_component_id=resolved.algorithm_id,
            ),
        )
        hpo = (
            PlannedFile(
                path="src/rlspl_product/hpo.py",
                role="hyperparameter_search",
                source_component_id=(
                    "core.bayesian_tpe"
                    if resolved.search and resolved.search.sampler == "bayesian_tpe"
                    else "core.random"
                ),
            ),
        ) if resolved.search is not None else ()
        return ProductPlan(
            product_name=resolved.name,
            configuration_hash=resolved.configuration_hash,
            environment_id=resolved.environment_id,
            algorithm_id=resolved.algorithm_id,
            behavior_id=resolved.behavior_id,
            optimizer_id=resolved.optimizer_id,
            hpo_enabled=resolved.search is not None,
            dependencies=tuple(sorted(dependencies)),
            files=common + hpo + selected,
            checkpoint_filename=algorithm.runtime_assets.checkpoint_filename,
            environment_template=environment.runtime_assets.adapter_template,
            agent_template=algorithm.runtime_assets.agent_template,
            trainer_template=algorithm.runtime_assets.trainer_template,
            behavior_template=behavior.runtime_assets.behavior_template,
            optimizer_template=optimizer.runtime_assets.optimizer_template,
            environment_template_root=environment.runtime_assets.template_root,
            algorithm_template_root=algorithm.runtime_assets.template_root,
            behavior_template_root=behavior.runtime_assets.template_root,
            optimizer_template_root=optimizer.runtime_assets.template_root,
        )

    def executable_pairings(self) -> tuple[tuple[str, str], ...]:
        """Return the capability-compatible Cartesian product of installed components."""

        pairings: list[tuple[tuple[int, int, str, str], tuple[str, str]]] = []
        for environment in self.registry.environments:
            if environment.runtime_assets is None:
                continue
            for algorithm in self.registry.algorithms:
                if algorithm.runtime_assets is None:
                    continue
                if self._compatible(environment, algorithm):
                    score = (
                        0 if environment.id in algorithm.verified_environment_ids else 1,
                        len(environment.dependencies) + len(algorithm.dependencies),
                        environment.id,
                        algorithm.id,
                    )
                    pairings.append((score, (environment.id, algorithm.id)))
        return tuple(pairing for _, pairing in sorted(pairings))

    def executable_compositions(self) -> tuple[tuple[str, str, str, str], ...]:
        """Return complete installed environment × algorithm × behavior × optimizer products."""

        compositions: list[tuple[str, str, str, str]] = []
        for environment_id, algorithm_id in self.executable_pairings():
            environment = self.registry.environment(environment_id)
            algorithm = self.registry.algorithm(algorithm_id)
            assert environment is not None and algorithm is not None
            for behavior in self.registry.behaviors:
                if behavior.runtime_assets is None:
                    continue
                if behavior_reasons(environment, algorithm, behavior):
                    continue
                for optimizer in self.registry.optimizers:
                    if optimizer.runtime_assets is None:
                        continue
                    if not optimizer_reasons(algorithm, optimizer):
                        compositions.append((
                            environment_id,
                            algorithm_id,
                            behavior.id,
                            optimizer.id,
                        ))
        return tuple(sorted(compositions))

    @staticmethod
    def _compatible(
        environment: EnvironmentDescriptor,
        algorithm: AlgorithmDescriptor,
    ) -> bool:
        return not environment_algorithm_reasons(environment, algorithm)
