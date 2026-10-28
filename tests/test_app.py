from datetime import date, time, timedelta

from app.extensions import db
from app.models import AreaComum, Cobranca, Reserva, Role, StatusCobranca, Unidade, User
from tests.conftest import login


def test_login_required(client):
    r = client.get("/")
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_login_invalido_e_valido(client):
    r = client.post("/auth/login", data={"email": "admin@t.com", "senha": "errada"})
    assert "inválidos" in r.get_data(as_text=True)
    assert login(client, Role.ADMIN).status_code == 302
    assert client.get("/").status_code == 200


def test_open_redirect_bloqueado(client):
    r = client.post("/auth/login?next=//evil.com", data={"email": "admin@t.com", "senha": "senha1234"})
    assert "evil.com" not in r.headers["Location"]


def test_morador_nao_acessa_gestao(client):
    login(client, Role.MORADOR)
    assert client.get("/unidades/").status_code == 403
    assert client.get("/usuarios/").status_code == 403
    assert client.get("/cobrancas/nova").status_code == 403


def test_gerar_cobrancas_em_lote_sem_duplicar(client, app):
    login(client, Role.ADMIN)
    dados = {"descricao": "Taxa", "competencia": "2026-10-05", "valor": "400", "vencimento": "2026-10-10"}
    client.post("/cobrancas/lote", data=dados)
    client.post("/cobrancas/lote", data=dados)
    with app.app_context():
        assert db.session.query(Cobranca).count() == 1
        assert db.session.query(Cobranca).one().competencia == date(2026, 10, 1)


def test_morador_ve_apenas_suas_cobrancas(client, app):
    with app.app_context():
        outra = Unidade(bloco="B", numero="202")
        db.session.add(outra)
        db.session.flush()
        minha = db.session.scalar(db.select(Unidade).filter_by(bloco="A"))
        for u in (minha, outra):
            db.session.add(Cobranca(unidade_id=u.id, competencia=date(2026, 10, 1), valor=100,
                                    vencimento=date(2026, 10, 10), descricao=f"cob-{u.bloco}"))
        db.session.commit()
    login(client, Role.MORADOR)
    html = client.get("/cobrancas/").get_data(as_text=True)
    assert "cob-A" in html and "cob-B" not in html


def test_baixa_de_cobranca(client, app):
    with app.app_context():
        u = db.session.scalar(db.select(Unidade))
        c = Cobranca(unidade_id=u.id, competencia=date(2026, 10, 1), valor=100, vencimento=date(2026, 10, 10))
        db.session.add(c)
        db.session.commit()
        cid = c.id
    login(client, Role.ADMIN)
    client.post(f"/cobrancas/{cid}/pagar")
    with app.app_context():
        assert db.session.get(Cobranca, cid).status == StatusCobranca.PAGA


def test_conflito_de_reserva(client, app):
    with app.app_context():
        area = AreaComum(nome="Salão", valor_taxa=0)
        db.session.add(area)
        db.session.commit()
        area_id = area.id
        uid = db.session.scalar(db.select(Unidade)).id
    login(client, Role.MORADOR)
    dia = (date.today() + timedelta(days=5)).isoformat()
    base = {"area_id": area_id, "unidade_id": uid, "data": dia}
    client.post("/reservas/nova", data={**base, "inicio": "18:00", "fim": "22:00"})
    client.post("/reservas/nova", data={**base, "inicio": "20:00", "fim": "23:00"})  # sobrepõe
    client.post("/reservas/nova", data={**base, "inicio": "22:00", "fim": "23:00"})  # adjacente: ok
    with app.app_context():
        assert db.session.query(Reserva).count() == 2


def test_morador_nao_ve_ocorrencia_alheia(client, app):
    login(client, Role.ADMIN)
    # admin cria; morador não deve acessar
    client.post("/ocorrencias/nova", data={"titulo": "X", "categoria": "outros", "descricao": "d"})
    client.post("/auth/logout")
    login(client, Role.MORADOR)
    assert client.get("/ocorrencias/1").status_code == 403
