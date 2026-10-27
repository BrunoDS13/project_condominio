from datetime import date, time, timedelta
from decimal import Decimal

import click

from app.extensions import db
from app.models import (AreaComum, Cobranca, Comunicado, Ocorrencia, Reserva, Role,
                        StatusCobranca, StatusReserva, Unidade, User)
from app.utils import primeiro_dia_mes


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--nome", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_admin(nome, email, password):
        """Cria um usuário administrador."""
        if db.session.scalar(db.select(User).filter_by(email=email.lower())):
            raise click.ClickException("E-mail já cadastrado.")
        u = User(nome=nome, email=email.lower(), role=Role.ADMIN)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.echo(f"Admin {email} criado.")

    @app.cli.command("seed")
    def seed():
        """Popula o banco com dados de demonstração (login: admin@demo.com / admin123)."""
        if db.session.scalar(db.select(User).limit(1)):
            raise click.ClickException("Banco já possui dados; seed cancelado.")

        def novo_user(nome, email, role, unidade=None):
            u = User(nome=nome, email=email, role=role, unidade=unidade)
            u.set_password("admin123" if role == Role.ADMIN else "demo123")
            db.session.add(u)
            return u

        unidades = [Unidade(bloco=b, numero=f"{a}0{n}", area_m2=70, fracao_ideal=Decimal("0.0125"))
                    for b in ("A", "B") for a in range(1, 5) for n in (1, 2)]
        db.session.add_all(unidades)
        admin = novo_user("Administrador", "admin@demo.com", Role.ADMIN)
        novo_user("Síndica Maria", "sindico@demo.com", Role.SINDICO)
        novo_user("Seu José (portaria)", "porteiro@demo.com", Role.PORTEIRO)
        morador = novo_user("João Morador", "morador@demo.com", Role.MORADOR, unidades[0])
        churras = AreaComum(nome="Salão de festas", capacidade=60, valor_taxa=150)
        db.session.add_all([churras, AreaComum(nome="Churrasqueira", capacidade=20, valor_taxa=50)])
        db.session.flush()

        hoje = date.today()
        # Poucas unidades devedoras, como num prédio real: 3 com meses antigos em aberto e 2 só com o mês atual.
        devedoras_antigas = {unidades[2].id: 2, unidades[5].id: 1, unidades[11].id: 3}  # unidade -> meses em atraso
        mes_atual_aberto = {unidades[7].id, unidades[13].id}
        for i in range(3):
            comp = primeiro_dia_mes((hoje.replace(day=1) - timedelta(days=30 * (2 - i))))
            for u in unidades:
                venc = comp.replace(day=10)
                meses_atras = devedoras_antigas.get(u.id, 0)
                aberta = (i >= 3 - meses_atras) or (i == 2 and u.id in mes_atual_aberto and venc < hoje)
                db.session.add(Cobranca(
                    unidade=u, competencia=comp, valor=Decimal("450.00"), vencimento=venc,
                    status=StatusCobranca.PENDENTE if aberta else StatusCobranca.PAGA,
                    pago_em=None if aberta else venc, valor_pago=None if aberta else Decimal("450.00")))
        db.session.add(Reserva(area=churras, unidade=unidades[0], usuario=morador,
                               data=hoje + timedelta(days=7), inicio=time(18), fim=time(23),
                               status=StatusReserva.PENDENTE))
        db.session.add(Ocorrencia(usuario=morador, unidade=unidades[0], titulo="Lâmpada queimada no hall",
                                  descricao="Lâmpada do hall do 1º andar do bloco A queimada.",
                                  categoria="manutencao"))
        db.session.add(Comunicado(autor=admin, titulo="Bem-vindos ao sistema",
                                  corpo="A partir de agora, reservas e ocorrências são feitas por aqui.",
                                  fixado=True))
        db.session.commit()
        click.echo("Seed concluído. Logins: admin@demo.com/admin123, demais /demo123 "
                   "(sindico@, porteiro@, morador@demo.com)")
