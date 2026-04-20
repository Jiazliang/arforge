"""Validation ruleset lookup and profile-aware rule resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .semantic_validation import ValidationCase
from .validation.cases import core_validation_cases
from .validation_profile import ValidationProfile, ValidationProfileError, load_extension_cases

_RULESETS: Dict[str, List[ValidationCase]] = {
    "core": core_validation_cases(),
}


@dataclass(frozen=True)
class ResolvedValidationRuleset:
    name: str
    cases: List[ValidationCase]


def get_ruleset(name: str = "core") -> List[ValidationCase]:
    try:
        return list(_RULESETS[name])
    except KeyError as exc:
        known = ", ".join(sorted(_RULESETS.keys()))
        raise ValueError(f"Unknown validation ruleset '{name}'. Known rulesets: {known}") from exc


def resolve_ruleset(profile: ValidationProfile | None = None) -> ResolvedValidationRuleset:
    if profile is None:
        return ResolvedValidationRuleset(name="core", cases=get_ruleset("core"))

    core_cases = get_ruleset("core")
    extension_cases = load_extension_cases(profile)

    if profile.mode == "core+extensions":
        candidate_cases = core_cases + extension_cases
    else:
        candidate_cases = extension_cases

    catalog = _build_case_catalog(candidate_cases)
    active_codes = [case.case_id for case in candidate_cases]
    active_code_set = set(active_codes)

    for code in profile.disable:
        if code not in catalog:
            raise ValidationProfileError(
                [f"Profile '{profile.name}' references unknown rule code '{code}' in rules.disable."]
            )
        active_code_set.discard(code)

    for code in profile.enable:
        if code not in catalog:
            raise ValidationProfileError(
                [f"Profile '{profile.name}' references unknown rule code '{code}' in rules.enable."]
            )
        active_code_set.add(code)

    active_cases = [catalog[code] for code in sorted(active_code_set)]
    return ResolvedValidationRuleset(name=profile.ruleset_name, cases=active_cases)


def _build_case_catalog(cases: List[ValidationCase]) -> Dict[str, ValidationCase]:
    catalog: Dict[str, ValidationCase] = {}
    for case in cases:
        if case.case_id in catalog:
            raise ValidationProfileError(
                [f"Duplicate validation rule code '{case.case_id}' detected while building ruleset."]
            )
        catalog[case.case_id] = case
    return catalog

