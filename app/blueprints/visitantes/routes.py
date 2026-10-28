from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import TIPOS_VISITANTE, Unidade, Visitante
from app.utils import normalizar_placa, portaria_required

bp = Blueprint("visitantes", __name__)


class VisitanteForm(FlaskForm):
    unidade_id = SelectField("Unidade visitada", coerce=int)
    nome = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    documento = StringField("Documento (RG/CPF)", validators=[Optional(), Length(max=30)])
    tipo = SelectField("Tipo", choices=TIPOS_VISITANTE)
    placa = StringField("Placa do veículo", validators=[Optional(), Length(max=10)])
    observacao = StringField("Observação", validators=[Optional(), Length(max=300)])


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    filtro = request.args.get("filtro", "dentro")
    q = db.select(Visitante).order_by(Visitante.entrada_em.desc())
    if not (current_user.is_gestor or current_user.role == "porteiro"):
        q = q.where(Visitante.unidade_id == current_user.unidade_id)
    if filtro == "dentro":
        q = q.where(Visitante.saida_em.is_(None))
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("visitantes/lista.html", pag=pag, filtro=filtro)


@bp.route("/novo", methods=["GET", "POST"])
@portaria_required
def novo():
    form = VisitanteForm()
    unidades = db.session.scalars(db.select(Unidade).where(Unidade.ativa).order_by(Unidade.bloco, Unidade.numero)).all()
    form.unidade_id.choices = [(u.id, u.identificacao) for u in unidades]
    if form.validate_on_submit():
        db.session.add(Visitante(
            unidade_id=form.unidade_id.data, nome=form.nome.data.strip(), documento=form.documento.data,
            tipo=form.tipo.data, placa=normalizar_placa(form.placa.data) or None,
            observacao=form.observacao.data, entrada_em=datetime.now(), registrado_por_id=current_user.id))
        db.session.commit()
        flash("Entrada registrada.", "success")
        return redirect(url_for("visitantes.listar"))
    return render_template("form.html", form=form, titulo="Registrar entrada", voltar=url_for("visitantes.listar"))


@bp.route("/<int:id>/saida", methods=["POST"])
@portaria_required
def saida(id):
    v = db.get_or_404(Visitante, id)
    if not v.dentro:
        abort(400)
    v.saida_em = datetime.now()
    db.session.commit()
    flash(f"Saída de {v.nome} registrada.", "success")
    return redirect(request.referrer or url_for("visitantes.listar"))
