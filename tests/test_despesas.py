import io
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.blueprints.financeiro.routes import resumo_mes
from app.extensions import db
from app.models import AporteReserva, Cobranca, Despesa, Role, StatusCobranca, Unidade
from tests.conftest import login

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


@pytest.fixture(autouse=True)
def pasta_temporaria(app, tmp_path):
    app.instance_path = str(tmp_path)  # comprovantes vão para a pasta temporária do teste


def _despesa(client, **extra):
    dados = {"categoria": "manutencao", "descricao": "Bomba d'água", "fornecedor": "ACME", "valor": "300",
             "data": "2026-10-05", "fonte": "caixa", **extra}
    return client.post("/financeiro/despesas/nova", data=dados, content_type="multipart/form-data")


def test_resumo_do_mes_e_saldos(app):
    with app.app_context():
        uid = db.session.scalar(db.select(Unidade)).id
        db.session.add(Cobranca(unidade_id=uid, competencia=date(2026, 10, 1), valor=1000, vencimento=date(2026, 10, 10),
                                status=StatusCobranca.PAGA, pago_em=date(2026, 10, 8), valor_pago=1000))
        db.session.add(Cobranca(unidade_id=uid, competencia=date(2026, 9, 1), valor=400, vencimento=date(2026, 9, 10),
                                status=StatusCobranca.PAGA, pago_em=date(2026, 9, 9), valor_pago=400))
        db.session.add(Despesa(descricao="Luz", valor=300, data=date(2026, 10, 5), fonte="caixa", criado_por_id=1))
        db.session.add(Despesa(descricao="Reforma", valor=50, data=date(2026, 10, 6), fonte="reserva", criado_por_id=1))
        db.session.add(AporteReserva(valor=200, data=date(2026, 10, 7), criado_por_id=1))
        db.session.commit()
        r = resumo_mes(2026, 10)
    assert r["receitas"] == Decimal("1000") and r["despesas"] == Decimal("300") and r["aportes"] == Decimal("200")
    assert r["saldo_mes"] == Decimal("500")
    assert r["saldo_caixa"] == Decimal("900")  # (400 + 1000) - 300 - 200
    assert r["reserva"] == Decimal("150")  # 200 - 50


def test_morador_ve_prestacao_mas_nao_lanca(client):
    login(client, Role.MORADOR)
    assert client.get("/financeiro/prestacao").status_code == 200
    assert client.get("/financeiro/despesas/nova").status_code == 403
    assert client.get("/financeiro/aportes/novo").status_code == 403
    assert client.post("/financeiro/despesas/1/excluir").status_code == 403


def test_mes_invalido_nao_quebra(client):
    login(client, Role.ADMIN)
    assert client.get("/financeiro/prestacao?mes=lixo").status_code == 200
    assert client.get("/financeiro/prestacao?mes=2026-13").status_code == 200


def test_despesa_com_comprovante_pdf(client, app):
    login(client, Role.ADMIN)
    _despesa(client, comprovante=(io.BytesIO(PDF), "nota.pdf"))
    with app.app_context():
        d = db.session.scalar(db.select(Despesa))
        assert d and d.comprovante and d.comprovante.endswith(".pdf")
        assert (Path(app.instance_path) / "comprovantes" / d.comprovante).read_bytes() == PDF
        did = d.id
    r = client.get(f"/financeiro/comprovantes/{did}")
    assert r.status_code == 200 and r.headers["X-Content-Type-Options"] == "nosniff"


def test_comprovante_exige_login(client, app):
    login(client, Role.ADMIN)
    _despesa(client, comprovante=(io.BytesIO(PDF), "nota.pdf"))
    client.post("/auth/logout")
    r = client.get("/financeiro/comprovantes/1")
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_arquivo_falso_e_rejeitado(client, app):
    login(client, Role.ADMIN)
    _despesa(client, comprovante=(io.BytesIO(b"<script>alert(1)</script>"), "nota.pdf"))  # extensão pdf, conteúdo não
    _despesa(client, comprovante=(io.BytesIO(PDF), "malware.exe"))
    with app.app_context():
        assert db.session.query(Despesa).count() == 0


def test_excluir_remove_arquivo(client, app):
    login(client, Role.ADMIN)
    _despesa(client, comprovante=(io.BytesIO(PDF), "nota.pdf"))
    with app.app_context():
        d = db.session.scalar(db.select(Despesa))
        arquivo = Path(app.instance_path) / "comprovantes" / d.comprovante
        did = d.id
    assert arquivo.exists()
    client.post(f"/financeiro/despesas/{did}/excluir")
    assert not arquivo.exists()
    with app.app_context():
        assert db.session.query(Despesa).count() == 0


def test_valor_invalido_nao_grava(client, app):
    login(client, Role.ADMIN)
    _despesa(client, valor="-5")
    with app.app_context():
        assert db.session.query(Despesa).count() == 0
