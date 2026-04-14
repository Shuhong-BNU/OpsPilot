from app.services.auth_service import ROLE_ADMIN, ROLE_OPERATOR, auth_service


def test_default_users_can_authenticate():
    auth_service.initialize()

    viewer = auth_service.authenticate("viewer", "viewer123")
    operator = auth_service.authenticate("operator", "operator123")

    assert viewer is not None
    assert operator is not None
    assert viewer["role"] == "viewer"
    assert operator["role"] == ROLE_OPERATOR


def test_jwt_roundtrip():
    auth_service.initialize()
    user = auth_service.authenticate("admin", "admin123")

    token = auth_service.create_access_token(user)
    payload = auth_service.verify_token(token)

    assert payload["sub"] == "admin"
    assert payload["role"] == ROLE_ADMIN


def test_role_hierarchy():
    assert auth_service.require_role("admin", ROLE_OPERATOR) is True
    assert auth_service.require_role("viewer", ROLE_OPERATOR) is False
