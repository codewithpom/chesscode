# Asset credits

Every bundled asset, its source and its license. Add a row before adding an asset.

## Fonts (`src/assets/fonts/`)

IBM Plex, copyright IBM Corp., Reserved Font Name "Plex". License: SIL Open Font License 1.1 (https://openfontlicense.org). Source: official IBM Plex npm packages built from https://github.com/IBM/plex.

| Files | Package |
| --- | --- |
| IBMPlexSans-Regular, -Medium, -SemiBold | @ibm/plex-sans 1.1.0 |
| IBMPlexSansCondensed-SemiBold | @ibm/plex-sans-condensed 2.0.0 |
| IBMPlexMono-Regular, -Medium | @ibm/plex-mono 2.5.0 |
| IBMPlexSansDevanagari-Regular, -Medium, -SemiBold | @ibm/plex-sans-devanagari 1.1.0 |

## Chess pieces (`src/assets/pieces/`)

rhosgfx piece set (wK, wQ, wR, wB, wN, wP, bK, bQ, bR, bB, bN, bP .svg), by RhosGFX (https://rhosgfx.itch.io/). License: CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/). Source files: https://github.com/lichess-org/lila/tree/master/public/piece/rhosgfx; license confirmed in https://raw.githubusercontent.com/lichess-org/lila/master/COPYING.md (line "public/piece/rhosgfx | RhosGFX | CC0 1.0").

Modification (CC0 permits it): the six black piece files (`bK bQ bR bB bN bP .svg`) are recolored by replacing the original terracotta palette. Outline `#1a1a1a` and detail `#9c3d29` became ink `#D9DCE1`; body `#d1774b` became fill `#2E323B`; shade `#bb5938` became `#252830`. Shapes are unchanged. White pieces are unmodified. Tests assert the recolor and the 3:1 contrast against every board theme.

## Sound effects (`src/assets/sfx/`)

Kenney (https://kenney.nl) packs, each with a License.txt reading "Creative Commons Zero, CC0" (http://creativecommons.org/publicdomain/zero/1.0/), checked at download. Converted by `scripts/fetch_sfx.py` (48 kHz mono MP3, trimmed to 2 s, peak normalised to -16 dBFS before encoding, every file verified <= -12 dBFS).

| File | Source file | Pack page | License |
| --- | --- | --- | --- |
| oof_01.mp3 | Impact Sounds by Kenney, `Audio/impactSoft_heavy_000.ogg` | https://kenney.nl/assets/impact-sounds | CC0 1.0 (Creative Commons Zero) |
| hmm_01.mp3 | Interface Sounds by Kenney, `Audio/question_001.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| ding_01.mp3 | Interface Sounds by Kenney, `Audio/confirmation_002.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| gasp_01.mp3 | Interface Sounds by Kenney, `Audio/scratch_001.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| whip_01.mp3 | Interface Sounds by Kenney, `Audio/maximize_009.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| tick_01.mp3 | Interface Sounds by Kenney, `Audio/tick_001.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| tick_02.mp3 | Interface Sounds by Kenney, `Audio/tick_002.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| sparkle_01.mp3 | Interface Sounds by Kenney, `Audio/glass_003.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
| sting_01.mp3 | Impact Sounds by Kenney, `Audio/impactBell_heavy_000.ogg` | https://kenney.nl/assets/impact-sounds | CC0 1.0 (Creative Commons Zero) |
| sting_02.mp3 | Interface Sounds by Kenney, `Audio/drop_004.ogg` | https://kenney.nl/assets/interface-sounds | CC0 1.0 (Creative Commons Zero) |
