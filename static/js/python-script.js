/**
 * Python Script Terminal - WebSocket Client
 *
 * Manages interactive Python script execution with real-time I/O via WebSocket.
 * Supports keepalive, timeout handling, and dynamic button state management.
 */

(function() {
    'use strict';

    // Initialize all script terminals on page load
    document.addEventListener('DOMContentLoaded', function() {
        const scriptWrappers = document.querySelectorAll('.script-wrapper');

        scriptWrappers.forEach(wrapper => {
            new ScriptTerminal(wrapper);
        });
    });

    /**
     * ScriptTerminal Class
     * Manages a single script terminal instance
     */
    class ScriptTerminal {
        constructor(wrapper) {
            this.wrapper = wrapper;
            this.scriptPath = wrapper.dataset.scriptPath;

            // DOM elements
            this.terminal = wrapper.querySelector('.script-terminal');
            this.output = wrapper.querySelector('.script-output');
            this.inputContainer = wrapper.querySelector('.script-input-container');
            this.input = wrapper.querySelector('.script-input');
            this.button = wrapper.querySelector('.script-start');
            this.runningIndicator = wrapper.querySelector('.script-running-indicator');

            // Initialize the play icon
            const icon = this.button.querySelector('.script-icon');
            if (icon) {
                icon.innerHTML = getIcon('play');
            }

            // State
            this.ws = null;
            this.hasRunOnce = false;
            this.keepaliveInterval = null;

            // Move input container into output area (at the top initially)
            this.output.appendChild(this.inputContainer);

            // Input is always visible and enabled (script controls when to use it)
            this.enableInput(false); // Don't focus initially

            // Make terminal clickable initially (before first run)
            this.terminal.classList.add('clickable');

            // Bind event handlers
            this.button.addEventListener('click', () => this.handleButtonClick());
            this.input.addEventListener('keydown', (e) => this.handleInputKeyDown(e));

            // Make terminal clickable to start script (only when not running)
            this.terminal.addEventListener('click', () => this.handleTerminalClick());

            console.log(`[ScriptTerminal] Initialized for script: ${this.scriptPath}`);
        }

        /**
         * Handle terminal click - start script if not running, or focus input if running
         */
        handleTerminalClick() {
            // Only start if script hasn't been started yet
            if (!this.hasRunOnce && !this.ws) {
                this.handleButtonClick();
            } else if (this.ws && !this.input.disabled) {
                // Focus input when clicking terminal while script is running
                this.input.focus();
            }
        }

        /**
         * Handle start/restart button click
         */
        handleButtonClick() {
            if (this.ws) {
                // Disconnect existing connection (kills running script)
                this.disconnect();
            }

            // Clear output
            this.clearOutput();

            // Re-enable input for new script run (don't focus yet, will focus on connection)
            this.enableInput(false);

            // Clear indicator text
            this.runningIndicator.textContent = '';

            // Update button to "Restart" after first run
            if (!this.hasRunOnce) {
                this.hasRunOnce = true;
                this.button.classList.remove('script-start');
                this.button.classList.add('script-restart');
                this.button.setAttribute('aria-label', 'Restart skryptu');

                // Change icon from play to restart
                const icon = this.button.querySelector('.script-icon');
                if (icon) {
                    icon.innerHTML = getIcon('restart');
                }

                // Remove clickable state from terminal
                this.terminal.classList.remove('clickable');
            }

            // Connect to WebSocket
            this.connect();
        }

        /**
         * Handle Enter key in input field
         */
        handleInputKeyDown(e) {
            if (e.key === 'Enter' && !this.input.disabled) {
                const text = this.input.value;
                this.sendInput(text);
                this.input.value = '';
            }
        }

        /**
         * Connect to WebSocket server
         */
        connect() {
            // Get CSRF token from global variable
            const csrfToken = window.csrfToken || '';
            if (!csrfToken) {
                console.error('[ScriptTerminal] Missing CSRF token');
                return;
            }

            // Build WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const url = `${protocol}//${host}/script/ws?path=${encodeURIComponent(this.scriptPath)}&csrf_token=${encodeURIComponent(csrfToken)}`;

            console.log(`[ScriptTerminal] Connecting to ${url}`);

            try {
                this.ws = new WebSocket(url);

                this.ws.onopen = () => this.handleOpen();
                this.ws.onmessage = (event) => this.handleMessage(event);
                this.ws.onclose = () => this.handleClose();
                this.ws.onerror = (error) => this.handleError(error);
            } catch (error) {
                console.error('[ScriptTerminal] Connection error:', error);
            }
        }

        /**
         * Disconnect from WebSocket
         */
        disconnect() {
            if (this.ws) {
                console.log('[ScriptTerminal] Disconnecting...');
                this.ws.close();
                this.ws = null;
            }

            this.stopKeepalive();
        }

        /**
         * Handle WebSocket open event
         */
        handleOpen() {
            console.log('[ScriptTerminal] Connected');
            // Button stays enabled to allow restart while running

            // Show running indicator
            this.runningIndicator.classList.add('running');
            this.runningIndicator.textContent = 'Śmigam';

            // Focus input when script starts
            this.input.focus();

            // Start sending keepalive pings every 60 seconds
            this.startKeepalive();
        }

        /**
         * Handle WebSocket message event
         */
        handleMessage(event) {
            try {
                const message = JSON.parse(event.data);
                console.log('[ScriptTerminal] Received:', message.type);

                switch (message.type) {
                    case 'output':
                        this.appendOutput(message.text, 'output');
                        break;

                    case 'error':
                        this.appendOutput(message.text, 'error');
                        break;

                    case 'exit':
                        // Update indicator to stopped state
                        this.runningIndicator.classList.remove('running');
                        this.runningIndicator.textContent = 'Nie śmigam';
                        // Disable input
                        this.disableInput();
                        this.disconnect();
                        break;

                    case 'timeout':
                        this.appendOutput('\n[Za długo się zastanawiasz, zrestartuj.]', 'error');
                        // Update indicator to stopped state
                        this.runningIndicator.classList.remove('running');
                        this.runningIndicator.textContent = 'Nie śmigam';
                        // Disable input
                        this.disableInput();
                        this.disconnect();
                        break;

                    default:
                        console.warn('[ScriptTerminal] Unknown message type:', message.type);
                }
            } catch (error) {
                console.error('[ScriptTerminal] Message parsing error:', error);
            }
        }

        /**
         * Handle WebSocket close event
         */
        handleClose() {
            console.log('[ScriptTerminal] Disconnected');
            // Update indicator to stopped state on disconnect
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
            // Disable input
            this.disableInput();
            this.stopKeepalive();
        }

        /**
         * Handle WebSocket error event
         */
        handleError(error) {
            console.error('[ScriptTerminal] WebSocket error:', error);
        }

        /**
         * Send user input to script
         */
        sendInput(text) {
            if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                console.error('[ScriptTerminal] Cannot send input: not connected');
                return;
            }

            console.log('[ScriptTerminal] Sending input:', text);

            // Send to server
            this.ws.send(JSON.stringify({
                type: 'input',
                text: text
            }));

            // Keep input enabled - user can send more input anytime
        }

        /**
         * Start sending keepalive pings
         */
        startKeepalive() {
            this.stopKeepalive(); // Clear any existing interval

            this.keepaliveInterval = setInterval(() => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    console.log('[ScriptTerminal] Sending keepalive');
                    this.ws.send(JSON.stringify({ type: 'keepalive' }));
                }
            }, 60000); // 60 seconds
        }

        /**
         * Stop sending keepalive pings
         */
        stopKeepalive() {
            if (this.keepaliveInterval) {
                clearInterval(this.keepaliveInterval);
                this.keepaliveInterval = null;
            }
        }

        /**
         * Append text to terminal output
         */
        appendOutput(text, type = 'output') {
            // Remove empty class on first output
            this.output.classList.remove('empty');

            const span = document.createElement('span');
            span.className = type === 'error' ? 'output-error' : 'output-line';
            // Use textContent for plain text (ANSI codes stripped on server)
            span.textContent = text;

            // Insert before input container to keep input at the bottom
            this.output.insertBefore(span, this.inputContainer);

            // Auto-scroll to bottom
            this.terminal.scrollTop = this.terminal.scrollHeight;
        }

        /**
         * Clear terminal output
         */
        clearOutput() {
            this.output.innerHTML = '';
            // Add empty class back
            this.output.classList.add('empty');
            // Re-add input container after clearing
            this.output.appendChild(this.inputContainer);
        }

        /**
         * Enable input field
         * @param {boolean} shouldFocus - Whether to focus the input field (default: true)
         */
        enableInput(shouldFocus = true) {
            this.inputContainer.classList.add('visible');
            this.input.disabled = false;
            if (shouldFocus) {
                this.input.focus();
            }
        }

        /**
         * Disable input field
         */
        disableInput() {
            this.inputContainer.classList.remove('visible');
            this.input.disabled = true;
        }
    }

})();
