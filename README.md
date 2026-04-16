# BudgetBuddy

AI-powered budget tracking app with natural language expense parsing, receipt scanning, and city-aware financial advice.

## Quick Start

```powershell
# Run the quick start script
.\quick-start.ps1
```

This will:
- Install frontend dependencies
- Install backend dependencies  
- Start the backend server (port 8000)
- Start the frontend (port 5176)

## Features

- 📝 **Natural Language Input** - "Spent $50 on groceries yesterday"
- 📸 **Receipt Scanning** - Upload receipt images for automatic parsing
- 🤖 **AI Budget Advisor** - City-aware financial recommendations
- 📊 **Spending Analytics** - Calendar view, graphs, and category breakdown
- 🎯 **Budget Goals** - Set and track spending limits

## Tech Stack

- **Frontend**: React 18+ with TypeScript, Tailwind CSS
- **Backend**: FastAPI with Python 3.12
- **AI**: Groq (LLaMA 3.1), Gemini 2.5-flash
- **OCR**: Tesseract for receipt text extraction

## Documentation

See the [docs/](docs/) folder for detailed documentation:
- [SETUP.md](docs/SETUP.md) - Installation and setup guide
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Testing instructions
- [API_TESTING.md](docs/API_TESTING.md) - API documentation

## Project Structure

```
BudgetBuddy/
├── backend/          # FastAPI backend
├── src/             # React frontend
├── tests/           # Test files
├── docs/            # Documentation
├── database/        # Database schema
└── receipts/        # Receipt uploads
```

## License

See [docs/ATTRIBUTIONS.md](docs/ATTRIBUTIONS.md) for licenses and credits.
