"""General causal simulation contracts and Concordia lifecycle adapter."""

from .models import (
    ActorContext,
    GeneralWorldSpec,
    GeneralWorldState,
    SemanticActionIntent,
    TransitionAuthoritySpec,
    WorldTransaction,
)
from .authoring_models import GeneralSimulationProposalV1
from .compiler import compile_general_simulation, compile_general_simulation_v2
from .contracts_v2 import RunSpecV2, ScenarioSpecV2, adapt_general_proposal_v1
from .study_models import AuthoredSimulationBundleV2, adapt_authored_bundle_v1
from .world import CanonicalWorld

__all__ = [
    "ActorContext",
    "CanonicalWorld",
    "GeneralWorldSpec",
    "GeneralWorldState",
    "SemanticActionIntent",
    "TransitionAuthoritySpec",
    "WorldTransaction",
    "GeneralSimulationProposalV1",
    "ScenarioSpecV2",
    "RunSpecV2",
    "AuthoredSimulationBundleV2",
    "adapt_general_proposal_v1",
    "adapt_authored_bundle_v1",
    "compile_general_simulation",
    "compile_general_simulation_v2",
]
