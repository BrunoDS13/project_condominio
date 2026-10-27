import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DateField, DecimalField, SelectField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.extensions import db
from app.models import (CATEGORIAS_DESPESA, FONTE_CAIXA, FONTE_RESERVA, FONTES_DESPESA, AporteReserva,
                        Cobranca, Despesa, StatusCobranca)
from app.utils import gestor_required

bp = Blueprint("financeiro", __name__)

EXTENSOES = ("pdf", "png", "jpg", "jpeg")
ASSINATURAS = {"pdf": (b"%PDF",), "png": (b"\x89PNG",), "jpg": (b"\xff\xd8",), "jpeg": (b"\xff\xd8",)}
ZERO = Decimal("0.00")


class DespesaForm(FlaskForm):
    categoria = SelectField("Categoria", choices=CATEGORIAS_DESPESA)
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)])
    fornecedor = StringField("Fornecedor", validators=[Optional(), Length(max=120)])
    valor = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    data = DateField("Data do pagamento", validators=[DataRequired()])
    fonte = SelectField("Pago com", choices=FONTES_DESPESA)
    comprovante = FileField("Comprovante (PDF, PNG ou JPG, até 5 MB)",
                            validators=[Optional(), FileAllowed(EXTENSOES, "Envie PDF, PNG ou JPG.")])


class AporteForm(FlaskForm):
    descricao = StringField("Descrição", validators=[DataRequired(), Length(max=200)],
                            default="Aporte ao fundo de reserva")
    valor = DecimalField("Valor (R$)", validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    data = DateField("Data", validators=[DataRequired()])


# ---------- apuração ----------

def _dec(v):
    return Decimal(str(v)) if v is not None else ZERO


def _soma(coluna, *filtros):
    return _dec(db.session.scalar(db.select(db.func.sum(coluna)).where(*filtros)))


def _limites(ano, mes):
    ini = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    return ini, fim


def _recebido(ini=None, fim=None):
    f = [Cobranca.status == StatusCobranca.PAGA]
    if ini:
        f.append(Cobranca.pago_em >= ini)
    if fim:
        f.append(Cobranca.pago_em < fim)
    return _soma(Cobranca.valor_pago, *f)


def _gasto(fonte, ini=None, fim=None):
    f = [Despesa.fonte == fonte]
    if ini:
        f.append(Despesa.data >= ini)
    if fim:
        f.append(Despesa.data < fim)
    return _soma(Despesa.valor, *f)


def _aportes(ini=None, fim=None):
    f = []
    if ini:
        f.append(AporteReserva.data >= ini)
    if fim:
        f.append(AporteReserva.data < fim)
    return _soma(AporteReserva.valor, *f)


def resumo_mes(ano, mes):
    """Receitas, despesas e saldos do mês. Caixa = recebido - despesas do caixa - aportes ao fundo."""
    ini, fim = _limites(ano, mes)
    receitas = _recebido(ini, fim)
    desp_caixa = _gasto(FONTE_CAIXA, ini, fim)
    aportes = _aportes(ini, fim)
    return {
        "receitas": receitas,
        "despesas": desp_caixa,
        "aportes": aportes,
        "saldo_mes": receitas - desp_caixa - aportes,
        "saldo_caixa": _recebido(fim=fim) - _gasto(FONTE_CAIXA, fim=fim) - _aportes(fim=fim),
        "reserva": _aportes(fim=fim) - _gasto(FONTE_RESERVA, fim=fim),
    }


def _parse_mes(texto):
    try:
        ano, mes = (int(x) for x in texto.split("-"))
        date(ano, mes, 1)
        return ano, mes
    except (ValueError, AttributeError):
        hoje = date.today()
        return hoje.year, hoje.month


# ---------- comprovantes ----------

def _pasta_comprovantes():
    pasta = Path(current_app.instance_path) / "comprovantes"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _salvar_comprovante(arquivo):
    """Valida extensão e assinatura do arquivo; devolve o nome salvo ou None."""
    if not arquivo or not arquivo.filename:
        return None
    ext = arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
    cabecalho = arquivo.stream.read(8)
    arquivo.stream.seek(0)
    if ext not in EXTENSOES or not any(cabecalho.startswith(a) for a in ASSINATURAS[ext]):
        raise ValueError("O arquivo não parece ser um PDF, PNG ou JPG válido.")
    nome = f"{uuid.uuid4().hex}.{ext}"
    arquivo.save(_pasta_comprovantes() / nome)
    return nome


# ---------- rotas ----------

@bp.route("/prestacao")
@login_required
def prestacao():
    ano, mes = _parse_mes(request.args.get("mes"))
    ini, fim = _limites(ano, mes)
    resumo = resumo_mes(ano, mes)

    despesas = db.session.scalars(
        db.select(Despesa).where(Despesa.data >= ini, Despesa.data < fim).order_by(Despesa.data.desc(), Despesa.id.desc())
    ).all()
    por_categoria = {}
    for d in despesas:
        por_categoria[d.categoria_label] = por_categoria.get(d.categoria_label, ZERO) + d.valor
    total_desp = sum(por_categoria.values(), ZERO)
    categorias = [{"nome": n, "valor": v, "pct": (v / total_desp * 100) if total_desp else ZERO}
                  for n, v in sorted(por_categoria.items(), key=lambda kv: kv[1], reverse=True)]
    aportes = db.session.scalars(
        db.select(AporteReserva).where(AporteReserva.data >= ini, AporteReserva.data < fim).order_by(AporteReserva.data.desc())
    ).all()

    fluxo = []
    a, m = ano, mes
    for _ in range(12):  # últimos 12 meses terminando no mês escolhido
        r = resumo_mes(a, m)
        fluxo.append({"ano": a, "mes": m, **r})
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)

    return render_template("financeiro/prestacao.html", ano=ano, mes=mes, mes_str=f"{ano:04d}-{mes:02d}",
                           resumo=resumo, despesas=despesas, categorias=categorias, aportes=aportes, fluxo=fluxo)


@bp.route("/despesas/nova", methods=["GET", "POST"])
@gestor_required
def nova_despesa():
    form = DespesaForm()
    if form.validate_on_submit():
        try:
            nome = _salvar_comprovante(form.comprovante.data)
        except ValueError as e:
            flash(str(e), "danger")
        else:
            db.session.add(Despesa(
                categoria=form.categoria.data, descricao=form.descricao.data.strip(),
                fornecedor=form.fornecedor.data, valor=form.valor.data, data=form.data.data,
                fonte=form.fonte.data, comprovante=nome, criado_por_id=current_user.id))
            db.session.commit()
            flash("Despesa registrada.", "success")
            return redirect(url_for("financeiro.prestacao", mes=form.data.data.strftime("%Y-%m")))
    return render_template("form.html", form=form, titulo="Nova despesa", voltar=url_for("financeiro.prestacao"))


@bp.route("/despesas/<int:id>/excluir", methods=["POST"])
@gestor_required
def excluir_despesa(id):
    d = db.get_or_404(Despesa, id)
    mes = d.data.strftime("%Y-%m")
    if d.comprovante:
        (_pasta_comprovantes() / d.comprovante).unlink(missing_ok=True)
    db.session.delete(d)
    db.session.commit()
    flash("Despesa excluída.", "info")
    return redirect(url_for("financeiro.prestacao", mes=mes))


@bp.route("/aportes/novo", methods=["GET", "POST"])
@gestor_required
def novo_aporte():
    form = AporteForm()
    if form.validate_on_submit():
        db.session.add(AporteReserva(descricao=form.descricao.data.strip(), valor=form.valor.data,
                                     data=form.data.data, criado_por_id=current_user.id))
        db.session.commit()
        flash("Aporte registrado.", "success")
        return redirect(url_for("financeiro.prestacao", mes=form.data.data.strftime("%Y-%m")))
    return render_template("form.html", form=form, titulo="Aporte ao fundo de reserva",
                           voltar=url_for("financeiro.prestacao"))


@bp.route("/comprovantes/<int:id>")
@login_required
def comprovante(id):
    d = db.get_or_404(Despesa, id)
    if not d.comprovante:
        abort(404)
    resp = send_from_directory(_pasta_comprovantes(), d.comprovante)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
