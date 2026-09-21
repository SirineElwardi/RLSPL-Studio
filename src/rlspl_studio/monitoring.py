"""Read-only projections over generated products and study executions.

Monitoring consumes product and runner metadata. It never mutates state,
resumes a process, or changes a product configuration.
"""

from __future__ import annotations

import csv
import errno
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import (
    ResolvedConfiguration,
    StudyExecutionState,
    StudyManifest,
    StudyRunRecord,
    StudyRunStatus,
)


class MonitoringError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MonitoringService:
    """Safely discover and summarize Studio-owned products and studies."""

    _MAX_JSON_BYTES = 12_000_000
    _MAX_TRACE_BYTES = 24_000_000
    _MAX_LOG_TAIL_BYTES = 64_000
    _MAX_TRACE_POINTS = 600
    _PRODUCT_PREFIX = "product:"
    _ADJACENT_STUDY_PREFIX = "adjacent:"
    _RESERVED_DIRECTORIES = frozenset({"studies", "study-runs"})
    _INACTIVE = "(not active)"

    def __init__(self, workspace_root: Path) -> None:
        resolved = workspace_root.resolve()
        # Preserve the v0.10 constructor contract for callers that supplied the
        # study-runs directory directly.
        if resolved.name == "study-runs":
            self.workspace_root = resolved.parent
            self.executions_root = resolved
        else:
            self.workspace_root = resolved
            self.executions_root = resolved / "study-runs"

    def list_executions(self) -> dict[str, Any]:
        executions = self._study_overviews() + self._product_overviews()
        executions.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        counts = Counter(item.get("kind", "unknown") for item in executions)
        return {
            "executions": executions,
            "root": str(self.workspace_root),
            "counts": {
                "studies": counts.get("study", 0),
                "products": counts.get("product", 0),
            },
        }

    def execution(self, execution_id: str) -> dict[str, Any]:
        if execution_id.startswith(self._PRODUCT_PREFIX):
            return self._product_execution(execution_id)
        return self._study_execution(execution_id)

    def run(self, execution_id: str, run_id: str) -> dict[str, Any]:
        if execution_id.startswith(self._PRODUCT_PREFIX):
            return self._product_run(execution_id, run_id)
        return self._study_run(execution_id, run_id)

    def hpo(self, execution_id: str, run_id: str) -> dict[str, Any]:
        """Return the dedicated HPO projection for one product run."""

        projection = self.run(execution_id, run_id).get("hpo")
        if not isinstance(projection, dict) or not projection.get("enabled"):
            raise MonitoringError("MON-05", f"run is not an HPO execution: {run_id}")
        return projection

    def _study_overviews(self) -> list[dict[str, Any]]:
        executions: list[dict[str, Any]] = []
        sources = (
            (self.executions_root, ""),
            # Before v0.15.3, omitting --workspace placed a run beside a
            # Studio-saved manifest under generated/studies/. Keep those
            # workspaces visible without moving or rewriting their evidence.
            (self.workspace_root / "studies", self._ADJACENT_STUDY_PREFIX),
        )
        for root, identifier_prefix in sources:
            if not root.is_dir():
                continue
            try:
                candidates = sorted(
                    (
                        item for item in root.iterdir()
                        if item.is_dir() and not item.is_symlink()
                    ),
                    key=lambda item: item.name,
                )
            except OSError as exc:
                raise MonitoringError(
                    "MON-02", f"execution root cannot be read: {exc}"
                ) from exc
            for candidate in candidates:
                state_path = candidate / "study-state.json"
                if not state_path.is_file():
                    continue
                catalog_id = f"{identifier_prefix}{candidate.name}"
                try:
                    state = self._load_state(state_path)
                    manifest = self._load_manifest(candidate / "study-manifest.json")
                    lifecycle = self._study_lifecycle(candidate, state)
                    executions.append(
                        self._study_overview(
                            candidate,
                            state,
                            manifest,
                            catalog_id=catalog_id,
                            lifecycle=lifecycle,
                        )
                    )
                except MonitoringError as exc:
                    executions.append({
                        "id": catalog_id,
                        "name": candidate.name,
                        "kind": "study",
                        "kind_label": "Study",
                        "status": "unreadable",
                        "error": str(exc),
                        "counts": {},
                        "total_runs": 0,
                        "completed_runs": 0,
                        "progress_percent": 0.0,
                    })
        return executions

    def _product_overviews(self) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        if not self.workspace_root.is_dir():
            return products
        try:
            candidates = sorted(
                (
                    item for item in self.workspace_root.iterdir()
                    if item.is_dir()
                    and not item.is_symlink()
                    and item.name not in self._RESERVED_DIRECTORIES
                    and (item / "config.json").is_file()
                    and (item / "generation-manifest.json").is_file()
                ),
                key=lambda item: item.name,
            )
        except OSError as exc:
            raise MonitoringError("MON-02", f"product workspace cannot be read: {exc}") from exc
        for product in candidates:
            try:
                configuration = self._load_configuration(product / "config.json")
                rows = self._product_run_rows(product, configuration)
                products.append(self._product_overview(product, configuration, rows))
            except MonitoringError as exc:
                products.append({
                    "id": f"{self._PRODUCT_PREFIX}{product.name}",
                    "name": product.name,
                    "kind": "product",
                    "kind_label": "Product",
                    "status": "unreadable",
                    "error": str(exc),
                    "counts": {},
                    "total_runs": 0,
                    "completed_runs": 0,
                    "progress_percent": 0.0,
                })
        return products

    def _study_execution(self, execution_id: str) -> dict[str, Any]:
        workspace = self._study_workspace(execution_id)
        state = self._load_state(workspace / "study-state.json")
        manifest = self._load_manifest(workspace / "study-manifest.json")
        lifecycle = self._study_lifecycle(workspace, state)
        variants = {item.configuration_id: item for item in manifest.variants}
        run_rows = [
            self._study_run_overview(
                workspace,
                run,
                variants.get(run.configuration_id),
                stale_execution=lifecycle["stale"],
            )
            for run in state.runs
        ]
        configurations = [
            {
                "configuration_id": item.configuration_id,
                "configuration": item.configuration.model_dump(mode="json"),
                "axis_values": item.axis_values,
            }
            for item in manifest.variants
        ]
        comparisons, variability = self._configuration_analysis(configurations, run_rows)
        self._attach_varied_values(run_rows, comparisons)
        overview = self._study_overview(
            workspace,
            state,
            manifest,
            catalog_id=execution_id,
            lifecycle=lifecycle,
        )
        run_progress = [
            100.0
            if item["status"] in {"completed", "failed", "interrupted"}
            else float(
                (
                    item["hpo_progress"].get("progress_percent")
                    if item.get("hpo_enabled")
                    else item["progress"].get("budget_percent")
                )
                or 0.0
            )
            for item in run_rows
        ]
        if run_progress:
            overview["progress_percent"] = round(sum(run_progress) / len(run_progress), 1)
        overview.update({
            "study_hash": state.study_hash,
            "manifest_hash": state.manifest_hash,
            "jobs": state.jobs,
            "dependencies": list(state.dependencies),
            "python_executable": state.python_executable,
            "environment_snapshot_path": state.environment_snapshot_path,
            "error": state.error or lifecycle["message"],
            "runs": run_rows,
            "comparisons": comparisons,
            "variability": variability,
            "study_summary": self._study_completion_summary(
                state, comparisons, variability, lifecycle=lifecycle
            ),
            "algorithms": sorted({row["algorithm_id"] for row in run_rows}),
            "environments": sorted({row["environment_id"] for row in run_rows}),
            "behaviors": sorted({row["behavior_id"] for row in run_rows}),
            "optimizers": sorted({row["optimizer_id"] for row in run_rows}),
            "hpo_enabled": any(
                item.configuration.search is not None for item in manifest.variants
            ),
            "hpo_run_count": sum(bool(row.get("hpo_enabled")) for row in run_rows),
        })
        return overview

    def _product_execution(self, execution_id: str) -> dict[str, Any]:
        product = self._product_workspace(execution_id)
        configuration = self._load_configuration(product / "config.json")
        payload = configuration.model_dump(mode="json")
        rows = self._product_run_rows(product, configuration)
        configuration_id = self._configuration_id(payload)
        comparisons, variability = self._configuration_analysis([{
            "configuration_id": configuration_id,
            "configuration": payload,
            "axis_values": {},
        }], rows)
        self._attach_varied_values(rows, comparisons)
        overview = self._product_overview(product, configuration, rows)
        overview.update({
            "study_hash": None,
            "manifest_hash": None,
            "jobs": None,
            "dependencies": [],
            "python_executable": None,
            "environment_snapshot_path": None,
            "error": None,
            "runs": rows,
            "comparisons": comparisons,
            "variability": variability,
            "study_summary": None,
            "algorithms": [configuration.algorithm_id],
            "environments": [configuration.environment_id],
            "behaviors": [configuration.behavior_id],
            "optimizers": [configuration.optimizer_id],
            "hpo_enabled": configuration.search is not None,
            "hpo_run_count": sum(bool(row.get("hpo_enabled")) for row in rows),
        })
        return overview

    def _study_run(self, execution_id: str, run_id: str) -> dict[str, Any]:
        workspace = self._study_workspace(execution_id)
        state = self._load_state(workspace / "study-state.json")
        manifest = self._load_manifest(workspace / "study-manifest.json")
        lifecycle = self._study_lifecycle(workspace, state)
        record = next((item for item in state.runs if item.run_id == run_id), None)
        if record is None:
            raise MonitoringError("MON-01", f"unknown run: {run_id}")
        variant = next(
            (item for item in manifest.variants if item.configuration_id == record.configuration_id),
            None,
        )
        overview = self._study_run_overview(
            workspace,
            record,
            variant,
            stale_execution=lifecycle["stale"],
        )
        configurations = [
            {
                "configuration_id": item.configuration_id,
                "configuration": item.configuration.model_dump(mode="json"),
                "axis_values": item.axis_values,
            }
            for item in manifest.variants
        ]
        comparisons, _ = self._configuration_analysis(configurations, [])
        self._attach_varied_values([overview], comparisons)
        artifact = self._study_artifact_directory(workspace, record)
        configuration = self._optional_json(
            self._safe_path(workspace, record.configuration_path)
        )
        metadata = self._optional_json(artifact / "run-metadata.json") if artifact else None
        metrics = self._optional_json(artifact / "metrics.json") if artifact else None
        hpo = self._hpo_projection(
            artifact,
            expected=bool(configuration and configuration.get("search")),
        )
        hpo["environment_success"] = overview["environment_success"]
        return {
            "run": overview,
            "configuration": configuration,
            "metadata": metadata,
            "metrics": metrics,
            "trace": self._trace(artifact),
            "log_tail": self._study_log_tail(workspace, record),
            "artifacts": self._artifacts(workspace, artifact),
            "hpo": hpo,
        }

    def _product_run(self, execution_id: str, run_id: str) -> dict[str, Any]:
        product = self._product_workspace(execution_id)
        configuration = self._load_configuration(product / "config.json")
        selected: Path | None = None
        metadata: dict[str, Any] | None = None
        for artifact in self._product_artifact_directories(product):
            candidate_metadata = self._optional_json(artifact / "run-metadata.json")
            candidate_id = (
                str(candidate_metadata.get("run_id"))
                if candidate_metadata and candidate_metadata.get("run_id")
                else artifact.name
            )
            if candidate_id == run_id:
                selected = artifact
                metadata = candidate_metadata
                break
        if selected is None:
            raise MonitoringError("MON-01", f"unknown run: {run_id}")
        overview = self._product_run_overview(product, selected, configuration, metadata)
        overview["varied_values"] = {}
        run_configuration = self._optional_json(selected / "resolved-configuration.json")
        if run_configuration is None:
            run_configuration = configuration.model_dump(mode="json")
        hpo = self._hpo_projection(
            selected,
            expected=configuration.search is not None,
        )
        hpo["environment_success"] = overview["environment_success"]
        return {
            "run": overview,
            "configuration": run_configuration,
            "metadata": metadata,
            "metrics": self._optional_json(selected / "metrics.json"),
            "trace": self._trace(selected),
            "log_tail": self._file_tail(selected / "run.log"),
            "artifacts": self._artifacts(product, selected),
            "hpo": hpo,
        }

    def _study_overview(
        self,
        workspace: Path,
        state: StudyExecutionState,
        manifest: StudyManifest,
        *,
        catalog_id: str | None = None,
        lifecycle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lifecycle = lifecycle or self._study_lifecycle(workspace, state)
        counts = Counter(item.status.value for item in state.runs)
        if lifecycle["stale"]:
            counts["interrupted"] += counts.pop("running", 0)
        total = len(state.runs)
        completed = counts.get("completed", 0)
        terminal = completed + counts.get("failed", 0) + counts.get("interrupted", 0)
        algorithms = sorted({item.configuration.algorithm_id for item in manifest.variants})
        environments = sorted({item.configuration.environment_id for item in manifest.variants})
        behaviors = sorted({item.configuration.behavior_id for item in manifest.variants})
        optimizers = sorted({item.configuration.optimizer_id for item in manifest.variants})
        return {
            "id": catalog_id or workspace.name,
            "name": manifest.study.name,
            "kind": "study",
            "kind_label": "Study",
            "execution_id": state.execution_id,
            "status": lifecycle["status"],
            "recorded_status": state.status.value,
            "runner_active": lifecycle["runner_active"],
            "stale": lifecycle["stale"],
            "lifecycle_message": lifecycle["message"],
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "workspace": str(workspace),
            "counts": dict(counts),
            "total_runs": total,
            "completed_runs": completed,
            "terminal_runs": terminal,
            "configuration_count": manifest.summary.unique_configuration_count,
            "seed_count": len(manifest.study.replications.seeds),
            "progress_percent": round((terminal / total * 100.0) if total else 0.0, 1),
            "algorithm_id": algorithms[0] if len(algorithms) == 1 else None,
            "environment_id": environments[0] if len(environments) == 1 else None,
            "behavior_id": behaviors[0] if len(behaviors) == 1 else None,
            "optimizer_id": optimizers[0] if len(optimizers) == 1 else None,
            "hpo_enabled": any(
                item.configuration.search is not None for item in manifest.variants
            ),
            "error": lifecycle["message"],
        }

    def _product_overview(
        self,
        product: Path,
        configuration: ResolvedConfiguration,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        counts = Counter(item["status"] for item in rows)
        total = len(rows)
        completed = counts.get("completed", 0)
        terminal = completed + counts.get("failed", 0) + counts.get("interrupted", 0)
        if counts.get("running", 0):
            status = "running"
        elif total and terminal == total and counts.get("failed", 0):
            status = "failed"
        elif total and completed == total:
            status = "completed"
        elif total:
            status = "interrupted"
        else:
            status = "generated"
        progress_values = [
            100.0 if row["status"] in {"completed", "failed", "interrupted"}
            else float(
                (
                    row["hpo_progress"].get("progress_percent")
                    if row.get("hpo_enabled")
                    else row["progress"].get("budget_percent")
                )
                or 0.0
            )
            for row in rows
        ]
        created_at = self._path_timestamp(product / "generation-manifest.json")
        updated_candidates = [created_at] + [
            str(row.get("ended_at") or row.get("started_at") or "") for row in rows
        ]
        return {
            "id": f"{self._PRODUCT_PREFIX}{product.name}",
            "name": configuration.name,
            "kind": "product",
            "kind_label": "Product",
            "execution_id": f"{self._PRODUCT_PREFIX}{product.name}",
            "status": status,
            "created_at": created_at,
            "updated_at": max(updated_candidates),
            "workspace": str(product),
            "counts": dict(counts),
            "total_runs": total,
            "completed_runs": completed,
            "terminal_runs": terminal,
            "configuration_count": 1,
            "seed_count": len({row["training_seed"] for row in rows}),
            "progress_percent": round(
                sum(progress_values) / len(progress_values), 1
            ) if progress_values else 0.0,
            "algorithm_id": configuration.algorithm_id,
            "environment_id": configuration.environment_id,
            "behavior_id": configuration.behavior_id,
            "optimizer_id": configuration.optimizer_id,
            "hpo_enabled": configuration.search is not None,
        }

    def _study_run_overview(
        self,
        workspace: Path,
        run: StudyRunRecord,
        variant: Any,
        *,
        stale_execution: bool = False,
    ) -> dict[str, Any]:
        configuration = variant.configuration if variant is not None else None
        artifact = self._study_artifact_directory(workspace, run)
        metrics_payload = self._optional_json(artifact / "metrics.json") if artifact else None
        metrics = metrics_payload.get("metrics", {}) if isinstance(metrics_payload, dict) else {}
        progress = self._progress_summary(artifact, configuration)
        duration = None
        if run.started_at is not None and run.ended_at is not None:
            duration = max(0.0, (run.ended_at - run.started_at).total_seconds())
        hpo = self._hpo_projection(
            artifact,
            expected=bool(configuration is not None and configuration.search is not None),
            include_trials=False,
        )
        environment_success = self._environment_success(configuration)
        hpo["environment_success"] = environment_success
        recorded_status = run.status.value
        interrupted_stale_run = (
            stale_execution and run.status is StudyRunStatus.RUNNING
        )
        effective_status = (
            StudyRunStatus.INTERRUPTED.value
            if interrupted_stale_run
            else recorded_status
        )
        lifecycle_error = (
            "The study runner stopped before it could finalize this run; "
            "the displayed episode is the last persisted observation."
            if interrupted_stale_run
            else run.error
        )
        return {
            **run.model_dump(mode="json"),
            "status": effective_status,
            "recorded_status": recorded_status,
            "error": lifecycle_error,
            "environment_id": configuration.environment_id if configuration else "unknown",
            "algorithm_id": configuration.algorithm_id if configuration else "unknown",
            "behavior_id": configuration.behavior_id if configuration else "unknown",
            "optimizer_id": configuration.optimizer_id if configuration else "unknown",
            "configuration_name": configuration.name if configuration else run.configuration_id,
            "training_budget": configuration.training_budget if configuration else None,
            "training_budget_unit": configuration.training_budget_unit if configuration else None,
            "axis_values": variant.axis_values if variant is not None else {},
            "metrics": metrics,
            "progress": progress,
            "environment_success": environment_success,
            "duration_seconds": duration,
            "execution_mode": "hpo" if hpo.get("enabled") else "single",
            "hpo_enabled": hpo.get("enabled", False),
            "hpo_progress": hpo,
        }

    def _product_run_rows(
        self,
        product: Path,
        configuration: ResolvedConfiguration,
    ) -> list[dict[str, Any]]:
        rows = []
        for artifact in self._product_artifact_directories(product):
            metadata = self._optional_json(artifact / "run-metadata.json")
            rows.append(self._product_run_overview(product, artifact, configuration, metadata))
        rows.sort(key=lambda item: str(item.get("started_at") or item["run_id"]), reverse=True)
        return rows

    def _product_run_overview(
        self,
        product: Path,
        artifact: Path,
        configuration: ResolvedConfiguration,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metrics_payload = self._optional_json(artifact / "metrics.json")
        metrics = metrics_payload.get("metrics", {}) if isinstance(metrics_payload, dict) else {}
        run_id = str(metadata.get("run_id")) if metadata and metadata.get("run_id") else artifact.name
        hpo = self._hpo_projection(
            artifact,
            expected=configuration.search is not None,
            include_trials=False,
        )
        environment_success = self._environment_success(configuration)
        hpo["environment_success"] = environment_success
        status = str(metadata.get("status", "running")) if metadata else "running"
        if metadata is None and hpo.get("status") == "failed":
            status = "failed"
        study = metadata.get("study", {}) if metadata else {}
        seed_binding = configuration.effective_parameters.get("training.seed")
        training_seed = study.get(
            "training_seed",
            seed_binding.value if seed_binding is not None else 0,
        )
        started_at = metadata.get("started_at") if metadata else self._path_timestamp(artifact)
        ended_at = metadata.get("ended_at") if metadata else None
        relative_artifact = artifact.relative_to(product).as_posix()
        return {
            "run_id": run_id,
            "configuration_id": self._configuration_id(configuration.model_dump(mode="json")),
            "training_seed": training_seed,
            "resolved_configuration_hash": configuration.configuration_hash,
            "status": status,
            "attempt": 1,
            "product_path": ".",
            "configuration_path": "config.json",
            "attempt_path": relative_artifact,
            "log_path": None,
            "artifact_path": relative_artifact,
            "started_at": started_at,
            "ended_at": ended_at,
            "return_code": 0 if status == "completed" else None,
            "error": None,
            "environment_id": configuration.environment_id,
            "algorithm_id": configuration.algorithm_id,
            "behavior_id": configuration.behavior_id,
            "optimizer_id": configuration.optimizer_id,
            "configuration_name": configuration.name,
            "training_budget": configuration.training_budget,
            "training_budget_unit": configuration.training_budget_unit,
            "axis_values": {},
            "metrics": metrics,
            "progress": self._progress_summary(artifact, configuration),
            "environment_success": environment_success,
            "duration_seconds": self._duration_seconds(started_at, ended_at),
            "execution_mode": (
                str(metadata.get("execution_mode", "hpo" if hpo.get("enabled") else "single"))
                if metadata else "hpo" if hpo.get("enabled") else "single"
            ),
            "hpo_enabled": hpo.get("enabled", False),
            "hpo_progress": hpo,
        }

    def _hpo_projection(
        self,
        artifact: Path | None,
        *,
        expected: bool,
        include_trials: bool = True,
    ) -> dict[str, Any]:
        """Normalize live HPO evidence without mutating the executing product."""

        empty = {
            "enabled": bool(expected),
            "available": False,
            "status": "pending" if expected else None,
            "phase": None,
            "progress_percent": 0.0,
            "completed_trials": 0,
            "failed_trials": 0,
            "running_trial": None,
            "trial_budget": None,
            "completed_seed_runs": 0,
            "best": None,
        }
        if artifact is None:
            return empty
        path = artifact / "hpo-summary.json"
        if not path.is_file() or path.is_symlink():
            return empty
        payload = self._optional_json(path)
        if payload is None:
            return {**empty, "status": "unreadable"}
        try:
            completed = self._hpo_count(payload.get("completed_trials"), "completed_trials")
            failed = self._hpo_count(payload.get("failed_trials"), "failed_trials")
            completed_seed_runs = self._hpo_count(
                payload.get("completed_seed_runs"), "completed_seed_runs"
            )
        except ValueError:
            return {**empty, "status": "unreadable"}
        trials = [
            item for item in payload.get("trials", []) if isinstance(item, dict)
        ] if isinstance(payload.get("trials"), list) else []
        trial_budget = payload.get("trial_budget")
        if (
            trial_budget is not None
            and (
                isinstance(trial_budget, bool)
                or not isinstance(trial_budget, int)
                or trial_budget <= 0
            )
        ):
            return {**empty, "status": "unreadable"}
        terminal = completed + failed
        if isinstance(trial_budget, int) and trial_budget > 0:
            progress_percent = min(100.0, terminal / trial_budget * 100.0)
        elif payload.get("status") in {"completed", "failed"}:
            progress_percent = 100.0
        else:
            progress_percent = 0.0
        projection = {
            "enabled": True,
            "available": True,
            "status": str(payload.get("status", "running")),
            "phase": payload.get("phase"),
            "sampler": payload.get("sampler"),
            "provider_id": payload.get("provider_id"),
            "objective": payload.get("objective"),
            "direction": payload.get("direction", "maximize"),
            "aggregation": payload.get("aggregation"),
            "trial_budget": trial_budget,
            "timeout_seconds": payload.get("timeout_seconds"),
            "search_seeds": [
                seed for seed in payload.get("search_seeds", [])
                if isinstance(seed, int) and not isinstance(seed, bool)
            ] if isinstance(payload.get("search_seeds"), list) else [],
            "sampler_seed": payload.get("sampler_seed"),
            "top_k": payload.get("top_k"),
            "search_space": payload.get("search_space", {})
            if isinstance(payload.get("search_space"), dict) else {},
            "planned_seed_runs": payload.get("planned_seed_runs"),
            "completed_seed_runs": completed_seed_runs,
            "completed_trials": completed,
            "failed_trials": failed,
            "running_trial": payload.get("running_trial"),
            "progress_percent": round(progress_percent, 1),
            "started_at": payload.get("started_at"),
            "ended_at": payload.get("ended_at"),
            "best": payload.get("best") if isinstance(payload.get("best"), dict) else None,
            "history": [
                item for item in payload.get("history", []) if isinstance(item, dict)
            ] if isinstance(payload.get("history"), list) else [],
            "top_trials": [
                item for item in payload.get("top_trials", []) if isinstance(item, dict)
            ] if isinstance(payload.get("top_trials"), list) else [],
            "final_evaluation_metrics": payload.get("final_evaluation_metrics")
            if isinstance(payload.get("final_evaluation_metrics"), dict) else None,
            "error": payload.get("error"),
        }
        if include_trials:
            projection["trials"] = trials
        return projection

    @staticmethod
    def _hpo_count(value: Any, name: str) -> int:
        if value is None:
            return 0
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
        return value

    def _configuration_analysis(
        self,
        configurations: list[dict[str, Any]],
        runs: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        grouped_runs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for run in runs:
            grouped_runs[run["configuration_id"]].append(run)
        comparisons = []
        for entry in configurations:
            configuration_id = entry["configuration_id"]
            payload = entry["configuration"]
            items = grouped_runs.get(configuration_id, [])
            numeric_metrics: dict[str, list[float]] = defaultdict(list)
            for item in items:
                if item["status"] != "completed":
                    continue
                for name, value in item["metrics"].items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        numeric_metrics[name].append(float(value))
            settings = self._configuration_settings(payload)
            hyperparameters = {
                key: value for key, value in settings.items()
                if self._setting_kind(key) == "hyperparameter"
            }
            comparisons.append({
                "configuration_id": configuration_id,
                "configuration_name": payload.get("name", configuration_id),
                "environment_id": payload.get("environment_id", "unknown"),
                "algorithm_id": payload.get("algorithm_id", "unknown"),
                "behavior_id": payload.get("behavior_id", "unknown"),
                "optimizer_id": payload.get("optimizer_id", "unknown"),
                "environment_success": self._environment_success(payload),
                "axis_values": entry.get("axis_values", {}),
                "settings": settings,
                "hyperparameters": hyperparameters,
                "completed_seeds": sum(item["status"] == "completed" for item in items),
                "total_seeds": len(items),
                "metric_means": {
                    name: sum(values) / len(values)
                    for name, values in numeric_metrics.items() if values
                },
            })

        dimensions = self._variation_dimensions(comparisons)
        for comparison in comparisons:
            comparison["varied_values"] = {
                item["target"]: comparison["settings"].get(item["target"], self._INACTIVE)
                for item in dimensions
            }
        kind_counts = Counter(item["kind"] for item in dimensions)
        variability = {
            "dimensions": dimensions,
            "dimension_count": len(dimensions),
            "explicit_dimension_count": sum(
                item["source"] == "explicit_axis" for item in dimensions
            ),
            "derived_dimension_count": sum(
                item["source"] == "resolved_default" for item in dimensions
            ),
            "structural_count": kind_counts.get("structural", 0),
            "training_count": kind_counts.get("training", 0),
            "hyperparameter_count": kind_counts.get("hyperparameter", 0),
            "evaluation_count": kind_counts.get("evaluation", 0),
            "fixed_setting_count": max(
                0,
                len({key for item in comparisons for key in item["settings"]}) - len(dimensions),
            ),
        }
        return sorted(comparisons, key=lambda item: item["configuration_id"]), variability

    def _study_completion_summary(
        self,
        state: StudyExecutionState,
        comparisons: list[dict[str, Any]],
        variability: dict[str, Any],
        *,
        lifecycle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a final, environment-aware descriptive summary.

        Reward scales belong to environments, so leaders are selected only
        within an environment. This projection is computed read-only from the
        frozen configurations and completed-run metrics.
        """

        final_statuses = {"completed", "failed", "interrupted"}
        status = lifecycle["status"] if lifecycle else state.status.value
        counts = Counter(item.status.value for item in state.runs)
        if lifecycle and lifecycle["stale"]:
            counts["interrupted"] += counts.pop("running", 0)
        base = {
            "available": status in final_statuses,
            "status": status,
            "total_runs": len(state.runs),
            "completed_runs": counts.get("completed", 0),
            "failed_runs": counts.get("failed", 0),
            "interrupted_runs": counts.get("interrupted", 0),
            "configuration_count": len(comparisons),
            "completed_configuration_count": sum(
                item["completed_seeds"] > 0 for item in comparisons
            ),
            "fully_replicated_configuration_count": sum(
                item["total_seeds"] > 0
                and item["completed_seeds"] == item["total_seeds"]
                for item in comparisons
            ),
            "variability": {
                key: variability.get(key, 0)
                for key in (
                    "dimension_count",
                    "explicit_dimension_count",
                    "derived_dimension_count",
                    "structural_count",
                    "training_count",
                    "hyperparameter_count",
                    "evaluation_count",
                )
            },
            "environment_results": [],
            "comparison_note": (
                "Reward scales are environment-specific. Highest observed mean "
                "reward is reported within each environment, never across environments."
            ),
        }
        if not base["available"]:
            return {
                **base,
                "message": "The final study summary appears after execution stops.",
            }

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in comparisons:
            grouped[item["environment_id"]].append(item)
        environment_results = []
        for environment_id, items in sorted(grouped.items()):
            reward_candidates = [
                item for item in items
                if self._finite_metric(item["metric_means"].get("average_reward"))
            ]
            success_candidates = [
                item for item in items
                if self._finite_metric(item["metric_means"].get("success_rate"))
            ]
            environment_results.append({
                "environment_id": environment_id,
                "environment_success": items[0]["environment_success"],
                "configuration_count": len(items),
                "completed_configuration_count": sum(
                    item["completed_seeds"] > 0 for item in items
                ),
                "completed_runs": sum(item["completed_seeds"] for item in items),
                "total_runs": sum(item["total_seeds"] for item in items),
                "highest_mean_reward": self._metric_leader(
                    reward_candidates, "average_reward"
                ),
                "highest_success_rate": self._metric_leader(
                    success_candidates, "success_rate"
                ),
            })
        return {
            **base,
            "environment_results": environment_results,
            "message": (
                "All planned runs completed."
                if status == "completed"
                else (
                    lifecycle["message"]
                    if lifecycle and lifecycle["message"]
                    else "Execution stopped; the summary uses completed-run evidence only."
                )
            ),
        }

    @staticmethod
    def _finite_metric(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    @classmethod
    def _metric_leader(
        cls,
        candidates: list[dict[str, Any]],
        metric: str,
    ) -> dict[str, Any] | None:
        if not candidates:
            return None
        maximum = max(float(item["metric_means"][metric]) for item in candidates)
        leaders = [
            item for item in candidates
            if math.isclose(
                float(item["metric_means"][metric]), maximum, rel_tol=1e-12, abs_tol=1e-12
            )
        ]
        return {
            "metric": metric,
            "value": maximum,
            "configuration_ids": [item["configuration_id"] for item in leaders],
            "configuration_names": [item["configuration_name"] for item in leaders],
            "completed_seeds": min(item["completed_seeds"] for item in leaders),
            "tie_count": len(leaders),
        }

    def _variation_dimensions(self, comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(comparisons) < 2:
            return []
        targets = sorted({key for item in comparisons for key in item["settings"]})
        explicit_targets = {
            self._canonical_axis_target(target)
            for item in comparisons
            for target in item.get("axis_values", {})
        }
        dimensions = []
        order = {"structural": 0, "training": 1, "hyperparameter": 2, "evaluation": 3}
        for target in targets:
            values = [item["settings"].get(target, self._INACTIVE) for item in comparisons]
            distinct: dict[str, Any] = {}
            for value in values:
                encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
                distinct.setdefault(encoded, value)
            if len(distinct) < 2:
                continue
            kind = self._setting_kind(target)
            dimensions.append({
                "target": target,
                "label": self._setting_label(target),
                "kind": kind,
                "source": "explicit_axis" if target in explicit_targets else "resolved_default",
                "values": list(distinct.values()),
                "value_count": len(distinct),
            })
        return sorted(dimensions, key=lambda item: (order[item["kind"]], item["target"]))

    @staticmethod
    def _canonical_axis_target(target: str) -> str:
        prefix = "training.parameters."
        return target[len(prefix):] if target.startswith(prefix) else target

    @classmethod
    def _configuration_settings(cls, payload: dict[str, Any]) -> dict[str, Any]:
        settings: dict[str, Any] = {
            "environment.component_id": payload.get("environment_id"),
            "algorithm.component_id": payload.get("algorithm_id"),
            "behavior.component_id": payload.get("behavior_id"),
            "optimizer.component_id": payload.get("optimizer_id"),
            "training.budget": payload.get("training_budget"),
            "training.budget_unit": payload.get("training_budget_unit"),
            "training.checkpoint_policy": payload.get("checkpoint_policy"),
            "training.checkpoint_interval": payload.get("checkpoint_interval"),
        }
        evaluation = payload.get("evaluation") or {}
        settings["evaluation.episodes_per_seed"] = evaluation.get("episodes_per_seed")
        for parameter_id, binding in (payload.get("effective_parameters") or {}).items():
            if parameter_id == "training.seed":
                continue
            if isinstance(binding, dict) and binding.get("mode") == "fixed":
                settings[parameter_id] = binding.get("value")
            elif isinstance(binding, dict):
                settings[parameter_id] = {
                    "mode": binding.get("mode"),
                    "domain": binding.get("domain"),
                }
            else:
                settings[parameter_id] = binding
        return settings

    @staticmethod
    def _setting_kind(target: str) -> str:
        if target in {
            "environment.component_id",
            "algorithm.component_id",
            "behavior.component_id",
            "optimizer.component_id",
        }:
            return "structural"
        if target.startswith("evaluation."):
            return "evaluation"
        if target in {
            "training.budget",
            "training.budget_unit",
            "training.checkpoint_policy",
            "training.checkpoint_interval",
        }:
            return "training"
        return "hyperparameter"

    @staticmethod
    def _setting_label(target: str) -> str:
        special = {
            "environment.component_id": "Environment",
            "algorithm.component_id": "Algorithm",
            "behavior.component_id": "Action behavior",
            "optimizer.component_id": "Optimizer / update rule",
            "training.budget": "Training budget",
            "training.budget_unit": "Budget unit",
            "training.checkpoint_policy": "Checkpoint policy",
            "training.checkpoint_interval": "Checkpoint interval",
            "evaluation.episodes_per_seed": "Evaluation episodes",
        }
        if target in special:
            return special[target]
        return target.replace("_", " ").replace(".", " · ")

    @staticmethod
    def _attach_varied_values(
        runs: list[dict[str, Any]],
        comparisons: list[dict[str, Any]],
    ) -> None:
        values = {
            item["configuration_id"]: item.get("varied_values", {})
            for item in comparisons
        }
        for run in runs:
            run["varied_values"] = values.get(run["configuration_id"], {})

    def _progress_summary(self, artifact: Path | None, configuration: Any) -> dict[str, Any]:
        points = self._trace(artifact)
        latest = points[-1] if points else None
        if isinstance(configuration, dict):
            budget = configuration.get("training_budget")
            unit = configuration.get("training_budget_unit")
            capability_evidence = configuration.get("capability_evidence", {})
        else:
            budget = configuration.training_budget if configuration is not None else None
            unit = configuration.training_budget_unit if configuration is not None else None
            capability_evidence = (
                configuration.capability_evidence
                if configuration is not None else {}
            )
        environment_success = self._environment_success(configuration)
        has_success_signal = environment_success["available"] is True
        completed_units = None
        if latest is not None:
            completed_units = latest["episode"] if unit == "episodes" else latest["total_steps"]
        percent = None
        if budget and completed_units is not None:
            percent = round(min(100.0, completed_units / budget * 100.0), 1)
        return {
            "episode": latest["episode"] if latest else 0,
            "total_steps": latest["total_steps"] if latest else 0,
            "latest_reward": latest["reward"] if latest else None,
            "rolling_reward": self._rolling_mean(points, 25),
            "success_rate": (
                sum(1 for item in points if item["success"]) / len(points)
                if points and has_success_signal else None
            ),
            "environment_success": environment_success,
            "budget_percent": percent,
            "point_count": len(points),
        }

    @staticmethod
    def _environment_success(configuration: Any) -> dict[str, Any]:
        if isinstance(configuration, dict):
            evidence = configuration.get("capability_evidence", {})
        else:
            evidence = (
                configuration.capability_evidence
                if configuration is not None else {}
            )
        evidence = evidence if isinstance(evidence, dict) else {}
        declared = evidence.get("environment_success_signal")
        definition = evidence.get("environment_success_definition")
        if declared is True:
            return {
                "available": True,
                "kind": "environment_episode_signal",
                "label": "Environment success signal",
                "definition": (
                    definition.strip()
                    if isinstance(definition, str) and definition.strip()
                    else (
                        "The environment adapter reports an episode-level success event; "
                        "this component did not supply a more specific predicate description."
                    )
                ),
            }
        if declared is False:
            return {
                "available": False,
                "kind": "return_only",
                "label": "No native binary success signal",
                "definition": (
                    "This environment has no native binary success event. Interpret reward "
                    "and return directly; success rate is not applicable."
                ),
            }
        return {
            "available": None,
            "kind": "undeclared",
            "label": "Success signal not declared",
            "definition": (
                "This environment component did not declare whether it exposes a binary "
                "success event."
            ),
        }

    def _trace(self, artifact: Path | None) -> list[dict[str, Any]]:
        if artifact is None:
            return []
        completed = artifact / "training-reward-trace.csv"
        if completed.is_file() and not completed.is_symlink():
            try:
                self._assert_file_size(completed, self._MAX_TRACE_BYTES)
                with completed.open("r", encoding="utf-8", newline="") as stream:
                    rows = []
                    total_steps = 0
                    for item in csv.DictReader(stream):
                        normalized = self._normalize_trace_row(item)
                        total_steps += normalized["steps"]
                        normalized["total_steps"] = total_steps
                        rows.append(normalized)
                return self._downsample(rows)
            except (OSError, ValueError, csv.Error):
                return []
        live = artifact / "training-progress.jsonl"
        if live.is_file() and not live.is_symlink():
            rows: list[dict[str, Any]] = []
            try:
                self._assert_file_size(live, self._MAX_TRACE_BYTES)
                with live.open("r", encoding="utf-8") as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(payload, dict):
                            rows.append(self._normalize_trace_row(payload))
            except (OSError, ValueError):
                return []
            return self._downsample(rows)
        return []

    @staticmethod
    def _normalize_trace_row(row: dict[str, Any]) -> dict[str, Any]:
        reward = float(row.get("reward", 0.0))
        if not math.isfinite(reward):
            raise ValueError("trace reward must be finite")
        return {
            "episode": int(row.get("episode", 0)),
            "reward": reward,
            "steps": int(row.get("steps", 0)),
            "total_steps": int(row.get("total_steps", row.get("steps", 0))),
            "success": str(row.get("success", "false")).lower() in {"1", "true", "yes"},
            "elapsed_seconds": (
                float(row["elapsed_seconds"]) if row.get("elapsed_seconds") is not None else None
            ),
        }

    def _downsample(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(rows) <= self._MAX_TRACE_POINTS:
            return rows
        stride = math.ceil(len(rows) / self._MAX_TRACE_POINTS)
        selected = rows[::stride]
        if selected[-1] is not rows[-1]:
            selected.append(rows[-1])
        return selected

    @staticmethod
    def _rolling_mean(rows: list[dict[str, Any]], window: int) -> float | None:
        if not rows:
            return None
        values = [item["reward"] for item in rows[-window:]]
        return sum(values) / len(values)

    def _study_workspace(self, execution_id: str) -> Path:
        root = self.executions_root
        stored_id = execution_id
        if execution_id.startswith(self._ADJACENT_STUDY_PREFIX):
            root = self.workspace_root / "studies"
            stored_id = execution_id[len(self._ADJACENT_STUDY_PREFIX):]
        self._validate_identifier(stored_id, "execution")
        workspace = self._safe_path(root, stored_id)
        if not workspace.is_dir() or not (workspace / "study-state.json").is_file():
            raise MonitoringError("MON-01", f"unknown execution: {execution_id}")
        return workspace

    def _study_lifecycle(
        self,
        workspace: Path,
        state: StudyExecutionState,
    ) -> dict[str, Any]:
        """Project runner liveness without rewriting immutable execution evidence."""

        recorded_status = state.status.value
        if recorded_status not in {"preparing", "running"}:
            return {
                "status": recorded_status,
                "runner_active": False,
                "stale": False,
                "message": None,
            }
        runner_active = self._study_lock_is_held(workspace)
        if runner_active is False:
            return {
                "status": "interrupted",
                "runner_active": False,
                "stale": True,
                "message": (
                    "The saved state still said running, but no study runner owns "
                    "this workspace. It is shown as interrupted; saved progress "
                    "and artifacts were not changed."
                ),
            }
        return {
            "status": recorded_status,
            "runner_active": runner_active,
            "stale": False,
            "message": None,
        }

    @staticmethod
    def _study_lock_is_held(workspace: Path) -> bool | None:
        """Return whether the orchestrator lock is owned; never create or edit it."""

        lock_path = workspace.parent / f".{workspace.name}.rlspl.lock"
        if not lock_path.is_file() or lock_path.is_symlink():
            return False
        try:
            stream = lock_path.open("r+", encoding="utf-8")
        except OSError:
            return None
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
            return False
        except BlockingIOError:
            return True
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                return True
            return None
        finally:
            if acquired:
                try:
                    if os.name == "nt":
                        import msvcrt

                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            stream.close()

    def _product_workspace(self, execution_id: str) -> Path:
        if not execution_id.startswith(self._PRODUCT_PREFIX):
            raise MonitoringError("MON-01", f"unknown product: {execution_id}")
        product_id = execution_id[len(self._PRODUCT_PREFIX):]
        self._validate_identifier(product_id, "product")
        product = self._safe_path(self.workspace_root, product_id)
        if (
            not product.is_dir()
            or not (product / "config.json").is_file()
            or not (product / "generation-manifest.json").is_file()
        ):
            raise MonitoringError("MON-01", f"unknown product: {product_id}")
        return product

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise MonitoringError("MON-01", f"invalid {label} identifier")

    def _load_state(self, path: Path) -> StudyExecutionState:
        try:
            return StudyExecutionState.model_validate(self._read_json(path))
        except ValidationError as exc:
            raise MonitoringError("MON-03", f"invalid study state: {exc}") from exc

    def _load_manifest(self, path: Path) -> StudyManifest:
        try:
            return StudyManifest.model_validate(self._read_json(path))
        except ValidationError as exc:
            raise MonitoringError("MON-03", f"invalid study manifest: {exc}") from exc

    def _load_configuration(self, path: Path) -> ResolvedConfiguration:
        try:
            return ResolvedConfiguration.model_validate(self._read_json(path))
        except ValidationError as exc:
            raise MonitoringError("MON-03", f"invalid product configuration: {exc}") from exc

    def _read_json(self, path: Path) -> Any:
        try:
            if path.is_symlink():
                raise MonitoringError("MON-01", f"symbolic metadata links are not accepted: {path.name}")
            self._assert_file_size(path, self._MAX_JSON_BYTES)
            return json.loads(path.read_text(encoding="utf-8"))
        except MonitoringError:
            raise
        except (OSError, json.JSONDecodeError) as exc:
            raise MonitoringError("MON-02", f"metadata cannot be read: {path.name}: {exc}") from exc

    def _optional_json(self, path: Path | None) -> dict[str, Any] | None:
        if path is None or not path.is_file():
            return None
        try:
            payload = self._read_json(path)
        except MonitoringError:
            return None
        return payload if isinstance(payload, dict) else None

    def _study_artifact_directory(self, workspace: Path, run: StudyRunRecord) -> Path | None:
        if run.artifact_path:
            artifact = self._safe_path(workspace, run.artifact_path)
            return artifact if artifact.is_dir() else None
        if not run.attempt_path:
            return None
        attempt = self._safe_path(workspace, run.attempt_path)
        root = attempt / "artifacts"
        if not root.is_dir():
            return None
        try:
            candidates = [item for item in root.iterdir() if item.is_dir() and not item.is_symlink()]
        except OSError:
            return None
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _product_artifact_directories(product: Path) -> list[Path]:
        root = product / "runs"
        if not root.is_dir() or root.is_symlink():
            return []
        try:
            return sorted(
                (item for item in root.iterdir() if item.is_dir() and not item.is_symlink()),
                key=lambda item: item.name,
            )
        except OSError:
            return []

    def _study_log_tail(self, workspace: Path, run: StudyRunRecord) -> str:
        if not run.log_path:
            return ""
        return self._file_tail(self._safe_path(workspace, run.log_path))

    def _file_tail(self, path: Path) -> str:
        try:
            if path.is_symlink():
                return ""
            with path.open("rb") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                stream.seek(max(0, size - self._MAX_LOG_TAIL_BYTES))
                return stream.read().decode("utf-8", errors="replace")
        except OSError:
            return ""

    def _artifacts(self, workspace: Path, artifact: Path | None) -> list[dict[str, Any]]:
        if artifact is None or not artifact.is_dir():
            return []
        items = []
        try:
            candidates = sorted(artifact.iterdir(), key=lambda item: item.name)
        except OSError:
            return []
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            resolved = self._safe_path(workspace, path.relative_to(workspace).as_posix())
            try:
                size = resolved.stat().st_size
            except OSError:
                continue
            items.append({
                "name": path.name,
                "path": path.relative_to(workspace).as_posix(),
                "size_bytes": size,
            })
        return items

    @staticmethod
    def _duration_seconds(started_at: Any, ended_at: Any) -> float | None:
        if not started_at or not ended_at:
            return None
        try:
            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(ended_at).replace("Z", "+00:00"))
        except ValueError:
            return None
        return max(0.0, (end - start).total_seconds())

    @staticmethod
    def _path_timestamp(path: Path) -> str:
        try:
            timestamp = path.stat().st_mtime
        except OSError:
            timestamp = 0.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    @staticmethod
    def _configuration_id(payload: dict[str, Any]) -> str:
        value = str(payload.get("configuration_hash") or "unknown")
        return f"cfg-{value[:12]}"

    @staticmethod
    def _assert_file_size(path: Path, maximum: int) -> None:
        size = path.stat().st_size
        if size > maximum:
            raise MonitoringError("MON-04", f"monitoring file is too large: {path.name}")

    @staticmethod
    def _safe_path(root: Path, stored_path: str) -> Path:
        relative = Path(stored_path)
        if relative.is_absolute():
            raise MonitoringError("MON-01", "absolute monitoring paths are not accepted")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise MonitoringError("MON-01", "monitoring path escapes the execution root") from exc
        return candidate
