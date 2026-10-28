import pytest

from app import create_app
from app.extensions import db
from app.models import Role, Unidade, User


@pytest.fixture
def app():
    app = create_app("test")
    with app.app_context():
        db.create_all()
        u = Unidade(bloco="A", numero="101")
        db.session.add(u)
        for nome, role in [("Admin", Role.ADMIN), ("Morador", Role.MORADOR)]:
            user = User(nome=nome, email=f"{role}@t.com", role=role, unidade=u if role == Role.MORADOR else None)
            user.set_password("senha1234")
            db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, role):
    return client.post("/auth/login", data={"email": f"{role}@t.com", "senha": "senha1234"})
