---
layout: default
title: Features
nav_order: 4
description: "Explore RestBook's powerful features for API workflow automation"
permalink: /features/
---

# Features

RestBook comes with a powerful set of features designed to make API workflow automation simple and efficient.

## Environment Variables

RestBook supports environment variable templating throughout the playbook. You can access environment variables using the `env` namespace:

{% raw %}
```yaml
# In session configuration
sessions:
  api:
    base_url: "{{ env.API_BASE_URL }}"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

# In request data
steps:
  - session: "api"
    request:
      method: POST
      endpoint: "/users"
      data:
        api_key: "{{ env.API_KEY }}"
        environment: "{{ env.DEPLOY_ENV }}"

# In request parameters
steps:
  - session: "api"
    request:
      method: GET
      endpoint: "/search"
      params:
        api_version: "{{ env.API_VERSION }}"
```
{% endraw %}

Environment variables are loaded from:
1. System environment variables
2. CI/CD environment variables

## Session Management

RestBook provides robust session management capabilities:

- **Authentication Types**: Support for various authentication methods including Bearer tokens, Basic auth, and OAuth2
- **Session Reuse**: Maintain authentication state across requests

## Parallel Execution

Run steps and iterations concurrently for improved performance:

```yaml
# Parallel phase execution
phases:
  - name: "Parallel Phase"
    parallel: true
    steps:
      - session: "api"
        request: # ...

# Parallel iteration execution
steps:
  - session: "api"
    iterate: "item in items"
    parallel: true
    request: # ...
```

## Variable Storage and Templates

Store and use data between steps with powerful templating:

{% raw %}
```yaml
steps:
  - session: "api"
    request:
      method: GET
      endpoint: "/users"
    store:
      - var: "users"
        jq: ".[]"  # Store all users

  - session: "api"
    iterate: "user in users"
    request:
      method: POST
      endpoint: "/users/{{ user.id }}/process"
      data:
        name: "{{ user.name }}"
        email: "{{ user.email }}"
```
{% endraw %}

### List Appending

Append to list variables across multiple steps:

{% raw %}
```yaml
steps:
  - session: "api"
    request:
      method: GET
      endpoint: "/users/page/1"
    store:
      - var: "all_users"
        jq: ".users"
        append: true  # Creates a new list

  - session: "api"
    request:
      method: GET
      endpoint: "/users/page/2"
    store:
      - var: "all_users"
        jq: ".users"
        append: true  # Appends to existing list
```
{% endraw %}

## Error Handling and Retries

Configure robust error handling and retry policies:

```yaml
steps:
  - session: "api"
    request:
      method: GET
      endpoint: "/users"
    retry:
      max_retries: 3
      backoff_factor: 1.0
      max_delay: 10
      circuit_breaker:
        threshold: 2
        reset: 5
        jitter: 0.1
    timeout: 30
    on_error: ignore  # Continue on error
```

Features include:
- Exponential backoff with configurable factor
- Maximum delay cap between retries
- Circuit breaker pattern to prevent cascading failures
- Random jitter to prevent thundering herd problems
- Configurable request timeout per step
- Error handling strategies (abort or ignore)

## Incremental Execution

Resume workflows after failures with incremental execution:

```yaml
incremental:
  enabled: true
  store: file
  file_path: "/path/to/checkpoints"
```

Benefits:
- Checkpoints saved after each successful step
- Resume execution from last checkpoint
- Preserve variables and state
- Disable resume with `--no-resume` flag

## CI/CD Integration

RestBook is designed to work seamlessly in CI/CD environments:

- Environment variable support for secrets
- Configurable logging levels
- Exit codes for pipeline integration
- Checkpoint support for long-running workflows

## Resilient HTTP Client

RestBook includes a resilient HTTP client that handles retries, circuit breaking, and rate limiting. This ensures that your API requests are reliable even in the face of transient failures.

### Retry Configuration

You can configure retry behavior at both the session and step levels:

```yaml
# Session-level retry configuration
sessions:
  api:
    base_url: "https://api.example.com"
    retry:
      max_retries: 3
      backoff_factor: 1.0
      max_delay: 10

# Step-level retry configuration (overrides session defaults)
phases:
  - name: "Example Phase"
    steps:
      - session: api
        request:
          method: GET
          endpoint: "/users"
        retry:
          max_retries: 5
          backoff_factor: 0.5
```

### Circuit Breaker

Circuit breakers prevent cascading failures by temporarily stopping requests to failing services:

```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    retry:
      circuit_breaker:
        threshold: 5
        reset: 60
        jitter: 0.1
```

### Rate Limiting

Rate limiting helps prevent overwhelming APIs:

```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    retry:
      rate_limit:
        use_server_retry_delay: true
        retry_header: "Retry-After"
```

## Metrics Collection

RestBook provides a comprehensive metrics collection system that allows you to monitor and analyze the performance and behavior of your playbooks.

### Metrics Collectors

RestBook supports three types of metrics collectors:

1. **JSON Collector**: Saves metrics to a JSON file for debugging and CI/CD pipelines
2. **Prometheus Collector**: Pushes metrics to a Prometheus Pushgateway for production monitoring
3. **Console Collector**: Outputs metrics to the console in real-time for local development

### Configuration Example

```yaml
metrics:
  enabled: true
  collector: json
  output_file: "metrics_output.json"
```

For more details, see the [Metrics documentation](./metrics.md).

## Next Steps

- Check out [Examples](./examples.md) for common use cases
- Set up [CI/CD Integration](./ci-cd.md) for your workflows 