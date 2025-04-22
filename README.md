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
# Enable incremental mode so workflow progress is saved to disk
# If a step fails, it can resume from the last successful step
incremental:
  enabled: true
  store: file
  file_path: .restbook-checkpoint.json

# Define an API session pointing to httpstat.us (used to simulate flaky responses)
sessions:
  httpstat:
    base_url: https://httpstat.us

phases:
  - name: "Simulate Failure and Recover"
    steps:
      # Step 1: Simulate a failing endpoint (503)
      # - This step retries up to 3 times
      # - If it fails 2+ times, the circuit breaker trips
      - session: httpstat
        request:
          method: GET
          endpoint: "/503?sleep=3000"  # Simulate 503 after 3s delay
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
          # Will store the full JSON response for use in later steps
          # For more information on storing variables, see:
          # https://shalev007.github.io/restbook/playbook-structure/
          - var: "flaky_result" 

      # Step 2: A normal request (200 OK)
      # This step only runs if Step 1 eventually succeeds
      # (If you re-run after fixing step 1, execution will resume here)
      - session: httpstat
        request:
          method: GET
          endpoint: "/200"
          headers:
            Accept: "application/json"
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
File an [Issue](https://github.com/shalev007/restbook/issues).
We’d love to hear what workflows you’re automating!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
