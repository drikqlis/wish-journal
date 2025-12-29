import functools
from typing import Callable

from flask import Blueprint, g, redirect, render_template, request, session, url_for

from . import models

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = models.get_user_by_id(user_id)


def login_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        password = request.form.get("password", "")

        user = models.get_user_by_password(password)

        if user is None:
            return redirect(url_for("auth.login", error=1))
        else:
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            return redirect(url_for("main.index"))

    show_error = request.args.get("error") == "1"
    return render_template("login.html", show_error=show_error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
