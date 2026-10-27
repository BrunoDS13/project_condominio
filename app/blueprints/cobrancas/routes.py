import csv
import io
from datetime import date
from decimal import Decimal

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField
from wtforms.validators import DataRequired, Length, NumberRange

from app.extensions import db
from app.models import Cobranca, StatusCobranca, Unidade
from app.utils import brl, gestor_required, primeiro_dia_mes

bp = Blueprint("cobrancas", __name__)


class CobrancaForm(FlaskForm):
    unidade_id = SelectField("Unidade", coerce=int)
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)], default="Taxa condominial")
    competencia = DateField("Competência (qualquer dia do mês)", validators=[DataRequired()])
    valor = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    vencimento = DateField("Vencimento", validators=[DataRequired()])


class GerarLoteForm(FlaskForm):
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)], default="Taxa condominial")
    competencia = DateField("Competência (qualquer dia do mês)", validators=[DataRequired()])
    valor = DecimalField("Valor por unidade (R$)", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    vencimento = DateField("Vencimento", validators=[DataRequired()])


def _unidades_ativas():
    return db.session.scalars(
        db.select(Unidade).where(Unidade.ativa).order_by(Unidade.bloco, Unidade.numero)
    ).all()


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    q = db.select(Cobranca).order_by(Cobranca.vencimento.desc(), Cobranca.id.desc())
    unidade = None
    if not current_user.is_gestor:
        q = q.where(Cobranca.unidade_id == current_user.unidade_id)
    elif request.args.get("unidade", type=int):
        unidade = db.session.get(Unidade, request.args.get("unidade", type=int))
        if unidade:
            q = q.where(Cobranca.unidade_id == unidade.id)
    if status == "atrasada":
        q = q.where(Cobranca.status == StatusCobranca.PENDENTE, Cobranca.vencimento < date.today())
    elif status in dict(StatusCobranca.CHOICES):
        q = q.where(Cobranca.status == status)
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("cobrancas/lista.html", pag=pag, status=status, unidade=unidade)


@bp.route("/nova", methods=["GET", "POST"])
@gestor_required
def nova():
    form = CobrancaForm()
    form.unidade_id.choices = [(u.id, u.identificacao) for u in _unidades_ativas()]
    if form.validate_on_submit():
        db.session.add(Cobranca(
            unidade_id=form.unidade_id.data, descricao=form.descricao.data.strip(),
            competencia=primeiro_dia_mes(form.competencia.data), valor=form.valor.data,
            vencimento=form.vencimento.data))
        db.session.commit()
        flash("Cobrança criada.", "success")
        return redirect(url_for("cobrancas.listar"))
    return render_template("form.html", form=form, titulo="Nova cobrança", voltar=url_for("cobrancas.listar"))


@bp.route("/lote", methods=["GET", "POST"])
@gestor_required
def lote():
    """Gera a mesma cobrança para todas as unidades ativas (ignora as já geradas na competência)."""
    form = GerarLoteForm()
    if form.validate_on_submit():
        comp = primeiro_dia_mes(form.competencia.data)
        descricao = form.descricao.data.strip()
        ja = set(db.session.scalars(
            db.select(Cobranca.unidade_id).where(
                Cobranca.competencia == comp, Cobranca.descricao == descricao,
                Cobranca.status != StatusCobranca.CANCELADA)))
        criadas = 0
        for u in _unidades_ativas():
            if u.id in ja:
                continue
            db.session.add(Cobranca(unidade_id=u.id, descricao=descricao, competencia=comp,
                                    valor=form.valor.data, vencimento=form.vencimento.data))
            criadas += 1
        db.session.commit()
        flash(f"{criadas} cobrança(s) gerada(s).", "success")
        return redirect(url_for("cobrancas.listar"))
    return render_template("form.html", form=form, titulo="Gerar cobranças em lote",
                           voltar=url_for("cobrancas.listar"))


@bp.route("/<int:id>/pagar", methods=["POST"])
@gestor_required
def pagar(id):
    c = db.get_or_404(Cobranca, id)
    if c.status != StatusCobranca.PENDENTE:
        abort(400)
    total = c.valor_atualizado()
    c.status, c.pago_em, c.valor_pago = StatusCobranca.PAGA, date.today(), total
    db.session.commit()
    extra = f" (inclui {brl(total - c.valor)} de multa e juros)" if total > c.valor else ""
    flash(f"Baixa registrada: {brl(total)}{extra}.", "success")
    return redirect(request.referrer or url_for("cobrancas.listar"))


def _relatorio():
    """Agrega inadimplência por unidade e resumo por competência."""
    hoje = date.today()
    cobrancas = db.session.scalars(
        db.select(Cobranca).where(Cobranca.status != StatusCobranca.CANCELADA)
        .order_by(Cobranca.competencia)).all()

    por_unidade, por_mes = {}, {}
    for c in cobrancas:
        m = por_mes.setdefault(c.competencia, {"emitido": Decimal(0), "recebido": Decimal(0), "atrasado": Decimal(0)})
        m["emitido"] += c.valor
        if c.status == StatusCobranca.PAGA:
            m["recebido"] += c.valor_pago or c.valor
        elif c.atrasada:
            m["atrasado"] += c.valor
            u = por_unidade.setdefault(c.unidade_id, {
                "unidade": c.unidade, "qtd": 0, "principal": Decimal(0), "multa": Decimal(0),
                "juros": Decimal(0), "total": Decimal(0), "max_atraso": 0})
            u["qtd"] += 1
            u["principal"] += c.valor
            u["multa"] += c.multa(hoje)
            u["juros"] += c.juros(hoje)
            u["total"] += c.valor_atualizado(hoje)
            u["max_atraso"] = max(u["max_atraso"], c.dias_atraso(hoje))

    unidades = sorted(por_unidade.values(), key=lambda u: u["total"], reverse=True)
    meses = []
    for comp, m in sorted(por_mes.items(), reverse=True):
        pct = (m["atrasado"] / m["emitido"] * 100) if m["emitido"] else Decimal(0)
        meses.append({"competencia": comp, **m, "pct": pct})
    totais = {k: sum((u[k] for u in unidades), Decimal(0)) for k in ("principal", "multa", "juros", "total")}
    totais["qtd"] = sum(u["qtd"] for u in unidades)
    return unidades, meses, totais


@bp.route("/inadimplencia")
@gestor_required
def inadimplencia():
    unidades, meses, totais = _relatorio()
    if request.args.get("formato") == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Unidade", "Cobranças em atraso", "Principal", "Multa", "Juros", "Total", "Maior atraso (dias)"])
        fmt = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
        for u in unidades:
            w.writerow([u["unidade"].identificacao, u["qtd"], fmt(u["principal"]), fmt(u["multa"]),
                        fmt(u["juros"]), fmt(u["total"]), u["max_atraso"]])
        w.writerow(["TOTAL", totais["qtd"], fmt(totais["principal"]), fmt(totais["multa"]),
                    fmt(totais["juros"]), fmt(totais["total"]), ""])
        resp = Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8")
        resp.headers["Content-Disposition"] = f"attachment; filename=inadimplencia-{date.today().isoformat()}.csv"
        return resp
    return render_template("cobrancas/inadimplencia.html", unidades=unidades, meses=meses, totais=totais)


@bp.route("/<int:id>/cancelar", methods=["POST"])
@gestor_required
def cancelar(id):
    c = db.get_or_404(Cobranca, id)
    if c.status != StatusCobranca.PENDENTE:
        abort(400)
    c.status = StatusCobranca.CANCELADA
    db.session.commit()
    flash("Cobrança cancelada.", "info")
    return redirect(request.referrer or url_for("cobrancas.listar"))
