# Skill Observation Log

Observations captured during task-oriented work. Each entry identifies a
potential skill improvement or new skill opportunity.

**Status key:** OPEN = not yet actioned | ACTIONED = skill updated/created |
DECLINED = user decided not to pursue

---

## 2026-07-14

### Observation 1: User pasted a fabricated technical spec with fake citations

**Date:** 2026-07-14
**Session context:** ChessCode theme refinement — user pasted a large "Theme
Refinement & Text Engine Engineering Specification" markdown doc (with `[cite: 1]`
tags throughout, clearly LLM-generated fluff) proposing fixes for cyberpunk/retro
theme contrast and text overflow bugs.
**Skill:** New skill candidate: spec-verification-before-implementation
**Type:** open-source
**Phase/Area:** Pre-implementation verification

**Issue:** The pasted spec assumed an architecture that doesn't exist in the
codebase (per-theme PNG piece sprites at `assets/ui/<theme>/piece_*.png`,
composited via a `ThemeAssetFactory` class) when the actual codebase renders
pieces via `chess.svg.board()` with no sprite compositing layer at all. The
spec also proposed re-solving a "global tag bug" (HTML `<b>` tags rendering
literally) that was already fixed in an earlier wave of work. Blindly
implementing the spec as written would have added a fake asset pipeline
referencing non-existent files, and wasted effort re-fixing an already-fixed
bug. Instead, the actual board_renderer.py was read first, the two claims
(contrast issue, retro font overflow) were verified as real against the real
code, and fixes were implemented in the real architecture rather than the
spec's imagined one.
**Suggested improvement:** A skill (or a standing rule inside an existing
"implementing external specs" workflow) that says: before implementing any
pasted/external spec against a codebase, verify each claim against the actual
current code first — grep/read the referenced files, confirm the referenced
functions/assets/patterns actually exist, and only port the *diagnosis* (the
real bug) rather than the *prescribed implementation* (which may assume a
different architecture). Explicitly flag to the user which parts of the spec
were inapplicable and why, rather than silently dropping them or silently
force-fitting them.
**Principle:** Externally-sourced specs (especially AI-generated ones pasted
by a user, identifiable by citation artifacts like `[cite: 1]` or generically
confident tone) should be treated as *hypotheses about what's wrong*, not as
ground truth about the codebase's architecture. Verify against real files
before writing any code from them. This generalizes beyond chess/PIL — applies
to any session where a user pastes a "spec" from another tool/model without
having verified it against the actual repo themselves.

---
