from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Role:
    ADMIN = "admin"
    SINDICO = "sindico"
    MORADOR = "morador"
    PORTEIRO = "porteiro"

    CHOICES = [
        (ADMIN, "Administrador"),
        (SINDICO, "Síndico"),
        (MORADOR, "Morador"),
        (PORTEIRO, "Porteiro"),
    ]
    GESTORES = (ADMIN, SINDICO)


class User(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    telefone = db.Column(db.String(20))
    senha_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.MORADOR)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"))
    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    unidade = db.relationship("Unidade", back_populates="moradores")

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_gestor(self):
        return self.role in Role.GESTORES

    @property
    def role_label(self):
        return dict(Role.CHOICES).get(self.role, self.role)

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
