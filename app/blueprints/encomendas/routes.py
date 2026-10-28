from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import Encomenda, Unidade
from app.utils import portaria_required

bp = Blueprint("encomendas", __name__)


class EncomendaForm(FlaskForm):
    unidade_id = SelectField("Unidade", coerce=int)
    descricao = StringField("Descrição (ex.: caixa média, envelope)", validators=[DataRequired(), Length(max=200)])
    remetente = StringField("Remetente / transportadora", validators=[Optional(), Length(max=120)])


class RetiradaForm(FlaskForm):
    retirada_por = StringField("Quem retirou?", validators=[DataRequired(), Length(max=120)])


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    filtro = request.args.get("filtro", "aguardando")
    q = db.select(Encomenda).order_by(Encomenda.recebida_em.desc())
    if not (current_user.is_gestor or current_user.role == "porteiro"):
        q = q.where(Encomenda.unidade_id == current_user.unidade_id)
    if filtro == "aguardando":
        q = q.where(Encomenda.retirada_em.is_(None))
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("encomendas/lista.html", pag=pag, filtro=filtro)


@bp.route("/nova", methods=["GET", "POST"])
@portaria_required
def nova():
    form = EncomendaForm()
    unidades = db.session.scalars(db.select(Unidade).where(Unidade.ativa).order_by(Unidade.bloco, Unidade.numero)).all()
    form.unidade_id.choices = [(u.id, u.identificacao) for u in unidades]
    if form.validate_on_submit():
        db.session.add(Encomenda(
            unidade_id=form.unidade_id.data, descricao=form.descricao.data.strip(),
            remetente=form.remetente.data, recebida_em=datetime.now(), recebida_por_id=current_user.id))
        db.session.commit()
        flash("Encomenda registrada.", "success")
        return redirect(url_for("encomendas.listar"))
    return render_template("form.html", form=form, titulo="Receber encomenda", voltar=url_for("encomendas.listar"))


@bp.route("/<int:id>/retirar", methods=["GET", "POST"])
@portaria_required
def retirar(id):
    e = db.get_or_404(Encomenda, id)
    if not e.aguardando:
        abort(400)
    form = RetiradaForm()
    if form.validate_on_submit():
        e.retirada_em, e.retirada_por = datetime.now(), form.retirada_por.data.strip()
        db.session.commit()
        flash("Retirada registrada.", "success")
        return redirect(url_for("encomendas.listar"))
    return render_template("form.html", form=form, titulo=f"Retirada: {e.descricao} ({e.unidade.identificacao})",
                           voltar=url_for("encomendas.listar"))
