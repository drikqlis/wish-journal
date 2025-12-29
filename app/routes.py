import json
import mimetypes
import time

from flask import Blueprint, Response, current_app, flash, g, redirect, render_template, request, url_for

from . import content, models, script_runner, utils
from .auth import login_required

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def index():
    posts = content.get_posts()
    return render_template("index.html", posts=posts)


@bp.route("/post/<slug>")
@login_required
def post(slug: str):
    post_data = content.get_post(slug)
    if not post_data:
        return render_template("404.html"), 404

    comments = models.get_comments_for_post(slug)
    transformed_comments = []
    for comment in comments:
        transformed_comments.append(
            {
                "id": comment["id"],
                "username": comment["username"],
                "first_name": comment["first_name"],
                "content": comment["content"],
                "display_date": utils.format_date_polish(comment["created_at"], include_time=True),
            }
        )

    csrf_token = utils.generate_csrf_token()

    show_success = request.args.get("success") == "1"

    return render_template(
        "post.html",
        post=post_data,
        comments=transformed_comments,
        csrf_token=csrf_token,
        show_success=show_success,
    )


@bp.route("/post/<slug>/comment", methods=["POST"])
@login_required
def add_comment(slug: str):
    token = request.form.get("csrf_token")
    if not utils.validate_csrf_token(token):
        flash("Nieprawidlowy token bezpieczenstwa", "error")
        return redirect(url_for("main.post", slug=slug))

    post_data = content.get_post(slug)
    if not post_data:
        return render_template("404.html"), 404

    comment_content = request.form.get("content", "").strip()
    if not comment_content:
        flash("Komentarz nie moze byc pusty", "error")
        return redirect(url_for("main.post", slug=slug) + "#comment-form")

    models.add_comment(slug, g.user["id"], comment_content)
    return redirect(url_for("main.post", slug=slug, success="1") + "#comment-form")


@bp.route("/media/<path:path>")
@login_required
def media(path: str):
    media_path = content.get_media_path(path)
    if not media_path:
        return "Nie znaleziono", 404

    mime_type, _ = mimetypes.guess_type(str(media_path))

    with open(media_path, "rb") as f:
        file_content = f.read()

    # Check if download is requested
    is_download = request.args.get("download") == "1"

    response = Response(file_content, mimetype=mime_type or "application/octet-stream")

    # Add Content-Disposition header for downloads
    if is_download:
        filename = path.split("/")[-1]
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


def script_websocket(ws):
    """
    WebSocket endpoint for interactive Python script execution.

    Query parameters:
        path: Script path (relative to content/scripts/)
        csrf_token: CSRF token for validation

    Message protocol (JSON):
        Client -> Server:
            {type: "input", text: "..."}     - User input
            {type: "keepalive"}              - Keepalive ping (resets timeout)

        Server -> Client:
            {type: "output", text: "..."}    - Script output
            {type: "error", text: "..."}     - Error message
            {type: "input_request", prompt: "..."} - Script waiting for input
            {type: "exit", code: 0}          - Script finished
            {type: "timeout"}                - Execution timeout
    """
    session_id = None

    try:
        # Validate CSRF token
        csrf_token = request.args.get("csrf_token", "")
        if not utils.validate_csrf_token(csrf_token):
            current_app.logger.warning("WebSocket: Invalid CSRF token")
            ws.send(json.dumps({
                "type": "error",
                "text": "Nieprawidłowy token bezpieczeństwa"
            }))
            return

        # Validate script path
        script_path_str = request.args.get("path", "")
        script_path = content.get_script_path(script_path_str)

        if not script_path:
            current_app.logger.warning(f"WebSocket: Invalid script path: {script_path_str}")
            ws.send(json.dumps({
                "type": "error",
                "text": f"Nie znaleziono skryptu: {script_path_str}"
            }))
            return

        # Create and start session
        session_id = script_runner.create_session(script_path)
        current_app.logger.info(f"WebSocket: Created session {session_id}")

        if not script_runner.start_execution(session_id):
            ws.send(json.dumps({
                "type": "error",
                "text": "Nie udało się uruchomić skryptu"
            }))
            return

        # Send session_id to client (for debugging)
        current_app.logger.debug(f"WebSocket: Session {session_id} started")

        # Main communication loop
        while True:
            # Check if session still exists and is running
            if not script_runner.get_session(session_id):
                current_app.logger.info(f"WebSocket: Session {session_id} no longer exists")
                break

            # Poll for output from script (non-blocking)
            output_messages = script_runner.get_output(session_id)
            for msg in output_messages:
                try:
                    ws.send(json.dumps(msg))
                except Exception as e:
                    # Client disconnected - stop processing
                    current_app.logger.info(f"WebSocket: Client disconnected for session {session_id}")
                    return

                # If script exited or timed out, break
                if msg["type"] in ("exit", "timeout"):
                    current_app.logger.info(
                        f"WebSocket: Session {session_id} {msg['type']}"
                    )
                    # Give client time to receive message
                    time.sleep(0.1)
                    return

            # Check for client messages (non-blocking with timeout)
            try:
                message = ws.receive(timeout=0.1)
                if message:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "input":
                            # Send user input to script
                            text = data.get("text", "")
                            if script_runner.send_input(session_id, text):
                                current_app.logger.debug(
                                    f"WebSocket: Sent input to session {session_id}"
                                )
                            else:
                                current_app.logger.warning(
                                    f"WebSocket: Failed to send input to session {session_id}"
                                )

                        elif msg_type == "keepalive":
                            # Update activity timestamp to prevent timeout
                            script_runner.update_activity(session_id)
                            current_app.logger.debug(
                                f"WebSocket: Keepalive for session {session_id}"
                            )

                    except json.JSONDecodeError:
                        current_app.logger.warning(
                            f"WebSocket: Invalid JSON from client: {message}"
                        )

            except Exception as e:
                # Timeout or connection error - continue loop
                if "timed out" not in str(e).lower():
                    current_app.logger.debug(f"WebSocket receive error: {e}")

            # Small sleep to prevent CPU spinning
            time.sleep(0.05)

    except Exception as e:
        current_app.logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            ws.send(json.dumps({
                "type": "error",
                "text": "Błąd serwera"
            }))
        except:
            pass

    finally:
        # Cleanup session
        if session_id:
            script_runner.destroy_session(session_id)
            current_app.logger.info(f"WebSocket: Cleaned up session {session_id}")
