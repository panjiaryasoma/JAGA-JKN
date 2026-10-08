"""Immutable trusted authority contexts for the synthetic sandbox.

These values are implementation-owned. They never read CSV rows, environment
variables, or caller-provided authorization flags.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RuleAuthorityContext:
    authorized: bool
    authority_id: str
    rule_version: str
    applicable_period_verified: bool
    effective_from: str | None
    effective_to: str | None
    source_ids: tuple[str, ...]


_UNRESOLVED_VALUES = {"UNKNOWN", "UNVERIFIED", "UNRESOLVED", "NONE", "NULL", "PENDING"}


def _resolved_identifier(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    value = value.strip().upper()
    return value not in _UNRESOLVED_VALUES and not value.startswith(
        ("UNRESOLVED_", "UNVERIFIED_", "PENDING_")
    )


def _month(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value) is not None
    )


def authority_context_ready(
    context: RuleAuthorityContext, evaluated_period: object
) -> bool:
    """Structural readiness, not independent legal-authority verification.

    Context values must originate from trusted governance/registry, never CSV.
    """
    if not isinstance(context, RuleAuthorityContext):
        return False
    if type(context.authorized) is not bool or context.authorized is not True:
        return False
    if (
        type(context.applicable_period_verified) is not bool
        or context.applicable_period_verified is not True
    ):
        return False
    if not _resolved_identifier(context.authority_id):
        return False
    if not _resolved_identifier(context.rule_version):
        return False
    if (
        not isinstance(context.source_ids, tuple)
        or not context.source_ids
        or any(not _resolved_identifier(item) for item in context.source_ids)
        or len(set(context.source_ids)) != len(context.source_ids)
    ):
        return False
    if not all(_month(p) for p in (
        context.effective_from, context.effective_to, evaluated_period
    )):
        return False
    return context.effective_from <= evaluated_period <= context.effective_to


REGISTRATION_AUTHORITY_CONTEXT = RuleAuthorityContext(
    authorized=False,
    authority_id="UNRESOLVED",
    rule_version="UNVERIFIED",
    applicable_period_verified=False,
    effective_from=None,
    effective_to=None,
    source_ids=(),
)

WAGE_POLICY_CONTEXT = RuleAuthorityContext(
    authorized=False,
    authority_id="B2_UNRESOLVED",
    rule_version="UNVERIFIED",
    applicable_period_verified=False,
    effective_from=None,
    effective_to=None,
    source_ids=(),
)

CONTRIBUTION_POLICY_CONTEXT = RuleAuthorityContext(
    authorized=False,
    authority_id="B2_UNRESOLVED",
    rule_version="UNVERIFIED",
    applicable_period_verified=False,
    effective_from=None,
    effective_to=None,
    source_ids=(),
)
