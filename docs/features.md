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

## Next Steps

- Check out [Examples](./examples.md) for common use cases
- Set up [CI/CD Integration](./ci-cd.md) for your workflows 