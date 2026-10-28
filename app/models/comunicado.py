from app.extensions import db


class Comunicado(db.Model):
    __tablename__ = "comunicados"

    id = db.Column(db.Integer, primary_key=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    corpo = db.Column(db.Text, nullable=False)
    fixado = db.Column(db.Boolean, nullable=False, default=False)
    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    autor = db.relationship("User")
