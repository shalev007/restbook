<p align="center">
  <img alt="RestBook logo" src="https://github.com/user-attachments/assets/191aa5e8-a672-492f-8596-8ae83ba23706" />
</p>

<h1 align="center">RestBook</h1>
<h3 align="center">Orchestrate long-running API workflows with YAML. No glue code. No retries-by-hand. Just results.</h3>

---

**RestBook** is an open-source CLI tool for automating complex REST API workflows.

It’s not an API testing tool. It’s a **resilient API runner** with:

✅ built-in retry logic  
✅ response storage & variable passing  
✅ templating with Jinja2  
✅ checkpointing so you can resume where it failed

If you've ever glued APIs together with bash, Python, or Postman scripts—and hit a flaky request, token expiry, or just forgot where you left off—RestBook is for you.

---

## 🚀 Features

- **📘 Declarative YAML Playbooks** – No need to write code, just describe your flow
- **🔐 Session Management** – Bearer, Basic, OAuth2, all built in
- **🔁 Retries, Rate Limits & Circuit Breakers** – Survive flaky APIs like a pro
- **🧠 Variable System** – Extract data from responses and reuse it anywhere (JQ + Jinja2)
- **🪄 Resumable Execution** – Automatically pick up from last success (incremental mode)
- **⚡️ Parallel Execution** – Run iterations concurrently if you want
- **🔍 Verbose Logging** – Great for debugging or CI/CD visibility

---

<p align="center">
  <img src="assets/demo.gif" alt="RestBook retry and checkpointing demo" width="600" />
</p>

## 📦 Installation

```bash
pip install restbook
```

## 📖 Usage

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
