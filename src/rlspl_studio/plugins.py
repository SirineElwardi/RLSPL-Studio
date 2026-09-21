"""Discover local, manifest-driven RLSPL components without core edits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, ValidationError, model_validator

from .descriptors import (
    AlgorithmDescriptor,
    BehaviorDescriptor,
    EnvironmentDescriptor,
    OptimizerDescriptor,
)
from .models import IssueSeverity, StrictModel, ValidationIssue
from .registry import ComponentRegistry


class EnvironmentPluginManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["environment"]
    descriptor: EnvironmentDescriptor

    @model_validator(mode="after")
    def parameter_owners_match(self) -> "EnvironmentPluginManifest":
        _require_parameter_owners(self.descriptor)
        return self


class AlgorithmPluginManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["algorithm"]
    descriptor: AlgorithmDescriptor

    @model_validator(mode="after")
    def parameter_owners_match(self) -> "AlgorithmPluginManifest":
        _require_parameter_owners(self.descriptor)
        return self


class BehaviorPluginManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["behavior"]
    descriptor: BehaviorDescriptor

    @model_validator(mode="after")
    def parameter_owners_match(self) -> "BehaviorPluginManifest":
        _require_parameter_owners(self.descriptor)
        return self


class OptimizerPluginManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["optimizer"]
    descriptor: OptimizerDescriptor

    @model_validator(mode="after")
    def parameter_owners_match(self) -> "OptimizerPluginManifest":
        _require_parameter_owners(self.descriptor)
        return self


PluginManifest = Annotated[
    EnvironmentPluginManifest
    | AlgorithmPluginManifest
    | BehaviorPluginManifest
    | OptimizerPluginManifest,
    Field(discriminator="kind"),
]
_MANIFEST_ADAPTER = TypeAdapter(PluginManifest)


def _require_parameter_owners(
    descriptor: (
        EnvironmentDescriptor
        | AlgorithmDescriptor
        | BehaviorDescriptor
        | OptimizerDescriptor
    ),
) -> None:
    invalid = [item.id for item in descriptor.parameters if item.owner != descriptor.id]
    if invalid:
        raise ValueError(
            f"parameter owners must equal component id {descriptor.id!r}: {invalid}"
        )


def discover_plugins(
    registry: ComponentRegistry,
    plugin_roots: tuple[Path, ...] | list[Path],
) -> None:
    """Register valid manifests and retain diagnostics for rejected plug-ins."""

    for configured_root in plugin_roots:
        root = configured_root.expanduser().resolve()
        if not root.exists():
            continue
        if not root.is_dir():
            _diagnostic(registry, "PLG-01", root, "plug-in root is not a directory")
            continue
        for manifest_path in sorted(root.rglob("component.json")):
            _load_manifest(registry, manifest_path)


def _load_manifest(registry: ComponentRegistry, manifest_path: Path) -> None:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _diagnostic(registry, "PLG-01", manifest_path, f"manifest cannot be read: {exc}")
        return
    try:
        manifest = _MANIFEST_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(item) for item in first["loc"])
        _diagnostic(
            registry,
            "PLG-02",
            manifest_path,
            f"invalid manifest at {location}: {first['msg']}",
        )
        return

    descriptor = manifest.descriptor
    if descriptor.contract_version != "1.0":
        _diagnostic(
            registry,
            "PLG-02",
            manifest_path,
            f"unsupported component contract version: {descriptor.contract_version}",
        )
        return
    try:
        descriptor = _attach_template_root(descriptor, manifest_path.parent)
    except ValueError as exc:
        _diagnostic(registry, "PLG-03", manifest_path, str(exc))
        return

    try:
        if manifest.kind == "environment":
            assert isinstance(descriptor, EnvironmentDescriptor)
            registry.register_environment(descriptor, origin=str(manifest_path))
        elif manifest.kind == "algorithm":
            assert isinstance(descriptor, AlgorithmDescriptor)
            registry.register_algorithm(descriptor, origin=str(manifest_path))
        elif manifest.kind == "behavior":
            assert isinstance(descriptor, BehaviorDescriptor)
            registry.register_behavior(descriptor, origin=str(manifest_path))
        else:
            assert isinstance(descriptor, OptimizerDescriptor)
            registry.register_optimizer(descriptor, origin=str(manifest_path))
    except ValueError as exc:
        _diagnostic(registry, "PLG-04", manifest_path, str(exc))


def _attach_template_root(
    descriptor: (
        EnvironmentDescriptor
        | AlgorithmDescriptor
        | BehaviorDescriptor
        | OptimizerDescriptor
    ),
    plugin_root: Path,
) -> EnvironmentDescriptor | AlgorithmDescriptor | BehaviorDescriptor | OptimizerDescriptor:
    assets = descriptor.runtime_assets
    if assets is None:
        return descriptor
    if isinstance(descriptor, EnvironmentDescriptor):
        template_names = (assets.adapter_template,)
    elif isinstance(descriptor, AlgorithmDescriptor):
        template_names = (assets.agent_template, assets.trainer_template)
    elif isinstance(descriptor, BehaviorDescriptor):
        template_names = (assets.behavior_template,)
    else:
        template_names = (assets.optimizer_template,)
    resolved_root = plugin_root.resolve()
    for template_name in template_names:
        if Path(template_name).is_absolute():
            raise ValueError("runtime template paths must be relative to the plug-in directory")
        candidate = (resolved_root / template_name).resolve()
        if not candidate.is_relative_to(resolved_root):
            raise ValueError(f"runtime template escapes plug-in directory: {template_name}")
        if not candidate.is_file():
            raise ValueError(f"runtime template does not exist: {template_name}")
    rooted_assets = assets.model_copy(update={"template_root": str(resolved_root)})
    return descriptor.model_copy(update={"runtime_assets": rooted_assets})


def _diagnostic(
    registry: ComponentRegistry,
    code: str,
    source: Path,
    message: str,
) -> None:
    registry.add_plugin_diagnostic(
        ValidationIssue(
            severity=IssueSeverity.ERROR,
            code=code,
            path=str(source),
            message=message,
            suggestion="Fix or remove this plug-in manifest; other components remain available.",
        )
    )
