# Arrow Visualization Guide

## Overview

ChessCode now includes **smart arrow visualization** on the chess board to help viewers understand tactical and strategic concepts. Arrows are color-coded and intelligently filtered to show the most important moves without cluttering the display.

## Arrow Types & Colors

### 🟢 Green Arrows — Best Move
- **Meaning**: The computer's recommended best move (from Stockfish analysis)
- **When shown**: Always displayed when analysis data is available
- **Example**: After a blunder, shows what the player should have played

### 🔴 Red Arrows — Threats
- **Meaning**: Opponent's most dangerous attacking move
- **Subtypes**:
  - Direct check or attack on the king
  - Capture of a valuable piece
  - Tactical threat (e.g., fork, pin)
- **When shown**: When a threat exists that requires attention

### 🟡 Yellow Arrows — Defensive Moves
- **Meaning**: Moves that defend against the most critical threat
- **Usage**: Helps viewers understand defensive logic
- **When shown**: When a threat arrow is present and a good defense exists

## Usage

### Enabling/Disabling Arrows

```bash
# Enable arrows (default)
python main.py game.pgn

# Disable arrows completely
python main.py game.pgn --no-arrows

# Adjust arrow intensity
python main.py game.pgn --arrow-intensity conservative    # 2 arrows max
python main.py game.pgn --arrow-intensity normal          # 4 arrows max (default)
python main.py game.pgn --arrow-intensity aggressive      # 6 arrows max
```

### Environment Configuration

Set in `.env`:
```
ARROW_INTENSITY=normal              # conservative, normal, or aggressive
```

## Smart Filtering Algorithm

ChessCode uses intelligent filtering to prevent arrow clutter:

1. **Always Show Best Move** (green) — highest priority
2. **Show Key Threats** (red) — up to 2 in simple positions, 1 in complex positions
3. **Show Defensive Options** (yellow) — only if space allows
4. **Complexity Detection** — automatically reduces arrows in positions with 20+ legal moves

### Example

- **Simple Position** (10 legal moves): May show 3-4 arrows
- **Complex Middlegame** (30+ legal moves): Shows only the most critical 1-2 arrows
- **Quiet Position** (no threats): May show only best move

## Architecture

### Files Modified

- **`arrow_analyzer.py`** — Core threat/defense detection logic
  - `ArrowAnalyzer` class manages arrow generation
  - `ArrowType` enum defines arrow categories
  - `ChessArrow` dataclass represents individual arrows

- **`board_renderer.py`** — Board rendering with arrow support
  - `RenderOptions.show_arrows` — Enable/disable arrows
  - `RenderOptions.arrow_intensity` — Control arrow density
  - Arrow legend added to video sidebar

- **`main.py`** — CLI interface
  - `--no-arrows` flag to disable arrows
  - `--arrow-intensity` flag to set density

- **`config.py`** — Configuration
  - `show_arrows` setting
  - `arrow_intensity` environment variable

- **`opening_video_generator.py`** — Opening theory videos
  - Integrated arrow support

### Algorithm Details

#### Threat Detection (`_detect_threat_arrows`)
1. Check for immediate checks first (highest priority)
2. Look for undefended/hanging pieces
3. Identify opponent's most dangerous captures

#### Defensive Detection (`_detect_defensive_arrows`)
1. Identify threatened pieces/squares
2. Find moves that protect them
3. Return first viable defense

#### Smart Filtering (`_smart_filter`)
1. Separate arrows by type (best move, threat, defensive)
2. Count legal moves to detect complexity
3. Prioritize arrows based on criticality and available space
4. Enforce max arrows per frame

## Limitations & Future Work

### Current Limitations
- Threat detection is basic (no deep tactical analysis)
- Defensive suggestions may miss complex defensive ideas
- No multi-piece tactics detection (forks, pins, skewers shown as simple threats)

### Future Enhancements
1. **Tactical Pattern Recognition**
   - Auto-detect forks, pins, skewers, discovered attacks
   - Color-code by tactic type

2. **Animated Arrow Transitions**
   - Smooth animations between consecutive frames
   - Visual emphasis on critical moments

3. **User Customization**
   - Let viewers toggle arrow visibility per type
   - Custom color schemes

4. **Analysis Integration**
   - Show alternative candidate moves
   - Display evaluation changes with arrows

## Troubleshooting

### Arrows Not Showing
- Check `show_arrows=True` in RenderOptions
- Verify analysis data is being passed to renderer
- Ensure Stockfish analysis is available

### Too Many/Too Few Arrows
- Adjust `--arrow-intensity` flag
- Check `arrow_intensity` in config
- Review smart filtering logic for your position

### Arrow Colors Not Visible
- Verify board theme contrast
- Check SVG arrow color values in `arrow_analyzer.py`
- Test with different themes (--theme option)

## Examples

### Fool's Mate Setup
```
1.f3 e5 2.g4 — Red arrow shows Qh4# checkmate threat
                Yellow arrow shows Qe7 defensive attempt
```

### Sicilian Defense
```
1.e4 c5 2.Nf3 d6 3.d4 cxd4 — Green arrow highlights best continuations
                              Red arrows show Black's counterplay options
```

## Technical Notes

- Arrows are rendered using `python-chess` SVG library
- Arrow data is cached separately from board image cache
- Smart filtering runs per-frame (no performance impact)
- Compatible with both HD (1920×1080) and Shorts (1080×1920) formats
