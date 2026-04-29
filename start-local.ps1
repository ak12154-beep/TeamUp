$ErrorActionPreference = "Stop"

Write-Host "Starting local TeamUp stack..." -ForegroundColor Cyan
docker compose up -d --build

Write-Host "Seeding verification accounts and base data..." -ForegroundColor Cyan
docker compose exec -T backend python /app/app/db/seed.py

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://localhost:8000"
Write-Host "Swagger:  http://localhost:8000/docs"
Write-Host ""
Write-Host "Test partner credentials:"
Write-Host "email:    partner.test@teamup.kg"
Write-Host "password: Partner123!"
Write-Host ""
Write-Host "Test admin credentials:"
Write-Host "email:    admin@teamup.com"
Write-Host "password: admin123"
Write-Host ""
Write-Host "Test user credentials:"
Write-Host "email:    user.test@teamup.kg"
Write-Host "password: User123!"
