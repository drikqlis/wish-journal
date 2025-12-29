/**
 * Interactive Widgets System
 *
 * Web-native framework for embedding interactive JavaScript widgets in markdown posts.
 * Widgets run entirely in the browser with no backend dependencies.
 *
 * Architecture:
 * - WidgetRegistry: Central registry for widget types
 * - Widget classes: Individual widget implementations
 * - Auto-initialization from markdown-generated HTML
 */

(function() {
    'use strict';

    /**
     * Widget Registry
     * Manages registration and initialization of widget types
     */
    class WidgetRegistry {
        constructor() {
            this.widgets = new Map();
        }

        /**
         * Register a widget type
         * @param {string} type - Widget type identifier (e.g., 'terminal-sim')
         * @param {class} WidgetClass - Widget class constructor
         */
        register(type, WidgetClass) {
            this.widgets.set(type, WidgetClass);
            console.log(`[WidgetRegistry] Registered widget type: ${type}`);
        }

        /**
         * Initialize all widgets on the page
         */
        initializeAll() {
            document.querySelectorAll('.interactive-widget').forEach(element => {
                const type = element.dataset.widgetType;
                const WidgetClass = this.widgets.get(type);

                if (WidgetClass) {
                    try {
                        new WidgetClass(element);
                        console.log(`[WidgetRegistry] Initialized ${type} widget`);
                    } catch (error) {
                        console.error(`[WidgetRegistry] Error initializing ${type}:`, error);
                    }
                } else {
                    console.warn(`[WidgetRegistry] Unknown widget type: ${type}`);
                }
            });
        }
    }

    // Create global registry
    const registry = new WidgetRegistry();

    /**
     * Terminal Simulation Widget
     *
     * Recreates the terminal.py interactive terminal in pure JavaScript.
     * Features:
     * - System loading sequence
     * - Code input with arrow key navigation
     * - Blinking cursor
     * - Success/failure verification
     * - Retry attempts
     */
    class TerminalSimWidget {
        constructor(element) {
            this.element = element;
            this.config = this.parseConfig(element.dataset.config);

            // Default config
            this.targetCode = this.config.code || [4, 6, 2, 4];
            this.maxAttempts = this.config.attempts || 3;
            this.clickSound = this.config.sound !== false; // Disabled by default for web

            // State
            this.attemptsLeft = this.maxAttempts;
            this.code = [0, 0, 0, 0];
            this.position = 0;
            this.blinkState = true;
            this.blinkInterval = null;
            this.running = false;
            this.hasRunOnce = false;

            // Create terminal container
            this.terminal = document.createElement('div');
            this.terminal.className = 'widget-terminal';
            this.element.appendChild(this.terminal);

            // Create controls
            this.controls = document.createElement('div');
            this.controls.className = 'widget-controls';
            this.element.appendChild(this.controls);

            // Create start button
            this.button = document.createElement('button');
            this.button.className = 'widget-start';
            this.button.setAttribute('aria-label', 'Uruchom widget');

            const icon = document.createElement('span');
            icon.className = 'widget-icon';
            icon.innerHTML = getIcon('play');
            this.button.appendChild(icon);

            // Create running indicator
            this.runningIndicator = document.createElement('span');
            this.runningIndicator.className = 'widget-running-indicator';

            this.controls.appendChild(this.button);
            this.controls.appendChild(this.runningIndicator);

            // Bind button click
            this.button.addEventListener('click', () => this.handleButtonClick());

            // Bind terminal click to start (like python-script)
            this.terminal.addEventListener('click', () => this.handleTerminalClick());

            // Show initial message (matches python-script)
            this.terminal.innerHTML = '<span style="color: var(--text-dim); font-style: italic;">Uruchom skrypt...</span>';
            this.terminal.classList.add('clickable');
        }

        handleTerminalClick() {
            // Only start on click if not running yet (like python-script)
            if (!this.running && !this.hasRunOnce) {
                this.handleButtonClick();
            }
        }

        handleButtonClick() {
            if (this.running) {
                // Stop current execution
                this.stop();
            }

            // Update button to restart after first run
            if (!this.hasRunOnce) {
                this.hasRunOnce = true;
                this.button.className = 'widget-restart';
                this.button.setAttribute('aria-label', 'Restart widgetu');
                const icon = this.button.querySelector('.widget-icon');
                if (icon) {
                    icon.innerHTML = getIcon('restart');
                }
                // Remove clickable state from terminal (like python-script)
                this.terminal.classList.remove('clickable');
            }

            // Reset state
            this.attemptsLeft = this.maxAttempts;

            // Start
            this.start();
        }

        stop() {
            this.running = false;
            this.stopBlink();
            this.detachKeyboard();
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
        }

        parseConfig(configStr) {
            try {
                return configStr ? JSON.parse(configStr) : {};
            } catch (e) {
                console.error('[TerminalSimWidget] Invalid config:', e);
                return {};
            }
        }

        start() {
            this.running = true;

            // Show running indicator
            this.runningIndicator.classList.add('running');
            this.runningIndicator.textContent = 'Śmigam';

            this.systemLoading();
        }

        async systemLoading() {
            await this.clearScreen();

            if (!this.running) return; // Check if stopped

            await this.slowPrint("INICJALIZACJA SYSTEMU...", '', 30);
            await this.sleep(300);

            if (!this.running) return;

            await this.slowPrint("\nŁADOWANIE MODUŁÓW ZABEZPIECZEŃ", '', 20);
            await this.sleep(400);

            if (!this.running) return;

            await this.slowPrint("\nWERYFIKACJA DANYCH SYSTEMOWYCH", '', 20);
            await this.sleep(400);

            if (!this.running) return;

            await this.slowPrint("\n\nSYSTEM GOTOWY.", '', 30);
            await this.sleep(600);

            if (!this.running) return;

            this.inputCode();
        }

        inputCode() {
            this.clearScreen();
            this.code = [0, 0, 0, 0];
            this.position = 0;

            this.render();
            this.startBlink();
            this.attachKeyboard();
        }

        render() {
            let html = '';
            html += `<div class="terminal-line">TERMINAL ZABEZPIECZONY</div>`;
            html += `<div class="terminal-line">POZOSTAŁE PRÓBY: ${this.attemptsLeft}</div>`;
            html += `<div class="terminal-line">======================</div>`;
            html += `<div class="terminal-line"></div>`;

            // Code display
            let codeDisplay = '';
            for (let i = 0; i < this.code.length; i++) {
                if (i === this.position && this.blinkState) {
                    codeDisplay += `<span class="code-digit active">[${this.code[i]}]</span> `;
                } else {
                    codeDisplay += `<span class="code-digit"> ${this.code[i]} </span> `;
                }
            }
            html += `<div class="terminal-line code-line">${codeDisplay}</div>`;

            this.terminal.innerHTML = html;
        }

        startBlink() {
            this.stopBlink();
            this.blinkInterval = setInterval(() => {
                this.blinkState = !this.blinkState;
                this.render();
            }, 250);
        }

        stopBlink() {
            if (this.blinkInterval) {
                clearInterval(this.blinkInterval);
                this.blinkInterval = null;
            }
        }

        attachKeyboard() {
            // Remove previous listener if any
            if (this.keyHandler) {
                document.removeEventListener('keydown', this.keyHandler);
            }

            this.keyHandler = (e) => this.handleKeyPress(e);
            document.addEventListener('keydown', this.keyHandler);

            // Focus terminal without scrolling
            this.terminal.setAttribute('tabindex', '0');
            this.terminal.focus({ preventScroll: true });
        }

        detachKeyboard() {
            if (this.keyHandler) {
                document.removeEventListener('keydown', this.keyHandler);
                this.keyHandler = null;
            }
        }

        handleKeyPress(e) {
            if (!this.running) return;

            // Check if event target is input or textarea
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return; // Don't interfere with other inputs
            }

            switch (e.key) {
                case 'ArrowUp':
                    e.preventDefault();
                    this.code[this.position] = (this.code[this.position] + 1) % 10;
                    this.render();
                    break;

                case 'ArrowDown':
                    e.preventDefault();
                    this.code[this.position] = (this.code[this.position] - 1 + 10) % 10;
                    this.render();
                    break;

                case 'Enter':
                    e.preventDefault();
                    if (this.position < 3) {
                        this.position++;
                        this.render();
                    } else {
                        this.submitCode();
                    }
                    break;

                case 'Backspace':
                    e.preventDefault();
                    if (this.position > 0) {
                        this.position--;
                        this.render();
                    }
                    break;

                case 'Escape':
                    e.preventDefault();
                    this.reset();
                    break;
            }
        }

        async submitCode() {
            this.stopBlink();
            this.detachKeyboard();

            const success = this.checkCode();
            await this.verificationSequence(success);

            if (!this.running) return;

            if (success) {
                await this.waitForEnter();
                if (!this.running) return;
                this.finish();
            } else {
                this.attemptsLeft--;

                if (this.attemptsLeft > 0) {
                    await this.sleep(1000);
                    if (!this.running) return;
                    this.inputCode();
                } else {
                    await this.terminalBlocked();
                    if (!this.running) return;
                    await this.sleep(2000);
                    this.finish();
                }
            }
        }

        checkCode() {
            return this.code.every((digit, i) => digit === this.targetCode[i]);
        }

        async verificationSequence(success) {
            await this.clearScreen();
            await this.slowPrint("SPRAWDZANIE KODU", '', 60);

            for (let i = 0; i < 3; i++) {
                await this.sleep(400);
                this.terminal.innerHTML += '<span>.</span>';
            }

            await this.sleep(400);

            if (success) {
                await this.slowPrint("\n\nDOSTĘP PRZYZNANY", '', 30);
            } else {
                await this.slowPrint("\n\nBŁĘDNY KOD", '', 30);
            }

            await this.sleep(800);
        }

        async terminalBlocked() {
            await this.clearScreen();
            await this.slowPrint("TERMINAL ZABLOKOWANY", '', 40);
        }

        async waitForEnter() {
            await this.slowPrint("\n\nNACIŚNIJ ENTER, ABY ZAKOŃCZYĆ.", '', 20);

            return new Promise(resolve => {
                const handler = (e) => {
                    if (e.key === 'Enter' || !this.running) {
                        document.removeEventListener('keydown', handler);
                        resolve();
                    }
                };
                document.addEventListener('keydown', handler);
            });
        }

        finish() {
            this.running = false;
            this.stopBlink();
            this.detachKeyboard();
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
        }

        async clearScreen() {
            this.terminal.innerHTML = '';
            return this.sleep(50);
        }

        async slowPrint(text, color = '', delay = 20) {
            const className = color ? `terminal-line ${color}` : 'terminal-line';
            const line = document.createElement('div');
            line.className = className;
            this.terminal.appendChild(line);

            for (let char of text) {
                line.textContent += char;
                await this.sleep(delay);
            }
        }

        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    }

    // Register widgets
    registry.register('terminal-sim', TerminalSimWidget);

    // Auto-initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        registry.initializeAll();
    });

    // Expose registry globally for potential extensions
    window.WidgetRegistry = registry;

})();
