from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import CATEGORIAS_OCORRENCIA, Ocorrencia, StatusOcorrencia
from app.utils import gestor_required

bp = Blueprint("ocorrencias", __name__)


class OcorrenciaForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=150)])
    categoria = SelectField("Categoria", choices=CATEGORIAS_OCORRENCIA)
    descricao = TextAreaField("Descrição", validators=[DataRequired()])


class RespostaForm(FlaskForm):
    status = SelectField("Status", choices=StatusOcorrencia.CHOICES)
    resposta = TextAreaField("Resposta / andamento", validators=[Optional()])


def _pode_ver(o):
    return current_user.is_gestor or o.usuario_id == current_user.id


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    q = db.select(Ocorrencia).order_by(Ocorrencia.criada_em.desc())
    if not current_user.is_gestor:
        q = q.where(Ocorrencia.usuario_id == current_user.id)
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("ocorrencias/lista.html", pag=pag)


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    form = OcorrenciaForm()
    if form.validate_on_submit():
        db.session.add(Ocorrencia(
            usuario_id=current_user.id, unidade_id=current_user.unidade_id,
            titulo=form.titulo.data.strip(), categoria=form.categoria.data, descricao=form.descricao.data))
        db.session.commit()
        flash("Ocorrência registrada.", "success")
        return redirect(url_for("ocorrencias.listar"))
    return render_template("form.html", form=form, titulo="Nova ocorrência", voltar=url_for("ocorrencias.listar"))


@bp.route("/<int:id>", methods=["GET", "POST"])
@login_required
def detalhe(id):
    o = db.get_or_404(Ocorrencia, id)
    if not _pode_ver(o):
        abort(403)
    form = RespostaForm(obj=o) if current_user.is_gestor else None
    if form and form.validate_on_submit():
        o.status, o.resposta = form.status.data, form.resposta.data
        db.session.commit()
        flash("Ocorrência atualizada.", "success")
        return redirect(url_for("ocorrencias.detalhe", id=o.id))
    return render_template("ocorrencias/detalhe.html", o=o, form=form)
