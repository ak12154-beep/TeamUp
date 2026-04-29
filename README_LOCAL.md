# Локальный запуск TeamUp

## Mac / Linux

1. Убедитесь, что установлен `Node.js 20+` и доступен `docker compose`.
2. В корне проекта выполните:

```bash
./start-local.sh
```

После запуска:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Тестовый пользователь: `user.test@teamup.kg` / `User123!`
- Тестовый партнёр: `partner.test@teamup.kg` / `Partner123!`
- Тестовый админ: `admin@teamup.com` / `admin123`

Почему именно так:

- `rm -rf node_modules dist` убирает кроссплатформенные артефакты после Windows/Linux.
- `npm ci` заново ставит зависимости под текущий Mac, включая native optional packages для Vite/Rollup.
- `vite.config.js` уже проксирует `/api` на локальный backend, поэтому CORS не мешает разработке.
- Базовые данные и тестовые аккаунты `admin / user / partner` сидятся из `backend/app/db/seed.py`.

## Самый простой вариант (рекомендуется)

1. Откройте PowerShell в корне проекта.
2. Выполните:

```powershell
.\start-local.ps1
```

После запуска:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

Тестовый аккаунт партнера:

- email: `partner.test@teamup.kg`
- password: `Partner123!`

Тестовый аккаунт администратора:

- email: `admin@teamup.com`
- password: `admin123`

Тестовый аккаунт пользователя:

- email: `user.test@teamup.kg`
- password: `User123!`

Остановка:

```powershell
.\stop-local.ps1
```

## Как устроена база данных локально

- Используется PostgreSQL в Docker-контейнере.
- Данные сохраняются в Docker volume `teamup_pgdata`, поэтому после перезапуска контейнеров БД не пропадает.
- Порт локальной БД: `55434`.

## Почему не БД “в файле”

Текущий backend завязан на PostgreSQL (миграции Alembic, типы и SQL-логика).  
Поэтому вариант “просто sqlite-файл” здесь будет нестабилен и может ломать функционал.  
Для этого проекта надёжнее и проще оставить PostgreSQL в Docker.
