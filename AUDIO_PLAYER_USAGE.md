# Custom Audio Player Usage

The audio player has been styled to match your purple color palette with Polish interface text.

## Basic Usage

Add an audio element with metadata via data attributes:

```html
<audio controls data-title="Tytuł utworu" data-artist="Wykonawca">
  <source src="/media/audio/song.mp3" type="audio/mpeg">
</audio>
```

## Data Attributes

- `data-title`: Song title (default: "Bez tytułu")
- `data-artist`: Artist name (default: "Nieznany wykonawca")
- `data-artwork`: Path to album art image (optional, 80x80px thumbnail)

## Example with Album Art

```html
<audio controls
       data-title="Save Me"
       data-artist="Queen"
       data-artwork="/media/images/queen-album.jpg">
  <source src="/media/audio/Queen-Save_Me.mp3" type="audio/mpeg">
</audio>
```

## Example without Album Art

```html
<audio controls data-title="Mój utwór" data-artist="Artysta">
  <source src="/media/audio/song.mp3" type="audio/mpeg">
</audio>
```

## Features

- ✓ Full width player matching your purple color palette
- ✓ Polish interface (odtwórz/pauza, głośność)
- ✓ Dark background (--bg-elevated: #0f0e14)
- ✓ Song title and artist display
- ✓ Optional album artwork (80x80px)
- ✓ Custom progress bar with seek functionality
- ✓ Time display (current/duration)
- ✓ Play/pause button with consistent styling
- ✓ Hover effects matching your button style

## Styling

The player automatically inherits your site's color scheme:
- Background: `var(--bg-elevated)` (#0f0e14)
- Border: `var(--border-color)` (#221a2e)
- Title: `var(--accent-color)` (#D4A5FF)
- Artist: `var(--text-dim)` (#8866CC)
- Progress bar: `var(--accent-color)` (#D4A5FF)
- Buttons: Purple border with hover fill effect
