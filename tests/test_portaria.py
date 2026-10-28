from app.extensions import db
from app.models import Encomenda, Role, Unidade, User, Veiculo, Visitante
from tests.conftest import login


def _uid(app):
    with app.app_context():
        return db.session.scalar(db.select(Unidade)).id


def _porteiro(app):
    with app.app_context():
        u = User(nome="Porteiro", email="porteiro@t.com", role=Role.PORTEIRO)
        u.set_password("senha1234")
        db.session.add(u)
        db.session.commit()


def test_visitante_entrada_e_saida(client, app):
    _porteiro(app)
    uid = _uid(app)
    login(client, Role.PORTEIRO)
    client.post("/visitantes/novo", data={"unidade_id": uid, "nome": "Ana", "tipo": "visitante", "placa": "abc-1d23"})
    with app.app_context():
        v = db.session.scalar(db.select(Visitante))
        assert v.dentro and v.placa == "ABC1D23"
        vid = v.id
    client.post(f"/visitantes/{vid}/saida")
    with app.app_context():
        assert not db.session.get(Visitante, vid).dentro
    assert client.post(f"/visitantes/{vid}/saida").status_code == 400


def test_morador_nao_registra_entrada(client, app):
    login(client, Role.MORADOR)
    assert client.get("/visitantes/novo").status_code == 403
    assert client.post("/encomendas/nova", data={}).status_code == 403
    assert client.get("/veiculos/novo").status_code == 403


def test_encomenda_fluxo(client, app):
    uid = _uid(app)
    login(client, Role.ADMIN)
    client.post("/encomendas/nova", data={"unidade_id": uid, "descricao": "Caixa"})
    with app.app_context():
        eid = db.session.scalar(db.select(Encomenda)).id
    client.post(f"/encomendas/{eid}/retirar", data={"retirada_por": "João"})
    with app.app_context():
        e = db.session.get(Encomenda, eid)
        assert not e.aguardando and e.retirada_por == "João"
    assert client.get(f"/encomendas/{eid}/retirar").status_code == 400


def test_veiculo_placa_valida_e_unica(client, app):
    uid = _uid(app)
    login(client, Role.ADMIN)
    dados = {"unidade_id": uid, "tipo": "carro", "ativo": "y"}
    client.post("/veiculos/novo", data={**dados, "placa": "XXXX"})
    client.post("/veiculos/novo", data={**dados, "placa": "abc-1234"})
    client.post("/veiculos/novo", data={**dados, "placa": "ABC1234"})
    with app.app_context():
        assert db.session.query(Veiculo).count() == 1


def test_morador_ve_so_encomendas_da_sua_unidade(client, app):
    with app.app_context():
        minha = db.session.scalar(db.select(Unidade))
        outra = Unidade(bloco="B", numero="1")
        db.session.add(outra)
        db.session.flush()
        for u, d in ((minha, "pacote-meu"), (outra, "pacote-alheio")):
            db.session.add(Encomenda(unidade_id=u.id, descricao=d, recebida_por_id=1))
        db.session.commit()
    login(client, Role.MORADOR)
    html = client.get("/encomendas/").get_data(as_text=True)
    assert "pacote-meu" in html and "pacote-alheio" not in html
