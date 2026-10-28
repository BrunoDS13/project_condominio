import re
from datetime import date
from decimal import Decimal
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles):
    """Restringe a rota aos papéis informados (já exige login)."""

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def gestor_required(fn):
    from app.models.user import Role

    return roles_required(Role.ADMIN, Role.SINDICO)(fn)


def portaria_required(fn):
    from app.models.user import Role

    return roles_required(Role.ADMIN, Role.SINDICO, Role.PORTEIRO)(fn)


def normalizar_placa(placa):
    return re.sub(r"[^A-Z0-9]", "", (placa or "").upper())


def brl(valor):
    """Formata Decimal/float como moeda brasileira."""
    valor = Decimal(valor or 0)
    s = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def data_br(d):
    return d.strftime("%d/%m/%Y") if isinstance(d, date) else ""


def primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)
