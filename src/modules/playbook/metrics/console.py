from datetime import datetime
from typing import Dict, Any
import json

from .base import MetricsCollector, RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics

class ConsoleMetricsCollector(MetricsCollector):
    """Collector that outputs metrics to the console."""
    
    def __init__(self, verbosity: str = "info"):
        """Initialize the console collector.
        
        Args:
            verbosity: Log level (debug, info, warning)
        """
        self.verbosity = verbosity
        self._should_print = {
            "debug": lambda _: True,
            "info": lambda metrics: not isinstance(metrics, RequestMetrics),
            "warning": lambda metrics: isinstance(metrics, PlaybookMetrics)
        }.get(verbosity, lambda _: True)
    
    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for console output."""
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _print_metrics(self, prefix: str, metrics: Any) -> None:
        """Print metrics to console if verbosity level allows."""
        if not self._should_print(metrics):
            return
            
        if isinstance(metrics, (RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics)):
            data: Dict[str, Any] = {}
            for field in metrics.__dataclass_fields__:
                value = getattr(metrics, field)
                if isinstance(value, datetime):
                    data[field] = self._format_datetime(value)
                elif isinstance(value, (RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics)):
                    data[field] = self._format_metrics(value)
                elif isinstance(value, list):
                    data[field] = [self._format_metrics(item) for item in value]
                else:
                    data[field] = value
            print(f"{prefix}{json.dumps(data, indent=2)}")
    
    def _format_metrics(self, metrics: Any) -> Any:
        """Format metrics for console output."""
        if isinstance(metrics, (RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics)):
            data: Dict[str, Any] = {}
            for field in metrics.__dataclass_fields__:
                value = getattr(metrics, field)
                if isinstance(value, datetime):
                    data[field] = self._format_datetime(value)
                elif isinstance(value, (RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics)):
                    data[field] = self._format_metrics(value)
                elif isinstance(value, list):
                    data[field] = [self._format_metrics(item) for item in value]
                else:
                    data[field] = value
            return data
        return metrics
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics."""
        self._print_metrics("Request Metrics: ", metrics)
    
    def record_step(self, metrics: StepMetrics) -> None:
        """Record step metrics."""
        self._print_metrics("Step Metrics: ", metrics)
    
    def record_phase(self, metrics: PhaseMetrics) -> None:
        """Record phase metrics."""
        self._print_metrics("Phase Metrics: ", metrics)
    
    def record_playbook(self, metrics: PlaybookMetrics) -> None:
        """Record playbook metrics."""
        self._print_metrics("Playbook Metrics: ", metrics)
    
    def finalize(self) -> None:
        """No-op for console collector."""
        pass 