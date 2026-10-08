# SPEC

## §G GOAL
Reliable conversation scrolling, Windows presentation, web/file link actions, inference speed selection; standalone stable-upstream distribution.
Broader GUI contract: repository `GUI.md`.

## §C CONSTRAINTS
- Independent allquixotic/codex-gui; Apache-2.0; latest stable Codex release only, immutable Git pin, minimal documented Codex patches.
- Native Slint 1.18.1; bound transcript memory; no idle repaint polling.
- Windows x64 ZIP and universal macOS DMG; signed distribution and GitHub attestations; no PKG.
- Never run GUI tests or launch this project's GUI on Sean's Mac unless the user explicitly says "test the GUI on this Mac"; use Windows hosts.
- Full release build only after fixes and development verification complete.
- Verify GitHub asset digest before deleting local build outputs.

## §I INTERFACES
- I.scroll: wheel, scrollbar, Jump to latest in conversation pane.
- I.paint: Windows restore, remote desktop exposure, existing redraw events.
- I.questions: synchronous server-request forms; asynchronous message forms and ordinary send/steer/queue replies.
- I.speed: provider-catalog speed picker; thread/settings/update and turn/start.
- I.summaries: sidebar titles/tooltips, resize handle; GUI-only persistent cache, ephemeral fast-model requests.
- I.distribution: Azure Authenticode, Developer ID Application, Apple notarization/stapling, GitHub artifact attestations.
- I.links: glyph hover, Copy link, Open in browser, Open file.

## §V INVARIANTS
V1: Upward user scroll ! detach tail-following before virtual row measurement; small idle scroll ! persist; automatic height/offset adjustment ! preserve live tail following.
V2: Lost Windows surface pixels ! repaint next frame without resize; idle ! schedule no polling frames.
V3: Link hit ! match shaped glyph and clipping; wrapped web/file links ! retain exact destination.
V4: Copy/tooltip ! preserve file line and resolve relative path; browser action ! encode file URL.

V5: Speed choices and actual request tiers ! follow provider catalog and feature requirements; Standard ! send explicit default; model switch ! reset unsupported tier; resume/fork ! preserve reported tier.

V6: Async questions ! show choices + free text; no send before Submit; exact message/index reply identity; turn end ! retain unanswered fields; rejected send ! preserve drafts; history replay ! deduplicate; transcript ! render question once.

V7: Purpose inference ! consume only completed user requests, never assistant/tool context; one turn ! return title + plain-text tooltip; completed request ! also satisfy initial cache-missing scheduling; ephemeral ! no listed thread/rollout; fast model failure ! retry normal model.

V8: Cache ! survive restart under resolved CODEX_HOME; any manual rename ! permanently protect title; tooltip ! remain generated; resize ! debounce ten seconds, visible rows only, cached tooltips only; title ! fit actual row without ellipses; stale result ! never replace newer context/width/name.

V9: Conversation selection ! match rendered rich/plain glyphs and UTF-8 graphemes; pointer drag + Shift/arrows ! select; Ctrl/Cmd+C and menu Copy ! selected plain text; links and markdown ! preserve; tab change ! clear; selected scene ! remain bounded.

V10: Mac native payload ! contain arm64 + x86_64 slices, verified by actual Apple tools before signing; dynamic dependencies ! Apple system libraries only. Release ! sign every native payload with expected identity + secure timestamp; Mac ! harden runtime, restrict V8 entitlements to code-mode helper; execute IPC on both slices, staple accepted app before DMG construction, accept both Apple logs, validate DMG + mounted app. Attestation ! bind final package bytes to exact successful source/workflow; temporary Mac runner ! manual main only, no GUI, remove after job.

V11: Composer Enter ! queue after entire active turn; Shift+Enter ! steer as soon as possible; Alt+Enter ! newline; explicit Queue and Steer coexist while busy; per-message intent ! survive startup and image preparation.

V12: Every sidebar tooltip ! remain fully inside conversation-pane bounds at all window sizes and pointer positions; wrapped text ! remain readable without blocking sidebar rows. Generated titles ! use natural spaced words, representative font-width budget and measured final fit without ellipses. Tooltip purpose ! directly describe work, never narrate the requester.

V13: Viewing/resuming/reading ! never advance thread activity; user/agent/tool changes ! advance it. Read state ! persist independently of activity; blue filled ! unread or running, empty ! visited/read idle, absent ! unvisited idle, warning ! needs input, red ! failure.

V14: Pending-message pencil ! edit or delete local unsent input and server queue entries; preserve non-text attachments; queue update/delete ! atomic backend boundary; consumed input ! never silently rewrite history; failed/racing edits ! retain draft.

## §T TASKS
id|status|task|cites
T1|x|Fix small-scroll tail feedback|V1,I.scroll
T2|x|Recover Windows retained surface; Auto uses CPU in RDP|V2,I.paint
T3|x|Shared link menus and hover tooltips|V3,V4,I.links
T4|x|Verify, commit, push, publish Windows package, clean outputs|V1,V2,V3,V4; GUI.md §16

T5|x|Add catalog-driven inference speed and verify upstream migration|V5,I.speed

T6|x|Extract standalone GUI, pin latest stable, verify Windows CI, commit/push/release|GUI.md §19

T7|x|Fix asynchronous question forms, reply delivery, history replay and Windows interaction verification|V6,I.questions

T8|x|Persistent background purpose summaries, manual-title protection and resizable sidebar; verify and ship next release|V7,V8,I.summaries

T9|x|Selectable user/assistant conversation text, keyboard/clipboard/context menu; verify and ship with T8|V9,I.links

T10|x|Build, sign, notarize/staple and attest 0.3.1 Windows/Mac packages; verify exact bytes, publish and remove temporary runner|V10,I.distribution; GUI.md §25

T11|.|Integrate stable 0.162.0; replace Astra patches with minimal upstream Sol catalog backport|V5
T12|.|Explicit queue/steer input and key routing, including delayed input|V11,I.questions
T13|.|Bound sidebar tooltips, readable summaries and persistent activity/read state|V7,V8,V12,V13,I.summaries
T14|.|Verify Windows software/GPU interactions; sign, attest and publish 0.4.0 for Windows/Mac|V10,I.distribution

T15|.|Edit/delete pending messages from transcript, preserving delivery intent and attachment data; verify Windows races|V14,I.questions

## §B BUGS
id|date|cause|fix
B1|2026-10-06|32px tail threshold and height-estimate callbacks pull upward scroll back to bottom|V1
B2|2026-10-06|Retained surface pixels assumed valid across Windows remote-display exposure; missing full invalidation|V2
B3|2026-10-06|Slint overwrites link hit with each wrapped-line rectangle instead of accumulating hits|V3; pinned core patch
B4|2026-10-06|Treating automatic content-y corrections as user gestures disables following during streamed row updates|V1; detach on input, never on offset alone
B5|2026-10-06|TouchArea moved fires only during dragging; stopping on hover movement without restarting loses tooltips|V3; handle pointer move and reset the stationary delay

B6|2026-10-07|Upstream protocol migration adds required fields and replaces skill PathBuf with LegacyAppPathString; clean Git merge still fails compilation|Adapt typed paths and protocol constructors; one-time migration, no new invariant

B7|2026-10-07|Development-main protocol fields and path wrappers differ from stable 0.161.0|Adapt release constructors and optional wire capabilities; one-time migration

B8|2026-10-07|Async question metadata rendered as duplicate passive markdown; no input form or ordinary reply route|V6; retained form and upstream question reply envelope

B9|2026-10-07|Extraction omitted workspace Clippy test settings; copied deny lints reject existing test assertions|Own minimal Clippy config retains test assertions and lock-guard checks; one-time migration

B10|2026-10-07|Windows Cargo checkout contains a 266-character upstream snapshot path even when TUI is not linked|Short Cargo cache path plus Git core.longpaths in Windows CI; environment constraint, no new invariant

B11|2026-10-07|Stable Bedrock catalog normalization clears all speed tiers; GUI-only fixtures miss loss of native Astra Ultrafast|V5; minimal provider catalog backport and native Mantle/Runtime/custom Sol regression

B12|2026-10-07|Nine inherited Windows test failures use Unix-only absolute paths, file URLs or displayed separators|Use upstream native test paths and platform-correct URL/display expectations; existing path invariants suffice

B13|2026-10-07|Stable core request builder independently discards all Bedrock tiers even after catalog normalization is fixed|V5; minimal core expression backport and actual HTTP-body regression for Mantle/Runtime, native/future models and unsupported tiers

B14|2026-10-07|Global/posted keys fail to activate guest native menus; GW_OWNER does not identify their owning window|V9; GetGUIThreadInfo ownership + IAccessible default action; standalone native-popup regression

B15|2026-10-07|Pristine stable workspace Cargo.lock requires resolution changes when building helpers; --locked stops packaging after GUI build|Consumer helper manifest compiles unchanged stable entrypoints with the GUI root lockfile and exact Git dependencies, retaining setup asInvoker metadata; stable pin/package invariant covers recurrence

B16|2026-10-07|Mock model catalog omitted the canonical instruction template required by stable Codex; real GUI server never became ready|Add minimal model_messages.instructions_template, parse fixture with upstream schema before Windows smoke, and retain startup logs; existing stable API migration policy covers recurrence

B17|2026-10-07|Rich shaping gave every paragraph range 0..0, clamping cursor geometry and suppressing paint; native user-text right clicks were grabbed before the parent menu; synthetic Ctrl chords used uppercase text|V9; assign rich plain-text byte ranges, explicitly open native text menus, normalize unshifted primary chords, and assert real cursor progression/round-trip plus drag/clipboard/menu behavior

B18|2026-10-07|Completed-turn summary scheduling did not mark the initial missing-cache attempt, allowing sidebar refresh to invalidate and duplicate in-flight inference|V7; share queue bookkeeping and verify exactly two purpose calls for two processed requests on software and GPU renderers

Release evidence: v0.3.0, commit e3494e5943458e61b5209ba7761bdbd02f4922e1; hosted workflow 37697823119 passed all 629 Windows tests and interaction/package gates. The exact ZIP passed software/GPU and question-form smoke tests on games, helper dispatch/startup/manifest checks, and GitHub digest verification. Mac: 638 headless tests and clean Clippy; no GUI launch. See GUI.md §24.

B19|2026-10-07|Installed Apple lipo rejects combined two-architecture -verify_arch invocation even with input-first order|V10; verify slices independently and add real clang/lipo universal-positive plus single-slice-negative headless packaging gate

B20|2026-10-07|allow-jit alone works on arm64 but signed x86_64 V8 traps during code-range setup; unsigned control passes and stable upstream already includes allow-unsigned-executable-memory|V10; reuse exact upstream helper entitlements, keep GUI unentitled, force both architectures through signed IPC/JIT regression before notarization

B21|2026-10-07|Native lzma-sys pkg-config discovery links MacPorts liblzma and adds its search path, also selecting MacPorts libiconv in the ARM GUI|V10; use supported LZMA_API_STATIC build switch, check dependencies before packaging, and test rejection with a real temporary dylib

Release evidence: v0.3.1, source 084b9f8271a61abee6e22630df91f3c8265062dc; Windows run 37721517380 passed 629 tests, interaction gates, Azure signing and attestation. The exact signed ZIP passed signatures/timestamps, helper checks, question forms and software/GPU purpose/selection tests on games. Mac run 37721517143 passed 638 headless tests, dual-architecture signed helper IPC/JIT, both Accepted notarizations, staples and Gatekeeper including the mounted app. Both online/bundled attestations and all eight GitHub upload digests verified. Temporary Mac runner deregistered and removed; no Mac GUI launched. See GUI.md §25.

B22|2026-10-08|Sidebar tooltips use native cursor-relative popups that can leave the screen and cover neighboring rows|V12; single bounded conversation-pane overlay
B23|2026-10-08|Widest-glyph character budget severely underfills normal prose; summary prompt permits compressed labels and requester narration|V12; representative width, measured final fit and explicit natural-language prompts
B24|2026-10-08|Sidebar uses generic update time and open-tab phase as activity/read status; resume writes look like conversation progress|V13; meaningful turn timestamps and separate persistent read state

B25|2026-10-08|Stable 0.162 adds turn lineage, subagent model telemetry and string skill paths|Adapt typed constructors and skill paths; stable API migration, no new invariant

B26|2026-10-08|New pencil tooltip passed plain string to styled-text Slint property|Use explicit markdown conversion; compile-time regression

B27|2026-10-08|Glob protocol import shadows std Result and fixture uses obsolete image field|Explicit imports and current image/detail shape

B28|2026-10-08|New automation measurement borrows an existing item reference; activity read condition nests a collapsible branch|Remove redundant borrow and collapse condition; mechanical lint cleanup, no new invariant

B29|2026-10-08|Preparation validates restored generated-crate provenance before replacing an older upstream cache|Validate source pins first, regenerate, then enforce provenance; verified with deliberately stale cache
