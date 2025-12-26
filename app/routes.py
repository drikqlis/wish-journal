import mimetypes

from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from . import content, models, utils
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

    return Response(file_content, mimetype=mime_type or "application/octet-stream")
