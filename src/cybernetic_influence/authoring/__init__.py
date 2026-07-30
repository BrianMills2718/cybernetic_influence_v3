"""Typed, reviewable scenario-authoring contracts and approved compilers."""

from cybernetic_influence.authoring.compiler import (
    AuthoringCompilationError,
    CompiledScenario,
    compile_coordination_decision,
    compile_scenario,
    compile_resource_request,
)
from cybernetic_influence.authoring.models import ScenarioDraftProposal
from cybernetic_influence.authoring.examples import reviewed_coordination_proposal

__all__ = [
    "AuthoringCompilationError",
    "CompiledScenario",
    "ScenarioDraftProposal",
    "compile_coordination_decision",
    "compile_resource_request",
    "compile_scenario",
    "reviewed_coordination_proposal",
]
