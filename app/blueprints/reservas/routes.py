from datetime import date

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TimeField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import AreaComum, Reserva, Role, StatusReserva, Unidade
from app.utils import gestor_required

bp = Blueprint("reservas", __name__)


class ReservaForm(FlaskForm):
    area_id = SelectField("Área comum", coerce=int)
    unidade_id = SelectField("Unidade", coerce=int)
    data = DateField("Data", validators=[DataRequired()])
    inicio = TimeField("Início", validators=[DataRequired()])
    fim = TimeField("Fim", validators=[DataRequired()])
    observacao = StringField("Observação", validators=[Optional(), Length(max=300)])


@bp.route("/")
@login_required
def listar():
    page = request.args.get("page", 1, type=int)
    q = db.select(Reserva).order_by(Reserva.data.desc(), Reserva.inicio)
    if current_user.role == Role.MORADOR:
        q = q.where(Reserva.unidade_id == current_user.unidade_id)
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("reservas/lista.html", pag=pag)


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    form = ReservaForm()
    areas = db.session.scalars(db.select(AreaComum).where(AreaComum.ativa).order_by(AreaComum.nome)).all()
    form.area_id.choices = [(a.id, a.nome) for a in areas]
    if current_user.is_gestor or current_user.role == Role.PORTEIRO:
        unidades = db.session.scalars(db.select(Unidade).where(Unidade.ativa).order_by(Unidade.bloco, Unidade.numero)).all()
    else:
        unidades = [current_user.unidade] if current_user.unidade else []
    form.unidade_id.choices = [(u.id, u.identificacao) for u in unidades]

    if form.validate_on_submit():
        if form.data.data < date.today():
            flash("A data não pode estar no passado.", "danger")
        elif form.fim.data <= form.inicio.data:
            flash("O horário final deve ser maior que o inicial.", "danger")
        elif Reserva.existe_conflito(form.area_id.data, form.data.data, form.inicio.data, form.fim.data):
            flash("Já existe uma reserva nesse horário para essa área.", "danger")
        else:
            db.session.add(Reserva(
                area_id=form.area_id.data, unidade_id=form.unidade_id.data, usuario_id=current_user.id,
                data=form.data.data, inicio=form.inicio.data, fim=form.fim.data,
                observacao=form.observacao.data,
                status=StatusReserva.APROVADA if current_user.is_gestor else StatusReserva.PENDENTE))
            db.session.commit()
            flash("Reserva registrada.", "success")
            return redirect(url_for("reservas.listar"))
    return render_template("form.html", form=form, titulo="Nova reserva", voltar=url_for("reservas.listar"))


def _mudar_status(r, novo):
    if r.status not in StatusReserva.ATIVAS:
        abort(400)
    r.status = novo
    db.session.commit()
    return redirect(request.referrer or url_for("reservas.listar"))


@bp.route("/<int:id>/aprovar", methods=["POST"])
@gestor_required
def aprovar(id):
    r = db.get_or_404(Reserva, id)
    conflito = db.session.scalar(db.select(Reserva.id).where(
        Reserva.id != r.id, Reserva.area_id == r.area_id, Reserva.data == r.data,
        Reserva.status == StatusReserva.APROVADA, Reserva.inicio < r.fim, Reserva.fim > r.inicio).limit(1))
    if conflito:
        flash("Há outra reserva aprovada nesse horário.", "danger")
        return redirect(url_for("reservas.listar"))
    return _mudar_status(r, StatusReserva.APROVADA)


@bp.route("/<int:id>/recusar", methods=["POST"])
@gestor_required
def recusar(id):
    return _mudar_status(db.get_or_404(Reserva, id), StatusReserva.RECUSADA)


@bp.route("/<int:id>/cancelar", methods=["POST"])
@login_required
def cancelar(id):
    r = db.get_or_404(Reserva, id)
    if not current_user.is_gestor and r.usuario_id != current_user.id:
        abort(403)
    return _mudar_status(r, StatusReserva.CANCELADA)
