from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from flask import current_app

from app.extensions import db

CENTAVO = Decimal("0.01")
ZERO = Decimal("0.00")


class StatusCobranca:
    PENDENTE = "pendente"
    PAGA = "paga"
    CANCELADA = "cancelada"
    CHOICES = [(PENDENTE, "Pendente"), (PAGA, "Paga"), (CANCELADA, "Cancelada")]


class Cobranca(db.Model):
    __tablename__ = "cobrancas"

    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=False, default="Taxa condominial")
    competencia = db.Column(db.Date, nullable=False)  # sempre dia 1 do mês
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(12), nullable=False, default=StatusCobranca.PENDENTE, index=True)
    pago_em = db.Column(db.Date)
    valor_pago = db.Column(db.Numeric(10, 2))
    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    unidade = db.relationship("Unidade", back_populates="cobrancas")

    def dias_atraso(self, ref=None):
        if self.status != StatusCobranca.PENDENTE:
            return 0
        return max(((ref or date.today()) - self.vencimento).days, 0)

    def multa(self, ref=None):
        if not self.dias_atraso(ref):
            return ZERO
        pct = Decimal(str(current_app.config["MULTA_PERCENTUAL"]))
        return (self.valor * pct / 100).quantize(CENTAVO, ROUND_HALF_UP)

    def juros(self, ref=None):
        dias = self.dias_atraso(ref)
        if not dias:
            return ZERO
        pct = Decimal(str(current_app.config["JUROS_MENSAL_PERCENTUAL"]))
        return (self.valor * pct / 100 / 30 * dias).quantize(CENTAVO, ROUND_HALF_UP)

    def valor_atualizado(self, ref=None):
        """Valor + multa + juros (só para pendentes em atraso)."""
        return self.valor + self.multa(ref) + self.juros(ref)

    @property
    def atrasada(self):
        return self.status == StatusCobranca.PENDENTE and self.vencimento < date.today()

    @property
    def status_label(self):
        if self.atrasada:
            return "Atrasada"
        return dict(StatusCobranca.CHOICES).get(self.status, self.status)

    @property
    def status_cor(self):
        if self.atrasada:
            return "danger"
        return {"pendente": "warning", "paga": "success", "cancelada": "secondary"}[self.status]
