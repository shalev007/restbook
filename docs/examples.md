---
layout: default
title: Examples
nav_order: 6
description: "Explore practical examples of RestBook playbooks for common use cases"
permalink: /examples/
---

# Examples

This page provides practical examples of RestBook playbooks for common use cases.

## Basic Examples

### Simple API Request

A basic example of making a single API request:

{% raw %}
```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

phases:
  - name: "Fetch Data"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/users"
        store:
          - var: "users"
            jq: "."
```
{% endraw %}

### Authentication Flow

Example of handling OAuth2 authentication:

{% raw %}
```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "oauth2"
      credentials:
        client_id: "{{ env.CLIENT_ID }}"
        client_secret: "{{ env.CLIENT_SECRET }}"
        token_url: "https://auth.example.com/token"
        scopes:
          - "read"
          - "write"

phases:
  - name: "Authenticate and Fetch"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/protected-resource"
```
{% endraw %}

## Advanced Examples

### Pagination Handling

Example of handling paginated API responses:

{% raw %}
```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

phases:
  - name: "Fetch All Users"
    steps:
      # First, get the total number of pages
      - session: "api"
        request:
          method: GET
          endpoint: "/users"
          params:
            page: 1
            limit: 100
        store:
          - var: "total_pages"
            jq: ".total_pages"
          - var: "all_users"
            jq: ".users"
            append: true

      # Then iterate over the remaining pages
      - session: "api"
        iterate: "page in total_pages"
        request:
          method: GET
          endpoint: "/users"
          params:
            page: "{{ page }}"
            limit: 100
        store:
          - var: "all_users"
            jq: ".users"
            append: true
```
{% endraw %}

### Parallel Processing

Example of parallel processing of items:

{% raw %}
```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

phases:
  - name: "Process Users"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/users"
        store:
          - var: "users"
            jq: ".[]"

      - session: "api"
        iterate: "user in users"
        parallel: true
        request:
          method: POST
          endpoint: "/users/{{ user.id }}/process"
          data:
            name: "{{ user.name }}"
            email: "{{ user.email }}"
```
{% endraw %}

### Data Transformation

Example of transforming data between requests:

{% raw %}
```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

phases:
  - name: "Transform and Upload"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/source-data"
        store:
          - var: "source_data"
            jq: "."

      - session: "api"
        request:
          method: POST
          endpoint: "/target-endpoint"
          data:
            transformed_data: "{{ source_data | map(attribute='id') | list }}"
```
{% endraw %}

## Common Patterns

### Error Handling

Example of handling errors and retries:

{% raw %}
```yaml
sessions:
  api:
    base_url: "https://api.example.com"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

phases:
  - name: "Resilient Request"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/unstable-endpoint"
        retry:
          max_retries: 3
          backoff_factor: 1.0
          max_delay: 10
        timeout: 30
        on_error: ignore
```
{% endraw %}

### Environment-Specific Configuration

Example of using environment variables for different environments:

{% raw %}
```yaml
sessions:
  api:
    base_url: "{{ env.API_BASE_URL }}"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"

phases:
  - name: "Environment-Specific Request"
    steps:
      - session: "api"
        request:
          method: GET
          endpoint: "/{{ env.ENVIRONMENT }}/config"
```
{% endraw %}

## Next Steps

- Learn about [Features](./features.md) in detail
- Set up [CI/CD Integration](./ci-cd.md) for your workflows 