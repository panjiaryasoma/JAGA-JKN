"""Immutable trusted authority contexts for the synthetic sandbox.

These values are implementation-owned. They never read CSV rows, environment
variables, or caller-provided authorization flags.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleAuthorityContext:
    authorized: bool
    authority_id: str
    rule_version: str
    applicable_period_verified: bool
    effective_from: str | None
    effective_to: str | None
    source_ids: tuple[str, ...]


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
