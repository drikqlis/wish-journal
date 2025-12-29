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


@bp.route("/script/stream")
@login_required
def script_stream():
    """
    SSE endpoint for streaming Python script output in real-time.

    Query parameters:
        path: Script path (relative to content/scripts/)
        session_id: Optional session ID to resume existing session

    SSE event types:
        output: Script output text
        error: Error message
        exit: Script finished (with exit code in data)
        timeout: Execution timeout
        session: Session ID (sent at start)
    """
    # Validate script path
    script_path_str = request.args.get("path", "")
    script_path = content.get_script_path(script_path_str)

    if not script_path:
        current_app.logger.warning(f"SSE: Invalid script path: {script_path_str}")
        return Response(
            f"event: error\ndata: {json.dumps({'text': f'Nie znaleziono skryptu: {script_path_str}'})}\n\n",
            mimetype="text/event-stream"
        )

    # Create or get session
    session_id = request.args.get("session_id")
    if not session_id:
        session_id = script_runner.create_session(script_path)
        current_app.logger.info(f"SSE: Created session {session_id}")

        if not script_runner.start_execution(session_id):
            return Response(
                f"event: error\ndata: {json.dumps({'text': 'Nie udało się uruchomić skryptu'})}\n\n",
                mimetype="text/event-stream"
            )

    def generate():
        """Generator function for SSE stream."""
        try:
            # Send session ID to client
            yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"

            # Stream output
            while True:
                # Check if session still exists
                if not script_runner.get_session(session_id):
                    current_app.logger.info(f"SSE: Session {session_id} no longer exists")
                    break

                # Poll for output from script (non-blocking)
                output_messages = script_runner.get_output(session_id)
                for msg in output_messages:
                    msg_type = msg.get("type", "output")

                    # Send as SSE event
                    yield f"event: {msg_type}\ndata: {json.dumps(msg)}\n\n"

                    # If script exited or timed out, stop streaming
                    if msg_type in ("exit", "timeout"):
                        current_app.logger.info(f"SSE: Session {session_id} {msg_type}")
                        return

                # Small sleep to prevent CPU spinning
                time.sleep(0.01)

        except GeneratorExit:
            # Client disconnected
            current_app.logger.info(f"SSE: Client disconnected from session {session_id}")
        except Exception as e:
            current_app.logger.error(f"SSE error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'text': 'Błąd serwera'})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@bp.route("/script/input", methods=["POST"])
@login_required
def script_input():
    """
    POST endpoint for sending input to running script.

    JSON body:
        session_id: Session to send input to
        text: Input text
        csrf_token: CSRF token for validation
    """
    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

    # Validate CSRF token
    csrf_token = data.get("csrf_token", "")
    if not utils.validate_csrf_token(csrf_token):
        current_app.logger.warning("Script input: Invalid CSRF token")
        return {"error": "Nieprawidłowy token bezpieczeństwa"}, 403

    session_id = data.get("session_id")
    text = data.get("text", "")

    if not session_id:
        return {"error": "Missing session_id"}, 400

    if script_runner.send_input(session_id, text):
        script_runner.update_activity(session_id)  # Reset timeout
        return {"success": True}
    else:
        return {"error": "Failed to send input"}, 500


@bp.route("/script/keepalive", methods=["POST"])
@login_required
def script_keepalive():
    """
    POST endpoint for keepalive pings.

    JSON body:
        session_id: Session to keep alive
        csrf_token: CSRF token for validation
    """
    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

    # Validate CSRF token
    csrf_token = data.get("csrf_token", "")
    if not utils.validate_csrf_token(csrf_token):
        return {"error": "Nieprawidłowy token bezpieczeństwa"}, 403

    session_id = data.get("session_id")
    if not session_id:
        return {"error": "Missing session_id"}, 400

    if script_runner.update_activity(session_id):
        return {"success": True}
    else:
        return {"error": "Session not found"}, 404


@bp.route("/script/stop", methods=["POST"])
@login_required
def script_stop():
    """
    POST endpoint for stopping a running script.

    JSON body:
        session_id: Session to stop
        csrf_token: CSRF token for validation
    """
    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

    # Validate CSRF token
    csrf_token = data.get("csrf_token", "")
    if not utils.validate_csrf_token(csrf_token):
        return {"error": "Nieprawidłowy token bezpieczeństwa"}, 403

    session_id = data.get("session_id")
    if not session_id:
        return {"error": "Missing session_id"}, 400

    if script_runner.destroy_session(session_id):
        return {"success": True}
    else:
        return {"error": "Session not found"}, 404
