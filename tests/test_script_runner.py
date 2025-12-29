"""Tests for script_runner module."""

import time
from pathlib import Path
import pytest
from app import script_runner


@pytest.fixture
def simple_script(tmp_path):
    """Create a simple test script that prints and exits."""
    script = tmp_path / "simple.py"
    script.write_text('print("Hello, World!")\n')
    return script


@pytest.fixture
def interactive_script(tmp_path):
    """Create an interactive script that asks for input."""
    script = tmp_path / "interactive.py"
    script.write_text(
        'name = input("What is your name? ")\n'
        'print(f"Hello, {name}!")\n'
    )
    return script


@pytest.fixture
def timeout_script(tmp_path):
    """Create a script that sleeps briefly."""
    script = tmp_path / "sleep.py"
    script.write_text('import time\ntime.sleep(0.5)\nprint("Done")\n')
    return script


@pytest.fixture
def error_script(tmp_path):
    """Create a script that raises an error."""
    script = tmp_path / "error.py"
    script.write_text('raise ValueError("Test error")\n')
    return script


def test_create_session(app, simple_script):
    """Test creating a new script session."""
    with app.app_context():
        session_id = script_runner.create_session(simple_script)

        assert session_id is not None
        assert isinstance(session_id, str)

        session = script_runner.get_session(session_id)
        assert session is not None
        assert session.script_path == simple_script
        assert not session.is_running

        # Cleanup
        script_runner.destroy_session(session_id)


def test_session_lifecycle(app, simple_script):
    """Test full session lifecycle: create, execute, destroy."""
    with app.app_context():
        session_id = script_runner.create_session(simple_script)

        # Start execution
        assert script_runner.start_execution(session_id)

        # Wait for script to complete
        time.sleep(0.5)

        # Get output
        output = script_runner.get_output(session_id)
        assert len(output) >= 1

        # Should have output and exit messages
        output_messages = [msg for msg in output if msg['type'] == 'output']
        exit_messages = [msg for msg in output if msg['type'] == 'exit']

        assert len(output_messages) >= 1
        # Concatenate all output text (script_runner sends char-by-char)
        full_output = ''.join(msg['text'] for msg in output_messages)
        assert 'Hello, World!' in full_output
        assert len(exit_messages) == 1
        assert exit_messages[0]['code'] == 0

        # Cleanup
        script_runner.destroy_session(session_id)


def test_interactive_script(app, interactive_script):
    """Test interactive script with input."""
    with app.app_context():
        session_id = script_runner.create_session(interactive_script)
        script_runner.start_execution(session_id)

        # Wait for prompt
        time.sleep(0.5)

        output = script_runner.get_output(session_id)
        assert len(output) >= 1

        # Should have output (the prompt from the script)
        assert any(msg['type'] == 'output' for msg in output)

        # Send input
        assert script_runner.send_input(session_id, "Alice")

        # Wait for response
        time.sleep(0.5)

        output = script_runner.get_output(session_id)
        output_text = ''.join(msg.get('text', '') for msg in output if msg['type'] == 'output')

        assert 'Alice' in output_text or 'Hello, Alice!' in output_text

        # Cleanup
        script_runner.destroy_session(session_id)


def test_invalid_session(app):
    """Test operations on nonexistent session."""
    with app.app_context():
        fake_id = "nonexistent-session-id"

        assert script_runner.get_session(fake_id) is None
        assert not script_runner.start_execution(fake_id)
        assert not script_runner.send_input(fake_id, "test")
        assert script_runner.get_output(fake_id) == []
        assert not script_runner.update_activity(fake_id)


def test_double_start(app, timeout_script):
    """Test starting an already running session."""
    with app.app_context():
        session_id = script_runner.create_session(timeout_script)

        # First start should succeed
        assert script_runner.start_execution(session_id)

        # Give thread time to start
        time.sleep(0.1)

        # Second start should fail (already running)
        assert not script_runner.start_execution(session_id)

        # Wait for completion
        time.sleep(1.0)

        # Cleanup
        script_runner.destroy_session(session_id)


def test_script_error_handling(app, error_script):
    """Test script that raises an error."""
    with app.app_context():
        session_id = script_runner.create_session(error_script)
        script_runner.start_execution(session_id)

        # Wait for script to complete execution
        for i in range(30):  # Wait up to 3 seconds
            time.sleep(0.1)
            if not script_runner.is_running(session_id):
                break

        # Give thread a bit more time to write the exit message
        time.sleep(0.2)

        # Get all output
        output = script_runner.get_output(session_id)

        # Should have exit with non-zero code
        exit_messages = [msg for msg in output if msg['type'] == 'exit']
        assert len(exit_messages) == 1, f"Expected 1 exit message, got {len(exit_messages)}. All output: {output}"
        assert exit_messages[0]['code'] != 0

        # Cleanup
        script_runner.destroy_session(session_id)


def test_keepalive_updates_activity(app, simple_script):
    """Test that update_activity updates last_activity timestamp."""
    with app.app_context():
        session_id = script_runner.create_session(simple_script)

        session = script_runner.get_session(session_id)
        initial_activity = session.last_activity

        # Wait a bit
        time.sleep(0.1)

        # Update activity
        assert script_runner.update_activity(session_id)

        session = script_runner.get_session(session_id)
        assert session.last_activity > initial_activity

        # Cleanup
        script_runner.destroy_session(session_id)


def test_is_running_and_waiting(app, interactive_script):
    """Test is_running check."""
    with app.app_context():
        session_id = script_runner.create_session(interactive_script)

        # Not running initially
        assert not script_runner.is_running(session_id)

        # Start execution
        script_runner.start_execution(session_id)
        time.sleep(0.2)

        # Should be running
        assert script_runner.is_running(session_id)

        # Cleanup
        script_runner.destroy_session(session_id)


def test_destroy_session_cleanup(app, simple_script):
    """Test that destroy_session properly cleans up."""
    with app.app_context():
        session_id = script_runner.create_session(simple_script)
        script_runner.start_execution(session_id)

        # Session exists
        assert script_runner.get_session(session_id) is not None

        # Destroy
        assert script_runner.destroy_session(session_id)

        # Session no longer exists
        assert script_runner.get_session(session_id) is None

        # Second destroy should return False
        assert not script_runner.destroy_session(session_id)


def test_cleanup_old_sessions(app, simple_script):
    """Test cleanup of old sessions."""
    with app.app_context():
        # Create and finish a session
        session_id = script_runner.create_session(simple_script)
        script_runner.start_execution(session_id)
        time.sleep(0.5)  # Let it finish

        # Session should exist
        assert script_runner.get_session(session_id) is not None

        # Get session and manually set old timestamp
        session = script_runner.get_session(session_id)
        session.last_activity = time.time() - 3700  # Over 1 hour ago

        # Run cleanup with 1 hour threshold
        script_runner.cleanup_old_sessions(max_age_seconds=3600)

        # Session should be removed
        assert script_runner.get_session(session_id) is None


def test_output_queue_cleared(app, simple_script):
    """Test that get_output clears the queue."""
    with app.app_context():
        session_id = script_runner.create_session(simple_script)
        script_runner.start_execution(session_id)

        time.sleep(0.5)

        # First call gets output
        output1 = script_runner.get_output(session_id)
        assert len(output1) > 0

        # Second immediate call should get empty queue
        output2 = script_runner.get_output(session_id)
        assert len(output2) == 0

        # Cleanup
        script_runner.destroy_session(session_id)
