from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.extensions import db
from app.models import Comunicado
from app.utils import gestor_required

bp = Blueprint("comunicados", __name__)


class ComunicadoForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=150)])
    corpo = TextAreaField("Mensagem", validators=[DataRequired()])
    fixado = BooleanField("Fixar no topo")


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    q = db.select(Comunicado).order_by(Comunicado.fixado.desc(), Comunicado.criado_em.desc())
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("comunicados/lista.html", pag=pag)


@bp.route("/novo", methods=["GET", "POST"])
@gestor_required
def novo():
    form = ComunicadoForm()
    if form.validate_on_submit():
        db.session.add(Comunicado(autor_id=current_user.id, titulo=form.titulo.data.strip(),
                                  corpo=form.corpo.data, fixado=form.fixado.data))
        db.session.commit()
        flash("Comunicado publicado.", "success")
        return redirect(url_for("comunicados.listar"))
    return render_template("form.html", form=form, titulo="Novo comunicado", voltar=url_for("comunicados.listar"))


@bp.route("/<int:id>/excluir", methods=["POST"])
@gestor_required
def excluir(id):
    db.session.delete(db.get_or_404(Comunicado, id))
    db.session.commit()
    flash("Comunicado removido.", "info")
    return redirect(url_for("comunicados.listar"))
