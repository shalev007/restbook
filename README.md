<!-- ![restbook-logo2](https://github.com/user-attachments/assets/1f22790b-8829-4cae-a33f-3d499cfc1ea3) -->
<p align="center">
  <img src="https://github.com/user-attachments/assets/191aa5e8-a672-492f-8596-8ae83ba23706">
</p>
RestBook

RestBook is a powerful API request orchestration tool that lets you define and execute complex REST API workflows using declarative YAML playbooks. Unlike API testing tools, RestBook **isn't about testing** endpoints one by one—it's designed to chain together multiple API calls, manage state between requests, and even resume workflows after failures.

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
pip install restbook
```

## Quick Start

Here's a simple example using the Open Library API that you can try right away:

```yaml
sessions:
  openlibrary:
    base_url: "https://openlibrary.org"

phases:
  - name: "Book Search"
    steps:
      # Search for books by title
      - session: "openlibrary"
        request:
          method: GET
          endpoint: "/search.json"
          params:
            q: "the lord of the rings"
            limit: 5
        store:
          - var: "search_results"
            jq: ".docs"

      # Get details of first book
      - session: "openlibrary"
        request:
          method: GET
          endpoint: "{{ search_results[0].key }}.json"
        store:
          - var: "book_details"
            jq: "."
```

Save this as `books.yml` and run it with:
```bash
restbook playbook run books.yml
```

This example:
1. Searches for "The Lord of the Rings" books
2. Gets detailed information about the first result
3. Stores both the search results and book details

## Documentation

For detailed documentation, including:
- Getting started guide
- Playbook structure and configuration
- Features and capabilities
- Examples and use cases
- CI/CD integration

Visit our [documentation site](https://shalev007.github.io/restbook/).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[License Type] - MIT
