# Project Configuration Guide

This guide explains how to manage your project's configuration, including infrastructure settings (`router.ini`) and swarm data (`personas.json`).

---

## 1. Overview
This project uses a modular configuration system:
*   **Infrastructure (`config/router.ini`)**: Controls API providers, routing priorities, and rate-limiting.
*   **Agent Data (`config/*.json`)**: Defines the "intelligence" and persona definitions for your agent swarm.

---

## 2. Infrastructure: `config/router.ini`

### Basic Settings
Each section represents a **Provider**.

```ini
[ProviderName]
base_url = https://api.provider.com/v1
api_key_env = PROVIDER_API_KEY
rate_limit = 30
tpm_limit = 60000
price_prompt = 0.0001
price_completion = 0.0002
models = model_name:tier[:limit], ...
```

*   **`api_key_env`**: The **name** of the environment variable (e.g., `OPENAI_API_KEY`) containing the secret key. Never store actual keys in this file.

### Model Mapping & Rate Limiting
The system enforces rate limits **independently for each model**. Each model tracks its own usage, meaning one model's traffic will not affect another model's quota, even if they share the same provider.

**Syntax**: `model_name:tier[:limit]`

*   **Standard**: `llama3.1-8b:SUPERLOW` (Inherits provider-wide `rate_limit`)
*   **Specific**: `llama3.1-8b:SUPERLOW:20` (Hard limit of 20 RPM for this model only)
*   **Window**: Rate limits use a rolling 60-second tracking window per model.

### Model Tiers
Tiers determine routing priority:
*   `SUPERLOW`, `LOW`, `MEDIUM`, `HIGH`, `EXTREME`, `SYNTHESIS`

They influence routing priority and fallback selection.

### Hot Reload Behavior
Changes are detected automatically at runtime.
*   **Reloadable**: rate limits, model mappings, pricing, provider URLs.
*   **Non-Reloadable**: Internal router architecture changes, new environment variables.

### Example Configuration
```ini
[OpenRouter]
base_url = https://openrouter.ai/api/v1
api_key_env = OPENROUTER_API_KEY
rate_limit = 60
tpm_limit = 120000
price_prompt = 0.000002
price_completion = 0.000006
models = mistralai/mistral-small:LOW:40, meta-llama/llama-3.1-70b:HIGH:20
```

---

## 3. Persona JSON Files

### Schema Rules
Required fields for agents in `personas.json` and `extra_personas.json`:
*   `id`: Unique identifier (e.g., `A-01`).
*   `role`: Professional title.
*   `description`: Brief behavioral overview.

*Additional fields are ignored unless explicitly supported by the loader.*

---

## 4. Routing & Fallback Logic

If a model exceeds its specific RPM/TPM limit:
1.  The router attempts another eligible model in the same tier.
2.  If unavailable, it considers fallback providers.
3.  If no route is found, the request is rejected with a `PAUSE` signal.

**Independent Model Quotas Benefit**:
*   No cross-model starvation.
*   Better throughput balancing.
*   Safer multi-model orchestration.

---

## 5. Troubleshooting

*   **Missing Variables**: Ensure all `api_key_env` values are defined in your `.env` file.
*   **Invalid Syntax**: Check for trailing commas in JSON or missing colons in model strings.
*   **Duplicate IDs**: Ensure `id` fields in your JSON files are globally unique.
*   **Mismatched Tiers**: Only use valid `tiers_order` values in `router.ini`.

---

## 6. Security Notes
Always store your secrets in a `.env` file in the root directory. Ensure `.env` is listed in your `.gitignore` to prevent accidental commits.
