![restbook-logo2](https://github.com/user-attachments/assets/1f22790b-8829-4cae-a33f-3d499cfc1ea3)

# RestBook

RestBook is a powerful, declarative tool for executing complex REST API workflows using YAML playbooks. It supports parallel execution, variable storage, response processing with JQ, and templating with Jinja2.

## What Makes RestBook Different

RestBook is not a tool to test your APIs—it's an orchestration tool for complex API workflows. While tools like Postman, Insomnia, or curl focus on individual requests or basic testing, RestBook is distinct in that it's designed to orchestrate complex API workflows (including authentication, error handling, incremental execution, and variable storage) entirely through declarative YAML playbooks.

This combination of features—especially the incremental execution, OAuth2 integrations, and recording/playbook generation—sets it apart from other API tools. RestBook excels at:

- **Complex Workflow Orchestration**: Chain multiple API calls with sophisticated logic
- **Incremental Execution**: Resume from the last successful step after failures
- **State Management**: Maintain and transform state between requests
- **Enterprise Integration**: Advanced auth flows and security features

## Features

- **YAML-Based Playbooks**: Define your API workflows in simple, readable YAML files
- **Session Management**: Reuse authenticated sessions across requests with support for environment variables
- **Parallel Execution**: Run steps and iterations concurrently for improved performance
- **Response Processing**: Extract and store data from responses using JQ queries
- **Variable System**: Store and reuse data between steps with Jinja2 templating
- **Flexible Configuration**: Customize retry policies, SSL verification, and error handling
- **Comprehensive Logging**: Detailed logging of requests, responses, and operations
- **CI/CD Ready**: Support for environment variables in configuration

## Installation

```bash
pip install restbook  # Package name may vary
```

## Quick Start

Here's a simple example of a RestBook playbook:

```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"  # Use environment variable

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

### Sessions

Sessions define the base configuration for API connections, including authentication:

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
    headers:
      Custom-Header: "value"
    verify_ssl: true
```

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

### Environment Variables

RestBook supports environment variables in session configuration, making it ideal for CI/CD pipelines:

```yaml
sessions:
  production_api:
    base_url: "{{ env.API_BASE_URL }}"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"
    headers:
      Api-Key: "{{ env.API_KEY }}"
```

Environment variables can be used in:
- Base URLs
- Authentication credentials
- Custom headers
- Any other string field in the session configuration

### Session Management

Sessions maintain authentication and cookies across requests:

```yaml
sessions:
  my_session:
    base_url: "https://api.example.com"
    auth:
      type: "basic"
      credentials:
        username: "{{ env.USERNAME }}"
        password: "{{ env.PASSWORD }}"
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

You can also append to list variables across multiple steps:

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

This is useful for collecting data across paginated API responses or from different endpoints for later processing.

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

### Incremental Execution

RestBook supports incremental execution, allowing playbooks to resume from the last successful step after a failure:

```yaml
incremental:
  enabled: true
  store: file
  file_path: "/path/to/checkpoints"
```

With incremental execution:
- Checkpoints are saved after each successful step
- Playbooks can resume execution from the last checkpoint
- All variables and state are preserved
- You can disable resume with the `--no-resume` flag

This is particularly valuable for long-running workflows where a failure halfway through would otherwise require starting from the beginning.

## Using in CI/CD

To use RestBook in your CI/CD pipeline:

1. Install RestBook in your CI environment
2. Set up your environment variables in your CI platform
3. Create your playbook YAML file with environment variable references
4. Run the playbook using the RestBook CLI

Example GitHub Actions workflow:

```yaml
name: API Integration
on: [push]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install RestBook
        run: pip install restbook
      - name: Run Integration
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
          API_BASE_URL: "https://api.example.com"
        run: restbook run playbook.yml
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[License Type] - MIT
