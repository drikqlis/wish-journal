# Interactive Widgets System

**Web-native interactive widgets for Wish Journal markdown posts**

## Overview

The Interactive Widgets system allows you to embed fully functional, browser-based interactive components directly in your markdown blog posts. Unlike the Python script execution system (which runs Python on the backend via SSE), these widgets run **entirely in the browser** using vanilla JavaScript.

### Key Features

- **Web-native**: No backend dependencies, runs entirely in the browser
- **Extensible**: Easy to add new widget types
- **Markdown integration**: Simple syntax embedded in post content
- **Customizable**: JSON configuration for widget parameters
- **Theme-aware**: Styled to match the dark purple theme

---

## Architecture

### Components

1. **Markdown Extension** ([app/content.py](app/content.py))
   - `InteractiveWidgetBlockProcessor`: Parses `:::widget` blocks
   - `InteractiveWidgetExtension`: Registers processor with markdown parser

2. **JavaScript Framework** ([static/js/interactive-widgets.js](static/js/interactive-widgets.js))
   - `WidgetRegistry`: Central registry for widget types
   - Widget classes: Individual widget implementations (e.g., `TerminalSimWidget`)
   - Auto-initialization on page load

3. **Styling** ([static/css/interactive-widgets.css](static/css/interactive-widgets.css))
   - Base widget container styles
   - Widget-specific styles
   - Responsive design

### Data Flow

```
Markdown Post
    ↓
Content Parser (Python)
    ↓
HTML with data attributes
    ↓
Browser Renders Page
    ↓
JavaScript Widget Registry
    ↓
Widget Initialization
    ↓
Interactive Widget (Client-side)
```

---

## Usage

### Basic Syntax

```markdown
:::widget type="widget-type" title="Widget Title" config='{"key": "value"}'
:::
```

### Parameters

- **type** (required): Widget type identifier (e.g., `terminal-sim`)
- **title** (optional): Display title (defaults to formatted widget type)
- **config** (optional): JSON string with widget-specific configuration

### Example

```markdown
:::widget type="terminal-sim" title="Terminal Zabezpieczony" config='{"code": [4, 6, 2, 4], "attempts": 3}'
:::
```

---

## Available Widgets

### Terminal Simulation (`terminal-sim`)

Interactive terminal simulation recreating the `terminal.py` script functionality.

**Features:**
- System loading sequence with slow-print animation
- Code input with arrow key navigation
- Blinking cursor effect
- Verification sequence
- Attempt tracking
- Success/failure states

**Configuration:**

```json
{
  "code": [4, 6, 2, 4],    // Target code (array of 4 digits, 0-9)
  "attempts": 3,           // Number of attempts allowed
  "sound": false           // Enable/disable sound effects (not implemented)
}
```

**Controls:**
- **Arrow Up/Down**: Change digit value
- **Enter**: Move to next digit or submit code
- **Backspace**: Move to previous digit
- **Escape**: Reset terminal
- **Space** (after completion): Restart

**Example:**

```markdown
# Unlock the Terminal

Can you crack the code?

:::widget type="terminal-sim" title="Security Terminal"
:::
```

---

## Creating New Widgets

### Step 1: Create Widget Class

Add a new widget class in [static/js/interactive-widgets.js](static/js/interactive-widgets.js):

```javascript
class MyCustomWidget {
    constructor(element) {
        this.element = element;
        this.config = this.parseConfig(element.dataset.config);

        // Initialize your widget
        this.init();
    }

    parseConfig(configStr) {
        try {
            return configStr ? JSON.parse(configStr) : {};
        } catch (e) {
            console.error('[MyCustomWidget] Invalid config:', e);
            return {};
        }
    }

    init() {
        // Widget initialization code
        const container = document.createElement('div');
        container.className = 'my-widget-container';
        container.textContent = 'Hello from custom widget!';
        this.element.appendChild(container);
    }
}
```

### Step 2: Register Widget

Register your widget with the registry:

```javascript
// At the bottom of interactive-widgets.js
registry.register('my-widget', MyCustomWidget);
```

### Step 3: Add Styling (Optional)

Add widget-specific styles in [static/css/interactive-widgets.css](static/css/interactive-widgets.css):

```css
.my-widget-container {
    padding: 1rem;
    background: var(--bg-elevated);
    border-radius: 4px;
}
```

### Step 4: Use in Markdown

```markdown
:::widget type="my-widget" title="My Custom Widget" config='{"foo": "bar"}'
:::
```

---

## Widget Development Guidelines

### Best Practices

1. **Self-contained**: Widgets should be independent and not interfere with each other
2. **Event cleanup**: Always remove event listeners when widget is destroyed
3. **Responsive**: Design for mobile and desktop
4. **Accessible**: Use ARIA labels and keyboard navigation
5. **Error handling**: Gracefully handle invalid config
6. **Performance**: Avoid heavy computations on the main thread

### Widget Lifecycle

```javascript
class ExampleWidget {
    constructor(element) {
        // 1. Store references
        this.element = element;

        // 2. Parse config
        this.config = this.parseConfig(element.dataset.config);

        // 3. Initialize state
        this.state = {};

        // 4. Build DOM
        this.render();

        // 5. Attach event listeners
        this.attachEvents();
    }

    render() {
        // Create and append DOM elements
    }

    attachEvents() {
        // Add event listeners
    }

    destroy() {
        // Cleanup (if needed)
        // Remove event listeners, clear intervals, etc.
    }
}
```

### Keyboard Event Handling

When handling keyboard events, always check if the target is an input field:

```javascript
handleKeyPress(e) {
    // Don't interfere with other inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }

    // Your keyboard handling code
    switch (e.key) {
        case 'Enter':
            // Handle Enter
            break;
    }
}
```

### Focus Management

Make widgets keyboard-accessible:

```javascript
this.container.setAttribute('tabindex', '0');
this.container.focus();
```

---

## Widget Ideas

Here are some ideas for future widgets:

### Educational
- **Quiz Widget**: Multiple choice questions with scoring
- **Flashcard Widget**: Interactive flashcards for learning
- **Code Playground**: Live HTML/CSS/JS editor (sandboxed iframe)

### Interactive
- **Poll Widget**: Interactive polls with results visualization
- **Calculator Widget**: Various calculators (scientific, date, etc.)
- **Color Picker**: Interactive color palette generator

### Visualization
- **Chart Widget**: D3.js or Chart.js integration
- **Timeline Widget**: Interactive event timeline
- **Mind Map**: Interactive mind mapping tool

### Games
- **Puzzle Widget**: Sliding puzzles, crosswords, etc.
- **Memory Game**: Card matching game
- **Tic-Tac-Toe**: Simple strategy game

### Utilities
- **Countdown Timer**: Event countdown
- **Unit Converter**: Interactive unit conversion
- **Markdown Preview**: Live markdown rendering

---

## Comparison: Widgets vs Python Scripts

| Feature | Interactive Widgets | Python Scripts |
|---------|-------------------|----------------|
| **Execution** | Browser (JavaScript) | Server (Python + SSE) |
| **Dependencies** | None (web-native) | Backend server required |
| **Performance** | Fast (client-side) | Network latency |
| **Capabilities** | UI interactions only | Full Python stdlib |
| **Use Cases** | Animations, games, calculators | File I/O, complex algorithms |
| **Best For** | Visual/interactive content | Script execution, data processing |

### When to Use Each

**Use Interactive Widgets when:**
- You need visual interactivity (animations, games)
- No server-side computation needed
- Want instant response with no latency
- Building UI components (quizzes, calculators)

**Use Python Scripts when:**
- You need Python's stdlib (file I/O, regex, etc.)
- Server-side computation required
- Working with external Python packages
- Terminal-style input/output interactions

---

## Technical Details

### HTML Output Structure

When you write:

```markdown
:::widget type="terminal-sim" title="My Terminal"
:::
```

The markdown processor generates:

```html
<div class="interactive-widget"
     data-widget-type="terminal-sim"
     data-config='{}'>
  <div class="widget-title">My Terminal</div>
</div>
```

### JavaScript Initialization

On page load:

1. `DOMContentLoaded` event fires
2. `WidgetRegistry.initializeAll()` is called
3. Finds all `.interactive-widget` elements
4. Reads `data-widget-type` attribute
5. Looks up widget class in registry
6. Instantiates widget class with element
7. Widget renders itself into the container

### Security Considerations

**Config Validation:**
- Always validate and sanitize config JSON
- Use `JSON.parse()` with try/catch
- Provide safe defaults

**Event Handling:**
- Check event targets to avoid interfering with other inputs
- Always preventDefault() when handling special keys

**XSS Prevention:**
- Use `textContent` instead of `innerHTML` when possible
- Sanitize user input if rendered as HTML
- Avoid `eval()` or dynamic code execution

---

## Testing

### Manual Testing

1. Create a test post in `content/posts/widget-test.md`
2. Add widget markdown syntax
3. Start the development server: `flask run --debug`
4. Visit the post in your browser
5. Interact with the widget

### Browser Console

Check for initialization logs:

```
[WidgetRegistry] Registered widget type: terminal-sim
[WidgetRegistry] Initialized terminal-sim widget
[TerminalSimWidget] Initialized for widget
```

### Debugging

Enable verbose logging:

```javascript
// In interactive-widgets.js constructor
console.log('[MyWidget] Config:', this.config);
console.log('[MyWidget] Element:', this.element);
```

---

## Performance Optimization

### Lazy Loading

For heavy widgets (large libraries), consider lazy loading:

```javascript
async init() {
    // Load library only when widget is used
    const D3 = await import('https://cdn.example.com/d3.js');
    this.renderChart(D3);
}
```

### Debouncing

For event-heavy widgets, debounce frequent events:

```javascript
handleInput(e) {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
        this.processInput(e.target.value);
    }, 300);
}
```

### Virtual Scrolling

For widgets with long lists, implement virtual scrolling to render only visible items.

---

## Troubleshooting

### Widget Not Appearing

**Symptoms:** Widget div exists but content not rendered

**Check:**
1. Is the widget type registered in `interactive-widgets.js`?
2. Check browser console for JavaScript errors
3. Verify `data-widget-type` attribute matches registered type

### Widget Not Initializing

**Symptoms:** No console logs, widget inactive

**Check:**
1. Is `interactive-widgets.js` loaded in base template?
2. Is `interactive-widgets.css` loaded in base template?
3. Check Network tab for 404 errors

### Config Not Working

**Symptoms:** Widget uses defaults instead of config

**Check:**
1. Is config valid JSON? Use a JSON validator
2. Check `data-config` attribute in HTML source
3. Add console.log in `parseConfig()` to debug

### Keyboard Events Not Working

**Symptoms:** Key presses don't trigger widget actions

**Check:**
1. Is widget element focusable? (`tabindex="0"`)
2. Are you checking for input/textarea targets?
3. Try using `document.addEventListener` instead of element listener

---

## Files Reference

### Core Files

- [static/js/interactive-widgets.js](static/js/interactive-widgets.js) - Widget framework and implementations
- [static/css/interactive-widgets.css](static/css/interactive-widgets.css) - Widget styling
- [app/content.py](app/content.py) - Markdown extension (lines 237-305)
- [templates/base.html](templates/base.html) - Asset loading

### Example Files

- [content/posts/example-widget.md](content/posts/example-widget.md) - Example post with widget
- [INTERACTIVE_WIDGETS.md](INTERACTIVE_WIDGETS.md) - This documentation

---

## Future Enhancements

### Planned Features

- [ ] Widget configuration UI (click widget to edit config)
- [ ] Widget marketplace/library system
- [ ] Widget state persistence (localStorage)
- [ ] Multi-language support for widgets
- [ ] Widget preview in markdown editor
- [ ] Widget accessibility audit tool
- [ ] Performance profiling dashboard

### Contribution Guidelines

To add a new widget:

1. Create widget class in `interactive-widgets.js`
2. Add styles in `interactive-widgets.css`
3. Register with widget registry
4. Create example post in `content/posts/`
5. Document in this file
6. Add tests if applicable

---

## License

This widget system is part of Wish Journal and follows the same license as the main project.

---

## Support

For questions or issues:
1. Check this documentation
2. Review example implementations in `interactive-widgets.js`
3. Test with `example-widget.md` post
4. Check browser console for errors

---

**Happy widget building!** 🎨✨
