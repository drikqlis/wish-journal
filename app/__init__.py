import os
from flask import Flask


def create_app(config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 7 * 24 * 60 * 60  # 7 days

    app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", "/data/wish-journal.db")
    app.config["CONTENT_PATH"] = os.environ.get("CONTENT_PATH", "/content")

    if config:
        app.config.update(config)

    from . import models
    models.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import routes
    app.register_blueprint(routes.bp)

    from . import content
    with app.app_context():
        content.load_posts()
        content.start_watcher(app)

    from . import utils
    app.jinja_env.filters["format_date"] = utils.format_date_polish

    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    return app
