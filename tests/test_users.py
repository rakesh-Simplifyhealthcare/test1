from httpx import AsyncClient


async def test_register_and_login(client: AsyncClient) -> None:
    register_response = await client.post(
        "/api/v1/users",
        json={"email": "jane@example.com", "password": "supersecret1", "full_name": "Jane Doe"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "jane@example.com"
    assert "hashed_password" not in body

    duplicate_response = await client.post(
        "/api/v1/users",
        json={"email": "jane@example.com", "password": "supersecret1"},
    )
    assert duplicate_response.status_code == 409

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "jane@example.com", "password": "supersecret1"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "jane@example.com"


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/users",
        json={"email": "bob@example.com", "password": "supersecret1"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "bob@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
