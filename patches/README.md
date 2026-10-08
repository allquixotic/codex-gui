# Stable Codex patches

Base: `rust-v0.162.0`, commit `c1382380de69521303b416720a52f42d51af6248`.

Stable 0.162.0 contains Astra Ultrafast and catalog-aware core request tier
selection (#50472). The previous provider/core patches are removed.

`bedrock-sol-ultrafast.patch` is the model-provider catalog hunk (including its
provider assertion) from upstream commit
[87be737](https://github.com/openai/codex/commit/87be737b664508d48402f08f57d09aba48e5f17a)
(#51794), which is not in this stable release. It advertises opt-in Ultrafast for
`openai.gpt-6.1-sol`, `global.openai.gpt-6.1-sol` and `us.openai.gpt-6.1-sol`.
The pending-steer patches below are separate from Bedrock support. Runtime
helper entrypoints stay pristine.

`python scripts/upstream.py prepare` applies each patch to an ignored copy of its crate,
verifies the stable base, and generates standalone manifests with dependencies
pinned to that same release. Cargo source overrides statically embed these
three patched crates. The inventory is `upstream.json`.

The V5 provider and actual HTTP-body regressions cover Astra and Sol across
Mantle and both Runtime IDs, including Standard and rejection of unadvertised
Fast/Flex tiers and custom catalog preservation. Remove this patch, inventory
entry and Cargo override when a stable release contains #51794 and those tests
pass. Never move the product dependency to main to obtain the change.

## Pending steering edits

`pending-steer-core.patch` adds one operation to CodexThread and its input
queue. It replaces or removes an input by client message ID while holding the
active-turn and pending-input locks used by the consumer. Input metadata is
preserved. A consumed input returns no match and cannot be rewritten.

`pending-steer-server.patch` exposes that operation through the existing queue
update/delete API using the reserved GUI ID prefix `gui-steer:`. Ordinary
queued submission IDs retain upstream behavior. Existing thread authorization,
subagent constraints and image validation still apply. There is no wire schema
fork. Unpatched remote servers reject these IDs safely; the GUI retains edits.

Both are based on stable 0.162.0. Remove them when a stable upstream exposes
atomic pending-steer editing. The Windows conversation regression covers edits,
deletions, and consumption racing the editor; consumed history stays unchanged.
