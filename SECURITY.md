# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| main    | Yes       |

## Reporting a vulnerability

Please report security issues via [GitHub Security Advisories](https://github.com/joereg4/pokeAPI/security/advisories/new) (private report).

Do not open public issues for undisclosed vulnerabilities.

We will acknowledge reports within a reasonable timeframe and coordinate disclosure.

## Secrets and configuration

- Never commit `.env`, database dumps, or service account JSON files.
- Use `.env.example` as a template; bring your own keys and production values locally.
