# Mascot concept brief (shape)

Source: `docs/SPEC.md` section 7, `PRODUCT.md`. Shape interview skipped: the spec is the settled brief and the owner confirms at the concept-choice checkpoint (assumptions below are open to correction there).

- **Job:** the clown to the narrator's straight man. Reacts to beats, never explains chess. Lives bottom-right in Studio (~200 px tall) and below the board in Shorts (~260 px), on the dark Studio background `#0F1115`.
- **Outcome:** a character a viewer recognises from its silhouette alone, whose acting reads at 200 px from the eyes and brows, built from layers the M4 rig can drive with plain numbers (`PoseState`).
- **Direction:** flat vector, one ink outline weight, three colours plus one accent, no gradients or effects. Big head, big eyes, small mouth: eyes do the acting. Noodle arms in ink appear only when a pose needs them. Comedy from proportion and attitude, not props.
- **Shared layers (same names on every concept):** `base`, `body`, `head`, `eye-l`, `eye-r` (sclera, pupil, lid), `brow-l`, `brow-r`, `mouth`, `arm-l`, `arm-r`, `prop`.
- **Proportions chosen:**
  - Pyaada: head radius 58 on a 180-wide base (head:base width ≈ 0.64, a real pawn is ≈ 0.45), so he reads as a squashed pawn. Eyes 30 × 40 each (≈ 26 % of head width). Crown 52 wide, tilted 12° clockwise, sitting right of centre.
  - Knight: same base as the pawn so the two read as one family; head in three-quarter view facing right, two eyes on the front of the face, mane in the accent.
  - Engine bot: rounded square body with a dark screen face; pixel eyes; the mouth is a thin eval bar whose fill level is the mood. No battery nub, no segments.
- **Anti-goals:** no Claude spark, no owl or Duo-like round green body, no traced AI image, no emoji-style faces, no chess-piece realism, no meanness toward players.
- **Open for the owner:** which concept; name; accent colour; crown on or off.
