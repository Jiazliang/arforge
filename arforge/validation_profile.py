from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
from pathlib import Path
import sys
from typing import Any, Iterator, Literal

import yaml

from .semantic_validation import ValidationCase, ValidationRuleFunc, function_validation_case

ValidationProfileMode = Literal["core+extensions", "extensions-only"]


class ValidationProfileError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("Validation profile failed")
        self.errors = errors


@dataclass(frozen=True)
class ValidationProfileExtension:
    module: str
    rules: tuple[str, ...]


@dataclass(frozen=True)
class ValidationProfile:
    name: str
    mode: ValidationProfileMode
    enable: tuple[str, ...]
    disable: tuple[str, ...]
    extensions: tuple[ValidationProfileExtension, ...]
    source_path: Path

    @property
    def ruleset_name(self) -> str:
        return f"profile:{self.name}"


def load_validation_profile(path: Path) -> ValidationProfile:
    data = _load_profile_yaml(path)

    profile_data = data.get("profile")
    if not isinstance(profile_data, dict):
        raise ValidationProfileError([f"{path}:profile: expected a mapping"])

    name = profile_data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValidationProfileError([f"{path}:profile.name: expected a non-empty string"])

    mode = profile_data.get("mode", "core+extensions")
    if mode not in ("core+extensions", "extensions-only"):
        raise ValidationProfileError(
            [f"{path}:profile.mode: expected 'core+extensions' or 'extensions-only'"]
        )

    rules_data = data.get("rules", {})
    if not isinstance(rules_data, dict):
        raise ValidationProfileError([f"{path}:rules: expected a mapping"])

    enable = _load_rule_code_list(path, rules_data, "enable")
    disable = _load_rule_code_list(path, rules_data, "disable")

    extensions_data = data.get("extensions", [])
    if not isinstance(extensions_data, list):
        raise ValidationProfileError([f"{path}:extensions: expected a list"])

    extensions: list[ValidationProfileExtension] = []
    for index, item in enumerate(extensions_data):
        label = f"{path}:extensions[{index}]"
        if not isinstance(item, dict):
            raise ValidationProfileError([f"{label}: expected a mapping"])
        module_name = item.get("module")
        if not isinstance(module_name, str) or not module_name.strip():
            raise ValidationProfileError([f"{label}.module: expected a non-empty string"])
        rule_names = item.get("rules")
        if not isinstance(rule_names, list) or not rule_names:
            raise ValidationProfileError([f"{label}.rules: expected a non-empty list of rule function names"])
        invalid_names = [value for value in rule_names if not isinstance(value, str) or not value.strip()]
        if invalid_names:
            raise ValidationProfileError([f"{label}.rules: every entry must be a non-empty string"])
        extensions.append(
            ValidationProfileExtension(module=module_name, rules=tuple(rule_names))
        )

    return ValidationProfile(
        name=name.strip(),
        mode=mode,
        enable=tuple(enable),
        disable=tuple(disable),
        extensions=tuple(extensions),
        source_path=path.resolve(),
    )


def load_extension_cases(profile: ValidationProfile) -> list[ValidationCase]:
    extension_cases: list[ValidationCase] = []
    for extension in profile.extensions:
        rule_functions = load_extension_rule_functions(
            profile.source_path.parent,
            extension.module,
            extension.rules,
        )
        for rule in rule_functions:
            try:
                extension_cases.append(function_validation_case(rule))
            except ValueError as exc:
                raise ValidationProfileError([str(exc)]) from exc
    return extension_cases


def load_extension_rule_functions(
    import_root: Path,
    module_name: str,
    rule_names: tuple[str, ...],
) -> list[ValidationRuleFunc]:
    with _prepend_sys_path(import_root):
        _clear_profile_local_modules(import_root, module_name)
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - exercised in tests through message text only
            raise ValidationProfileError(
                [f"Failed to import extension module '{module_name}': {exc}"]
            ) from exc

    loaded_rules: list[ValidationRuleFunc] = []
    for rule_name in rule_names:
        rule = getattr(module, rule_name, None)
        if rule is None:
            raise ValidationProfileError(
                [f"Extension module '{module_name}' does not define rule function '{rule_name}'."]
            )
        if not callable(rule):
            raise ValidationProfileError(
                [f"Extension entry '{module_name}.{rule_name}' is not callable."]
            )
        try:
            loaded_rules.append(rule)
        except TypeError as exc:  # pragma: no cover - defensive only
            raise ValidationProfileError(
                [f"Extension rule '{module_name}.{rule_name}' is invalid: {exc}"]
            ) from exc
    return loaded_rules


def _load_profile_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ValidationProfileError([f"{path}: profile file not found"]) from exc
    except yaml.YAMLError as exc:
        raise ValidationProfileError([f"{path}: failed to parse YAML: {exc}"]) from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValidationProfileError([f"{path}: expected a YAML mapping (object) at root"])
    return data


def _load_rule_code_list(path: Path, rules_data: dict[str, Any], key: str) -> list[str]:
    values = rules_data.get(key, [])
    if not isinstance(values, list):
        raise ValidationProfileError([f"{path}:rules.{key}: expected a list"])
    invalid = [value for value in values if not isinstance(value, str) or not value.strip()]
    if invalid:
        raise ValidationProfileError([f"{path}:rules.{key}: every entry must be a non-empty string"])
    return list(values)


@contextmanager
def _prepend_sys_path(path: Path) -> Iterator[None]:
    resolved = str(path.resolve())
    sys.path.insert(0, resolved)
    try:
        yield
    finally:
        if sys.path and sys.path[0] == resolved:
            sys.path.pop(0)
        elif resolved in sys.path:
            sys.path.remove(resolved)


def _clear_profile_local_modules(import_root: Path, module_name: str) -> None:
    module_parts = module_name.split(".")
    candidates = [".".join(module_parts[: index + 1]) for index in range(len(module_parts))]
    for candidate in reversed(candidates):
        sys.modules.pop(candidate, None)
