from typing import Type
from .base import BaseLogger
from .colorful import ColorfulLogger
from .plain import PlainLogger
from .json import JsonLogger


def create_logger(output_type: str) -> BaseLogger:
    """Factory function to create the appropriate logger."""
    loggers: dict[str, Type[BaseLogger]] = {
        "colorful": ColorfulLogger,
        "plain": PlainLogger,
        "json": JsonLogger
    }
    
    if output_type.lower() not in loggers:
        raise ValueError(f"Invalid output type: {output_type}. Must be one of: {', '.join(loggers.keys())}")
    
    return loggers[output_type.lower()]()

__all__ = ['BaseLogger', 'ColorfulLogger', 'PlainLogger', 'JsonLogger', 'create_logger'] 