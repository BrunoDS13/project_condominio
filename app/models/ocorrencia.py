from app.extensions import db


class StatusOcorrencia:
    ABERTA = "aberta"
    ANDAMENTO = "em_andamento"
    RESOLVIDA = "resolvida"
    CHOICES = [(ABERTA, "Aberta"), (ANDAMENTO, "Em andamento"), (RESOLVIDA, "Resolvida")]
    CORES = {ABERTA: "danger", ANDAMENTO: "warning", RESOLVIDA: "success"}


CATEGORIAS_OCORRENCIA = [
    ("manutencao", "Manutenção"),
    ("barulho", "Barulho"),
    ("seguranca", "Segurança"),
    ("limpeza", "Limpeza"),
    ("outros", "Outros"),
]


class Ocorrencia(db.Model):
    __tablename__ = "ocorrencias"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"))
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(20), nullable=False, default="outros")
    status = db.Column(db.String(15), nullable=False, default=StatusOcorrencia.ABERTA, index=True)
    resposta = db.Column(db.Text)
    criada_em = db.Column(db.DateTime, server_default=db.func.now())
    atualizada_em = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    usuario = db.relationship("User")
    unidade = db.relationship("Unidade")

    @property
    def status_cor(self):
        return StatusOcorrencia.CORES[self.status]

    @property
    def status_label(self):
        return dict(StatusOcorrencia.CHOICES)[self.status]

    @property
    def categoria_label(self):
        return dict(CATEGORIAS_OCORRENCIA).get(self.categoria, self.categoria)
