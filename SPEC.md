# SPEC

## §G GOAL
Reliable conversation scrolling, Windows presentation, web/file link actions, inference speed selection; standalone stable-upstream distribution.
Broader GUI contract: repository `GUI.md`.

## §C CONSTRAINTS
- Independent allquixotic/codex-gui; Apache-2.0; latest stable Codex release only, immutable Git pin, zero Codex patches.
- Native Slint 1.18.1; bound transcript memory; no idle repaint polling.
- Windows x64 release first; macOS release builds deferred.
- Never run GUI tests or launch this project's GUI on Sean's Mac unless the user explicitly says "test the GUI on this Mac"; use Windows hosts.
- Full release build only after fixes and development verification complete.
- Verify GitHub asset digest before deleting local build outputs.

## §I INTERFACES
- I.scroll: wheel, scrollbar, Jump to latest in conversation pane.
- I.paint: Windows restore, remote desktop exposure, existing redraw events.
- I.speed: provider-catalog speed picker; thread/settings/update and turn/start.
- I.links: glyph hover, Copy link, Open in browser, Open file.

## §V INVARIANTS
V1: Upward user scroll ! detach tail-following before virtual row measurement; small idle scroll ! persist; automatic height/offset adjustment ! preserve live tail following.
V2: Lost Windows surface pixels ! repaint next frame without resize; idle ! schedule no polling frames.
V3: Link hit ! match shaped glyph and clipping; wrapped web/file links ! retain exact destination.
V4: Copy/tooltip ! preserve file line and resolve relative path; browser action ! encode file URL.

V5: Speed choices ! follow provider catalog and feature requirements; Standard ! send explicit default; model switch ! reset unsupported tier; resume/fork ! preserve reported tier.

## §T TASKS
id|status|task|cites
T1|x|Fix small-scroll tail feedback|V1,I.scroll
T2|x|Recover Windows retained surface; Auto uses CPU in RDP|V2,I.paint
T3|x|Shared link menus and hover tooltips|V3,V4,I.links
T4|x|Verify, commit, push, publish Windows package, clean outputs|V1,V2,V3,V4; GUI.md §16

T5|x|Add catalog-driven inference speed and verify upstream migration|V5,I.speed

T6|.|Extract standalone GUI, pin latest stable, verify Windows CI, commit/push/release|GUI.md §19

## §B BUGS
id|date|cause|fix
B1|2026-10-06|32px tail threshold and height-estimate callbacks pull upward scroll back to bottom|V1
B2|2026-10-06|Retained surface pixels assumed valid across Windows remote-display exposure; missing full invalidation|V2
B3|2026-10-06|Slint overwrites link hit with each wrapped-line rectangle instead of accumulating hits|V3; pinned core patch
B4|2026-10-06|Treating automatic content-y corrections as user gestures disables following during streamed row updates|V1; detach on input, never on offset alone
B5|2026-10-06|TouchArea moved fires only during dragging; stopping on hover movement without restarting loses tooltips|V3; handle pointer move and reset the stationary delay

B6|2026-10-07|Upstream protocol migration adds required fields and replaces skill PathBuf with LegacyAppPathString; clean Git merge still fails compilation|Adapt typed paths and protocol constructors; one-time migration, no new invariant

B7|2026-10-07|Development-main protocol fields and path wrappers differ from stable 0.161.0|Adapt release constructors and optional wire capabilities; one-time migration
