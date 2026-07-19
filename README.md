# funaithings 🧪 *(archived — where it all started)*

> **Status: deprecated / archived.** This is the rough terminal experiment that kicked off
> everything else I've built. It still runs, but it's no longer maintained — its two good
> ideas grew up into separate, better projects (see [Legacy](#legacy) below).

A terminal-based **multi-agent "swarm"** playground. It spins up a set of AI personas
(agents with roles, loaded from `config/personas.json`), lets a `SwarmBrain` make them reason
together, and renders the whole thing live in a Rich terminal UI — including a
`demo_spectacle.py` "moving spectacle" diagnostic view. Under the hood it runs on a homegrown
LLM router (`ExtremeRouter`) that juggles multiple free-tier providers so it doesn't run out
of quota.

## Legacy

This project is the ancestor of two things I now maintain properly:

- **The router idea** → grew into **[flexrouter](https://github.com/notnotnotnoone)** — a real,
  standalone LLM router library with tiers, budgets, rate-limit awareness, and a dashboard.
- **The multi-agent-debate idea** → grew into **agora**, a polished web app where several
  models argue out a moral dilemma.

I'm keeping funaithings public as honest history, not as something to use. If you want the
mature versions, go to the projects above.

## Running it (if you really want to)

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
cp .env.example .env      # then fill in your own API keys
python main.py            # the swarm
python demo_spectacle.py  # the diagnostic "spectacle" demo
```

Configuration lives in `config/` (`router.ini`, `personas.json`) — see `CONFIGURATION.md`.
API keys are read from environment variables (`.env`), never hardcoded.

## License

[MIT](./LICENSE) © 2026 notnotnotnoone
