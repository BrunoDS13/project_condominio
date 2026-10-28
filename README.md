# Gestão de Condomínio (Flask)

Módulos: autenticação com perfis (admin, síndico, morador, porteiro), unidades, usuários,
cobranças (individuais e em lote, baixa/cancelamento), reservas de áreas comuns (com
detecção de conflito), ocorrências e comunicados.

## Setup (Windows / PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # ajuste SECRET_KEY

flask db upgrade            # cria o banco aplicando as migrations
flask seed                  # dados de demonstração (opcional)
flask run
```

Acesse http://127.0.0.1:5000 — logins do seed: `admin@demo.com / admin123`;
`sindico@`, `porteiro@`, `morador@demo.com / demo123`.

Admin real: `flask create-admin`.

## PostgreSQL

Crie o banco e defina no `.env`:
`DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/condominio`, depois `flask db upgrade`.

## Migrations

Após alterar modelos: `flask db migrate -m "descrição"` e `flask db upgrade`.

## Testes

```powershell
pytest
```

## Estrutura

```
app/
  __init__.py        # application factory
  extensions.py      # db, migrate, login, csrf
  models/            # um arquivo por domínio
  blueprints/<mod>/  # rotas + forms de cada módulo
  templates/  static/
  cli.py             # flask seed / create-admin
config.py  wsgi.py  migrations/  tests/
```

## Produção

Defina `APP_ENV=prod`, `SECRET_KEY` forte e PostgreSQL; rode atrás de um servidor WSGI
(no Windows, `waitress`; no Linux, `gunicorn wsgi:app`).
