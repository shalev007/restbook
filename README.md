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
  <img src="assets/demo.gif" alt="RestBook retry and checkpointing demo" width="800" />
</p>

## 📦 Installation

```bash
pip install restbook
```

## 📖 Getting started

```yaml
incremental:
  enabled: true
  store: file
  file_path: .restbook-checkpoint.json

sessions:
  httpstat:
    base_url: https://httpstat.us

phases:
  - name: "Simulate Failure and Recover"
    steps:
      - session: httpstat
        request:
          method: GET
          endpoint: "/503?sleep=3000"
          headers:
            Accept: "application/json"
        retry:
          max_retries: 3
          backoff_factor: 1
          circuit_breaker:
            threshold: 2
            reset: 5
        on_error: abort
        timeout: 5
        store:
          - var: "flaky_result"

      - session: httpstat
        request:
          method: GET
          endpoint: "/200"
          headers:
            Accept: "application/json"
        store:
          - var: "final_result"
```

Save this as `httpstat.yml` and run it with:
```bash
restbook playbook run httpstat.yml
```

This example simulates a flaky API using [httpstat.us](https://httpstat.us), and shows how RestBook:
- retries on failure
- respects timeout settings
- applies a circuit breaker
- resumes from a checkpoint when re-run

## Documentation

For detailed documentation, including:
- Getting started guide
- Playbook structure and configuration
- Features and capabilities
- Examples and use cases
- CI/CD integration

Visit our [documentation site](https://shalev007.github.io/restbook/).

## 💬 Feedback

Have questions, ideas, or bugs to report?  
Open a [GitHub Discussion](https://github.com/shalev007/restbook/discussions) or file an [Issue](https://github.com/shalev007/restbook/issues).  
We’d love to hear what workflows you’re automating!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
