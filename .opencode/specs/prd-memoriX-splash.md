# PRD: NeuralMemo CLI Gradient Splash

## Objective
Redesign the CLI terminal splash screen for NeuralMemo with a modern gradient color scheme and NeuralMemo branding.

## Context
The current CLI splash shows ASCII art for "NeuralMemo" and "AGENTX" with monochrome coloring. The user wants a more visually striking splash with gradient colors applied to the text.

## Requirements

### Functional Requirements
1. **Gradient Coloring**: Apply a smooth gradient effect across the ASCII art lines, transitioning from one color to another (e.g., cyan to purple, blue to magenta).
2. **NeuralMemo Branding**: Keep "NeuralMemo" as the primary brand name in the splash.
3. **Modern Aesthetic**: Update the ASCII art style to be cleaner and more modern while remaining readable in monospace terminals.
4. **Shadow Effect**: Enhance the shadow/depth effect under the main text for a 3D appearance.
5. **Session Info**: Preserve the session title and ID display in the exit splash.

### Visual Design
- **Gradient Palette**: Use a modern blue-to-purple or cyan-to-violet gradient (terminal-friendly colors).
- **Color Mapping**: Map gradient stops to ANSI 256 color palette for compatibility.
- **Shadow Colors**: Derive shadow colors from the gradient base with reduced opacity.

### Constraints
- Must work in standard terminal emulators (supporting ANSI 256 colors).
- Cannot use true-color (24-bit) as not all terminals support it.
- Must maintain readability on both dark and light terminal backgrounds.

## Success Criteria
1. The splash displays with visible gradient coloring across the ASCII art.
2. Colors transition smoothly from left to right or top to bottom.
3. The splash remains legible in 80-column terminals.
4. No regressions in session title/ID display.

## Out of Scope
- Animated effects (not supported in scrollback snapshots).
- Custom font loading.
- GUI/desktop splash changes (separate scope).
