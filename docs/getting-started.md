---
layout: default
title: Getting Started
nav_order: 2
description: "Learn how to install and get started with RestBook"
permalink: /getting-started/
---

# Getting Started with RestBook

This guide will help you get started with RestBook, from installation to your first playbook.

## Installation

Install RestBook using pip:

```bash
pip install restbook
```

## Quick Start Guide

Here's a simple example of a RestBook playbook to get you started:

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

## Basic Concepts

Before diving deeper into RestBook, let's understand the basic concepts:

### Sessions
Sessions define the base configuration for your API connections, including:
- Base URL
- Authentication settings
- Default headers
- SSL verification settings

### Phases
Phases are top-level containers for steps. They can be:
- Executed sequentially (default)
- Run in parallel
- Named for better organization

### Steps
Steps are individual API requests that can:
- Make HTTP requests (GET, POST, PUT, DELETE, PATCH)
- Store response data
- Iterate over collections
- Run in parallel
- Handle errors and retries

### Variables and Templates
RestBook supports:
- Environment variables
- Response data storage
- Jinja2 templating
- JQ queries for data extraction

## Next Steps

Now that you have the basics, you can:
1. Learn more about [Playbook Structure](./playbook-structure.md)
2. Explore [Features](./features.md) in detail
3. Check out [Examples](./examples.md) for common use cases
4. Set up [CI/CD Integration](./ci-cd.md) for your workflows 