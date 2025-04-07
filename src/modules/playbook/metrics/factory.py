from typing import Dict, Type

from src.modules.playbook.config import MetricsConfig, MetricsCollectorType
from src.modules.playbook.metrics.base import MetricsCollector
from src.modules.playbook.metrics.json import JsonMetricsCollector
from src.modules.playbook.metrics.prometheus import PrometheusMetricsCollector
from src.modules.playbook.metrics.console import ConsoleMetricsCollector

def create_metrics_collector(config: MetricsConfig) -> MetricsCollector:
    """Create a metrics collector based on the configuration.
    
    Args:
        config: The metrics configuration
        
    Returns:
        A metrics collector instance
        
    Raises:
        ValueError: If the collector type is not supported
    """
    collector_types: Dict[MetricsCollectorType, Type[MetricsCollector]] = {
        MetricsCollectorType.JSON: JsonMetricsCollector,
        MetricsCollectorType.PROMETHEUS: PrometheusMetricsCollector,
        MetricsCollectorType.CONSOLE: ConsoleMetricsCollector,
    }
    
    if config.collector not in collector_types:
        raise ValueError(f"Unsupported metrics collector type: {config.collector}")
    
    if config.collector == MetricsCollectorType.JSON:
        if not config.output_file:
            raise ValueError("output_file is required for JSON collector")
        return JsonMetricsCollector(config.output_file)
        
    elif config.collector == MetricsCollectorType.PROMETHEUS:
        if not config.push_gateway:
            raise ValueError("push_gateway is required for Prometheus collector")
        return PrometheusMetricsCollector(config.push_gateway, config.job_name)
        
    elif config.collector == MetricsCollectorType.CONSOLE:
        return ConsoleMetricsCollector(config.verbosity)
    
    raise ValueError(f"Unsupported metrics collector type: {config.collector}") 