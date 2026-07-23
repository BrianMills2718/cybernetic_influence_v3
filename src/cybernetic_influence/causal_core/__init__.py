"""Production-shaped exact causal-core contracts and execution surface.

This package is non-default during staged v3 migration.  It intentionally has
no dependency on the v2 substrate, the isolated v3 spike, cognition providers,
Concordia, or the workbench.
"""

from cybernetic_influence.causal_core.engine import (
    CausalCoreError,
    CausalLimits,
    CausalSession,
    ExactMechanismBinding,
    MechanismContractError,
    MechanismContext,
    MechanismInvariantError,
    PropagationBudgetExceeded,
    StateAccessViolation,
)
from cybernetic_influence.causal_core.fixtures import (
    ExactFixture,
    authentication_fixture,
    relay_fixture,
)
from cybernetic_influence.causal_core.models import (
    ActionAttempt,
    CausalCheckpoint,
    CausalRunResult,
    CausalScenario,
    CausalState,
    RUNTIME_CONTRACT,
    SCHEMA_VERSION,
)
from cybernetic_influence.causal_core.projection import (
    CausalGraphArtifact,
    CausalPrefixGraphArtifact,
    checkpoint_narrative_lines,
    narrative_lines,
    project_graph,
    project_checkpoint_graph,
    validate_checkpoint_graph_artifact,
)
from cybernetic_influence.causal_core.replay import (
    ReplayError,
    replay_committed_trajectory,
)

__all__ = [
    "ActionAttempt",
    "CausalCheckpoint",
    "CausalCoreError",
    "CausalGraphArtifact",
    "CausalPrefixGraphArtifact",
    "CausalLimits",
    "CausalRunResult",
    "CausalScenario",
    "CausalSession",
    "CausalState",
    "ExactMechanismBinding",
    "ExactFixture",
    "MechanismContractError",
    "MechanismContext",
    "MechanismInvariantError",
    "PropagationBudgetExceeded",
    "RUNTIME_CONTRACT",
    "ReplayError",
    "SCHEMA_VERSION",
    "StateAccessViolation",
    "authentication_fixture",
    "checkpoint_narrative_lines",
    "narrative_lines",
    "project_graph",
    "project_checkpoint_graph",
    "relay_fixture",
    "replay_committed_trajectory",
    "validate_checkpoint_graph_artifact",
]
