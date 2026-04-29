#!/bin/sh
set -e

echo "Starting local TeamUp stack..."
docker compose up -d --build db backend

echo "Seeding local verification accounts and base data..."
docker compose exec -T backend python /app/app/db/seed.py

echo "Preparing frontend dependencies for this machine..."
cd frontend
rm -rf node_modules dist
npm ci

echo ""
echo "Backend:  http://localhost:8000"
echo "Swagger:  http://localhost:8000/docs"
echo "Frontend: run 'cd frontend && npm run dev'"
echo ""
echo "Test partner credentials:"
echo "email:    partner.test@teamup.kg"
echo "password: Partner123!"
echo ""
echo "Test admin credentials:"
echo "email:    admin@teamup.com"
echo "password: admin123"
echo ""
echo "Test user credentials:"
echo "email:    user.test@teamup.kg"
echo "password: User123!"
