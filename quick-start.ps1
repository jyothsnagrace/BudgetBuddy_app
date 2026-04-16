# BudgetBuddy Quick Start Script
# Windows PowerShell

Write-Host "🐧 BudgetBuddy Quick Start" -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check Node
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

Write-Host "`n====================================`n" -ForegroundColor Cyan
Write-Host "Setup Options:" -ForegroundColor Yellow
Write-Host "1. Backend only"
Write-Host "2. Frontend only"
Write-Host "3. Full setup (backend + frontend)"
Write-Host "4. Exit"

$choice = Read-Host "`nSelect option (1-4)"

switch ($choice) {
    "1" {
        Write-Host "`nSetting up backend..." -ForegroundColor Cyan
        
        # Backend setup
        Set-Location backend
        
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
        
        Write-Host "Activating virtual environment..." -ForegroundColor Yellow
        .\venv\Scripts\Activate.ps1
        
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        pip install -r requirements.txt
        
        Write-Host "`n✓ Backend setup complete!" -ForegroundColor Green
        Write-Host "`nNext steps:" -ForegroundColor Yellow
        Write-Host "1. Copy .env.example to .env"
        Write-Host "2. Add your API keys to .env"
        Write-Host "3. Run: python main.py"
    }
    
    "2" {
        Write-Host "`nSetting up frontend..." -ForegroundColor Cyan
        
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        npm install
        
        Write-Host "`n✓ Frontend setup complete!" -ForegroundColor Green
        Write-Host "`nNext steps:" -ForegroundColor Yellow
        Write-Host "1. Copy .env.example to .env"
        Write-Host "2. Set VITE_API_URL in .env"
        Write-Host "3. Run: npm run dev"
    }
    
    "3" {
        Write-Host "`nSetting up full application..." -ForegroundColor Cyan
        
        # Backend
        Write-Host "`n[1/2] Setting up backend..." -ForegroundColor Yellow
        Set-Location backend
        python -m venv venv
        .\venv\Scripts\Activate.ps1
        pip install -r requirements.txt
        Set-Location ..
        
        # Frontend
        Write-Host "`n[2/2] Setting up frontend..." -ForegroundColor Yellow
        npm install
        
        Write-Host "`n✓ Full setup complete!" -ForegroundColor Green
        Write-Host "`nNext steps:" -ForegroundColor Yellow
        Write-Host "1. Configure backend/.env with API keys"
        Write-Host "2. Configure .env with API URL"
        Write-Host "3. Run backend: cd backend && python main.py"
        Write-Host "4. Run frontend: npm run dev"
        Write-Host "`nSee SETUP.md for detailed instructions"
    }
    
    "4" {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit 0
    }
    
    default {
        Write-Host "Invalid choice. Exiting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n====================================`n" -ForegroundColor Cyan
Write-Host "For help, see:" -ForegroundColor Yellow
Write-Host "  README.md - Project overview"
Write-Host "  SETUP.md - Detailed setup guide"
Write-Host "  ARCHITECTURE.md - System architecture"
Write-Host "`n"
