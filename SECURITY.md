# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | ✅ Current          |
| < 0.2   | ❌ End of life      |

## Reporting a Vulnerability

If you discover a security vulnerability in MCP-Maker, **please do not open a public issue.**

Instead, report it privately:

1. **Email:** [mrali.hassan997@gmail.com](mailto:mrali.hassan997@gmail.com)
2. **Subject:** `[SECURITY] MCP-Maker vulnerability report`

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within **48 hours** acknowledging your report. We aim to release a patch within **7 days** for critical issues.

## Scope

The following are in scope for security reports:

- **Generated server code** — SQL injection, credential leaks, auth bypass
- **CLI tool** — command injection, path traversal, credential exposure
- **Template engine** — Jinja2 injection, unsafe rendering
- **Connectors** — credential handling, API token exposure in logs/errors

The following are **out of scope**:

- Vulnerabilities in upstream dependencies (report to their maintainers)
- Issues requiring physical access to the machine
- Social engineering attacks

## Security Best Practices

When using MCP-Maker in production:

1. **Always set `DATABASE_URL` via environment variables**, never in source code
2. **Use `--auth api-key`** to gate access to generated servers
3. **Keep SSL enabled** (`--no-ssl` is for local development only)
4. **Review generated code** before deploying to production
5. **Use `--ops read`** for read-only access when write operations aren't needed
