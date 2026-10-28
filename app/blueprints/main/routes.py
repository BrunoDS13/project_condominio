from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (Cobranca, Comunicado, Encomenda, Ocorrencia, Reserva, StatusCobranca,
                        StatusOcorrencia, StatusReserva, Unidade, Visitante)

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    from datetime import date

    cob = db.select(Cobranca).where(Cobranca.status == StatusCobranca.PENDENTE)
    ocor = db.select(Ocorrencia).where(Ocorrencia.status != StatusOcorrencia.RESOLVIDA)
    res = db.select(Reserva).where(Reserva.status == StatusReserva.PENDENTE)
    if not current_user.is_gestor:
        cob = cob.where(Cobranca.unidade_id == current_user.unidade_id)
        ocor = ocor.where(Ocorrencia.usuario_id == current_user.id)
        res = res.where(Reserva.unidade_id == current_user.unidade_id)

    pendentes = db.session.scalars(cob).all()
    stats = {
        "unidades": db.session.scalar(db.select(db.func.count(Unidade.id)).where(Unidade.ativa)),
        "em_aberto": sum(c.valor_atualizado() for c in pendentes),
        "atrasadas": sum(1 for c in pendentes if c.atrasada),
        "ocorrencias": len(db.session.scalars(ocor).all()),
        "reservas": len(db.session.scalars(res).all()),
    }
    comunicados = db.session.scalars(
        db.select(Comunicado).order_by(Comunicado.fixado.desc(), Comunicado.criado_em.desc()).limit(5)
    ).all()
    visitas = db.select(db.func.count(Visitante.id)).where(Visitante.saida_em.is_(None))
    encom = db.select(db.func.count(Encomenda.id)).where(Encomenda.retirada_em.is_(None))
    if not (current_user.is_gestor or current_user.role == "porteiro"):
        visitas = visitas.where(Visitante.unidade_id == current_user.unidade_id)
        encom = encom.where(Encomenda.unidade_id == current_user.unidade_id)
    stats["visitantes"] = db.session.scalar(visitas)
    stats["encomendas"] = db.session.scalar(encom)
    em_atraso = sorted((c for c in pendentes if c.atrasada), key=lambda c: c.vencimento)[:5]
    return render_template("dashboard.html", stats=stats, em_atraso=em_atraso, comunicados=comunicados, hoje=date.today())
