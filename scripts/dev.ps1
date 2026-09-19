<#
.SYNOPSIS
    IITGN Alumni & Donor CRM - Development helper script for Windows PowerShell

.DESCRIPTION
    Provides common development tasks for the CRM project.

.EXAMPLE
    .\scripts\dev.ps1 -Task install-api
    .\scripts\dev.ps1 -Task dev-api
    .\scripts\dev.ps1 -Task db-up
    .\scripts\dev.ps1 -Task check
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        'install-api', 'install-web', 'install',
        'dev-api', 'dev-web',
        'check-api', 'check-web', 'check',
        'db-up', 'db-down', 'db-migrate', 'db-revision', 'db-reset',
        'docker-up', 'docker-down', 'docker-logs', 'docker-build',
        'clean', 'test-api'
    )]
    [string]$Task,

    [string]$Msg = ""
)

function Write-Header { param([string]$Text) Write-Host "`n=== $Text ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Text) Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Error { param([string]$Text) Write-Host "[ERR] $Text" -ForegroundColor Red }

switch ($Task) {
    'install-api' {
        Write-Header "Installing API dependencies"
        Set-Location apps/api
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
            Write-Success "Created virtual environment"
        }
        .venv\Scripts\pip install -e .[dev]
        Write-Success "API dependencies installed"
    }
    'install-web' {
        Write-Header "Installing web dependencies"
        npm install
        Write-Success "Web dependencies installed"
    }
    'install' {
        & $MyInvocation.MyCommand.Definition -Task install-api
        & $MyInvocation.MyCommand.Definition -Task install-web
    }
    'dev-api' {
        Write-Header "Starting API server"
        Set-Location apps/api
        if (-not (Test-Path ".venv")) {
            Write-Error "Virtual environment not found. Run: .\scripts\dev.ps1 -Task install-api"
            exit 1
        }
        .venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    }
    'dev-web' {
        Write-Header "Starting CRM web"
        npm run dev:crm
    }
    'check-api' {
        Write-Header "Checking API (ruff + mypy)"
        Set-Location apps/api
        .venv\Scripts\ruff check .
        .venv\Scripts\mypy src/app
        Write-Success "API checks passed"
    }
    'check-web' {
        Write-Header "Checking web (TypeScript + build)"
        npm run check:crm
        Write-Success "Web checks passed"
    }
    'check' {
        & $MyInvocation.MyCommand.Definition -Task check-api
        & $MyInvocation.MyCommand.Definition -Task check-web
    }
    'db-up' {
        Write-Header "Starting PostgreSQL and Redis"
        docker-compose up -d postgres redis
        Write-Success "Database services started"
    }
    'db-down' {
        Write-Header "Stopping database services"
        docker-compose down
        Write-Success "Database services stopped"
    }
    'db-migrate' {
        Write-Header "Applying migrations"
        Set-Location apps/api
        .venv\Scripts\alembic upgrade head
        Write-Success "Migrations applied"
    }
    'db-revision' {
        if (-not $Msg) { Write-Error "Message required: -Msg 'description'"; exit 1 }
        Write-Header "Creating migration: $Msg"
        Set-Location apps/api
        .venv\Scripts\alembic revision --autogenerate -m $Msg
        Write-Success "Migration created"
    }
    'db-reset' {
        Write-Header "Resetting database"
        docker-compose down -v
        docker-compose up -d postgres redis
        Write-Host "Waiting for PostgreSQL..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        Set-Location apps/api
        .venv\Scripts\alembic upgrade head
        Write-Success "Database reset complete"
    }
    'docker-up' {
        Write-Header "Starting all services"
        docker-compose up -d
        Write-Success "All services started"
    }
    'docker-down' {
        Write-Header "Stopping all services"
        docker-compose down
        Write-Success "All services stopped"
    }
    'docker-logs' {
        docker-compose logs -f
    }
    'docker-build' {
        Write-Header "Building Docker images"
        docker-compose build
        Write-Success "Images built"
    }
    'test-api' {
        Write-Header "Running API tests"
        Set-Location apps/api
        .venv\Scripts\pytest -v
    }
    'clean' {
        Write-Header "Cleaning build artifacts"
        Remove-Item -Recurse -Force apps\crm-web\dist, apps\crm-web\node_modules -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force apps\api\.venv, apps\api\__pycache__, apps\api\.pytest_cache, apps\api\.mypy_cache, apps\api\.ruff_cache -ErrorAction SilentlyContinue
        Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success "Cleaned"
    }
}