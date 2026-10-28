from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Length, Optional

from app.extensions import db
from app.models import Role, Unidade, User
from app.utils import gestor_required

bp = Blueprint("usuarios", __name__)


class UsuarioForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    telefone = StringField("Telefone", validators=[Optional(), Length(max=20)])
    role = SelectField("Perfil", choices=Role.CHOICES)
    unidade_id = SelectField("Unidade", coerce=int, validate_choice=False)
    senha = PasswordField("Senha (deixe em branco para manter)", validators=[Optional(), Length(min=8)])
    ativo = BooleanField("Ativo", default=True)


def _form(obj=None):
    form = UsuarioForm(obj=obj)
    unidades = db.session.scalars(db.select(Unidade).order_by(Unidade.bloco, Unidade.numero)).all()
    form.unidade_id.choices = [(0, "— nenhuma —")] + [(u.id, u.identificacao) for u in unidades]
    if obj is not None and request.method == "GET":
        form.unidade_id.data = obj.unidade_id or 0
    return form


@bp.route("/")
@gestor_required
def listar():
    page = request.args.get("page", 1, type=int)
    q = db.select(User).order_by(User.nome)
    pag = db.paginate(q, page=page, per_page=current_app.config["ITENS_POR_PAGINA"])
    return render_template("usuarios/lista.html", pag=pag)


def _salvar(form, user, novo):
    email = form.email.data.strip().lower()
    outro = db.session.scalar(db.select(User).filter_by(email=email))
    if outro and outro.id != user.id:
        flash("E-mail já cadastrado.", "danger")
        return False
    if novo and not form.senha.data:
        flash("Informe uma senha para o novo usuário.", "danger")
        return False
    if current_user.role != Role.ADMIN and (form.role.data == Role.ADMIN or user.role == Role.ADMIN):
        flash("Apenas administradores podem criar ou alterar administradores.", "danger")
        return False
    if user.id == current_user.id and (not form.ativo.data or form.role.data != user.role):
        flash("Você não pode desativar a si mesmo nem alterar o próprio perfil.", "danger")
        return False
    user.nome, user.email, user.telefone = form.nome.data.strip(), email, form.telefone.data
    user.role, user.ativo = form.role.data, form.ativo.data
    user.unidade_id = form.unidade_id.data or None
    if form.senha.data:
        user.set_password(form.senha.data)
    db.session.add(user)
    db.session.commit()
    flash("Usuário salvo.", "success")
    return True


@bp.route("/novo", methods=["GET", "POST"])
@gestor_required
def novo():
    form = _form()
    if form.validate_on_submit() and _salvar(form, User(), True):
        return redirect(url_for("usuarios.listar"))
    return render_template("form.html", form=form, titulo="Novo usuário", voltar=url_for("usuarios.listar"))


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@gestor_required
def editar(id):
    user = db.get_or_404(User, id)
    form = _form(user)
    if form.validate_on_submit() and _salvar(form, user, False):
        return redirect(url_for("usuarios.listar"))
    return render_template("form.html", form=form, titulo=f"Editar {user.nome}", voltar=url_for("usuarios.listar"))
