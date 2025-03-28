---
layout: home
nav_order: 1
title: "RestBook Documentation"
permalink: /
---

# RestBook Documentation

Welcome to the RestBook documentation! This documentation will guide you through using RestBook, a powerful API request orchestration tool for defining and executing complex REST API workflows using declarative YAML playbooks.

## Table of Contents

1. [Getting Started](./getting-started.md)
   - Installation
   - Quick Start Guide
   - Basic Concepts

2. [Playbook Structure](./playbook-structure.md)
   - Sessions
   - Phases
   - Steps
   - Configuration Options

3. [Features](./features.md)
   - Environment Variables
   - Session Management
   - Parallel Execution
   - Variable Storage and Templates
   - Error Handling and Retries
   - Incremental Execution

4. [CI/CD Integration](./ci-cd.md)
   - GitHub Actions
   - Environment Variables
   - Best Practices

5. [Examples](./examples.md)
   - Basic Examples
   - Advanced Use Cases
   - Common Patterns

## What is RestBook?

RestBook is a powerful API request orchestration tool that lets you define and execute complex REST API workflows using declarative YAML playbooks. Unlike API testing tools, RestBook **isn't about testing** endpoints one by one—it's designed to chain together multiple API calls, manage state between requests, and even resume workflows after failures.

### Key Features

- **YAML-Based Playbooks**: Define your API workflows in simple, readable YAML files
- **Session Management**: Reuse authenticated sessions across requests with support for environment variables
- **Parallel Execution**: Run steps and iterations concurrently for improved performance
- **Response Processing**: Extract and store data from responses using JQ queries
- **Variable System**: Store and reuse data between steps with Jinja2 templating
- **Flexible Configuration**: Customize retry policies, SSL verification, and error handling
- **Comprehensive Logging**: Detailed logging of requests, responses, and operations
- **CI/CD Ready**: Support for environment variables in configuration

## Documentation Status

This documentation is currently under development. We are in the process of moving content from the README to these dedicated documentation pages. Please check back regularly for updates and new content.

## Contributing to Documentation

We welcome contributions to the documentation! If you find any issues or have suggestions for improvements, please feel free to:

1. Open an issue
2. Submit a pull request
3. Contact the maintainers

## License

This documentation is part of the RestBook project and is licensed under the MIT License. 