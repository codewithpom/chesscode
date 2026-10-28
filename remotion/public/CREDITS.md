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
