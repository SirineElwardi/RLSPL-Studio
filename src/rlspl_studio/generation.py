"""Materialize a standalone product from an explicit product plan."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import FrozenModel, ResolvedConfiguration
from .planning import ProductPlan


class ProductGenerationError(ValueError):
    pass


class GeneratedProduct(FrozenModel):
    destination: str
    files: tuple[str, ...]
    entry_command: str


class ProductGenerator:
    _COMMON_TEMPLATES = {
        "README.md": "README.md.tmpl",
        "pyproject.toml": "pyproject.toml.tmpl",
        "run.py": "run.py.tmpl",
        "src/rlspl_product/__init__.py": "common/__init__.py.tmpl",
        "src/rlspl_product/__main__.py": "common/__main__.py.tmpl",
        "src/rlspl_product/main.py": "common/main.py.tmpl",
        "src/rlspl_product/evaluation.py": "common/evaluation.py.tmpl",
        "src/rlspl_product/hpo.py": "common/hpo.py.tmpl",
    }
    def __init__(self, template_root: Path | None = None) -> None:
        self.template_root = template_root or Path(__file__).with_name("product_templates")

    def generate(
        self,
        plan: ProductPlan,
        resolved: ResolvedConfiguration,
        destination: Path,
    ) -> GeneratedProduct:
        if plan.configuration_hash != resolved.configuration_hash:
            raise ProductGenerationError("plan and resolved configuration hashes differ")
        if destination.exists():
            raise ProductGenerationError(f"destination already exists: {destination}")

        expected = {item.path for item in plan.files}
        generated_special = {"config.json", "generation-manifest.json"}
        templates = self._template_map(plan)
        missing_templates = sorted(expected - generated_special - set(templates))
        if missing_templates:
            raise ProductGenerationError(f"no templates for planned files: {missing_templates}")

        package_name = self._slug(plan.product_name)
        replacements = {
            "{{PRODUCT_NAME}}": plan.product_name,
            "{{PACKAGE_NAME}}": package_name,
            "{{DEPENDENCIES}}": ",\n  ".join(json.dumps(item) for item in plan.dependencies),
            "{{ALGORITHM_ID}}": plan.algorithm_id,
            "{{ENVIRONMENT_ID}}": plan.environment_id,
            "{{BEHAVIOR_ID}}": plan.behavior_id,
            "{{OPTIMIZER_ID}}": plan.optimizer_id,
            "{{CHECKPOINT_FILENAME}}": plan.checkpoint_filename,
        }
        rendered: dict[str, str] = {}
        for path in sorted(expected - generated_special):
            try:
                template = templates[path].read_text(encoding="utf-8")
            except OSError as exc:
                raise ProductGenerationError(
                    f"runtime template cannot be read for {path}: {templates[path]}"
                ) from exc
            for token, value in replacements.items():
                template = template.replace(token, value)
            rendered[path] = template
        rendered["config.json"] = resolved.model_dump_json(indent=2) + "\n"
        rendered["generation-manifest.json"] = json.dumps(
            plan.model_dump(mode="json"), indent=2, sort_keys=True
        ) + "\n"

        destination.mkdir(parents=True)
        for relative_path, content in rendered.items():
            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return GeneratedProduct(
            destination=str(destination.resolve()),
            files=tuple(sorted(rendered)),
            entry_command=plan.entry_command,
        )

    def _template_map(self, plan: ProductPlan) -> dict[str, Path]:
        algorithm_root = (
            Path(plan.algorithm_template_root)
            if plan.algorithm_template_root
            else self.template_root
        )
        environment_root = (
            Path(plan.environment_template_root)
            if plan.environment_template_root
            else self.template_root
        )
        behavior_root = (
            Path(plan.behavior_template_root)
            if plan.behavior_template_root
            else self.template_root
        )
        optimizer_root = (
            Path(plan.optimizer_template_root)
            if plan.optimizer_template_root
            else self.template_root
        )
        return {
            **{
                output: self.template_root / template
                for output, template in self._COMMON_TEMPLATES.items()
            },
            "src/rlspl_product/agent.py": algorithm_root / plan.agent_template,
            "src/rlspl_product/trainer.py": algorithm_root / plan.trainer_template,
            "src/rlspl_product/behavior.py": behavior_root / plan.behavior_template,
            "src/rlspl_product/optimizer.py": optimizer_root / plan.optimizer_template,
            "src/rlspl_product/environment.py": environment_root / plan.environment_template,
        }

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "rlspl-product"
