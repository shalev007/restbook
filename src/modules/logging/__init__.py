from typing import Type
from .base import BaseLogger
from .colorful import ColorfulLogger
from .plain import PlainLogger
from .json import JsonLogger


def create_logger(output_type: str, log_level: str = "INFO") -> BaseLogger:
    """Factory function to create the appropriate logger.
    
    Args:
        output_type: The type of logger to create (colorful, plain, or json)
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    loggers: dict[str, Type[BaseLogger]] = {
        "colorful": ColorfulLogger,
        "plain": PlainLogger,
        "json": JsonLogger
    }
    
    if output_type.lower() not in loggers:
        raise ValueError(f"Invalid output type: {output_type}. Must be one of: {', '.join(loggers.keys())}")
    
    return loggers[output_type.lower()](log_level)

__all__ = ['BaseLogger', 'ColorfulLogger', 'PlainLogger', 'JsonLogger', 'create_logger'] 