# Security and privacy release policy

This branch intentionally excludes populated environment files, credentials, service tokens, raw Docker/service logs, PostgreSQL/SQLite database exports, model-response caches, and local volumes. Only generated agent posts and blinded judge contexts needed for the reported analyses are included or allowlisted.

Agent posts are machine-generated and use pseudonymous run/model labels. They can nevertheless contain invented personal details, URLs, or offensive claims. Treat the corpus as untrusted text: do not execute embedded code or follow links automatically, and review it before downstream publication.

The Reddit comparison does not store or redistribute Reddit submissions. Its published JSON contains aggregate and per-pair numeric metrics only. Anyone independently processing the source archive remains responsible for the source license, platform terms, deletion requests, and current research-ethics requirements.

Hosted judge/model reproduction requires a local `OPENROUTER_API_KEY`. Keep it in an ignored `.env` or the process environment. The included judge script reads the key but never prints it. Provider aliases, model behavior, pricing, and retention policies may change.
