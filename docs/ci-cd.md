---
layout: default
title: CI/CD Integration
nav_order: 5
description: "Learn how to integrate RestBook with your CI/CD pipelines"
permalink: /ci-cd/
---

# CI/CD Integration

RestBook is designed to work seamlessly in CI/CD environments, making it easy to automate API workflows as part of your pipeline.

## GitHub Actions

Here's an example of how to use RestBook in a GitHub Actions workflow:

{% raw %}
```yaml
name: API Integration
on: [push]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install RestBook
        run: pip install restbook
      
      - name: Run Integration
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
          API_BASE_URL: "https://api.example.com"
        run: restbook run playbook.yml
```
{% endraw %}

## Environment Variables

RestBook works well with CI/CD environment variables and secrets:

### GitHub Actions Secrets
```yaml
env:
  API_TOKEN: ${{ secrets.API_TOKEN }}
  API_KEY: ${{ secrets.API_KEY }}
  CLIENT_ID: ${{ secrets.CLIENT_ID }}
  CLIENT_SECRET: ${{ secrets.CLIENT_SECRET }}
```

### GitLab CI Variables
```yaml
variables:
  API_TOKEN: ${API_TOKEN}
  API_KEY: ${API_KEY}
  CLIENT_ID: ${CLIENT_ID}
  CLIENT_SECRET: ${CLIENT_SECRET}
```

## Best Practices

### 1. Environment-Specific Configuration

Use environment variables to configure different environments:

{% raw %}
```yaml
sessions:
  api:
    base_url: "{{ env.API_BASE_URL }}"
    auth:
      type: "bearer"
      credentials:
        token: "{{ env.API_TOKEN }}"
```
{% endraw %}

### 2. Parallel Execution

Use parallel execution to speed up workflows:

```yaml
phases:
  - name: "Parallel Phase"
    parallel: true
    steps:
      - session: "api"
        request: # ...
```

## Example Workflows

### Full API Integration Pipeline

{% raw %}
```yaml
name: Full API Integration
on: [push]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install RestBook
        run: pip install restbook
      
      - name: Run Integration
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
          API_BASE_URL: ${{ secrets.API_BASE_URL }}
          ENVIRONMENT: ${{ github.ref_name }}
        run: |
          restbook run playbook.yml
          restbook run validation.yml
```
{% endraw %}

### Multi-Environment Deployment

{% raw %}
```yaml
name: Multi-Environment Deployment
on:
  push:
    branches: [main, staging, production]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install RestBook
        run: pip install restbook
      
      - name: Deploy to Environment
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
          ENVIRONMENT: ${{ github.ref_name }}
        run: restbook run deploy.yml
```
{% endraw %}

## Next Steps

- Check out [Examples](./examples.md) for more use cases
- Learn about [Features](./features.md) in detail 