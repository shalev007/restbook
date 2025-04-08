---
layout: default
title: Metrics Collection
nav_order: 3
parent: Documentation
description: "Learn how to collect and analyze metrics from your RestBook playbooks"
permalink: /metrics/
---

# Metrics Collection

RestBook provides a comprehensive metrics collection system that allows you to monitor and analyze the performance and behavior of your playbooks. This guide will help you understand how to enable, configure, and analyze metrics in your playbooks.

## Overview

The metrics system collects data at multiple levels:

1. **Request Metrics**: Individual HTTP request performance
2. **Step Metrics**: Execution metrics for each step
3. **Phase Metrics**: Aggregated metrics for each phase
4. **Playbook Metrics**: Overall playbook execution metrics

## Configuration

To enable metrics collection, add a `metrics` section to your playbook configuration:

```yaml
metrics:
  enabled: true
  collectors:
    json:
      output_file: "metrics_output.json"
    prometheus:
      port: 9090
    console:
      enabled: true
```

## Metrics Collectors

RestBook supports three types of metrics collectors:

1. **JSON Collector**: Writes metrics to a JSON file
2. **Prometheus Collector**: Exposes metrics in Prometheus format
3. **Console Collector**: Prints metrics to the console

## Metrics Data Structure

### Request Metrics

```json
{
  "method": "GET",
  "endpoint": "/api/users",
  "start_time": "2024-03-15T10:00:00Z",
  "end_time": "2024-03-15T10:00:01Z",
  "status_code": 200,
  "duration_ms": 1000.0,
  "success": true,
  "request_size_bytes": 1024,
  "response_size_bytes": 2048,
  "memory_usage_bytes": 1048576,
  "cpu_percent": 5.2,
  "step": 1,
  "phase": "fetch-users"
}
```

### Step Metrics

```json
{
  "session": "api",
  "request": { ... },
  "retry_count": 0,
  "store_vars": ["users", "posts"],
  "variable_sizes": {
    "users": 1024,
    "posts": 2048
  },
  "memory_usage_bytes": 2097152,
  "cpu_percent": 8.5
}
```

### Phase Metrics

```json
{
  "name": "fetch-users",
  "start_time": "2024-03-15T10:00:00Z",
  "end_time": "2024-03-15T10:00:10Z",
  "duration_ms": 10000.0,
  "steps": [ ... ],
  "parallel": true,
  "memory_usage_bytes": 4194304,
  "cpu_percent": 12.3
}
```

### Playbook Metrics

```json
{
  "start_time": "2024-03-15T10:00:00Z",
  "end_time": "2024-03-15T10:01:00Z",
  "duration_ms": 60000.0,
  "phases": [ ... ],
  "total_requests": 100,
  "successful_requests": 95,
  "failed_requests": 5,
  "total_duration_ms": 60000.0,
  "peak_memory_usage_bytes": 8388608,
  "average_cpu_percent": 15.7,
  "total_request_size_bytes": 1048576,
  "total_response_size_bytes": 2097152,
  "total_variable_size_bytes": 3145728
}
```

## Resource Metrics

> **⚠️ Important Notice**: The CPU and memory metrics are currently experimental and may not provide accurate measurements in all environments. We are working on improving these metrics in future releases. For production monitoring, we recommend using external system monitoring tools to track resource usage.

RestBook collects detailed resource usage metrics at all levels of execution:

### Memory Usage
- ~~All memory measurements are in bytes~~
- ~~Tracks memory usage during requests, steps, and phases~~
- ~~Records peak memory usage for the entire playbook~~
- Measures memory impact of stored variables (through variable size tracking)

### CPU Usage
- ~~CPU usage is measured as a percentage (0-100)~~
- ~~All CPU measurements are guaranteed to be non-negative~~
- ~~Tracks CPU usage during requests, steps, and phases~~
- ~~Calculates average CPU usage for the playbook~~

### Data Size Metrics
- Request and response sizes are measured in bytes
- Tracks size of all request payloads
- Tracks size of all response payloads
- Measures size of stored variables

## Example Playbook

See `examples/example-metrics-playbook.yml` for a complete example of metrics configuration and usage.

## Analyzing Metrics

### JSON Metrics

```bash
# Get total memory usage
jq '.peak_memory_usage_bytes' metrics_output.json

# Get average CPU usage
jq '.average_cpu_percent' metrics_output.json

# Get total data transferred
jq '.total_request_size_bytes + .total_response_size_bytes' metrics_output.json
```

### Prometheus Metrics

```promql
# Memory usage over time
restbook_memory_usage_bytes

# CPU usage over time
restbook_cpu_percent

# Request/response sizes
restbook_request_size_bytes
restbook_response_size_bytes
```

### Console Output

The console collector provides real-time metrics during playbook execution:

```
[10:00:00] Request: GET /api/users
  Duration: 1000ms
  Memory: 1048576 bytes
  CPU: 5.2%
  Request Size: 1024 bytes
  Response Size: 2048 bytes
```

## Best Practices

1. **Enable Metrics**: Always enable metrics collection in production environments to monitor playbook performance.

2. **Choose Collectors**: Use JSON collector for detailed analysis, Prometheus for monitoring, and Console for debugging.

3. **Monitor Resource Usage**: Watch for:
   - High memory usage that might indicate memory leaks
   - Sustained high CPU usage that might impact system performance
   - Large request/response sizes that might impact network performance

4. **Set Alerts**: Configure alerts based on:
   - Memory usage thresholds
   - CPU usage thresholds
   - Request/response size limits
   - Error rates

5. **Analyze Trends**: Use historical metrics to:
   - Identify performance degradation
   - Optimize resource usage
   - Plan capacity requirements

### Context Tracking

RestBook uses a hierarchical context tracking system to properly associate metrics with their execution context:

1. **Playbook Context**: Each playbook execution has a unique context ID
2. **Phase Context**: Each phase has a unique context ID and references its parent playbook
3. **Step Context**: Each step has a unique context ID and references its parent phase
4. **Request Context**: Each request has a unique context ID and references its parent step and phase

This system ensures that:
- Multiple requests to the same endpoint are properly tracked
- Metrics can be aggregated at any level (playbook, phase, step)
- The execution hierarchy is preserved in the metrics data

For example, when executing parallel requests to the same endpoint:
```yaml
phases:
  - name: "Create Posts"
    steps:
      - session: api
        parallel: true
        iterate: "user_id in users"
        request:
          method: POST
          endpoint: "/posts"
```

Each request will have a unique context ID based on its step context, allowing proper tracking of metrics for each individual request. 