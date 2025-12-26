import pytest

from app.models import (
    add_comment,
    create_user,
    get_comments_for_post,
    get_user_by_id,
    get_user_by_password,
)


def test_create_user(app):
    with app.app_context():
        create_user("Anna", "Nowak", "ania", "secret123")
        user = get_user_by_password("secret123")
        assert user is not None
        assert user["first_name"] == "Anna"
        assert user["last_name"] == "Nowak"
        assert user["username"] == "ania"


def test_password_verification_correct(app):
    with app.app_context():
        create_user("Piotr", "Wisniewski", "piotrek", "mypassword")
        user = get_user_by_password("mypassword")
        assert user is not None
        assert user["username"] == "piotrek"


def test_password_verification_incorrect(app):
    with app.app_context():
        create_user("Piotr", "Wisniewski", "piotrek", "mypassword")
        user = get_user_by_password("wrongpassword")
        assert user is None


def test_get_user_by_id(app):
    with app.app_context():
        create_user("Test", "User", "testuser", "pass123")
        user = get_user_by_password("pass123")
        user_by_id = get_user_by_id(user["id"])
        assert user_by_id is not None
        assert user_by_id["username"] == "testuser"


def test_add_and_get_comments(app):
    with app.app_context():
        create_user("Test", "User", "tester", "pass")
        user = get_user_by_password("pass")

        add_comment("test-post", user["id"], "Swietny wpis!")
        add_comment("test-post", user["id"], "Kolejny komentarz")

        comments = get_comments_for_post("test-post")
        assert len(comments) == 2
        assert comments[0]["content"] == "Swietny wpis!"
        assert comments[1]["content"] == "Kolejny komentarz"
        assert comments[0]["username"] == "tester"


def test_comments_for_different_posts(app):
    with app.app_context():
        create_user("Test", "User", "tester", "pass")
        user = get_user_by_password("pass")

        add_comment("post-1", user["id"], "Komentarz do posta 1")
        add_comment("post-2", user["id"], "Komentarz do posta 2")

        comments_1 = get_comments_for_post("post-1")
        comments_2 = get_comments_for_post("post-2")

        assert len(comments_1) == 1
        assert len(comments_2) == 1
        assert comments_1[0]["content"] == "Komentarz do posta 1"
        assert comments_2[0]["content"] == "Komentarz do posta 2"
