from app.extensions import db


class StatusReserva:
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    RECUSADA = "recusada"
    CANCELADA = "cancelada"
    ATIVAS = (PENDENTE, APROVADA)
    CORES = {PENDENTE: "warning", APROVADA: "success", RECUSADA: "danger", CANCELADA: "secondary"}


class AreaComum(db.Model):
    __tablename__ = "areas_comuns"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    capacidade = db.Column(db.Integer)
    valor_taxa = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<AreaComum {self.nome}>"


class Reserva(db.Model):
    __tablename__ = "reservas"

    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey("areas_comuns.id"), nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    inicio = db.Column(db.Time, nullable=False)
    fim = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(12), nullable=False, default=StatusReserva.PENDENTE)
    observacao = db.Column(db.String(300))
    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    area = db.relationship("AreaComum")
    unidade = db.relationship("Unidade")
    usuario = db.relationship("User")

    @property
    def status_cor(self):
        return StatusReserva.CORES[self.status]

    @staticmethod
    def existe_conflito(area_id, data, inicio, fim, ignorar_id=None):
        q = db.select(Reserva.id).where(
            Reserva.area_id == area_id,
            Reserva.data == data,
            Reserva.status.in_(StatusReserva.ATIVAS),
            Reserva.inicio < fim,
            Reserva.fim > inicio,
        )
        if ignorar_id:
            q = q.where(Reserva.id != ignorar_id)
        return db.session.scalar(q.limit(1)) is not None
