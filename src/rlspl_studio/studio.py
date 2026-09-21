"""Extension-free local web interface for configuring RLSPL products."""

from __future__ import annotations

import json
import mimetypes
import re
import shlex
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from .catalog import build_initial_registry, core_training_parameters
from .exploration import StudyPlanner, StudyPlanningError
from .generation import ProductGenerationError, ProductGenerator
from .models import ExplorationStudy, UserConfiguration
from .monitoring import MonitoringError, MonitoringService
from .planning import ProductPlanner, ProductPlanningError
from .resolver import ConfigurationResolver
from .spl import SPLModel
from .theory import theory_catalog


class StudioService:
    """Application boundary shared by the HTTP interface and tests."""

    def __init__(
        self,
        workspace: Path,
        plugin_roots: Iterable[Path] = (),
    ) -> None:
        self.workspace = workspace.resolve()
        self.plugin_roots = tuple(root.expanduser().resolve() for root in plugin_roots)
        self.registry = build_initial_registry(self.plugin_roots)
        self.resolver = ConfigurationResolver(self.registry)
        self.spl_model = SPLModel(self.registry)
        self.planner = ProductPlanner(self.registry)
        self.study_planner = StudyPlanner(self.registry)
        self.generator = ProductGenerator()
        self.monitoring = MonitoringService(self.workspace)

    def catalog(self) -> dict[str, Any]:
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
        return {
            "schema_version": "1.0",
            "environments": [
                {
                    **item.model_dump(mode="json"),
                    "origin": self.registry.origin(item.id),
                }
                for item in self.registry.environments
            ],
            "algorithms": [
                {
                    **item.model_dump(mode="json"),
                    "origin": self.registry.origin(item.id),
                }
                for item in self.registry.algorithms
            ],
            "behaviors": [
                {
                    **item.model_dump(mode="json"),
                    "origin": self.registry.origin(item.id),
                }
                for item in self.registry.behaviors
                if item.public or item.id in referenced_behaviors
            ],
            "optimizers": [
                {
                    **item.model_dump(mode="json"),
                    "origin": self.registry.origin(item.id),
                }
                for item in self.registry.optimizers
                if item.public or item.id in referenced_optimizers
            ],
            "training_parameters": [
                item.model_dump(mode="json") for item in core_training_parameters()
            ],
            "execution_is_metadata": True,
            "monitoring_is_read_only": True,
            "plugin_diagnostics": [
                item.model_dump(mode="json")
                for item in self.registry.plugin_diagnostics
            ],
            "generation_pairings": [
                {"environment_id": environment_id, "algorithm_id": algorithm_id}
                for environment_id, algorithm_id in self.planner.executable_pairings()
            ],
            "generation_compositions": [
                {
                    "environment_id": environment_id,
                    "algorithm_id": algorithm_id,
                    "behavior_id": behavior_id,
                    "optimizer_id": optimizer_id,
                }
                for environment_id, algorithm_id, behavior_id, optimizer_id
                in self.planner.executable_compositions()
            ],
            "exploration_axes": list(self.study_planner.available_axes()),
            "exploration_defaults": self.study_planner.defaults(),
            "spl_model": self.spl_model.catalog(),
            "theory": theory_catalog(self.registry),
        }

    def monitor_executions(self) -> tuple[int, dict[str, Any]]:
        try:
            return HTTPStatus.OK, self.monitoring.list_executions()
        except MonitoringError as exc:
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "error": str(exc),
                "code": exc.code,
            }

    def monitor_execution(self, execution_id: str) -> tuple[int, dict[str, Any]]:
        try:
            return HTTPStatus.OK, self.monitoring.execution(execution_id)
        except MonitoringError as exc:
            status = HTTPStatus.NOT_FOUND if exc.code == "MON-01" else HTTPStatus.UNPROCESSABLE_ENTITY
            return status, {"error": str(exc), "code": exc.code}

    def monitor_run(self, execution_id: str, run_id: str) -> tuple[int, dict[str, Any]]:
        try:
            return HTTPStatus.OK, self.monitoring.run(execution_id, run_id)
        except MonitoringError as exc:
            status = HTTPStatus.NOT_FOUND if exc.code == "MON-01" else HTTPStatus.UNPROCESSABLE_ENTITY
            return status, {"error": str(exc), "code": exc.code}

    def monitor_hpo(self, execution_id: str, run_id: str) -> tuple[int, dict[str, Any]]:
        try:
            return HTTPStatus.OK, self.monitoring.hpo(execution_id, run_id)
        except MonitoringError as exc:
            status = HTTPStatus.NOT_FOUND if exc.code in {"MON-01", "MON-05"} else HTTPStatus.UNPROCESSABLE_ENTITY
            return status, {"error": str(exc), "code": exc.code}

    def validate(self, payload: Any) -> tuple[int, dict[str, Any]]:
        try:
            configuration = UserConfiguration.model_validate(payload)
        except ValidationError as exc:
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "valid": False,
                "issues": [
                    {
                        "severity": "error",
                        "code": "SCHEMA-01",
                        "path": ".".join(str(item) for item in error["loc"]),
                        "message": error["msg"],
                    }
                    for error in exc.errors()
                ],
            }
        result = self.resolver.resolve(configuration)
        status = HTTPStatus.OK if result.report.is_valid else HTTPStatus.UNPROCESSABLE_ENTITY
        return status, {
            "valid": result.report.is_valid,
            "issues": [item.model_dump(mode="json") for item in result.report.issues],
            "resolved": result.resolved.model_dump(mode="json") if result.resolved else None,
            "spl_trace": self.spl_model.trace(configuration, result),
        }

    def generate(self, payload: Any) -> tuple[int, dict[str, Any]]:
        configuration_payload = payload.get("configuration") if isinstance(payload, dict) else None
        status, validation = self.validate(configuration_payload)
        if not validation["valid"]:
            return status, validation
        configuration = UserConfiguration.model_validate(configuration_payload)
        resolved = self.resolver.resolve(configuration).resolved
        assert resolved is not None
        try:
            plan = self.planner.plan(resolved)
            slug = self._safe_slug(resolved.name)
            product = self.generator.generate(plan, resolved, self.workspace / slug)
        except (ProductPlanningError, ProductGenerationError) as exc:
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "generated": False,
                "issues": [{
                    "severity": "error",
                    "code": getattr(exc, "code", "GEN-04"),
                    "path": "generation",
                    "message": str(exc),
                }],
            }
        return HTTPStatus.CREATED, {
            "generated": True,
            "issues": validation["issues"],
            "product": product.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
        }

    def preview_study(self, payload: Any) -> tuple[int, dict[str, Any]]:
        return self._plan_study(payload)

    def save_study(self, payload: Any) -> tuple[int, dict[str, Any]]:
        status, planned = self._plan_study(payload)
        if status != HTTPStatus.OK:
            return status, planned
        manifest = planned["manifest"]
        study_hash = manifest["study_hash"]
        manifest_hash = manifest["manifest_hash"]
        slug = self._safe_slug(manifest["study"]["name"])
        destination = self.workspace / "studies" / f"{slug}-{manifest_hash[:12]}.json"
        execution_workspace = (
            self.workspace / "study-runs" / f"{slug}-{manifest_hash[:12]}"
        )
        run_command = self._study_run_command(destination, execution_workspace)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return HTTPStatus.INTERNAL_SERVER_ERROR, {
                "saved": False,
                "issues": [{
                    "severity": "error",
                    "code": "EXP-05",
                    "path": "study",
                    "message": f"study directory could not be created: {exc}",
                }],
            }
        if destination.exists():
            try:
                existing_manifest = json.loads(destination.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                return HTTPStatus.CONFLICT, {
                    "saved": False,
                    "issues": [{
                        "severity": "error",
                        "code": "EXP-05",
                        "path": "study",
                        "message": f"existing study manifest cannot be reused: {exc}",
                    }],
                }
            if (
                existing_manifest.get("study_hash") != study_hash
                or existing_manifest.get("manifest_hash") != manifest_hash
            ):
                return HTTPStatus.CONFLICT, {
                    "saved": False,
                    "issues": [{
                        "severity": "error",
                        "code": "EXP-05",
                        "path": "study",
                        "message": "study manifest path is occupied by different content",
                    }],
                }
            return HTTPStatus.OK, {
                "saved": True,
                "existing": True,
                "path": str(destination),
                "execution_workspace": str(execution_workspace),
                "run_command": run_command,
                "manifest": existing_manifest,
            }
        try:
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, indent=2, sort_keys=True)
                stream.write("\n")
        except OSError as exc:
            return HTTPStatus.INTERNAL_SERVER_ERROR, {
                "saved": False,
                "issues": [{
                    "severity": "error",
                    "code": "EXP-05",
                    "path": "study",
                    "message": f"study manifest could not be saved: {exc}",
                }],
            }
        return HTTPStatus.CREATED, {
            "saved": True,
            "existing": False,
            "path": str(destination),
            "execution_workspace": str(execution_workspace),
            "run_command": run_command,
            "manifest": manifest,
        }

    def _plan_study(self, payload: Any) -> tuple[int, dict[str, Any]]:
        if not isinstance(payload, dict):
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "planned": False,
                "issues": [{
                    "severity": "error",
                    "code": "EXP-00",
                    "path": "study",
                    "message": "study request must be a JSON object",
                }],
            }
        study_payload = payload.get("study", payload)
        try:
            limit = int(payload.get("limit", 500))
            study = ExplorationStudy.model_validate(study_payload)
            manifest = self.study_planner.plan(study, limit=limit)
        except (TypeError, ValueError, ValidationError) as exc:
            if isinstance(exc, StudyPlanningError):
                issue = {
                    "severity": "error",
                    "code": exc.code,
                    "path": exc.path,
                    "message": str(exc),
                }
                issues = [issue]
            elif isinstance(exc, ValidationError):
                issues = [{
                    "severity": "error",
                    "code": "EXP-00",
                    "path": ".".join(str(item) for item in error["loc"]),
                    "message": error["msg"],
                } for error in exc.errors()]
            else:
                issues = [{
                    "severity": "error",
                    "code": "EXP-00",
                    "path": "limit",
                    "message": str(exc),
                }]
            return HTTPStatus.UNPROCESSABLE_ENTITY, {
                "planned": False,
                "issues": issues,
            }
        return HTTPStatus.OK, {
            "planned": True,
            "manifest": manifest.model_dump(mode="json"),
        }

    @staticmethod
    def _safe_slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "rlspl-product"

    def _study_run_command(self, manifest: Path, workspace: Path) -> str:
        command = [
            "rlspl",
            "run-study",
            str(manifest),
            "--workspace",
            str(workspace),
            "--jobs",
            "2",
        ]
        for root in self.plugin_roots:
            command.extend(("--plugins", str(root)))
        return shlex.join(command)


def make_handler(service: StudioService, static_root: Path) -> type[BaseHTTPRequestHandler]:
    class StudioHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/catalog":
                self._json(HTTPStatus.OK, service.catalog())
                return
            if path == "/api/monitor/executions":
                self._json(*service.monitor_executions())
                return
            if path == "/api/monitor/execution":
                query = parse_qs(parsed.query)
                execution_id = query.get("execution_id", [""])[0]
                self._json(*service.monitor_execution(execution_id))
                return
            if path == "/api/monitor/run":
                query = parse_qs(parsed.query)
                execution_id = query.get("execution_id", [""])[0]
                run_id = query.get("run_id", [""])[0]
                self._json(*service.monitor_run(execution_id, run_id))
                return
            if path == "/api/monitor/hpo":
                query = parse_qs(parsed.query)
                execution_id = query.get("execution_id", [""])[0]
                run_id = query.get("run_id", [""])[0]
                self._json(*service.monitor_hpo(execution_id, run_id))
                return
            relative = "index.html" if path == "/" else path.lstrip("/")
            if relative not in {"index.html", "app.js", "styles.css"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            target = static_root / relative
            try:
                content = target.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:  # noqa: N802
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 1_000_000:
                    raise ValueError("request body must contain at most 1 MB")
                payload = json.loads(self.rfile.read(size))
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            path = urlparse(self.path).path
            if path == "/api/validate":
                self._json(*service.validate(payload))
            elif path == "/api/generate":
                self._json(*service.generate(payload))
            elif path == "/api/studies/preview":
                self._json(*service.preview_study(payload))
            elif path == "/api/studies/save":
                self._json(*service.save_study(payload))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return StudioHandler


def serve_studio(
    workspace: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    plugin_roots: Iterable[Path] = (),
) -> None:
    service = StudioService(workspace, plugin_roots)
    static_root = Path(__file__).with_name("web")
    server = ThreadingHTTPServer((host, port), make_handler(service, static_root))
    url = f"http://{host}:{server.server_port}"
    print(f"RLSPL Studio running at {url}")
    print(f"Generated products: {service.workspace}")
    print(
        f"Components: {len(service.registry.environments)} environments, "
        f"{len(service.registry.algorithms)} algorithms"
    )
    for issue in service.registry.plugin_diagnostics:
        print(f"Plugin {issue.code} {issue.path}: {issue.message}")
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nRLSPL Studio stopped")
    finally:
        server.server_close()
