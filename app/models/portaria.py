from app.extensions import db

TIPOS_VISITANTE = [
    ("visitante", "Visitante"),
    ("prestador", "Prestador de serviço"),
    ("entregador", "Entregador"),
]

TIPOS_VEICULO = [("carro", "Carro"), ("moto", "Moto")]


class Visitante(db.Model):
    __tablename__ = "visitantes"

    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    documento = db.Column(db.String(30))
    tipo = db.Column(db.String(15), nullable=False, default="visitante")
    placa = db.Column(db.String(8))
    observacao = db.Column(db.String(300))
    entrada_em = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)
    saida_em = db.Column(db.DateTime)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    unidade = db.relationship("Unidade")
    registrado_por = db.relationship("User")

    @property
    def dentro(self):
        return self.saida_em is None

    @property
    def tipo_label(self):
        return dict(TIPOS_VISITANTE).get(self.tipo, self.tipo)


class Encomenda(db.Model):
    __tablename__ = "encomendas"

    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    remetente = db.Column(db.String(120))
    recebida_em = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    recebida_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    retirada_em = db.Column(db.DateTime)
    retirada_por = db.Column(db.String(120))

    unidade = db.relationship("Unidade")
    recebida_por = db.relationship("User")

    @property
    def aguardando(self):
        return self.retirada_em is None


class Veiculo(db.Model):
    __tablename__ = "veiculos"

    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=False, index=True)
    placa = db.Column(db.String(8), nullable=False, unique=True)
    tipo = db.Column(db.String(10), nullable=False, default="carro")
    modelo = db.Column(db.String(60))
    cor = db.Column(db.String(30))
    vaga = db.Column(db.String(10))
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    unidade = db.relationship("Unidade")

    @property
    def tipo_label(self):
        return dict(TIPOS_VEICULO).get(self.tipo, self.tipo)
