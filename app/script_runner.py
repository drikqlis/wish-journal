"""
Script Runner Module - Executes Python scripts with interactive I/O via pexpect.

This module provides server-side subprocess execution for trusted Python scripts
with real-time terminal emulation, supporting interactive input() calls
and keepalive-based timeout tracking.
"""

import uuid
import threading
import time
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, List
import pexpect
from flask import current_app

# Logger for background threads (where current_app is not available)
logger = logging.getLogger(__name__)

# Configuration
TIMEOUT_SECONDS = 300  # 5 minutes
KEEPALIVE_INTERVAL = 60  # Client sends keepalive every 60 seconds


@dataclass
class ScriptSession:
    """Represents an active script execution session."""

    session_id: str
    script_path: Path
    process: Optional[pexpect.spawn] = None
    thread: Optional[threading.Thread] = None
    output_queue: List[Dict[str, str]] = field(default_factory=list)
    is_running: bool = False
    exit_code: Optional[int] = None
    last_activity: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)


# Thread-safe session storage
_sessions: Dict[str, ScriptSession] = {}
_sessions_lock = threading.Lock()


def create_session(script_path: Path) -> str:
    """
    Create a new script execution session.

    Args:
        script_path: Absolute path to the Python script to execute

    Returns:
        session_id: Unique identifier for this session
    """
    session_id = str(uuid.uuid4())

    session = ScriptSession(
        session_id=session_id,
        script_path=script_path
    )

    with _sessions_lock:
        _sessions[session_id] = session

    current_app.logger.info(f"Created session {session_id} for script {script_path}")
    return session_id


def get_session(session_id: str) -> Optional[ScriptSession]:
    """Get session by ID (thread-safe)."""
    with _sessions_lock:
        return _sessions.get(session_id)


def update_activity(session_id: str) -> bool:
    """
    Update last_activity timestamp for keepalive tracking.

    Args:
        session_id: Session to update

    Returns:
        True if session exists and was updated, False otherwise
    """
    session = get_session(session_id)
    if not session:
        return False

    with session.lock:
        session.last_activity = time.time()

    current_app.logger.debug(f"Session {session_id} activity updated")
    return True


def _run_script(session: ScriptSession):
    """
    Background thread function that executes the script using pexpect.

    Handles:
    - Script output streaming
    - Input prompt detection
    - Timeout tracking based on last_activity
    - Exit code capture
    - ANSI color support
    """
    try:
        logger.info(f"Starting script execution: {session.script_path}")

        # Spawn Python process with pexpect using the same Python interpreter as Flask
        session.process = pexpect.spawn(
            sys.executable,
            [str(session.script_path)],
            encoding='utf-8',
            timeout=10,  # Short timeout for read operations
            env={
                'PYTHONUNBUFFERED': '1'  # Disable output buffering
            }
        )

        with session.lock:
            session.is_running = True
            session.last_activity = time.time()

        # Main execution loop
        while True:
            # Check for global timeout (based on last_activity, not start time)
            with session.lock:
                elapsed_since_activity = time.time() - session.last_activity
                if elapsed_since_activity > TIMEOUT_SECONDS:
                    logger.warning(
                        f"Session {session.session_id} timed out "
                        f"({elapsed_since_activity:.1f}s since last activity)"
                    )
                    session.output_queue.append({
                        'type': 'timeout',
                        'text': ''
                    })
                    break

            try:
                # Read available output with a short timeout
                try:
                    # Read single byte for smooth character-by-character streaming
                    output_text = session.process.read_nonblocking(size=1, timeout=0.1)

                    if output_text:
                        with session.lock:
                            session.output_queue.append({
                                'type': 'output',
                                'text': output_text
                            })

                except pexpect.TIMEOUT:
                    # No output available - just continue
                    pass

                except pexpect.EOF:
                    # Process ended
                    session.process.close()
                    exit_code = session.process.exitstatus

                    with session.lock:
                        session.exit_code = exit_code
                        session.is_running = False
                        session.output_queue.append({
                            'type': 'exit',
                            'code': exit_code if exit_code is not None else 0
                        })

                    logger.info(
                        f"Script finished with exit code {exit_code}"
                    )
                    break

            except Exception as e:
                logger.error(f"Error reading from process: {e}", exc_info=True)
                break

            # Small sleep to prevent CPU spinning
            time.sleep(0.01)

    except Exception as e:
        logger.error(f"Script execution error: {e}", exc_info=True)

        with session.lock:
            session.is_running = False
            session.output_queue.append({
                'type': 'error',
                'text': f"Błąd wykonania skryptu: {str(e)}"
            })

    finally:
        # Ensure process is terminated
        if session.process and session.process.isalive():
            session.process.terminate(force=True)

        with session.lock:
            session.is_running = False


def start_execution(session_id: str) -> bool:
    """
    Start executing the script in a background thread.

    Args:
        session_id: Session to start

    Returns:
        True if started successfully, False if session not found or already running
    """
    session = get_session(session_id)
    if not session:
        current_app.logger.error(f"Session {session_id} not found")
        return False

    with session.lock:
        if session.is_running:
            current_app.logger.warning(f"Session {session_id} already running")
            return False

        # Clear previous state
        session.output_queue.clear()
        session.exit_code = None
        session.last_activity = time.time()

        # Start execution thread
        session.thread = threading.Thread(
            target=_run_script,
            args=(session,),
            daemon=True
        )
        session.thread.start()

    current_app.logger.info(f"Started execution for session {session_id}")
    return True


def send_input(session_id: str, text: str) -> bool:
    """
    Send user input to the running script.

    Args:
        session_id: Session to send input to
        text: Input text (will be sent with newline)

    Returns:
        True if input sent successfully, False otherwise
    """
    session = get_session(session_id)
    if not session:
        current_app.logger.error(f"Session {session_id} not found")
        return False

    with session.lock:
        if not session.is_running or not session.process:
            current_app.logger.error(f"Session {session_id} not running")
            return False

        try:
            # Send input with newline
            session.process.sendline(text)
            session.last_activity = time.time()  # Reset timeout on input

            current_app.logger.debug(f"Sent input to session {session_id}: {text}")
            return True

        except Exception as e:
            current_app.logger.error(f"Error sending input: {e}", exc_info=True)
            return False


def get_output(session_id: str) -> List[Dict[str, str]]:
    """
    Get accumulated output from the script (non-blocking).

    Returns all queued output messages and clears the queue.

    Args:
        session_id: Session to get output from

    Returns:
        List of output messages, each with 'type' and content fields
    """
    session = get_session(session_id)
    if not session:
        return []

    with session.lock:
        output = session.output_queue.copy()
        session.output_queue.clear()
        return output


def is_running(session_id: str) -> bool:
    """Check if session is currently running."""
    session = get_session(session_id)
    if not session:
        return False

    with session.lock:
        return session.is_running


def destroy_session(session_id: str) -> bool:
    """
    Terminate the script and cleanup session resources.

    Args:
        session_id: Session to destroy

    Returns:
        True if destroyed successfully, False if not found
    """
    session = get_session(session_id)
    if not session:
        return False

    current_app.logger.info(f"Destroying session {session_id}")

    # Terminate process
    with session.lock:
        if session.process and session.process.isalive():
            session.process.terminate(force=True)
        session.is_running = False

    # Remove from registry
    with _sessions_lock:
        _sessions.pop(session_id, None)

    current_app.logger.info(f"Session {session_id} destroyed")
    return True


def cleanup_old_sessions(max_age_seconds: int = 3600):
    """
    Remove sessions that haven't been active for a long time.

    This is a maintenance function that should be called periodically
    to prevent memory leaks from abandoned sessions.

    Args:
        max_age_seconds: Maximum age in seconds (default: 1 hour)
    """
    now = time.time()
    to_remove = []

    with _sessions_lock:
        for session_id, session in _sessions.items():
            with session.lock:
                age = now - session.last_activity
                if age > max_age_seconds and not session.is_running:
                    to_remove.append(session_id)

    for session_id in to_remove:
        destroy_session(session_id)

    if to_remove:
        current_app.logger.info(f"Cleaned up {len(to_remove)} old sessions")
