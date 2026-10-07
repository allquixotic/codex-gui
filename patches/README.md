# Stable Codex patches

Base: `rust-v0.161.0`, commit `979011409de0a60b52f179721948e65531d26144`.

`bedrock-service-tiers.patch` backports Bedrock catalog behavior already present
in development upstream: native Astra Ultrafast on Mantle and US/global Runtime,
no implicit premium default, and preservation of custom catalogs’ service tiers.
Stable 0.161.0 otherwise clears these tiers. Its existing Responses transports
already forward `service_tier`; no transport or CLI changes are needed.

The patch changes two catalog files and updates the affected provider assertion.
`python scripts/upstream.py prepare` fetches pristine stable source, applies this
patch to an ignored copy of only `codex-model-provider`, and generates a standalone
manifest with all other Codex dependencies pinned to the same stable Git commit.
Cargo’s root source override statically embeds that provider. Runtime helpers
continue to build from the pristine `.upstream/` checkout.

`v5_native_bedrock_astra_and_custom_sol_preserve_tiers` verifies real provider
catalogs, request tier filtering and future catalog-provided Sol tiers. Sol
Ultrafast is not guessed before the catalog advertises it.

Remove this patch, generated path override and inventory entry when a stable
release contains equivalent behavior and native provider tests pass. An update
fails if the patch no longer applies; review it rather than silently dropping it.

AWS announced native Astra UltraFast on September 30, 2026:
[official announcement](https://aws.amazon.com/about-aws/whats-new/2026/09/openai-gpt-6-astra-ultrafast-on-amazon-bedrock/).
The older model-card tier table has not caught up; the backport follows the
upstream implementation and the newer announcement.
