from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.blueprints.financeiro.routes import resumo_mes
from app.extensions import db
from app.models import (Cobranca, Comunicado, Encomenda, Ocorrencia, Reserva, Role, StatusCobranca,
                        StatusOcorrencia, StatusReserva, Unidade, Veiculo, Visitante)
from app.utils import brl

bp = Blueprint("main", __name__)


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


def _andar(numero):
    """'302' -> 3; numeração sem andar (ex.: 'Casa 4') fica sem rótulo."""
    return int(numero[:-2]) if numero.isdigit() and len(numero) >= 3 else None


def montar_fachada(unidades, atraso_por_unidade):
    """Agrupa as unidades por bloco e andar para desenhar a fachada do condomínio."""
    blocos = {}
    for u in unidades:
        info = atraso_por_unidade.get(u.id, {"qtd": 0, "total": 0})
        blocos.setdefault(u.bloco, {}).setdefault(_andar(u.numero), []).append(
            {"id": u.id, "numero": u.numero, "identificacao": u.identificacao, "qtd": info["qtd"], "total": info["total"]})
    resultado = []
    for nome in sorted(blocos):
        andares = []
        # andares de cima para baixo, como na fachada; sem andar vai ao final
        for chave in sorted(blocos[nome], key=lambda k: (k is None, -(k or 0))):
            rotulo = f"{chave}º" if chave is not None else ""
            andares.append({"rotulo": rotulo, "unidades": sorted(blocos[nome][chave], key=lambda x: x["numero"])})
        resultado.append({"nome": nome if nome.lower().startswith("bloco") else f"Bloco {nome}", "andares": andares})
    return resultado


@bp.route("/")
@login_required
def dashboard():
    hoje = date.today()
    perfil = "gestor" if current_user.is_gestor else ("porteiro" if current_user.role == Role.PORTEIRO else "morador")
    ctx = {"hoje": hoje, "perfil": perfil}

    ctx["comunicados"] = db.session.scalars(
        db.select(Comunicado).order_by(Comunicado.fixado.desc(), Comunicado.criado_em.desc()).limit(4)).all()

    if perfil == "gestor":
        pendentes = db.session.scalars(db.select(Cobranca).where(Cobranca.status == StatusCobranca.PENDENTE)).all()
        atrasadas = [c for c in pendentes if c.atrasada]
        por_unidade = {}
        for c in atrasadas:
            u = por_unidade.setdefault(c.unidade_id, {"qtd": 0, "total": 0})
            u["qtd"] += 1
            u["total"] += c.valor_atualizado()
        total_atraso = sum((c.valor_atualizado() for c in atrasadas), 0)
        unidades = db.session.scalars(
            db.select(Unidade).where(Unidade.ativa).order_by(Unidade.bloco, Unidade.numero)).all()
        mes = resumo_mes(hoje.year, hoje.month)

        n_res = db.session.scalar(db.select(db.func.count(Reserva.id)).where(Reserva.status == StatusReserva.PENDENTE))
        n_oco = db.session.scalar(db.select(db.func.count(Ocorrencia.id)).where(Ocorrencia.status != StatusOcorrencia.RESOLVIDA))
        n_enc = db.session.scalar(db.select(db.func.count(Encomenda.id)).where(Encomenda.retirada_em.is_(None)))
        n_vis = db.session.scalar(db.select(db.func.count(Visitante.id)).where(Visitante.saida_em.is_(None)))

        ctx.update(
            titulo_sub=(f"<strong>{plural(len(atrasadas), 'cobrança em atraso', 'cobranças em atraso')}</strong> em "
                        f"{plural(len(por_unidade), 'unidade', 'unidades')}: {brl(total_atraso)} a receber, com multa e juros."
                        if atrasadas else "Nenhuma cobrança em atraso. As taxas estão em dia."),
            total_atraso=total_atraso, n_atrasadas=len(atrasadas), mes=mes,
            fachada=montar_fachada(unidades, por_unidade),
            em_atraso=sorted(atrasadas, key=lambda c: c.vencimento)[:5],
            fila=[
                {"n": n_res, "rotulo": "Reservas aguardando aprovação", "sub": "Aprove ou recuse", "url": "reservas.listar"},
                {"n": n_oco, "rotulo": "Ocorrências abertas", "sub": "Responda os moradores", "url": "ocorrencias.listar"},
                {"n": n_enc, "rotulo": "Encomendas aguardando retirada", "sub": "Na portaria", "url": "encomendas.listar"},
                {"n": n_vis, "rotulo": "Visitantes no condomínio", "sub": "Entraram e ainda não saíram", "url": "visitantes.listar"},
            ])

    elif perfil == "porteiro":
        dentro = db.session.scalars(
            db.select(Visitante).where(Visitante.saida_em.is_(None)).order_by(Visitante.entrada_em.desc()).limit(8)).all()
        aguardando = db.session.scalars(
            db.select(Encomenda).where(Encomenda.retirada_em.is_(None)).order_by(Encomenda.recebida_em).limit(8)).all()
        n_vis = db.session.scalar(db.select(db.func.count(Visitante.id)).where(Visitante.saida_em.is_(None)))
        n_enc = db.session.scalar(db.select(db.func.count(Encomenda.id)).where(Encomenda.retirada_em.is_(None)))
        ctx.update(
            titulo_sub=(f"<strong>{'Ninguém registrado no condomínio agora' if not n_vis else plural(n_vis, 'pessoa', 'pessoas') + ' no condomínio agora'}</strong> e "
                        f"{'nenhuma encomenda aguardando' if not n_enc else plural(n_enc, 'encomenda aguardando', 'encomendas aguardando')} retirada."),
            dentro=dentro, aguardando=aguardando, n_vis=n_vis, n_enc=n_enc,
            proximas_reservas=db.session.scalars(
                db.select(Reserva).where(Reserva.status == StatusReserva.APROVADA, Reserva.data >= hoje,
                                         Reserva.data <= hoje + timedelta(days=7)).order_by(Reserva.data, Reserva.inicio).limit(6)).all())

    else:
        uid = current_user.unidade_id
        abertas = db.session.scalars(
            db.select(Cobranca).where(Cobranca.unidade_id == uid, Cobranca.status == StatusCobranca.PENDENTE)
            .order_by(Cobranca.vencimento)).all() if uid else []
        total = sum((c.valor_atualizado() for c in abertas), 0)
        encomendas = db.session.scalars(
            db.select(Encomenda).where(Encomenda.unidade_id == uid, Encomenda.retirada_em.is_(None))
            .order_by(Encomenda.recebida_em)).all() if uid else []
        reservas = db.session.scalars(
            db.select(Reserva).where(Reserva.unidade_id == uid, Reserva.data >= hoje,
                                     Reserva.status.in_(StatusReserva.ATIVAS)).order_by(Reserva.data).limit(4)).all() if uid else []
        atrasadas = [c for c in abertas if c.atrasada]
        ctx.update(
            titulo_sub=(f"<strong>{plural(len(abertas), 'cobrança em aberto', 'cobranças em aberto')}</strong>, "
                        f"{brl(total)}{' — ' + plural(len(atrasadas), 'vencida', 'vencidas') if atrasadas else ''}."
                        if abertas else "Nenhuma cobrança em aberto para a sua unidade."),
            abertas=abertas[:5], total_aberto=total, n_abertas=len(abertas),
            encomendas=encomendas[:5], n_encomendas=len(encomendas), reservas=reservas,
            minhas_ocorrencias=db.session.scalars(db.select(Ocorrencia).where(Ocorrencia.usuario_id == current_user.id)
                                                  .order_by(Ocorrencia.criada_em.desc()).limit(4)).all(),
            meus_veiculos=db.session.scalars(db.select(Veiculo).where(Veiculo.unidade_id == uid, Veiculo.ativo)
                                             .order_by(Veiculo.placa)).all() if uid else [])

    return render_template("dashboard.html", **ctx)
