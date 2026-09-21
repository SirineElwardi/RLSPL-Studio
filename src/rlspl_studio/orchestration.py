"""Resumable local execution of frozen RLSPL exploration manifests."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shlex
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .exploration import StudyPlanner, StudyPlanningError
from .generation import ProductGenerationError, ProductGenerator
from .models import (
    BindingMode,
    ParameterBinding,
    ResolvedConfiguration,
    StudyExecutionState,
    StudyExecutionStatus,
    StudyManifest,
    StudyRunRecord,
    StudyRunStatus,
    StudyVariant,
    UserConfiguration,
)
from .planning import ProductPlan, ProductPlanner, ProductPlanningError
from .registry import ComponentRegistry
from .resolver import ConfigurationResolver


ProgressReporter = Callable[[StudyRunRecord, int, int], None]


class StudyOrchestrationError(RuntimeError):
    """A study cannot be prepared or executed safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class StudyOrchestrator:
    """Generate each product once, then execute every configuration/seed run."""

    def __init__(
        self,
        registry: ComponentRegistry,
        reporter: ProgressReporter | None = None,
    ) -> None:
        self.registry = registry
        self.resolver = ConfigurationResolver(registry)
        self.product_planner = ProductPlanner(registry)
        self.product_generator = ProductGenerator()
        self.reporter = reporter
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._active_processes: dict[str, subprocess.Popen[str]] = {}
        self._state: StudyExecutionState | None = None
        self._state_path: Path | None = None

    def execute(
        self,
        manifest: StudyManifest,
        workspace: Path,
        *,
        jobs: int = 1,
        resume: bool = False,
        install_dependencies: bool = True,
    ) -> StudyExecutionState:
        """Execute a complete manifest and atomically persist progress."""

        self._stop.clear()
        self._validate_manifest(manifest)
        if jobs < 1:
            raise StudyOrchestrationError("EXE-01", "jobs must be at least one")
        workspace = workspace.expanduser().resolve()
        try:
            workspace.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StudyOrchestrationError(
                "EXE-08", f"study workspace parent cannot be created: {exc}"
            ) from exc
        lock = self._acquire_workspace_lock(workspace)
        try:
            return self._execute_locked(
                manifest,
                workspace,
                jobs=jobs,
                resume=resume,
                install_dependencies=install_dependencies,
            )
        finally:
            self._release_workspace_lock(lock)

    def _execute_locked(
        self,
        manifest: StudyManifest,
        workspace: Path,
        *,
        jobs: int,
        resume: bool,
        install_dependencies: bool,
    ) -> StudyExecutionState:
        self._state_path = workspace / "study-state.json"
        if self._state_path.exists():
            if not resume:
                raise StudyOrchestrationError(
                    "EXE-03",
                    f"study workspace already exists; use --resume: {workspace}",
                )
            self._state = self._load_state(self._state_path)
            if (
                self._state.study_hash != manifest.study_hash
                or self._state.manifest_hash != manifest.manifest_hash
            ):
                raise StudyOrchestrationError(
                    "EXE-03", "existing workspace belongs to a different study manifest"
                )
            self._synchronize_resumed_runs(manifest, workspace)
        else:
            try:
                if workspace.exists() and any(workspace.iterdir()):
                    raise StudyOrchestrationError(
                        "EXE-03", f"study workspace is not empty: {workspace}"
                    )
                workspace.mkdir(parents=True, exist_ok=True)
                self._state = self._prepare_new_state(manifest, workspace, jobs)
                self._persist_state()
            except OSError as exc:
                raise StudyOrchestrationError(
                    "EXE-04", f"study workspace could not be prepared: {exc}"
                ) from exc

        assert self._state is not None
        try:
            self._write_json_atomic(
                workspace / "study-manifest.json",
                manifest.model_dump(mode="json"),
            )
            self._write_seeded_configurations(manifest, workspace)
            plans = self._ensure_products(manifest, workspace)
            dependencies = tuple(
                sorted({dependency for plan in plans for dependency in plan.dependencies})
            )
            python_executable = self._prepare_python(
                workspace, dependencies, install_dependencies
            )
            snapshot_path = self._capture_environment_snapshot(
                Path(python_executable), workspace
            )
            self._replace_state(
                workspace=str(workspace),
                jobs=jobs,
                dependencies=dependencies,
                python_executable=str(python_executable),
                environment_snapshot_path=snapshot_path,
                status=StudyExecutionStatus.RUNNING,
                error=None,
            )
            self._run_pending(Path(python_executable), jobs)
        except KeyboardInterrupt:
            self._interrupt_active_processes()
            self._mark_unfinished_interrupted()
            self._replace_state(
                status=StudyExecutionStatus.INTERRUPTED,
                error="study execution was interrupted",
            )
            return self._state
        except StudyOrchestrationError as exc:
            self._record_execution_failure(str(exc))
            raise
        except (OSError, ValueError, ProductPlanningError, ProductGenerationError) as exc:
            self._record_execution_failure(str(exc))
            code = getattr(exc, "code", "EXE-04")
            raise StudyOrchestrationError(code, str(exc)) from exc

        statuses = {run.status for run in self._state.runs}
        if statuses == {StudyRunStatus.COMPLETED}:
            self._replace_state(status=StudyExecutionStatus.COMPLETED, error=None)
        elif StudyRunStatus.INTERRUPTED in statuses:
            self._replace_state(
                status=StudyExecutionStatus.INTERRUPTED,
                error="one or more runs were interrupted",
            )
        else:
            failed_count = sum(
                run.status is StudyRunStatus.FAILED for run in self._state.runs
            )
            self._replace_state(
                status=StudyExecutionStatus.FAILED,
                error=f"{failed_count} run(s) failed",
            )
        return self._state

    @staticmethod
    def _acquire_workspace_lock(workspace: Path):
        lock_path = workspace.parent / f".{workspace.name}.rlspl.lock"
        try:
            stream = lock_path.open("a+", encoding="utf-8")
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                if not stream.read(1):
                    stream.write("0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            try:
                stream.close()
            except (NameError, OSError):
                pass
            raise StudyOrchestrationError(
                "EXE-08", f"study workspace is already in use: {workspace}"
            ) from exc
        return stream

    @staticmethod
    def _release_workspace_lock(stream) -> None:
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    def _validate_manifest(self, manifest: StudyManifest) -> None:
        if not manifest.summary.expansion_complete:
            raise StudyOrchestrationError(
                "EXE-02",
                "cannot execute a truncated study manifest; regenerate it with a sufficient limit",
            )
        if not manifest.variants:
            raise StudyOrchestrationError(
                "EXE-02", "study manifest contains no valid configurations"
            )
        expected_runs = len(manifest.variants) * len(manifest.study.replications.seeds)
        if manifest.summary.planned_run_count != expected_runs:
            raise StudyOrchestrationError(
                "EXE-02", "study manifest has an inconsistent planned run count"
            )
        try:
            rebuilt = StudyPlanner(self.registry).plan(
                manifest.study,
                limit=max(1, manifest.summary.candidate_count),
            )
        except (StudyPlanningError, ValueError) as exc:
            raise StudyOrchestrationError(
                "EXE-02", f"study manifest cannot be revalidated: {exc}"
            ) from exc
        if (
            rebuilt.study_hash != manifest.study_hash
            or rebuilt.manifest_hash != manifest.manifest_hash
            or rebuilt.model_dump(exclude={"created_at"})
            != manifest.model_dump(exclude={"created_at"})
        ):
            raise StudyOrchestrationError(
                "EXE-02",
                "study manifest content does not match its recorded hashes or installed components",
            )

    def _prepare_new_state(
        self, manifest: StudyManifest, workspace: Path, jobs: int
    ) -> StudyExecutionState:
        records: list[StudyRunRecord] = []
        for variant in manifest.variants:
            self._assert_component_versions(variant)
            product_path = Path("products") / variant.configuration_id
            for seed in manifest.study.replications.seeds:
                resolved = self._resolve_seeded_configuration(variant, seed)
                run_id = self._run_id(
                    manifest.manifest_hash, variant.configuration_id, seed
                )
                configuration_path = Path("configurations") / f"{run_id}.json"
                records.append(StudyRunRecord(
                    run_id=run_id,
                    configuration_id=variant.configuration_id,
                    training_seed=seed,
                    resolved_configuration_hash=resolved.configuration_hash,
                    product_path=product_path.as_posix(),
                    configuration_path=configuration_path.as_posix(),
                ))
        now = datetime.now(timezone.utc)
        return StudyExecutionState(
            execution_id=f"execution-{manifest.manifest_hash[:12]}",
            study_hash=manifest.study_hash,
            manifest_hash=manifest.manifest_hash,
            status=StudyExecutionStatus.PREPARING,
            workspace=str(workspace),
            jobs=jobs,
            dependencies=(),
            python_executable=sys.executable,
            created_at=now,
            updated_at=now,
            runs=tuple(records),
        )

    def _synchronize_resumed_runs(
        self, manifest: StudyManifest, workspace: Path
    ) -> None:
        assert self._state is not None
        actual = {run.run_id: run for run in self._state.runs}
        if len(actual) != len(self._state.runs):
            raise StudyOrchestrationError("EXE-03", "study state contains duplicate run IDs")

        expected: list[tuple[StudyVariant, int, ResolvedConfiguration, str]] = []
        for variant in manifest.variants:
            self._assert_component_versions(variant)
            for seed in manifest.study.replications.seeds:
                resolved = self._resolve_seeded_configuration(variant, seed)
                run_id = self._run_id(
                    manifest.manifest_hash, variant.configuration_id, seed
                )
                expected.append((variant, seed, resolved, run_id))
        expected_ids = {item[3] for item in expected}
        if set(actual) != expected_ids:
            raise StudyOrchestrationError(
                "EXE-03", "study state run set does not match the frozen manifest"
            )

        normalized: list[StudyRunRecord] = []
        for variant, seed, resolved, run_id in expected:
            run = actual[run_id]
            if (
                run.configuration_id != variant.configuration_id
                or run.training_seed != seed
                or run.resolved_configuration_hash != resolved.configuration_hash
            ):
                raise StudyOrchestrationError(
                    "EXE-03", f"study state run metadata is inconsistent: {run_id}"
                )
            for stored_path in (
                run.attempt_path,
                run.log_path,
                run.artifact_path,
            ):
                if stored_path is not None:
                    self._safe_workspace_path(workspace, stored_path)

            configuration_path = Path("configurations") / f"{run_id}.json"
            run = run.model_copy(update={
                "product_path": (Path("products") / variant.configuration_id).as_posix(),
                "configuration_path": configuration_path.as_posix(),
            })
            if run.status is StudyRunStatus.COMPLETED:
                if not self._completed_run_exists(run, workspace):
                    run = run.model_copy(update={
                        "status": StudyRunStatus.FAILED,
                        "error": "recorded artifacts are missing or incomplete",
                    })
            elif run.status is StudyRunStatus.RUNNING:
                run = run.model_copy(update={
                    "status": StudyRunStatus.INTERRUPTED,
                    "ended_at": datetime.now(timezone.utc),
                    "error": "previous execution stopped before completion",
                })
            normalized.append(run)
        self._replace_state(
            workspace=str(workspace),
            runs=tuple(normalized),
            error=None,
        )

    def _write_seeded_configurations(
        self, manifest: StudyManifest, workspace: Path
    ) -> None:
        configurations = workspace / "configurations"
        configurations.mkdir(exist_ok=True)
        for variant in manifest.variants:
            for seed in manifest.study.replications.seeds:
                resolved = self._resolve_seeded_configuration(variant, seed)
                run_id = self._run_id(
                    manifest.manifest_hash, variant.configuration_id, seed
                )
                self._write_json_atomic(
                    configurations / f"{run_id}.json",
                    resolved.model_dump(mode="json"),
                )

    def _ensure_products(
        self, manifest: StudyManifest, workspace: Path
    ) -> tuple[ProductPlan, ...]:
        products = workspace / "products"
        products.mkdir(exist_ok=True)
        plans: list[ProductPlan] = []
        for variant in manifest.variants:
            self._assert_component_versions(variant)
            plan = self.product_planner.plan(variant.configuration)
            plans.append(plan)
            destination = workspace / "products" / variant.configuration_id
            if destination.exists():
                generation_manifest = destination / "generation-manifest.json"
                try:
                    payload = json.loads(generation_manifest.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise StudyOrchestrationError(
                        "EXE-05", f"generated product cannot be verified: {destination}"
                    ) from exc
                if payload.get("configuration_hash") != variant.configuration.configuration_hash:
                    raise StudyOrchestrationError(
                        "EXE-05", f"generated product does not match manifest: {destination}"
                    )
                missing = [
                    item.path for item in plan.files
                    if not (destination / item.path).is_file()
                ]
                if missing:
                    raise StudyOrchestrationError(
                        "EXE-05",
                        f"generated product is incomplete ({', '.join(missing)}): {destination}",
                    )
                continue
            temporary = destination.with_name(
                f".{destination.name}.{uuid.uuid4().hex}.tmp"
            )
            self.product_generator.generate(plan, variant.configuration, temporary)
            try:
                temporary.replace(destination)
            except OSError as exc:
                raise StudyOrchestrationError(
                    "EXE-05", f"generated product could not be committed: {destination}"
                ) from exc
        return tuple(plans)

    def _prepare_python(
        self,
        workspace: Path,
        dependencies: tuple[str, ...],
        install_dependencies: bool,
    ) -> Path:
        if not install_dependencies:
            return Path(sys.executable).resolve()

        environment = workspace / ".venv"
        python = environment / "bin" / "python"
        if os.name == "nt":
            python = environment / "Scripts" / "python.exe"
        if not python.exists():
            completed = subprocess.run(
                [sys.executable, "-m", "venv", str(environment)],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise StudyOrchestrationError(
                    "EXE-06",
                    f"study environment creation failed: {completed.stderr.strip()}",
                )

        marker = workspace / "installed-dependencies.json"
        expected = {"dependencies": list(dependencies)}
        if marker.exists():
            try:
                if json.loads(marker.read_text(encoding="utf-8")) == expected:
                    return python.resolve()
            except (OSError, json.JSONDecodeError):
                pass

        if dependencies:
            log_path = workspace / "dependency-install.log"
            command = [str(python), "-m", "pip", "install", *dependencies]
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"$ {shlex.join(command)}\n")
                log.flush()
                completed = subprocess.run(
                    command,
                    cwd=workspace,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            if completed.returncode != 0:
                raise StudyOrchestrationError(
                    "EXE-06", f"dependency installation failed; inspect {log_path}"
                )
        self._write_json_atomic(marker, expected)
        return python.resolve()

    def _capture_environment_snapshot(self, python: Path, workspace: Path) -> str:
        script = """
import importlib.metadata as metadata
import json
import platform
import sys

packages = []
for distribution in metadata.distributions():
    name = distribution.metadata.get("Name")
    if name:
        packages.append({"name": name, "version": distribution.version})
payload = {
    "python_executable": sys.executable,
    "python_version": platform.python_version(),
    "platform": platform.platform(),
    "packages": sorted(packages, key=lambda item: item["name"].lower()),
}
print(json.dumps(payload, sort_keys=True))
"""
        completed = subprocess.run(
            [str(python), "-c", script],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise StudyOrchestrationError(
                "EXE-06",
                f"execution environment could not be recorded: {completed.stderr.strip()}",
            )
        try:
            payload: Any = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise StudyOrchestrationError(
                "EXE-06", "execution environment returned an invalid package snapshot"
            ) from exc
        relative_path = "environment-snapshot.json"
        self._write_json_atomic(workspace / relative_path, payload)
        return relative_path

    def _run_pending(self, python: Path, jobs: int) -> None:
        assert self._state is not None
        pending = [
            run for run in self._state.runs
            if run.status is not StudyRunStatus.COMPLETED
        ]
        if not pending:
            return
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=jobs)
        futures = [
            executor.submit(self._execute_run, run.run_id, python) for run in pending
        ]
        try:
            for future in concurrent.futures.as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            self._stop.set()
            for future in futures:
                future.cancel()
            self._interrupt_active_processes()
            raise
        finally:
            executor.shutdown(wait=True, cancel_futures=self._stop.is_set())

    def _execute_run(self, run_id: str, python: Path) -> None:
        if self._stop.is_set():
            return
        run = self._run(run_id)
        assert self._state is not None
        workspace = Path(self._state.workspace)
        attempt = run.attempt + 1
        while (workspace / "runs" / run_id / f"attempt-{attempt:03d}").exists():
            attempt += 1
        attempt_path = Path("runs") / run_id / f"attempt-{attempt:03d}"
        artifact_root = attempt_path / "artifacts"
        log_path = attempt_path / "process.log"
        running = run.model_copy(update={
            "status": StudyRunStatus.RUNNING,
            "attempt": attempt,
            "attempt_path": attempt_path.as_posix(),
            "log_path": log_path.as_posix(),
            "artifact_path": None,
            "started_at": datetime.now(timezone.utc),
            "ended_at": None,
            "return_code": None,
            "error": None,
        })
        self._update_run(running)
        self._report(running)

        absolute_attempt = workspace / attempt_path
        absolute_artifacts = workspace / artifact_root
        absolute_log = workspace / log_path
        command = [
            str(python),
            "run.py",
            "--config",
            str(workspace / running.configuration_path),
            "--output",
            str(absolute_artifacts),
        ]
        environment = os.environ.copy()
        environment.update({
            "PYTHONUNBUFFERED": "1",
            "RLSPL_STUDY_EXECUTION_ID": self._state.execution_id,
            "RLSPL_STUDY_HASH": self._state.study_hash,
            "RLSPL_STUDY_MANIFEST_HASH": self._state.manifest_hash,
            "RLSPL_CONFIGURATION_ID": running.configuration_id,
            "RLSPL_STUDY_RUN_ID": running.run_id,
            "RLSPL_STUDY_ATTEMPT": str(attempt),
            "RLSPL_TRAINING_SEED": str(running.training_seed),
        })
        return_code: int | None = None
        try:
            absolute_attempt.mkdir(parents=True, exist_ok=False)
            with absolute_log.open("x", encoding="utf-8") as log:
                log.write(f"$ {shlex.join(command)}\n")
                log.flush()
                with self._lock:
                    if self._stop.is_set():
                        raise InterruptedError("study execution was interrupted")
                    process = subprocess.Popen(
                        command,
                        cwd=workspace / running.product_path,
                        env=environment,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    self._active_processes[run_id] = process
                return_code = process.wait()
        except (OSError, InterruptedError) as exc:
            status = (
                StudyRunStatus.INTERRUPTED
                if self._stop.is_set() else StudyRunStatus.FAILED
            )
            self._finish_run(running, status, return_code, str(exc), None)
            return
        finally:
            with self._lock:
                self._active_processes.pop(run_id, None)

        artifacts = tuple(
            path for path in absolute_artifacts.glob("*") if path.is_dir()
        )
        artifact_path = (
            artifacts[0].relative_to(workspace).as_posix()
            if len(artifacts) == 1 else None
        )
        if self._stop.is_set():
            status = StudyRunStatus.INTERRUPTED
            error = "study execution was interrupted"
        elif return_code == 0 and artifact_path is not None:
            status = StudyRunStatus.COMPLETED
            error = None
        elif return_code == 0:
            status = StudyRunStatus.FAILED
            error = "product completed without exactly one artifact directory"
        else:
            status = StudyRunStatus.FAILED
            error = f"product process exited with code {return_code}"
        self._finish_run(running, status, return_code, error, artifact_path)

    def _finish_run(
        self,
        run: StudyRunRecord,
        status: StudyRunStatus,
        return_code: int | None,
        error: str | None,
        artifact_path: str | None,
    ) -> None:
        finished = run.model_copy(update={
            "status": status,
            "return_code": return_code,
            "error": error,
            "artifact_path": artifact_path,
            "ended_at": datetime.now(timezone.utc),
        })
        self._update_run(finished)
        self._report(finished)

    def _resolve_seeded_configuration(
        self, variant: StudyVariant, seed: int
    ) -> ResolvedConfiguration:
        resolved = variant.configuration
        parameters = dict(resolved.effective_parameters)
        parameters["training.seed"] = ParameterBinding(
            mode=BindingMode.FIXED, value=seed
        )
        configuration = UserConfiguration.model_validate({
            "name": resolved.name,
            "environment": {
                "source": "catalog",
                "component_id": resolved.environment_id,
                "parameters": {},
            },
            "algorithm": {"component_id": resolved.algorithm_id},
            "behavior": {"component_id": resolved.behavior_id},
            "optimizer": {"component_id": resolved.optimizer_id},
            "training": {
                "budget_unit": resolved.training_budget_unit,
                "budget": resolved.training_budget,
                "parameters": {
                    key: binding.model_dump(mode="json")
                    for key, binding in parameters.items()
                },
                "checkpoint_policy": resolved.checkpoint_policy,
                "checkpoint_interval": resolved.checkpoint_interval,
            },
            "search": None,
            "evaluation": resolved.evaluation.model_dump(mode="json"),
        })
        result = self.resolver.resolve(configuration)
        if not result.report.is_valid or result.resolved is None:
            issues = "; ".join(
                f"{issue.code}: {issue.message}" for issue in result.report.errors
            )
            raise StudyOrchestrationError(
                "EXE-07", f"seeded configuration is no longer valid: {issues}"
            )
        if (
            result.resolved.environment_version != resolved.environment_version
            or result.resolved.algorithm_version != resolved.algorithm_version
            or result.resolved.behavior_version != resolved.behavior_version
            or result.resolved.optimizer_version != resolved.optimizer_version
        ):
            raise StudyOrchestrationError(
                "EXE-07", "installed component versions differ from the frozen manifest"
            )
        return result.resolved

    def _assert_component_versions(self, variant: StudyVariant) -> None:
        environment = self.registry.environment(variant.configuration.environment_id)
        algorithm = self.registry.algorithm(variant.configuration.algorithm_id)
        behavior = self.registry.behavior(variant.configuration.behavior_id)
        optimizer = self.registry.optimizer(variant.configuration.optimizer_id)
        if (
            environment is None
            or algorithm is None
            or behavior is None
            or optimizer is None
        ):
            raise StudyOrchestrationError(
                "EXE-07",
                f"manifest components are not installed: {variant.configuration_id}",
            )
        if (
            environment.version != variant.configuration.environment_version
            or algorithm.version != variant.configuration.algorithm_version
            or behavior.version != variant.configuration.behavior_version
            or optimizer.version != variant.configuration.optimizer_version
        ):
            raise StudyOrchestrationError(
                "EXE-07",
                f"component version drift detected: {variant.configuration_id}",
            )

    def _completed_run_exists(self, run: StudyRunRecord, workspace: Path) -> bool:
        if run.artifact_path is None:
            return False
        artifact = self._safe_workspace_path(workspace, run.artifact_path)
        return artifact.is_dir() and (artifact / "run-metadata.json").is_file()

    @staticmethod
    def _safe_workspace_path(workspace: Path, stored_path: str) -> Path:
        relative = Path(stored_path)
        if relative.is_absolute():
            raise StudyOrchestrationError(
                "EXE-03", f"study state contains an absolute artifact path: {stored_path}"
            )
        candidate = (workspace / relative).resolve()
        try:
            candidate.relative_to(workspace.resolve())
        except ValueError as exc:
            raise StudyOrchestrationError(
                "EXE-03", f"study state path escapes the workspace: {stored_path}"
            ) from exc
        return candidate

    def _interrupt_active_processes(self) -> None:
        self._stop.set()
        with self._lock:
            processes = tuple(self._active_processes.values())
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def _mark_unfinished_interrupted(self) -> None:
        assert self._state is not None
        now = datetime.now(timezone.utc)
        runs = tuple(
            run if run.status is StudyRunStatus.COMPLETED else run.model_copy(update={
                "status": StudyRunStatus.INTERRUPTED,
                "ended_at": now,
                "error": "study execution was interrupted",
            })
            for run in self._state.runs
        )
        self._replace_state(runs=runs)

    def _record_execution_failure(self, message: str) -> None:
        if self._state is None or self._state_path is None:
            return
        try:
            self._replace_state(status=StudyExecutionStatus.FAILED, error=message)
        except OSError:
            pass

    def _update_run(self, updated: StudyRunRecord) -> None:
        with self._lock:
            assert self._state is not None
            runs = tuple(
                updated if run.run_id == updated.run_id else run
                for run in self._state.runs
            )
            self._state = self._state.model_copy(update={
                "runs": runs,
                "updated_at": datetime.now(timezone.utc),
            })
            self._persist_state_unlocked()

    def _replace_state(self, **updates: Any) -> None:
        with self._lock:
            assert self._state is not None
            updates["updated_at"] = datetime.now(timezone.utc)
            self._state = self._state.model_copy(update=updates)
            self._persist_state_unlocked()

    def _persist_state(self) -> None:
        with self._lock:
            self._persist_state_unlocked()

    def _persist_state_unlocked(self) -> None:
        assert self._state is not None and self._state_path is not None
        self._write_json_atomic(
            self._state_path, self._state.model_dump(mode="json")
        )

    def _run(self, run_id: str) -> StudyRunRecord:
        with self._lock:
            assert self._state is not None
            return next(run for run in self._state.runs if run.run_id == run_id)

    def _report(self, run: StudyRunRecord) -> None:
        if self.reporter is None:
            return
        assert self._state is not None
        finished = sum(
            item.status in {
                StudyRunStatus.COMPLETED,
                StudyRunStatus.FAILED,
                StudyRunStatus.INTERRUPTED,
            }
            for item in self._state.runs
        )
        try:
            self.reporter(run, finished, len(self._state.runs))
        except Exception:
            return

    @staticmethod
    def _write_json_atomic(destination: Path, payload: Any) -> None:
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)

    @staticmethod
    def _load_state(path: Path) -> StudyExecutionState:
        try:
            return StudyExecutionState.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise StudyOrchestrationError(
                "EXE-03", f"study state cannot be loaded: {path}"
            ) from exc

    @staticmethod
    def _run_id(manifest_hash: str, configuration_id: str, seed: int) -> str:
        encoded = f"{manifest_hash}\0{configuration_id}\0{seed}".encode("utf-8")
        return f"run-{hashlib.sha256(encoded).hexdigest()[:16]}"
