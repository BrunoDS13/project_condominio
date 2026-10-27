import os

from flask import Flask, render_template

from app.extensions import csrf, db, login_manager, migrate
from app.security import LoginThrottle
from app.utils import brl, data_br
from config import config_by_name


def create_app(config_name="dev"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    app.extensions["login_throttle"] = LoginThrottle()

    from app import models  # noqa: F401  (registra os modelos p/ migrations)

    _register_blueprints(app)
    _register_errors(app)
    app.jinja_env.filters["brl"] = brl
    app.jinja_env.filters["data_br"] = data_br

    from app.cli import register_cli

    register_cli(app)
    return app


def _register_blueprints(app):
    from app.blueprints.auth.routes import bp as auth_bp
    from app.blueprints.cobrancas.routes import bp as cobrancas_bp
    from app.blueprints.comunicados.routes import bp as comunicados_bp
    from app.blueprints.main.routes import bp as main_bp
    from app.blueprints.ocorrencias.routes import bp as ocorrencias_bp
    from app.blueprints.reservas.routes import bp as reservas_bp
    from app.blueprints.unidades.routes import bp as unidades_bp
    from app.blueprints.usuarios.routes import bp as usuarios_bp
    from app.blueprints.visitantes.routes import bp as visitantes_bp
    from app.blueprints.financeiro.routes import bp as financeiro_bp
    from app.blueprints.encomendas.routes import bp as encomendas_bp
    from app.blueprints.veiculos.routes import bp as veiculos_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(unidades_bp, url_prefix="/unidades")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(cobrancas_bp, url_prefix="/cobrancas")
    app.register_blueprint(reservas_bp, url_prefix="/reservas")
    app.register_blueprint(ocorrencias_bp, url_prefix="/ocorrencias")
    app.register_blueprint(comunicados_bp, url_prefix="/comunicados")
    app.register_blueprint(visitantes_bp, url_prefix="/visitantes")
    app.register_blueprint(financeiro_bp, url_prefix="/financeiro")
    app.register_blueprint(encomendas_bp, url_prefix="/encomendas")
    app.register_blueprint(veiculos_bp, url_prefix="/veiculos")


def _register_errors(app):
    for code, msg in {403: "Acesso negado", 413: "Arquivo muito grande (máximo 5 MB)", 404: "Página não encontrada", 500: "Erro interno"}.items():
        app.register_error_handler(
            code, lambda e, code=code, msg=msg: (render_template("error.html", code=code, msg=msg), code)
        )
