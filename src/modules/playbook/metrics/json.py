import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from .base import MetricsCollector, RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics

class JsonMetricsCollector(MetricsCollector):
    """Collector that saves metrics to a JSON file."""
    
    def __init__(self, output_file: str):
        """Initialize the JSON collector.
        
        Args:
            output_file: Path to the output JSON file
        """
        self.output_file = Path(output_file)
        self.metrics: Dict[str, Any] = {
            'requests': [],
            'steps': [],
            'phases': [],
            'playbook': None
        }
    
    def _serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return dt.isoformat()
    
    def _serialize_metrics(self, metrics: Any) -> Any:
        """Serialize metrics to a dictionary."""
        if isinstance(metrics, (RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics)):
            data: Dict[str, Any] = {}
            for field in metrics.__dataclass_fields__:
                value = getattr(metrics, field)
                if isinstance(value, datetime):
                    data[field] = self._serialize_datetime(value)
                elif isinstance(value, (RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics)):
                    data[field] = self._serialize_metrics(value)
                elif isinstance(value, list):
                    data[field] = [self._serialize_metrics(item) for item in value]
                else:
                    data[field] = value
            return data
        return metrics
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics."""
        self.metrics['requests'].append(self._serialize_metrics(metrics))
    
    def record_step(self, metrics: StepMetrics) -> None:
        """Record step metrics."""
        self.metrics['steps'].append(self._serialize_metrics(metrics))
    
    def record_phase(self, metrics: PhaseMetrics) -> None:
        """Record phase metrics."""
        self.metrics['phases'].append(self._serialize_metrics(metrics))
    
    def record_playbook(self, metrics: PlaybookMetrics) -> None:
        """Record playbook metrics."""
        self.metrics['playbook'] = self._serialize_metrics(metrics)
    
    def finalize(self) -> None:
        """Save all collected metrics to the JSON file."""
        # Ensure the output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the metrics to the file
        with open(self.output_file, 'w') as f:
            json.dump(self.metrics, f, indent=2) 