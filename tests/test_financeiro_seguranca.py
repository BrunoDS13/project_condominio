from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Cobranca, Role, StatusCobranca, Unidade, User
from tests.conftest import login


def _cobranca(app, dias_atraso, valor=100):
    with app.app_context():
        u = db.session.scalar(db.select(Unidade))
        c = Cobranca(unidade_id=u.id, competencia=date.today().replace(day=1), valor=valor,
                     vencimento=date.today() - timedelta(days=dias_atraso))
        db.session.add(c)
        db.session.commit()
        return c.id


def test_multa_e_juros(app):
    cid = _cobranca(app, 10)
    with app.app_context():
        c = db.session.get(Cobranca, cid)
        assert c.multa() == Decimal("2.00")
        assert c.juros() == Decimal("0.33")  # 100 * 1% / 30 * 10
        assert c.valor_atualizado() == Decimal("102.33")


def test_sem_encargos_em_dia(app):
    cid = _cobranca(app, -5)  # vence daqui a 5 dias
    with app.app_context():
        c = db.session.get(Cobranca, cid)
        assert c.valor_atualizado() == Decimal("100")


def test_baixa_registra_valor_com_encargos(client, app):
    cid = _cobranca(app, 30)
    login(client, Role.ADMIN)
    client.post(f"/cobrancas/{cid}/pagar")
    with app.app_context():
        c = db.session.get(Cobranca, cid)
        assert c.status == StatusCobranca.PAGA and c.valor_pago == Decimal("103.00")
        assert c.valor_atualizado() == c.valor  # paga: sem novos encargos


def test_relatorio_inadimplencia_e_csv(client, app):
    _cobranca(app, 10)
    login(client, Role.ADMIN)
    html = client.get("/cobrancas/inadimplencia").get_data(as_text=True)
    assert "A - 101" in html and "102,33" in html
    csv_resp = client.get("/cobrancas/inadimplencia?formato=csv")
    assert csv_resp.mimetype == "text/csv"
    assert "A - 101;1;100,00;2,00;0,33;102,33;10" in csv_resp.get_data(as_text=True)


def test_relatorio_so_para_gestor(client):
    login(client, Role.MORADOR)
    assert client.get("/cobrancas/inadimplencia").status_code == 403


def test_admin_nao_se_desativa_nem_muda_perfil(client, app):
    login(client, Role.ADMIN)
    with app.app_context():
        u = db.session.scalar(db.select(User).filter_by(role=Role.ADMIN))
        uid, uni = u.id, u.unidade_id or 0
    base = {"nome": "Admin", "email": "admin@t.com", "role": Role.ADMIN, "unidade_id": uni}
    client.post(f"/usuarios/{uid}/editar", data=base)  # ativo omitido => False
    client.post(f"/usuarios/{uid}/editar", data={**base, "ativo": "y", "role": Role.MORADOR})
    with app.app_context():
        u = db.session.get(User, uid)
        assert u.ativo and u.role == Role.ADMIN


def test_sindico_nao_cria_admin_nem_edita_admin(client, app):
    with app.app_context():
        s = User(nome="Sind", email="sindico@t.com", role=Role.SINDICO)
        s.set_password("senha1234")
        db.session.add(s)
        db.session.commit()
        admin_id = db.session.scalar(db.select(User).filter_by(role=Role.ADMIN)).id
    login(client, Role.SINDICO)
    client.post("/usuarios/novo", data={"nome": "X", "email": "x@t.com", "role": Role.ADMIN,
                                        "unidade_id": 0, "senha": "senha1234", "ativo": "y"})
    client.post(f"/usuarios/{admin_id}/editar", data={"nome": "Hack", "email": "admin@t.com",
                                                      "role": Role.ADMIN, "unidade_id": 0, "ativo": "y"})
    with app.app_context():
        assert db.session.scalar(db.select(User).filter_by(email="x@t.com")) is None
        assert db.session.get(User, admin_id).nome == "Admin"


def test_bloqueio_apos_tentativas_de_login(client):
    for _ in range(5):
        client.post("/auth/login", data={"email": "admin@t.com", "senha": "errada"})
    r = client.post("/auth/login", data={"email": "admin@t.com", "senha": "senha1234"})  # senha certa, mas bloqueado
    assert r.status_code == 429
    assert client.get("/").status_code == 302  # continua deslogado
