# Logo Update: Transparent Logo with Dark/Light Mode Support

## Overview
The SpeechGradebook application has been updated to use a single transparent logo file that automatically adapts to light and dark modes using CSS filters.

## Changes Made

### 1. CSS Styling (index.html)
- Added CSS rules to handle transparent logo in both light and dark modes
- **Light Mode**: No filter applied - logo displays as-is on white/light backgrounds
- **Dark Mode**: CSS filter `invert(1) brightness(1.1) contrast(1.1)` is applied to invert colors and enhance visibility on dark backgrounds
- Updated header logo background to use dark background (`#1a1a1a`) in dark mode for better contrast
- Updated auth logo background styling for dark mode

### 2. Logo File References
All logo references have been updated from:
- `logo-light-bg.png` → `logo-transparent.png`
- `logo-dark-bg.png` → `logo-transparent.png`

Updated locations:
- Favicon link in HTML head
- Auth/login page logo
- Header/app logo
- All JavaScript functions that dynamically set logos
- Theme configuration objects

## Required File

You need to add your transparent logo file to:
```
assets/logo-transparent.png
```

## How It Works

### Light Mode
- Logo displays with no filters
- Header logo has white background (`#ffffff`)
- Auth logo uses card background color

### Dark Mode
- Logo colors are inverted using CSS filter: `invert(1) brightness(1.1) contrast(1.1)`
- Header logo background changes to dark (`#1a1a1a`) for contrast
- Auth logo background adapts to dark theme

## Customization

If you need to adjust the dark mode filter, you can modify the CSS in `index.html` around line 517-525. The current filter is:
```css
filter: invert(1) brightness(1.1) contrast(1.1);
```

You can adjust:
- `invert(1)` - Inverts all colors (1 = full inversion, 0 = no inversion)
- `brightness(1.1)` - Adjusts brightness (1.1 = 10% brighter, 1.0 = no change)
- `contrast(1.1)` - Adjusts contrast (1.1 = 10% more contrast, 1.0 = no change)

Alternative filter options:
- `filter: invert(1);` - Simple inversion
- `filter: invert(1) hue-rotate(180deg);` - Inversion with hue rotation
- `filter: brightness(0) invert(1);` - Makes logo white (for dark backgrounds)

## Testing

1. Add your `logo-transparent.png` file to the `assets/` folder
2. Test in light mode - logo should display normally
3. Toggle dark mode (Settings → Dark Mode toggle) - logo should invert colors
4. Check favicon in browser tab
5. Check logo on login/auth page
6. Check logo in header/navigation

## Notes

- The old logo files (`logo-light-bg.png`, `logo-dark-bg.png`) are still in the assets folder but are no longer used
- You can remove the old logo files if desired, or keep them as backups
- The CSS automatically detects dark mode via `data-theme="dark"` attribute or `.theme-option7-dark` class
