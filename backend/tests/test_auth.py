from sqlalchemy import select

from app.models import User

PASSWORD = "correct-horse-battery"
LOGIN = {"email": "a@example.com", "password": PASSWORD}


def _register(client, email="a@example.com", password=PASSWORD):
    return client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )


def test_register_creates_user_and_hashes_password(client, db_session):
    response = _register(client)
    assert response.status_code == 201
    assert response.json()["email"] == "a@example.com"
    assert "password_hash" not in response.json()
    user = db_session.scalars(select(User)).one()
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_register_normalizes_email_and_rejects_duplicates(client):
    assert _register(client, "A@Example.com").status_code == 201
    assert _register(client, "a@example.com").status_code == 409


def test_register_rejects_short_passwords(client):
    assert _register(client, password="short").status_code == 422


def test_login_sets_httponly_cookie_and_me_works(client):
    _register(client)
    response = client.post("/api/auth/login", json=LOGIN)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "access_token=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_login_fails_the_same_way_for_wrong_password_and_unknown_email(client):
    _register(client)
    wrong = client.post(
        "/api/auth/login", json={"email": "a@example.com", "password": "wrong-password-1"}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert "set-cookie" not in wrong.headers


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_the_session(client):
    _register(client)
    client.post("/api/auth/login", json=LOGIN)
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_tampered_token_is_rejected(client):
    client.cookies.set("access_token", "not.a.real.token", domain="testserver")
    assert client.get("/api/auth/me").status_code == 401


def test_inactive_user_cannot_log_in(client, db_session):
    _register(client)
    user = db_session.scalars(select(User)).one()
    user.is_active = False
    db_session.commit()
    assert client.post("/api/auth/login", json=LOGIN).status_code == 401