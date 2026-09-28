# Implementation Plan: NeuralMemo CLI Gradient Splash

## Overview
Update the CLI terminal splash to feature a gradient-colored "NeuralMemo" ASCII art with modern aesthetics.

## Architecture

### Files to Modify
1. **`packages/tui/src/logo.ts`** - ASCII art and go block definitions
2. **`packages/opencode/src/cli/cmd/run/splash.ts`** - Splash rendering logic
3. **`packages/opencode/src/cli/cmd/run/theme.ts`** - Splash theme color definitions

### Current Flow
```
logo.ts (ASCII art) -> splash.ts (render) -> theme.ts (colors)
```

## Step-by-Step Plan

### Step 1: Update ASCII Art in `logo.ts`
- Replace current "NeuralMemo" + "AGENTX" ASCII art with a single unified "NeuralMemo" wordmark
- Use a cleaner, more modern ASCII font style
- Ensure the art fits within 60 columns for good terminal compatibility

**New ASCII Art Design:**
```typescript
export const logo = {
  left: [
    "                _  __              ",
    "               | |/ /__ _ _ _ __  ",
    "               | ' // _` | | '  \\ ",
    "               |_|\\_\\__,_|_|_|_|_|",
    "           __  ____               ",
    "          /  |/  (_)__  __ ____   ",
    "         / /|_/ / / _ \\/ // / /  ",
    "        /__/  /_/ /_/ /_, /_/    ",
    "                  /___/          "
  ],
  right: []
}
```

Wait, this might be too large. Let me simplify to a compact wordmark.

**Revised ASCII Art (Compact):**
```typescript
export const logo = {
  left: [
    "  __  __  ___  ____  ",
    " |  \\/  |/ _ \\|  _ \\ ",
    " | |\\/| | | | | |_) |",
    " | |  | | |_| |  __/ ",
    " |_|  |_|\\___/|_|    "
  ],
  right: []
}
```

This shows "NeuralMemo" in a compact ASCII art style.

### Step 2: Add Gradient Color Mapping in `splash.ts`
- Create a `gradientColor` function that maps character position to an ANSI 256 color index
- Apply gradient to the logo characters based on their column position
- Use blue (#38bdf8) to purple (#a855f7) as the gradient range

**Gradient Implementation:**
```typescript
function gradientColor(position: number, total: number): number {
  // Map position 0-100 to ANSI 256 color range
  // Blue (69) -> Cyan (80) -> Purple (129)
  const t = position / total
  if (t < 0.33) return 69  // Blue
  if (t < 0.66) return 80  // Cyan
  return 129  // Purple
}
```

### Step 3: Update `RunSplashTheme` in `theme.ts`
- Add gradient-specific color properties
- Define gradient start/end colors

**New Theme Properties:**
```typescript
export type RunSplashTheme = {
  left: ColorInput
  right: ColorInput
  leftShadow: ColorInput
  rightShadow: ColorInput
  gradientStart: ColorInput  // NEW
  gradientEnd: ColorInput    // NEW
}
```

### Step 4: Update `splashTheme()` function
- Derive gradient colors from terminal palette
- Use ANSI 256 colors that approximate blue-purple gradient

### Step 5: Modify `build()` function in `splash.ts`
- Apply per-character gradient coloring to the logo text
- Keep shadow effect for depth

## Dependencies
- None - all changes are self-contained

## Testing
1. Run `bun dev` from `packages/opencode` to launch the interactive TUI
2. Verify the splash displays with gradient colors
3. Test on both dark and light terminal backgrounds
4. Verify exit splash also shows gradient

## Risk Assessment
- Low risk: Changes are cosmetic and don't affect functionality
- Fallback: If gradient colors don't render well, fallback to single accent color
