---
layout: default
title: Metrics
nav_order: 7
description: "Learn how to collect and analyze metrics from your RestBook playbooks"
permalink: /metrics/
---

# Metrics

RestBook provides a comprehensive metrics collection system that allows you to monitor and analyze the performance and behavior of your playbooks. This guide explains how to configure and use the metrics functionality.

## Overview

The metrics system collects data at multiple levels:

- **Request Metrics**: Individual API request details (duration, status code, success/failure)
- **Step Metrics**: Aggregated metrics for each step in your playbook
- **Phase Metrics**: Aggregated metrics for each phase, including parallel execution information
- **Playbook Metrics**: Overall playbook execution metrics

## Configuration

Metrics collection is configured at the playbook level using the `metrics` section:

```yaml
metrics:
  enabled: true
  collector: json  # Options: json, prometheus, console
  # Collector-specific configuration...
```

### Collector Types

RestBook supports three types of metrics collectors:

#### 1. JSON Collector

The JSON collector saves metrics to a JSON file, which is useful for debugging and CI/CD pipelines.

```yaml
metrics:
  enabled: true
  collector: json
  output_file: "metrics_output.json"
```

#### 2. Prometheus Collector

The Prometheus collector pushes metrics to a Prometheus Pushgateway, enabling integration with monitoring systems like Grafana.

```yaml
metrics:
  enabled: true
  collector: prometheus
  push_gateway: "http://localhost:9091"
  job_name: "restbook_example"
```

#### 3. Console Collector

The console collector outputs metrics to the console in real-time, which is useful for local development and debugging.

```yaml
metrics:
  enabled: true
  collector: console
  verbosity: "detailed"  # Options: basic, detailed
```

## Metrics Data Structure

### Request Metrics

```json
{
  "method": "GET",
  "endpoint": "/users",
  "start_time": "2023-06-01T12:00:00.000Z",
  "end_time": "2023-06-01T12:00:01.500Z",
  "status_code": 200,
  "duration_ms": 1500,
  "success": true,
  "error": null
}
```

### Step Metrics

```json
{
  "session": "api",
  "request": { /* RequestMetrics object */ },
  "retry_count": 0,
  "store_vars": ["users"]
}
```

### Phase Metrics

```json
{
  "name": "Fetch User Details",
  "start_time": "2023-06-01T12:00:00.000Z",
  "end_time": "2023-06-01T12:00:10.000Z",
  "duration_ms": 10000,
  "steps": [ /* Array of StepMetrics objects */ ],
  "parallel": true
}
```

### Playbook Metrics

```json
{
  "start_time": "2023-06-01T12:00:00.000Z",
  "end_time": "2023-06-01T12:00:30.000Z",
  "duration_ms": 30000,
  "phases": [ /* Array of PhaseMetrics objects */ ],
  "total_requests": 25,
  "successful_requests": 24,
  "failed_requests": 1,
  "total_duration_ms": 30000
}
```

## Example

See the [example-metrics-playbook.yml](../examples/example-metrics-playbook.yml) for a complete example of how to configure and use metrics in your playbooks.

## Analyzing Metrics

### JSON Metrics

You can analyze JSON metrics using standard tools like `jq`:

```bash
# Count successful requests
jq '.total_requests - .failed_requests' metrics_output.json

# Get average request duration
jq '.phases[].steps[].request.duration_ms | select(. != null) | add / length' metrics_output.json
```

### Prometheus Metrics

Prometheus metrics can be visualized using Grafana dashboards. Common metrics include:

- `restbook_request_duration_seconds`: Request duration in seconds
- `restbook_request_total`: Total number of requests
- `restbook_request_success_total`: Number of successful requests
- `restbook_request_failure_total`: Number of failed requests
- `restbook_phase_duration_seconds`: Phase duration in seconds

### Console Metrics

The console collector provides real-time feedback during playbook execution, showing:

- Request status and duration
- Step completion status
- Phase completion status
- Overall playbook progress

## Best Practices

1. **Enable metrics for all production playbooks**: This provides valuable insights into performance and reliability.

2. **Use appropriate collector types**:
   - JSON: For CI/CD pipelines and debugging
   - Prometheus: For production monitoring
   - Console: For local development

3. **Analyze metrics regularly**: Look for patterns in request durations, error rates, and retry counts to identify potential issues.

4. **Set up alerts**: Configure alerts based on metrics thresholds (e.g., high error rates, long durations) to proactively address issues.

5. **Correlate with other data**: Combine RestBook metrics with application logs and other monitoring data for comprehensive insights. 