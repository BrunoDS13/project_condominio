import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import TIPOS_VEICULO, Unidade, Veiculo
from app.utils import normalizar_placa, portaria_required

bp = Blueprint("veiculos", __name__)

PLACA_RE = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # antiga (ABC1234) e Mercosul (ABC1D23)


class VeiculoForm(FlaskForm):
    unidade_id = SelectField("Unidade", coerce=int)
    placa = StringField("Placa", validators=[DataRequired(), Length(max=10)])
    tipo = SelectField("Tipo", choices=TIPOS_VEICULO)
    modelo = StringField("Modelo", validators=[Optional(), Length(max=60)])
    cor = StringField("Cor", validators=[Optional(), Length(max=30)])
    vaga = StringField("Vaga", validators=[Optional(), Length(max=10)])
    ativo = BooleanField("Ativo", default=True)


def _form(obj=None):
    form = VeiculoForm(obj=obj)
    unidades = db.session.scalars(db.select(Unidade).where(Unidade.ativa).order_by(Unidade.bloco, Unidade.numero)).all()
    form.unidade_id.choices = [(u.id, u.identificacao) for u in unidades]
    return form


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    q = db.select(Veiculo).order_by(Veiculo.placa)
    if not (current_user.is_gestor or current_user.role == "porteiro"):
        q = q.where(Veiculo.unidade_id == current_user.unidade_id)
    busca = normalizar_placa(request.args.get("placa"))
    if busca:
        q = q.where(Veiculo.placa.contains(busca))
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("veiculos/lista.html", pag=pag, busca=request.args.get("placa", ""))


def _salvar(form, veiculo):
    placa = normalizar_placa(form.placa.data)
    if not PLACA_RE.match(placa):
        flash("Placa inválida (use ABC1234 ou ABC1D23).", "danger")
        return False
    outro = db.session.scalar(db.select(Veiculo).filter_by(placa=placa))
    if outro and outro.id != veiculo.id:
        flash("Placa já cadastrada.", "danger")
        return False
    form.populate_obj(veiculo)
    veiculo.placa = placa
    db.session.add(veiculo)
    db.session.commit()
    flash("Veículo salvo.", "success")
    return True


@bp.route("/novo", methods=["GET", "POST"])
@portaria_required
def novo():
    form = _form()
    if form.validate_on_submit() and _salvar(form, Veiculo()):
        return redirect(url_for("veiculos.listar"))
    return render_template("form.html", form=form, titulo="Novo veículo", voltar=url_for("veiculos.listar"))


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@portaria_required
def editar(id):
    v = db.get_or_404(Veiculo, id)
    form = _form(v)
    if form.validate_on_submit() and _salvar(form, v):
        return redirect(url_for("veiculos.listar"))
    return render_template("form.html", form=form, titulo=f"Editar {v.placa}", voltar=url_for("veiculos.listar"))
