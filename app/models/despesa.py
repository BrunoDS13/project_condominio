from app.extensions import db

CATEGORIAS_DESPESA = [
    ("agua_luz", "Água e luz"),
    ("folha", "Folha de pagamento"),
    ("manutencao", "Manutenção"),
    ("limpeza", "Limpeza"),
    ("seguranca", "Segurança"),
    ("administrativa", "Administrativa"),
    ("seguro_impostos", "Seguro e impostos"),
    ("outros", "Outros"),
]

FONTE_CAIXA = "caixa"
FONTE_RESERVA = "reserva"
FONTES_DESPESA = [(FONTE_CAIXA, "Caixa do condomínio"), (FONTE_RESERVA, "Fundo de reserva")]


class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(20), nullable=False, default="outros")
    descricao = db.Column(db.String(200), nullable=False)
    fornecedor = db.Column(db.String(120))
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    fonte = db.Column(db.String(10), nullable=False, default=FONTE_CAIXA)
    comprovante = db.Column(db.String(80))  # nome do arquivo em instance/comprovantes
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    criado_por = db.relationship("User")

    @property
    def categoria_label(self):
        return dict(CATEGORIAS_DESPESA).get(self.categoria, self.categoria)


class AporteReserva(db.Model):
    """Transferência do caixa para o fundo de reserva."""

    __tablename__ = "aportes_reserva"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False, default="Aporte ao fundo de reserva")
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    criado_por = db.relationship("User")
