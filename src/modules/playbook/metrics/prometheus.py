import time
from datetime import datetime
from typing import Dict, Any
import requests
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, push_to_gateway

from .base import MetricsCollector, RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics

class PrometheusMetricsCollector(MetricsCollector):
    """Collector that sends metrics to a Prometheus push gateway."""
    
    def __init__(self, push_gateway: str, job_name: str):
        """Initialize the Prometheus collector.
        
        Args:
            push_gateway: URL of the Prometheus push gateway
            job_name: Name of the job for the metrics
        """
        self.push_gateway = push_gateway
        self.job_name = job_name
        self.registry = CollectorRegistry()
        
        # Request metrics
        self.request_duration = Histogram(
            'restbook_request_duration_seconds',
            'Duration of requests in seconds',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        self.request_total = Counter(
            'restbook_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status_code', 'success'],
            registry=self.registry
        )
        
        # Step metrics
        self.step_retries = Counter(
            'restbook_step_retries_total',
            'Total number of step retries',
            ['session'],
            registry=self.registry
        )
        
        # Phase metrics
        self.phase_duration = Histogram(
            'restbook_phase_duration_seconds',
            'Duration of phases in seconds',
            ['name', 'parallel'],
            registry=self.registry
        )
        
        # Playbook metrics
        self.playbook_duration = Gauge(
            'restbook_playbook_duration_seconds',
            'Total duration of playbook execution in seconds',
            registry=self.registry
        )
        self.playbook_requests = Gauge(
            'restbook_playbook_requests_total',
            'Total number of requests in playbook',
            registry=self.registry
        )
        self.playbook_success_rate = Gauge(
            'restbook_playbook_success_rate',
            'Success rate of requests in playbook',
            registry=self.registry
        )
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics."""
        duration = metrics.duration_ms / 1000.0  # Convert to seconds
        self.request_duration.labels(
            method=metrics.method,
            endpoint=metrics.endpoint,
            status_code=str(metrics.status_code)
        ).observe(duration)
        
        self.request_total.labels(
            method=metrics.method,
            endpoint=metrics.endpoint,
            status_code=str(metrics.status_code),
            success=str(metrics.success).lower()
        ).inc()
    
    def record_step(self, metrics: StepMetrics) -> None:
        """Record step metrics."""
        if metrics.retry_count > 0:
            self.step_retries.labels(session=metrics.session).inc(metrics.retry_count)
    
    def record_phase(self, metrics: PhaseMetrics) -> None:
        """Record phase metrics."""
        duration = metrics.duration_ms / 1000.0  # Convert to seconds
        self.phase_duration.labels(
            name=metrics.name,
            parallel=str(metrics.parallel).lower()
        ).observe(duration)
    
    def record_playbook(self, metrics: PlaybookMetrics) -> None:
        """Record playbook metrics."""
        duration = metrics.duration_ms / 1000.0  # Convert to seconds
        self.playbook_duration.set(duration)
        self.playbook_requests.set(metrics.total_requests)
        
        if metrics.total_requests > 0:
            success_rate = metrics.successful_requests / metrics.total_requests
            self.playbook_success_rate.set(success_rate)
    
    def finalize(self) -> None:
        """Push all collected metrics to the Prometheus gateway."""
        try:
            push_to_gateway(
                self.push_gateway,
                job=self.job_name,
                registry=self.registry
            )
        except requests.exceptions.RequestException as e:
            # Log the error but don't raise it to avoid disrupting the playbook execution
            print(f"Failed to push metrics to Prometheus gateway: {e}") 