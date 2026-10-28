from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, StringField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import Unidade
from app.utils import gestor_required

bp = Blueprint("unidades", __name__)


class UnidadeForm(FlaskForm):
    bloco = StringField("Bloco", validators=[DataRequired(), Length(max=10)], default="Único")
    numero = StringField("Número", validators=[DataRequired(), Length(max=10)])
    area_m2 = DecimalField("Área (m²)", validators=[Optional()], places=2)
    fracao_ideal = DecimalField("Fração ideal", validators=[Optional()], places=6)
    ativa = BooleanField("Ativa", default=True)


@bp.route("/")
@gestor_required
def listar():
    page = request.args.get("page", 1, type=int)
    q = db.select(Unidade).order_by(Unidade.bloco, Unidade.numero)
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("unidades/lista.html", pag=pag)


def _salvar(form, unidade):
    existe = db.session.scalar(
        db.select(Unidade).filter_by(bloco=form.bloco.data.strip(), numero=form.numero.data.strip())
    )
    if existe and existe.id != unidade.id:
        flash("Já existe uma unidade com esse bloco e número.", "danger")
        return False
    form.populate_obj(unidade)
    unidade.bloco, unidade.numero = unidade.bloco.strip(), unidade.numero.strip()
    db.session.add(unidade)
    db.session.commit()
    flash("Unidade salva.", "success")
    return True


@bp.route("/nova", methods=["GET", "POST"])
@gestor_required
def nova():
    form = UnidadeForm()
    if form.validate_on_submit() and _salvar(form, Unidade()):
        return redirect(url_for("unidades.listar"))
    return render_template("form.html", form=form, titulo="Nova unidade", voltar=url_for("unidades.listar"))


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@gestor_required
def editar(id):
    unidade = db.get_or_404(Unidade, id)
    form = UnidadeForm(obj=unidade)
    if form.validate_on_submit() and _salvar(form, unidade):
        return redirect(url_for("unidades.listar"))
    return render_template("form.html", form=form, titulo=f"Editar unidade {unidade.identificacao}",
                           voltar=url_for("unidades.listar"))
