"""Session modes for different types of feedback gathering.

This module provides different session modes that control how
questions are presented to agents and how responses are collected.

Available modes:
- SingleMode: One question, all agents respond once
- DiscussionMode: Agents see and respond to each other
- StructuredMode: Guided phases (explore, critique, suggest, synthesize)

The SessionOrchestrator coordinates agents, tools, and modes
to run complete focusgroup sessions.
"""

from .base import (
    BaseSessionMode,
    ConversationHistory,
    ConversationTurn,
    RoundResult,
    SessionMode,
    SessionModeError,
)
from .discussion import DiscussionMode, create_discussion_mode
from .moderator import (
    DEFAULT_MODERATOR_PROMPT,
    ModeratorConfig,
    create_moderator_agent,
    quick_synthesize,
    synthesize_feedback,
)
from .orchestrator import SessionOrchestrator, run_focusgroup
from .single import SingleMode, create_single_mode
from .structured import Phase, StructuredMode, create_structured_mode

__all__ = [
    # Base types
    "SessionMode",
    "BaseSessionMode",
    "RoundResult",
    "ConversationTurn",
    "ConversationHistory",
    "SessionModeError",
    # Mode implementations
    "SingleMode",
    "create_single_mode",
    "DiscussionMode",
    "create_discussion_mode",
    "StructuredMode",
    "create_structured_mode",
    "Phase",
    # Moderator
    "ModeratorConfig",
    "create_moderator_agent",
    "synthesize_feedback",
    "quick_synthesize",
    "DEFAULT_MODERATOR_PROMPT",
    # Orchestration
    "SessionOrchestrator",
    "run_focusgroup",
]
