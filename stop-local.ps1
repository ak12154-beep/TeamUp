$ErrorActionPreference = "Stop"

Write-Host "Остановка локального окружения TeamUp..." -ForegroundColor Cyan
docker compose down
Write-Host "Готово." -ForegroundColor Green
