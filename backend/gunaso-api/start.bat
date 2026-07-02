@echo off
cd /d %~dp0
echo ============================================
echo  Gunaso API - Starting up...
echo ============================================

echo [1/3] Running migrations...
py manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Migration failed. Check your Django setup.
    pause
    exit /b 1
)

echo [2/3] Seeding sample data...
py manage.py seed_data
if %errorlevel% neq 0 (
    echo WARNING: Seed data failed (may already be seeded - this is OK).
)

echo [3/3] Starting development server on http://0.0.0.0:8000
echo  Admin panel: http://localhost:8000/admin/
echo  API root:    http://localhost:8000/api/v1/
echo ============================================
py manage.py runserver 0.0.0.0:8000
