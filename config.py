import os
from decimal import Decimal

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-inseguro-troque-em-producao")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "condominio.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITENS_POR_PAGINA = 15
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # comprovantes: até 5 MB
    # Encargos por atraso (padrão legal: multa de até 2% + juros de 1% a.m. pro rata die)
    MULTA_PERCENTUAL = Decimal(os.environ.get("MULTA_PERCENTUAL", "2"))
    JUROS_MENSAL_PERCENTUAL = Decimal(os.environ.get("JUROS_MENSAL_PERCENTUAL", "1"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    SESSION_COOKIE_SECURE = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost"


config_by_name = {"dev": DevConfig, "prod": ProdConfig, "test": TestConfig}
