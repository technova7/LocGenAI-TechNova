__version__ = "0.1.0"

# Re-export useful functions for convenience:
from .model_wrapper import get_response, find_local_answer  # noqa: F401

__all__ = ["__version__", "get_response", "find_local_answer"]
