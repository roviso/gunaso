@echo off
cd /d %~dp0
echo ============================================
echo  Gunaso API - Starting up...
echo ============================================

if not exist .venv (
    echo [0/4] Creating virtual environment...
    py -3 -m venv .venv
    call .venv\Scripts\pip install -r requirements-dev.txt
)
call .venv\Scripts\activate

if not exist .env (
    echo Creating .env from .env.example — review it before production use!
    copy .env.example .env
)

echo [1/3] Running migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Migration failed. Check your Django setup.
    pause
    exit /b 1
)

echo [2/3] Seeding sample data...
python manage.py seed_data
if %errorlevel% neq 0 (
    echo WARNING: Seed data failed (may already be seeded - this is OK).
)

echo [3/3] Starting development server on http://127.0.0.1:8000
echo  Admin panel: http://localhost:8000/admin/
echo  API docs:    http://localhost:8000/api/v1/schema/swagger-ui/
echo ============================================
python manage.py runserver 127.0.0.1:8000
