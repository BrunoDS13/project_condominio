from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length

from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    lembrar = BooleanField("Manter conectado")


class TrocarSenhaForm(FlaskForm):
    atual = PasswordField("Senha atual", validators=[DataRequired()])
    nova = PasswordField("Nova senha", validators=[DataRequired(), Length(min=8)])
    confirma = PasswordField("Confirmar nova senha", validators=[EqualTo("nova", "As senhas não conferem.")])


def _destino_seguro(nxt):
    return nxt if nxt and nxt.startswith("/") and not nxt.startswith("//") else url_for("main.dashboard")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        throttle = current_app.extensions["login_throttle"]
        email, ip = form.email.data.strip().lower(), request.remote_addr or "?"
        espera = throttle.segundos_restantes(ip, email)
        if espera:
            flash(f"Muitas tentativas. Tente novamente em {espera // 60 + 1} minuto(s).", "danger")
            return render_template("auth/login.html", form=form), 429
        user = db.session.scalar(db.select(User).filter_by(email=email))
        if user and user.ativo and user.check_password(form.senha.data):
            throttle.sucesso(email)
            login_user(user, remember=form.lembrar.data)
            return redirect(_destino_seguro(request.args.get("next")))
        throttle.falhou(ip, email)
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/senha", methods=["GET", "POST"])
@login_required
def trocar_senha():
    form = TrocarSenhaForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.atual.data):
            flash("Senha atual incorreta.", "danger")
        else:
            current_user.set_password(form.nova.data)
            db.session.commit()
            flash("Senha alterada com sucesso.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("form.html", form=form, titulo="Trocar senha", voltar=url_for("main.dashboard"))
