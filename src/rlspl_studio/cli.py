"""Command-line entry point for the RLSPL Studio core."""

from __future__ import annotations

import argparse
import json
import shlex
import signal
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .catalog import build_initial_registry
from .exploration import StudyPlanner, StudyPlanningError
from .generation import ProductGenerationError, ProductGenerator
from .models import (
    ExplorationStudy,
    StudyExecutionStatus,
    StudyManifest,
    UserConfiguration,
)
from .orchestration import StudyOrchestrationError, StudyOrchestrator
from .planning import ProductPlanner, ProductPlanningError
from .resolver import ConfigurationResolver
from .studio import serve_studio


def _plugin_roots(args: argparse.Namespace) -> tuple[Path, ...]:
    configured = getattr(args, "plugins", None)
    return tuple(configured or (Path.cwd() / "plugins",))


def _registry(args: argparse.Namespace):
    registry = build_initial_registry(_plugin_roots(args))
    for issue in registry.plugin_diagnostics:
        print(f"PLUGIN {issue.code} {issue.path}: {issue.message}", file=sys.stderr)
    return registry


def _load_configuration(path: Path) -> UserConfiguration:
    with path.open("r", encoding="utf-8") as stream:
        return UserConfiguration.model_validate(json.load(stream))


def _load_study(path: Path) -> ExplorationStudy:
    with path.open("r", encoding="utf-8") as stream:
        return ExplorationStudy.model_validate(json.load(stream))


def _load_manifest(path: Path) -> StudyManifest:
    with path.open("r", encoding="utf-8") as stream:
        return StudyManifest.model_validate(json.load(stream))


def _validate(args: argparse.Namespace) -> int:
    try:
        configuration = _load_configuration(args.configuration)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Configuration could not be loaded: {exc}", file=sys.stderr)
        return 2

    result = ConfigurationResolver(_registry(args)).resolve(configuration)
    for issue in result.report.issues:
        print(f"{issue.severity.value.upper()} {issue.code} {issue.path}: {issue.message}")
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")

    if not result.report.is_valid:
        print(f"INVALID ({len(result.report.errors)} blocking issue(s))")
        return 2

    print(f"VALID ({len(result.report.advisories)} advisory issue(s))")
    if args.resolved and result.resolved is not None:
        print(result.resolved.model_dump_json(indent=2))
    return 0


def _generate(args: argparse.Namespace) -> int:
    try:
        configuration = _load_configuration(args.configuration)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Configuration could not be loaded: {exc}", file=sys.stderr)
        return 2
    registry = _registry(args)
    result = ConfigurationResolver(registry).resolve(configuration)
    if not result.report.is_valid or result.resolved is None:
        for issue in result.report.issues:
            print(f"{issue.severity.value.upper()} {issue.code} {issue.path}: {issue.message}")
        return 2
    for issue in result.report.advisories:
        print(f"ADVISORY {issue.code} {issue.path}: {issue.message}")
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")
    try:
        plan = ProductPlanner(registry).plan(result.resolved)
        product = ProductGenerator().generate(plan, result.resolved, args.output)
    except (ProductPlanningError, ProductGenerationError) as exc:
        print(f"{getattr(exc, 'code', 'GEN-04')}: {exc}", file=sys.stderr)
        return 2
    print(f"Generated {len(product.files)} files in {product.destination}")
    print(f"Run: cd {product.destination} && python3 -m pip install -e . && {product.entry_command}")
    return 0


def _studio(args: argparse.Namespace) -> int:
    serve_studio(
        args.workspace,
        args.host,
        args.port,
        not args.no_browser,
        plugin_roots=_plugin_roots(args),
    )
    return 0


def _components(args: argparse.Namespace) -> int:
    registry = _registry(args)
    planner = ProductPlanner(registry)
    print("Environments:")
    for item in registry.environments:
        availability = "executable" if item.runtime_assets else "runtime pending"
        print(f"  {item.id} {item.version} [{registry.origin(item.id)}; {availability}]")
    print("Algorithms:")
    for item in registry.algorithms:
        availability = "executable" if item.runtime_assets else "runtime pending"
        print(f"  {item.id} {item.version} [{registry.origin(item.id)}; {availability}]")
    print("Action behaviors:")
    for item in registry.behaviors:
        availability = "executable" if item.runtime_assets else "runtime pending"
        visibility = "public" if item.public else "compatibility"
        print(
            f"  {item.id} {item.version} "
            f"[{registry.origin(item.id)}; {availability}; {visibility}]"
        )
    print("Optimizers / update rules:")
    for item in registry.optimizers:
        availability = "executable" if item.runtime_assets else "runtime pending"
        visibility = "public" if item.public else "compatibility"
        print(
            f"  {item.id} {item.version} "
            f"[{registry.origin(item.id)}; {availability}; {visibility}]"
        )
    print("Executable pairings:")
    for environment_id, algorithm_id in planner.executable_pairings():
        print(f"  {environment_id} + {algorithm_id}")
    return 2 if registry.plugin_diagnostics else 0


def _explore(args: argparse.Namespace) -> int:
    try:
        study = _load_study(args.study)
        manifest = StudyPlanner(_registry(args)).plan(study, limit=args.limit)
    except (OSError, json.JSONDecodeError, ValidationError, StudyPlanningError) as exc:
        code = getattr(exc, "code", "EXP-00")
        path = getattr(exc, "path", "study")
        print(f"{code} {path}: {exc}", file=sys.stderr)
        return 2
    summary = manifest.summary
    print(f"Study: {study.name}")
    print(
        f"Candidates: {summary.candidate_count} defined, "
        f"{summary.evaluated_candidate_count} evaluated"
    )
    print(
        f"Configurations: {summary.unique_configuration_count} unique, "
        f"{summary.invalid_candidate_count} invalid, "
        f"{summary.duplicate_candidate_count} duplicate"
    )
    print(f"Planned runs: {summary.planned_run_count}")
    for advisory in manifest.advisories:
        print(f"ADVISORY {advisory.code} {advisory.path}: {advisory.message}")
    if args.verbose:
        for variant in manifest.variants:
            selections = ", ".join(
                f"{target}={value}" for target, value in variant.axis_values.items()
            )
            print(f"VALID {variant.configuration_id}: {selections}")
        for candidate in manifest.rejected_candidates:
            codes = ", ".join(sorted({issue.code for issue in candidate.issues}))
            print(f"INVALID candidate-{candidate.candidate_index}: {codes}")
    if args.manifest is not None:
        try:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            with args.manifest.open("x", encoding="utf-8") as stream:
                stream.write(manifest.model_dump_json(indent=2))
                stream.write("\n")
        except OSError as exc:
            print(f"EXP-05 manifest could not be saved: {exc}", file=sys.stderr)
            return 2
        print(f"Manifest: {args.manifest.resolve()}")
        print(f"Run: {_study_run_command(args.manifest.resolve(), args, jobs=2)}")
    return 0 if summary.unique_configuration_count else 2


def _run_study(args: argparse.Namespace) -> int:
    try:
        manifest = _load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"EXE-00 manifest could not be loaded: {exc}", file=sys.stderr)
        return 2

    workspace = args.workspace
    if workspace is None:
        workspace = _default_study_workspace(args.manifest)
    workspace = workspace.expanduser().resolve()
    print(f"Study workspace: {workspace}", flush=True)

    def report(run, finished: int, total: int) -> None:
        print(
            f"[{finished}/{total}] {run.status.value.upper()} "
            f"{run.run_id} configuration={run.configuration_id} "
            f"seed={run.training_seed} attempt={run.attempt}",
            flush=True,
        )

    previous_handlers: dict[signal.Signals, Any] = {}
    for signal_name in ("SIGHUP", "SIGTERM"):
        termination_signal = getattr(signal, signal_name, None)
        if termination_signal is None:
            continue
        try:
            previous_handlers[termination_signal] = signal.signal(
                termination_signal,
                _raise_keyboard_interrupt,
            )
        except (OSError, ValueError):
            continue
    try:
        state = StudyOrchestrator(_registry(args), reporter=report).execute(
            manifest,
            workspace,
            jobs=args.jobs,
            resume=args.resume,
            install_dependencies=not args.no_install,
        )
    except StudyOrchestrationError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Study preparation interrupted before execution state was created.", file=sys.stderr)
        return 130
    finally:
        for termination_signal, previous_handler in previous_handlers.items():
            signal.signal(termination_signal, previous_handler)

    counts = Counter(run.status.value for run in state.runs)
    summary = ", ".join(
        f"{count} {status}" for status, count in sorted(counts.items())
    )
    print(f"Study execution: {state.status.value.upper()} ({summary})")
    print(f"State: {(Path(state.workspace) / 'study-state.json').resolve()}")
    if state.status is StudyExecutionStatus.COMPLETED:
        return 0
    if state.status is StudyExecutionStatus.INTERRUPTED:
        print(
            "Resume: " + _study_run_command(
                args.manifest.resolve(),
                args,
                workspace=workspace.resolve(),
                jobs=args.jobs,
                resume=True,
            ),
            file=sys.stderr,
        )
        return 130
    return 2


def _study_run_command(
    manifest: Path,
    args: argparse.Namespace,
    *,
    workspace: Path | None = None,
    jobs: int = 1,
    resume: bool = False,
) -> str:
    command = ["rlspl", "run-study", str(manifest)]
    if workspace is not None:
        command.extend(("--workspace", str(workspace)))
    command.extend(("--jobs", str(jobs)))
    if resume:
        command.append("--resume")
    if getattr(args, "no_install", False):
        command.append("--no-install")
    for root in _plugin_roots(args):
        command.extend(("--plugins", str(root.resolve())))
    return shlex.join(command)


def _raise_keyboard_interrupt(_signal_number: int, _frame: Any) -> None:
    """Route catchable terminal shutdown through the orchestrator cleanup path."""

    raise KeyboardInterrupt


def _default_study_workspace(manifest: Path) -> Path:
    """Place implicit study runs where a Studio rooted above the manifest can see them."""

    resolved = manifest.expanduser().resolve()
    catalog_root = (
        resolved.parent.parent
        if resolved.parent.name == "studies"
        else resolved.parent
    )
    return catalog_root / "study-runs" / resolved.stem


def _add_plugins_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--plugins",
        type=Path,
        action="append",
        help="plug-in root; repeat the option for multiple roots",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rlspl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate and resolve a JSON configuration")
    validate.add_argument("configuration", type=Path)
    validate.add_argument("--resolved", action="store_true", help="print the resolved configuration")
    _add_plugins_argument(validate)
    validate.set_defaults(handler=_validate)
    generate = subparsers.add_parser("generate", help="generate a standalone RL product")
    generate.add_argument("configuration", type=Path)
    generate.add_argument("--output", type=Path, required=True)
    _add_plugins_argument(generate)
    generate.set_defaults(handler=_generate)
    studio = subparsers.add_parser("studio", help="open the local configuration editor")
    studio.add_argument("--workspace", type=Path, default=Path.cwd() / "generated")
    _add_plugins_argument(studio)
    studio.add_argument("--host", default="127.0.0.1")
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--no-browser", action="store_true")
    studio.set_defaults(handler=_studio)
    components = subparsers.add_parser(
        "components", help="list built-in and discovered plug-in components"
    )
    _add_plugins_argument(components)
    components.set_defaults(handler=_components)
    explore = subparsers.add_parser(
        "explore", help="expand and validate a finite configuration study"
    )
    explore.add_argument("study", type=Path)
    explore.add_argument("--limit", type=int, default=500)
    explore.add_argument("--manifest", type=Path)
    explore.add_argument("--verbose", action="store_true")
    _add_plugins_argument(explore)
    explore.set_defaults(handler=_explore)
    run_study = subparsers.add_parser(
        "run-study", help="execute every configuration and seed in a frozen study manifest"
    )
    run_study.add_argument("manifest", type=Path)
    run_study.add_argument(
        "--workspace",
        type=Path,
        help="execution directory (defaults to <catalog-root>/study-runs/<manifest-name>)",
    )
    run_study.add_argument(
        "--jobs", type=int, default=1, help="maximum number of concurrent product runs"
    )
    run_study.add_argument(
        "--resume", action="store_true", help="retry only incomplete runs in an existing workspace"
    )
    run_study.add_argument(
        "--no-install",
        action="store_true",
        help="use the active Python environment instead of creating a shared study environment",
    )
    _add_plugins_argument(run_study)
    run_study.set_defaults(handler=_run_study)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
