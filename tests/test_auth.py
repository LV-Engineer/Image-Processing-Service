def test_signup_success(client):
    resp = client.post('/auth/signup', json={'email': 'a@example.com', 'password': 'Passw0rd!'})
    assert resp.status_code == 201
    body = resp.json()
    assert body['email'] == 'a@example.com'
    assert 'id' in body

def test_signup_duplicate_email(client):
    client.post('/auth/signup', json={'email': 'dup@example.com', 'password': 'Passw0rd!'})
    resp = client.post('/auth/signup', json={'email': 'dup@example.com', 'password': 'Passw0rd!'})
    assert resp.status_code == 400

def test_login_success(client):
    client.post('/auth/signup', json={'email': 'b@example.com', 'password': 'Passw0rd!'})
    resp = client.post('/auth/login', json={'email': 'b@example.com', 'password': 'Passw0rd!'})
    assert resp.status_code == 200
    assert 'access_token' in resp.json()

def test_login_wrong_password(client):
    client.post('/auth/signup', json={'email': 'c@example.com', 'password': 'Passw0rd!'})
    resp = client.post('/auth/login', json={'email': 'c@example.com', 'password': 'wrong'})
    assert resp.status_code == 401

def test_me_requires_auth(client):
    resp = client.get('/auth/me')
    assert resp.status_code == 401

def test_me_with_token(client):
    client.post('/auth/signup', json={'email': 'd@example.com', 'password': 'Passw0rd!'})
    token = client.post('/auth/login', json={'email': 'd@example.com', 'password': 'Passw0rd!'}).json()['access_token']
    resp = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert resp.json()['email'] == 'd@example.com'

def test_me_with_invalid_token(client):
    resp = client.get('/auth/me', headers={'Authorization': 'Bearer not-a-real-token'})
    assert resp.status_code == 401

def test_me_with_token_for_deleted_user(client, db_session):
    from models.user import User

    client.post('/auth/signup', json={'email': 'e@example.com', 'password': 'Passw0rd!'})
    token = client.post('/auth/login', json={'email': 'e@example.com', 'password': 'Passw0rd!'}).json()['access_token']

    db_session.query(User).filter(User.email == 'e@example.com').delete()
    db_session.commit()

    resp = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 401