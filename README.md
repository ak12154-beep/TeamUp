# TeamUp

`TeamUp` is a web application for organizing sports matches, managing venues, and coordinating work between players, partners, and administrators.

## About the Project

The system supports three roles:

- `Player` can register, log in, create games, join matches, use the wallet, and manage a profile.
- `Partner` can manage sports venues, availability, bookings, and analytics.
- `Admin` can manage users and monitor the platform through the admin panel.

## Main Features

- registration and authentication
- role-based access control
- game creation and participation
- venue and calendar management
- wallet and leaderboard
- admin panel
- email verification
- AI assistant integration

## Tech Stack

- Frontend: `React`, `Vite`, `React Router`, `i18next`
- Backend: `FastAPI`, `SQLAlchemy`, `Alembic`
- Database: `PostgreSQL`
- Authentication: `JWT`, `passlib`, `argon2`, `bcrypt`
- Infrastructure: `Docker Compose`

## Project Structure

```text
backend/   FastAPI backend, models, migrations, seed data
frontend/  React frontend
```

## Local Run

Requirements:

- `Node.js 20+`
- `docker compose`

### Mac / Linux

```bash
./start-local.sh
```

### Windows PowerShell

```powershell
.\start-local.ps1
```

After startup:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Test Accounts

These accounts are seeded for checking application functionality during review:

- `admin@teamup.com` / `admin123`
- `user.test@teamup.kg` / `User123!`
- `partner.test@teamup.kg` / `Partner123!`

## Notes

- The backend automatically applies migrations on startup.
- Test accounts and base data are created by `backend/app/db/seed.py`.
- Local PostgreSQL runs in Docker and stores data in the `teamup_pgdata` volume.
