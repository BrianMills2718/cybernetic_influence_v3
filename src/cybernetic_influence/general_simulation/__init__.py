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
from .compiler import compile_general_simulation
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
    "compile_general_simulation",
]
