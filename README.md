# RestBook

RestBook is a powerful, declarative tool for executing complex REST API workflows using YAML playbooks. It supports parallel execution, variable storage, response processing with JQ, and templating with Jinja2.

## Features

- **YAML-Based Playbooks**: Define your API workflows in simple, readable YAML files
- **Session Management**: Reuse authenticated sessions across requests
- **Parallel Execution**: Run steps and iterations concurrently for improved performance
- **Response Processing**: Extract and store data from responses using JQ queries
- **Variable System**: Store and reuse data between steps with Jinja2 templating
- **Flexible Configuration**: Customize retry policies, SSL verification, and error handling
- **Comprehensive Logging**: Detailed logging of requests, responses, and operations

## Installation

```bash
pip install restbook  # Package name may vary
```

## Quick Start

Here's a simple example of a RestBook playbook:

```yaml
phases:
  - name: "Fetch Users"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/users"
          params:
            limit: 10
        store:
          - var: "users"
            jq: "."

  - name: "Process Users"
    steps:
      - session: "api"
        iterate: "user in users"
        parallel: true
        request:
          method: GET
          endpoint: "/users/{{ user.id }}/details"
        store:
          - var: "user_{{ user.id }}_details"
            jq: "."
```

## Playbook Structure

### Phases

Phases are top-level containers for steps. They can be executed sequentially or in parallel:

```yaml
phases:
  - name: "Phase Name"
    parallel: false  # Optional, defaults to false
    steps:
      # ... steps
```

### Steps

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
      timeout: 10
    validate_ssl: true
    on_error: abort  # abort or ignore
```

## Features in Detail

### Session Management

Sessions maintain authentication and cookies across requests:

```yaml
- session: "my_session"
  request:
    method: POST
    endpoint: "/auth"
    data:
      username: "user"
      password: "pass"
```

### Parallel Execution

Execute steps or iterations concurrently:

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

### Variable Storage and Templates

Store and use response data with JQ and Jinja2:

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

### Error Handling

Configure how errors are handled:

```yaml
steps:
  - session: "api"
    request:
      method: GET
      endpoint: "/users"
    retry:
      max_retries: 3
      backoff_factor: 1.0
      timeout: 10
    on_error: ignore  # Continue on error
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[License Type] - See LICENSE file for details
