---
layout: default
title: Playbook Structure
nav_order: 1
parent: Documentation
description: "Understand the structure and components of RestBook playbooks"
permalink: /playbook-structure/
---

# Playbook Structure

This guide explains the structure and components of RestBook playbooks. A playbook is a YAML file that defines your API workflow, including sessions, phases, and steps.

## Sessions

Sessions define the base configuration for API connections, including authentication and default settings:
{% raw %}
```yaml
sessions:
  my_api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"  # none, bearer, basic, oauth2
      credentials:
        # Bearer token auth
        token: "{{ env.MY_API_TOKEN }}"
        
        # Or Basic auth
        username: "{{ env.API_USERNAME }}"
        password: "{{ env.API_PASSWORD }}"
        
        # Or OAuth2
        client_id: "{{ env.CLIENT_ID }}"
        client_secret: "{{ env.CLIENT_SECRET }}"
        token_url: "https://auth.example.com/token"
        scopes:
          - "read"
          - "write"
    retry:
      max_retries: 2
      backoff_factor: 1.0
      max_delay: 10
    circuit_breaker:
      threshold: 2
      reset: 10
      jitter: 0.0
    validate_ssl: true
    timeout: 30
```
{% endraw %}
### Session Configuration Options

- `base_url`: The base URL for all requests in this session
- `auth`: Authentication configuration
  - `type`: Authentication type (none, bearer, basic, oauth2)
  - `credentials`: Authentication credentials
- `retry`: Default retry configuration for all requests in this session
  - `max_retries`: Maximum number of retries (default: 2)
  - `backoff_factor`: Exponential backoff factor (default: 1.0)
  - `max_delay`: Maximum delay between retries
- `circuit_breaker`: Default circuit breaker configuration
  - `threshold`: Number of failures before opening the circuit (default: 2)
  - `reset`: Seconds to wait before resetting circuit breaker (default: 10)
  - `jitter`: Random jitter factor (0.0 to 1.0) to add to reset time (default: 0.0)
- `validate_ssl`: SSL validation setting (default: true)
- `timeout`: Request timeout in seconds (default: 30)

All session-level configurations can be overridden at the step level. When a step specifies a configuration, it takes precedence over the session's configuration. For example:

```yaml
sessions:
  my_api:
    base_url: "https://api.example.com"
    retry:
      max_retries: 3
      backoff_factor: 2.0
      max_delay: 60
    circuit_breaker:
      threshold: 2
      reset: 10
    validate_ssl: true
    timeout: 30

steps:
  - session: "my_api"
    request:
      method: GET
      endpoint: "/users"
    retry:
      max_retries: 5  # Overrides session's max_retries
    # Other retry settings will use session's values
    timeout: 60  # Overrides session's timeout
    # validate_ssl will use session's value
```

## Phases

Phases are top-level containers for steps. They can be executed sequentially or in parallel:

```yaml
phases:
  - name: "Phase Name"
    parallel: false  # Optional, defaults to false
    steps:
      # ... steps
```

### Phase Configuration Options

- `name`: Descriptive name for the phase
- `parallel`: Whether steps in this phase should run in parallel
- `steps`: List of steps to execute

## Steps

Steps define individual API requests and their configuration:

```yaml
steps:
  - session: "session_name"
    iterate: "item in collection"  # Optional
    parallel: true  # Optional, for parallel iterations
    request:
      method: GET  # GET, POST, PUT, DELETE, PATCH
      endpoint: "/api/endpoint"
      data: {}  # Optional request body
      params: {}  # Optional query parameters
      headers: {}  # Optional headers
    store:
      - var: "variable_name"
        jq: ".path.to.data"  # JQ query for response data
    retry:
      max_retries: 3
      backoff_factor: 1.0
      max_delay: 10
      circuit_breaker:
        threshold: 2
        reset: 5
        jitter: 0.1
    validate_ssl: true
    timeout: 30
    on_error: abort  # abort or ignore
```

### Step Configuration Options

#### Basic Options
- `session`: Name of the session to use
- `iterate`: Optional iteration over a collection
- `parallel`: Whether iterations should run in parallel

#### Request Options
- `method`: HTTP method (GET, POST, PUT, DELETE, PATCH)
- `endpoint`: API endpoint path
- `data`: Request body (for POST, PUT, PATCH)
- `params`: Query parameters
- `headers`: Request-specific headers

#### Response Processing
- `store`: List of variables to store from response
  - `var`: Variable name
  - `jq`: JQ query for data extraction

#### Error Handling
- `retry`: Retry configuration
  - `max_retries`: Maximum number of retries
  - `backoff_factor`: Exponential backoff factor
  - `max_delay`: Maximum delay between retries
  - `circuit_breaker`: Circuit breaker configuration
- `validate_ssl`: SSL validation setting
- `timeout`: Request timeout in seconds
- `on_error`: Error handling strategy (abort or ignore)

## Variable Storage and Templates

RestBook supports storing and using data between steps:
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

### Appending to Lists

You can append to list variables across multiple steps:
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
## Next Steps

- Learn about [Features](./features.md) in detail
- Check out [Examples](./examples.md) for common use cases
- Set up [CI/CD Integration](./ci-cd.md) for your workflows 