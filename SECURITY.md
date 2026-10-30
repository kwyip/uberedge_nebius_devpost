# Security

Do not commit API keys, passwords, private endpoints, production database files, or deployment credentials.

The public API returns configuration booleans and generic service labels only. Council traces may include provider names, model names, latency, token counts, statuses, run IDs, Tavily result counts, and public source URLs. They must never include authorization headers or secret values.

Report a suspected vulnerability privately to the repository owner rather than opening a public issue containing exploitable details.
