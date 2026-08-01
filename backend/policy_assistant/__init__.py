"""VinUni multi-agent policy assistant."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import PolicyAssistant


def __getattr__(name: str):
    if name == "PolicyAssistant":
        from .service import PolicyAssistant

        return PolicyAssistant
    raise AttributeError(name)

__all__ = ["PolicyAssistant"]
