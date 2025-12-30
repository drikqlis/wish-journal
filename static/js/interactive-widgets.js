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

    /**
     * Entry Widget (questionnaire)
     * Recreates entry.py with inline text inputs
     */
    class EntryWidget {
        constructor(element) {
            this.element = element;
            this.config = this.parseConfig(element.dataset.config);
            this.running = false;
            this.hasRunOnce = false;

            this.terminal = document.createElement('div');
            this.terminal.className = 'widget-terminal';
            this.element.appendChild(this.terminal);

            this.controls = document.createElement('div');
            this.controls.className = 'widget-controls';
            this.element.appendChild(this.controls);

            this.button = document.createElement('button');
            this.button.className = 'widget-start';
            this.button.setAttribute('aria-label', 'Uruchom widget');
            const icon = document.createElement('span');
            icon.className = 'widget-icon';
            icon.innerHTML = getIcon('play');
            this.button.appendChild(icon);

            this.runningIndicator = document.createElement('span');
            this.runningIndicator.className = 'widget-running-indicator';

            this.controls.appendChild(this.button);
            this.controls.appendChild(this.runningIndicator);

            this.button.addEventListener('click', () => this.handleButtonClick());
            this.terminal.addEventListener('click', () => this.handleTerminalClick());

            this.terminal.innerHTML = '<span style="color: var(--text-dim); font-style: italic;">Uruchom skrypt...</span>';
            this.terminal.classList.add('clickable');
        }

        parseConfig(configStr) {
            try {
                return configStr ? JSON.parse(configStr) : {};
            } catch (e) {
                return {};
            }
        }

        handleTerminalClick() {
            // If there's an active input, focus it
            if (this.currentInput && !this.currentInput.disabled) {
                this.currentInput.focus({ preventScroll: true });
                // Position cursor at end (after "> " prefix)
                const cursorPos = this.currentInput.value.length;
                this.currentInput.setSelectionRange(cursorPos, cursorPos);
                return;
            }

            // Otherwise, start the widget if not running
            if (!this.running && !this.hasRunOnce) {
                this.handleButtonClick();
            }
        }

        handleButtonClick() {
            if (this.running) {
                this.stop();
            }

            if (!this.hasRunOnce) {
                this.hasRunOnce = true;
                this.button.className = 'widget-restart';
                this.button.setAttribute('aria-label', 'Restart widgetu');
                const icon = this.button.querySelector('.widget-icon');
                if (icon) {
                    icon.innerHTML = getIcon('restart');
                }
                this.terminal.classList.remove('clickable');
            }

            this.start();
        }

        stop() {
            this.running = false;
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
        }

        start() {
            this.running = true;
            this.runningIndicator.classList.add('running');
            this.runningIndicator.textContent = 'Śmigam';
            this.run();
        }

        async run() {
            await this.clearScreen();
            if (!this.running) return;

            await this.slowPrint("Czego pragniesz najbardziej na świecie?", '', 30);
            await this.getInput();
            if (!this.running) return;

            await this.analyzing(5);
            if (!this.running) return;

            await this.slowPrint("Co jesteś w stanie za to oddać?", '', 30);
            await this.getInput();
            if (!this.running) return;

            await this.analyzing(5);
            if (!this.running) return;

            await this.slowPrint("Cena będzie wyższa. Czy chcesz kontynuować? (tak/nie)", '', 30);
            const decyzja = await this.getInput();
            if (!this.running) return;

            await this.sleep(500);
            if (!this.running) return;

            if (decyzja.toLowerCase().trim() === 'tak') {
                await this.slowPrint("Załóż animator i przekrocz barierę. Terminacja...", '', 30);
            } else {
                await this.slowPrint("Opuść placówkę. Terminacja...", '', 30);
            }

            await this.sleep(1000);
            this.finish();
        }

        async analyzing(seconds) {
            await this.slowPrint("Analizowanie", '', 50);
            for (let i = 0; i < 3; i++) {
                await this.sleep(seconds * 1000 / 3);
                if (!this.running) return;
                this.terminal.lastChild.textContent += '.';
                this.terminal.scrollTop = this.terminal.scrollHeight;
            }
        }

        async getInput() {
            return new Promise(resolve => {
                const inputLine = document.createElement('div');
                inputLine.className = 'terminal-line';

                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'terminal-input';
                input.value = '> ';
                input.autofocus = true;
                inputLine.appendChild(input);

                this.terminal.appendChild(inputLine);
                this.terminal.scrollTop = this.terminal.scrollHeight;
                input.focus({ preventScroll: true });

                // Store reference to current input for terminal click handler
                this.currentInput = input;

                // Position cursor after "> "
                input.setSelectionRange(2, 2);

                const handler = (e) => {
                    // Prevent deleting the "> " prefix
                    if ((e.key === 'Backspace' || e.key === 'Delete') && input.selectionStart <= 2) {
                        e.preventDefault();
                        input.setSelectionRange(2, 2);
                        return;
                    }

                    if (e.key === 'ArrowLeft' && input.selectionStart <= 2) {
                        e.preventDefault();
                        return;
                    }

                    if (e.key === 'Enter') {
                        const value = input.value.substring(2); // Remove "> " prefix
                        input.disabled = true;
                        input.removeEventListener('keydown', handler);
                        this.currentInput = null; // Clear reference
                        resolve(value);
                    }
                };

                input.addEventListener('keydown', handler);

                // Ensure cursor stays after "> " on click
                input.addEventListener('click', () => {
                    if (input.selectionStart < 2) {
                        input.setSelectionRange(2, 2);
                    }
                });
            });
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
                if (!this.running) return;
                line.textContent += char;
                this.terminal.scrollTop = this.terminal.scrollHeight;
                await this.sleep(delay);
            }
        }

        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        finish() {
            this.running = false;
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
        }
    }

    /**
     * Soul Reanimation Widget (light.py)
     */
    class SoulReanimationWidget extends EntryWidget {
        constructor(element) {
            super(element);
            this.allowedSouls = this.config.souls || ["ASTRA", "XELLA", "RICHARD", "JD", "PIERCE", "DIVENSON"];
            this.maxReanimations = this.config.max || 5;
            this.remaining = this.maxReanimations;
        }

        handleButtonClick() {
            this.remaining = this.maxReanimations;
            super.handleButtonClick();
        }

        async run() {
            await this.clearScreen();
            if (!this.running) return;

            await this.slowPrint("Kto był mordeczą duszą?", '', 30);
            const answer = await this.getInput();
            if (!this.running) return;

            if (answer.toLowerCase().trim() !== 'wszyscy') {
                await this.slowPrint("Błędna odpowiedź, terminacja...", '', 30);
                await this.sleep(2000);
                this.finish();
                return;
            }

            await this.slowPrint("Rezydualna zawartość plazmowa umożliwia wybiórczą reanimację.", '', 30);
            await this.slowPrint(`Pozostało ${this.remaining} możliwych reanimacji.`, '', 30);

            while (this.remaining > 0 && this.running) {
                await this.slowPrint("Podaj imię duszy:", '', 30);
                const name = await this.getInput();
                if (!this.running) return;

                const nameUpper = name.trim().toUpperCase();

                if (this.allowedSouls.includes(nameUpper)) {
                    await this.reanimateSequence(nameUpper);
                    if (!this.running) return;

                    this.remaining--;

                    if (this.remaining > 0) {
                        await this.slowPrint(`Pozostało ${this.remaining} możliwych reanimacji.`, '', 30);
                    } else {
                        await this.slowPrint("Limit reanimacji został wyczerpany. Proces zakończony.", '', 30);
                    }
                } else {
                    await this.slowPrint("Zbyt mała rezydualna zawartość plazmowa,", '', 30);
                    await this.slowPrint("by umożliwić pełną animację wybranej duszy bez kotwiczenia.", '', 30);
                    await this.slowPrint("Skonsultuj się z wyższym bytem.", '', 30);
                }
            }

            await this.sleep(2000);
            this.finish();
        }

        async reanimateSequence(name) {
            await this.slowPrint("Animowanie...", '', 30);
            await this.sleep(1500);
            await this.slowPrint("Inicjacja procesu biologicznego sprzężenia...", '', 30);
            await this.slowPrint("Ładowanie pamięci długoterminowej...", '', 30);
            await this.slowPrint("Synchronizacja wzorców neuronalnych...", '', 30);
            await this.slowPrint("Połączenie z siecią biometryczną...", '', 30);
            await this.slowPrint(`Obiekt ${name} został pomyślnie animowany.`, '', 30);
            await this.plasmaLoadingBar(60, 60);
        }

        async plasmaLoadingBar(totalTime, length) {
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.textContent = 'Ładowanie baterii plazmowej:\n[';
            this.terminal.appendChild(line);
            this.terminal.scrollTop = this.terminal.scrollHeight;

            const delayPerChar = totalTime * 1000 / length;

            for (let i = 0; i < length; i++) {
                if (!this.running) return;
                await this.sleep(delayPerChar);
                line.textContent += '█';
                this.terminal.scrollTop = this.terminal.scrollHeight;
            }

            line.textContent += ']';
            this.terminal.scrollTop = this.terminal.scrollHeight;
            await this.sleep(1000);
        }
    }

    /**
     * Dangerous Reanimation Widget (light2.py)
     */
    class DangerousReanimationWidget extends SoulReanimationWidget {
        constructor(element) {
            super(element);
            this.allowedSoul = this.config.soul || "DON";
        }

        async run() {
            await this.clearScreen();
            if (!this.running) return;

            await this.slowPrint("Rezydualna zawartość plazmowa umożliwia wybiórczą reanimację.", '', 30);
            await this.slowPrint("Pozostało 1 możliwych reanimacji.", '', 30);

            await this.slowPrint("Podaj imię duszy:", '', 30);
            const name = await this.getInput();
            if (!this.running) return;

            await this.slowPrint("Lokalizowanie duszy...", '', 30);
            await this.sleep(1000);
            if (!this.running) return;

            const nameUpper = name.trim().toUpperCase();

            if (nameUpper === this.allowedSoul) {
                await this.dangerousReanimation(nameUpper);
            } else {
                await this.slowPrint("Nie zlokalizowano duszy.", '', 30);
                await this.sleep(2000);
            }

            this.finish();
        }

        async dangerousReanimation(name) {
            await this.slowPrint("Reanimacja duszy bez odpowiedniego katharsis może spowodować ", '', 30);
            await this.slowPrint("przeładowanie baterii plazmowej i eksplozję placówki.", '', 30);
            await this.slowPrint("Czy chcesz kontynuować? (tak/nie)", '', 30);

            const decision = await this.getInput();
            if (!this.running) return;

            if (decision.toLowerCase().trim() !== 'tak') {
                await this.slowPrint("Procedura przerwana przez operatora.", '', 30);
                await this.sleep(1000);
                return;
            }

            await this.slowPrint(`Rozpoczynanie procedury reanimacji duszy: ${name}...`, '', 30);
            await this.sleep(1000);
            await this.slowPrint("Łączenie z wymiarem pośrednim...", '', 30);
            await this.sleep(1500);
            await this.slowPrint("Stabilizacja sygnału emocjonalnego...", '', 30);
            await this.sleep(1200);
            await this.slowPrint("Synchronizacja wspomnień z eterem...", '', 30);
            await this.sleep(1200);
            await this.slowPrint("Połączenie ustanowione.", '', 30);
            await this.slowPrint("Pertraktacja z bytem wyższym...", '', 30);
            await this.sleep(1200);
            if (!this.running) return;

            await this.slowPrint("KRYTYCZNY BŁĄD NEGOCJACJI!", 'error', 40);
            await this.slowPrint("Nieuchronna eksplozja systemu plazmowego!", 'error', 40);
            await this.slowPrint("Zaleca się opuścić placówkę w zorganizowanym pośpiechu.", '', 30);
            await this.sleep(1000);
            await this.slowPrint("Trzeba było nie wychodzić ze statku.", '', 30);
            await this.sleep(2000);
        }
    }

    /**
     * Object Animation Widget (anim.py)
     */
    class ObjectAnimationWidget extends SoulReanimationWidget {
        constructor(element) {
            super(element);
            this.objects = this.config.objects || [
                "OB-J467D", "OB-X377A", "OB-A576A",
                "OB-P136E", "OB-D158N", "OB-R134D"
            ];
            this.animated = new Set();
        }

        handleButtonClick() {
            this.animated = new Set();
            EntryWidget.prototype.handleButtonClick.call(this);
        }

        async run() {
            await this.clearScreen();
            if (!this.running) return;

            await this.slowPrint(`Odnaleziono ${this.objects.length} obiektów.`, '', 30);
            await this.sleep(500);

            while (this.animated.size < this.objects.length && this.running) {
                await this.showTable();
                if (!this.running) return;

                await this.slowPrint("Czy animować któryś z obiektów? (tak/nie)", '', 30);
                const decision = await this.getInput();
                if (!this.running) return;

                if (decision.toLowerCase().trim() !== 'tak') {
                    await this.slowPrint("Anulowano. Sekwencja wygaszania.", '', 30);
                    await this.sleep(2000);
                    this.finish();
                    return;
                }

                await this.slowPrint("Podaj numer porządkowy (Lp) obiektu do animowania:", '', 30);
                const choice = await this.getInput();
                if (!this.running) return;

                const choiceNum = parseInt(choice.trim());

                if (isNaN(choiceNum) || choiceNum < 1 || choiceNum > this.objects.length) {
                    await this.slowPrint("To nie jest poprawny numer.", '', 30);
                    await this.sleep(1000);
                } else if (this.animated.has(choiceNum)) {
                    await this.slowPrint("Nieprawidłowy wybór lub obiekt już animowany.", '', 30);
                    await this.sleep(1000);
                } else {
                    await this.clearScreen();
                    await this.animateObject(this.objects[choiceNum - 1]);
                    if (!this.running) return;
                    this.animated.add(choiceNum);
                    await this.clearScreen();
                }
            }

            if (this.running && this.animated.size === this.objects.length) {
                await this.showTable();
                await this.slowPrint("Wszystkie obiekty zostały pomyślnie animowane. Proces zakończony.", '', 30);
                await this.sleep(2000);
            }

            this.finish();
        }

        async showTable() {
            const table = document.createElement('div');
            table.className = 'terminal-line';

            let html = '\nLp | Obiekt       | Status\n';
            html += '---|--------------|----------------\n';

            for (let i = 0; i < this.objects.length; i++) {
                const lp = i + 1;
                const obj = this.objects[i];
                const status = this.animated.has(lp) ? 'Animowany' : 'Podtrzymywanie';
                html += `${lp.toString().padEnd(3)}| ${obj.padEnd(12)} | ${status}\n`;
            }

            table.textContent = html;
            this.terminal.appendChild(table);
            this.terminal.scrollTop = this.terminal.scrollHeight;
        }

        async animateObject(objectCode) {
            await this.slowPrint("Animowanie...", '', 30);
            await this.sleep(1500);
            await this.slowPrint("Inicjacja procesu biologicznego sprzężenia...", '', 30);
            await this.slowPrint("Ładowanie pamięci długoterminowej...", '', 30);
            await this.slowPrint("Synchronizacja wzorców neuronalnych...", '', 30);
            await this.slowPrint("Połączenie z siecią biometryczną...", '', 30);
            await this.slowPrint(`Obiekt ${objectCode} został pomyślnie animowany.`, '', 30);
            await this.plasmaLoadingBar(120, 60);
        }
    }

    // Register widgets
    registry.register('terminal-sim', TerminalSimWidget);
    registry.register('entry', EntryWidget);
    registry.register('soul-reanimation', SoulReanimationWidget);
    registry.register('dangerous-reanimation', DangerousReanimationWidget);
    registry.register('object-animation', ObjectAnimationWidget);

    // Auto-initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        registry.initializeAll();
    });

    // Expose registry globally for potential extensions
    window.WidgetRegistry = registry;

})();
