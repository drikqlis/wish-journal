/**
 * Python Script Terminal - SSE Client
 *
 * Manages interactive Python script execution with real-time I/O via Server-Sent Events (SSE).
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
            this.eventSource = null;
            this.sessionId = null;
            this.hasRunOnce = false;
            this.keepaliveInterval = null;

            // ANSI escape sequence buffer
            this.escapeBuffer = '';

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
            if (!this.hasRunOnce && !this.eventSource) {
                this.handleButtonClick();
            } else if (this.eventSource && !this.input.disabled) {
                // Focus input when clicking terminal while script is running
                this.input.focus({ preventScroll: true });
            }
        }

        /**
         * Handle start/restart button click
         */
        handleButtonClick() {
            if (this.eventSource) {
                // Disconnect existing connection (kills running script)
                this.disconnect();
            }

            // Clear output
            this.clearOutput();

            // Reset escape buffer
            this.escapeBuffer = '';

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

            // Connect to SSE stream
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
         * Connect to SSE stream
         */
        connect() {
            // Build SSE URL
            const url = `/script/stream?path=${encodeURIComponent(this.scriptPath)}`;

            console.log(`[ScriptTerminal] Connecting to ${url}`);

            try {
                this.eventSource = new EventSource(url);

                this.eventSource.addEventListener('session', (event) => this.handleSession(event));
                this.eventSource.addEventListener('output', (event) => this.handleOutput(event));
                this.eventSource.addEventListener('error', (event) => this.handleErrorMsg(event));
                this.eventSource.addEventListener('exit', () => this.handleExit());
                this.eventSource.addEventListener('timeout', () => this.handleTimeout());
                this.eventSource.onerror = (error) => this.handleError(error);
            } catch (error) {
                console.error('[ScriptTerminal] Connection error:', error);
            }
        }

        /**
         * Disconnect from SSE stream
         */
        disconnect() {
            if (this.eventSource) {
                console.log('[ScriptTerminal] Disconnecting...');
                this.eventSource.close();
                this.eventSource = null;
            }

            // Stop script on server side
            if (this.sessionId) {
                this.stopScript();
            }

            this.stopKeepalive();
        }

        /**
         * Handle session event (sent at start with session ID)
         */
        handleSession(event) {
            const data = JSON.parse(event.data);
            this.sessionId = data.session_id;
            console.log('[ScriptTerminal] Connected, session:', this.sessionId);

            // Show running indicator
            this.runningIndicator.classList.add('running');
            this.runningIndicator.textContent = 'Śmigam';

            // Focus input when script starts
            this.input.focus({ preventScroll: true });

            // Start sending keepalive pings every 60 seconds
            this.startKeepalive();
        }

        /**
         * Handle output event
         */
        handleOutput(event) {
            const data = JSON.parse(event.data);
            this.processOutput(data.text);
        }

        /**
         * Process output text, handling ANSI escape codes
         */
        processOutput(text) {
            // Add to escape buffer to handle sequences split across chunks
            this.escapeBuffer += text;

            // Check for clear screen sequence: ESC[2J ESC[H
            // This matches: \x1b[2J\x1b[H (7 bytes total)
            const clearPattern = /\x1b\[2J\x1b\[H/;

            const match = this.escapeBuffer.match(clearPattern);
            if (match) {
                // Get text before the clear sequence
                const beforeClear = this.escapeBuffer.substring(0, match.index);
                if (beforeClear) {
                    this.appendOutput(beforeClear, 'output');
                }

                // Clear the terminal output
                this.clearOutputKeepInput();

                // Keep text after the clear sequence
                this.escapeBuffer = this.escapeBuffer.substring(match.index + match[0].length);
            }

            // Check if buffer is getting too long without a clear sequence
            // This prevents memory issues from accumulating text
            if (this.escapeBuffer.length > 100 && !clearPattern.test(this.escapeBuffer.slice(-10))) {
                // No pending escape sequence, flush the buffer
                this.appendOutput(this.escapeBuffer, 'output');
                this.escapeBuffer = '';
            } else if (this.escapeBuffer.length > 0 && !this.escapeBuffer.includes('\x1b')) {
                // No escape character at all, flush immediately
                this.appendOutput(this.escapeBuffer, 'output');
                this.escapeBuffer = '';
            }
        }

        /**
         * Clear terminal output but keep input container
         */
        clearOutputKeepInput() {
            // Remove all children except input container
            while (this.output.firstChild && this.output.firstChild !== this.inputContainer) {
                this.output.removeChild(this.output.firstChild);
            }
        }

        /**
         * Handle error message event
         */
        handleErrorMsg(event) {
            const data = JSON.parse(event.data);
            this.appendOutput(data.text, 'error');
        }

        /**
         * Handle exit event
         */
        handleExit() {
            console.log('[ScriptTerminal] Script exited');
            // Update indicator to stopped state
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
            // Disable input
            this.disableInput();
            this.disconnect();
        }

        /**
         * Handle timeout event
         */
        handleTimeout() {
            this.appendOutput('\n[Za długo się zastanawiasz, zrestartuj.]', 'error');
            // Update indicator to stopped state
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
            // Disable input
            this.disableInput();
            this.disconnect();
        }

        /**
         * Handle connection error event
         */
        handleError(error) {
            console.error('[ScriptTerminal] SSE error:', error);
            // Connection closed, update UI
            this.runningIndicator.classList.remove('running');
            this.runningIndicator.textContent = 'Nie śmigam';
            this.disableInput();
            this.stopKeepalive();
        }

        /**
         * Send user input to script via POST
         */
        async sendInput(text) {
            if (!this.sessionId) {
                console.error('[ScriptTerminal] Cannot send input: no session');
                return;
            }

            console.log('[ScriptTerminal] Sending input:', text);

            try {
                const response = await fetch('/script/input', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        text: text,
                        csrf_token: window.csrfToken || ''
                    })
                });

                if (!response.ok) {
                    console.error('[ScriptTerminal] Failed to send input:', response.statusText);
                }
            } catch (error) {
                console.error('[ScriptTerminal] Error sending input:', error);
            }
        }

        /**
         * Stop script on server side via POST
         */
        async stopScript() {
            if (!this.sessionId) {
                return;
            }

            console.log('[ScriptTerminal] Stopping script');

            try {
                await fetch('/script/stop', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: this.sessionId,
                        csrf_token: window.csrfToken || ''
                    })
                });
            } catch (error) {
                console.error('[ScriptTerminal] Error stopping script:', error);
            }

            this.sessionId = null;
        }

        /**
         * Start sending keepalive pings
         */
        startKeepalive() {
            this.stopKeepalive(); // Clear any existing interval

            this.keepaliveInterval = setInterval(async () => {
                if (this.sessionId) {
                    console.log('[ScriptTerminal] Sending keepalive');
                    try {
                        await fetch('/script/keepalive', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                session_id: this.sessionId,
                                csrf_token: window.csrfToken || ''
                            })
                        });
                    } catch (error) {
                        console.error('[ScriptTerminal] Keepalive error:', error);
                    }
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
            // Use textContent for plain text
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
                this.input.focus({ preventScroll: true });
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
