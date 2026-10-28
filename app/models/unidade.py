from app.extensions import db


class Unidade(db.Model):
    __tablename__ = "unidades"
    __table_args__ = (db.UniqueConstraint("bloco", "numero", name="uq_unidade_bloco_numero"),)

    id = db.Column(db.Integer, primary_key=True)
    bloco = db.Column(db.String(10), nullable=False, default="Único")
    numero = db.Column(db.String(10), nullable=False)
    area_m2 = db.Column(db.Numeric(8, 2))
    fracao_ideal = db.Column(db.Numeric(8, 6))
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    moradores = db.relationship("User", back_populates="unidade")
    cobrancas = db.relationship("Cobranca", back_populates="unidade", cascade="all, delete-orphan")

    @property
    def identificacao(self):
        return f"{self.bloco} - {self.numero}"

    def __repr__(self):
        return f"<Unidade {self.identificacao}>"
