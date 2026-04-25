# 💰 BudgetBuddy

> An intelligent personal finance app with AI-powered expense tracking, receipt OCR, and a city-aware café companion for financial advice.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://reactjs.org/)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success)](#)

**Group 3 — DSBA 6010 Spring 2026 | UNC Charlotte**

---

## 🎯 Overview

A full-stack personal budgeting application that combines **Large Language Models (LLMs)** with **computer vision** to make expense tracking effortless. Features natural language processing, receipt OCR, a multi-agent café companion, and location-aware financial insights.

### ✨ Key Features

- 🤖 **AI Café Companion** — Chat with Penny 🐧, Esper 🐉, Mochi 🐱, or Capy 🦫 for personalized budget advice
- ☕ **Pet Community Cafe** — Turn-based gossip mode with one new agent message per click and per-user memory persistence
- 📸 **Receipt OCR** — Upload receipt photos for automatic expense extraction via Gemini Vision + Tesseract
- 💬 **Natural Language Input** — Type "Spent $45 on pizza" instead of filling forms
- 📍 **Location-Aware Insights** — Compare spending across US cities using real-time cost-of-living data
- 📅 **Interactive Calendar** — Visual spending patterns with hover details
- 🎨 **Companion System** — Build friendship levels through consistent tracking
- 📊 **Smart Analytics** — Category breakdowns, trends, and budget alerts

---

## 🚀 Live Deployments

| Service | URL |
|---------|-----|
| 🌐 Frontend (Vercel) | https://budget-buddy-llm-app.vercel.app |
| ⚙️ Backend (Railway) | https://budgetbuddy-group3.up.railway.app |
| 📖 API Docs | https://budgetbuddy-group3.up.railway.app/docs |

---

## 🏗️ Architecture

### Frontend (React + TypeScript)
```
src/app/
├── components/
│   ├── BudgetBuddy.tsx        # AI Chat / Café Companion
│   ├── BudgetSettings.tsx     # Budget goal management
│   ├── BudgetSummary.tsx      # Monthly analytics
│   ├── ExpenseList.tsx        # Expense history
│   ├── CompanionSelector.tsx  # Pet selection system
│   └── FriendshipStatus.tsx   # Companion friendship meter
└── dateUtils.ts               # Timezone-safe date handling
```

### Backend (FastAPI + Python)
```
backend/
├── main.py                    # FastAPI entry point & all API routes
├── auth.py                    # JWT authentication
├── database.py                # Supabase PostgreSQL client
├── llm_pipeline.py            # Groq / Gemini LLM wrappers
├── cafe_agents.py             # Multi-agent café companion
├── cafe_tools.py              # Companion memory load/save utilities
├── receipt_parser.py          # OCR + Gemini Vision receipt parsing
├── receipt_to_database.py     # Receipt → expense DB pipeline
├── function_calling.py        # LLM function/tool calling system
├── cost_of_living.py          # RapidAPI cost-of-living integration
└── rag.py                     # RAG system (optional, gracefully disabled)
```

---

## 🧠 LLM Architecture & Flow

![LLM Architecture and Flow](docs/LLM-Architecture-Work%20Flow.png)

### Stage Descriptions

| Stage | Model / Tool | Purpose |
|-------|-------------|---------|
| **Input Routing** | FastAPI | Detects text vs. image input |
| **NLP Parsing** | Groq LLaMA 3.1-8b | Extracts expense fields from natural language |
| **OCR Extraction** | Tesseract + Gemini 2.5 Flash Vision | Reads text from receipt images |
| **Normalization** | Groq LLaMA 3.1-8b | Standardizes amounts, dates, categories |
| **Function Calling** | Groq Tool Use | Structures output into DB-ready JSON |
| **Pet Community Cafe** | Multi-agent persona engine | One-turn gossip generation with speaker rotation and persisted per-user memory |
| **LLM Fallback Chain** | OpenAI -> Anthropic -> Groq -> Mock | Ensures cafe continuity if provider keys are missing or unavailable |
| **Agent Orchestration** | Planner -> Executor -> Reviewer | Multi-step task decomposition, tool execution, and response synthesis |
| **Cost-of-Living** | RapidAPI | City-specific financial context |
| **Persistence** | Supabase PostgreSQL | Stores expenses, budgets, user profiles |

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | SPA with Vite bundler |
| **UI Components** | MUI + Radix UI + Tailwind CSS | Accessible, customizable components |
| **Backend** | FastAPI + Python 3.12 | Async REST API |
| **Database** | Supabase (PostgreSQL) | Row-level security, real-time |
| **LLM** | Groq (LLaMA 3.1-8b) | Fast inference for chat & parsing |
| **Vision / OCR** | Gemini 2.5 Flash + Tesseract | Receipt image understanding |
| **Cost Data** | RapidAPI | Real-time city cost-of-living |
| **Auth** | JWT + Supabase | Secure user sessions |
| **Deploy Frontend** | Vercel | Auto-deploy from `main` branch |
| **Deploy Backend** | Railway + Railpack (default) | Auto-deploy from `\backend` |

---

## 🚀 Quick Start

Setup and deployment instructions are in [docs/SETUP.md](docs/SETUP.md).
For Railway and Vercel steps, see [docs/SETUP.md](docs/SETUP.md#production-deployment).

## 💡 Usage

### 1. Add an Expense — Natural Language
Type naturally: `"Spent $32 on Uber to airport"` or `"Coffee $5.50 this morning"`
- LLM extracts amount, category, description, and date automatically
- Review and confirm before saving

### 2. Receipt Upload
- Click **Upload Receipt**
- Select a photo (PNG/JPG)
- Gemini Vision + Tesseract auto-extracts amount, merchant, and items
- Review and submit

### 3. Chat with Your Café Companion
Choose your companion — each has a unique personality:
- **Penny the Penguin** 🐧 — Cheerful and encouraging
- **Esper the Dragon** 🐉 — Wise guardian of your treasure
- **Mochi the Cat** 🐱 — Sassy but genuinely helpful
- **Capy the Capybara** 🦫 — Zen and chill financial coach

**Example questions:**
- "Should I cut back on dining out this month?"
- "How does my spending compare to the Charlotte average?"
- "Where can I save on groceries?"

Responses adapt based on companion personality, friendship level (0–100), and your current budget status.

### 4. Pet Community Cafe (Turn-Based)
- Open the cafe panel and click **Visit Cafe** to start the session
- Each click on **Continue Chat** generates exactly one new turn
- Backend stores per-user cafe history so the conversation continues over time
- Endpoints used by the feature:
  - `POST /api/cafe/gossip`
  - `GET /api/cafe/context/{user_id}`
  - `GET /api/cafe/memory/{user_id}`
  - `DELETE /api/cafe/memory/{user_id}`

### 5. Analytics & Calendar
- Hover over any calendar day to see expense breakdown
- Category icons + amounts displayed inline
- Monthly budget vs. actual comparison

---

## 📊 Feature Status

| Feature | Status | Description |
|---------|--------|-------------|
| **Natural Language Parser** | ✅ | LLM-powered expense extraction |
| **Receipt OCR** | ✅ | Gemini Vision + Tesseract |
| **AI Café Companion** | ✅ | Multi-agent chat with memory |
| **Pet Community Cafe** | ✅ | Turn-based one-message-per-click gossip flow with per-user memory |
| **Cost-of-Living API** | ✅ | City-aware financial context |
| **Budget Tracking** | ✅ | Category limits with alerts |
| **Interactive Calendar** | ✅ | Hover tooltips with expense details |
| **Companion System** | ✅ | Friendship levels + mood |
| **JWT Authentication** | ✅ | Secure login + user profiles |
| **Supabase RLS** | ✅ | Row-level security per user |
| **Responsive Design** | ✅ | Mobile-friendly UI |
---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [docs/SETUP.md](docs/SETUP.md) | Full installation & troubleshooting guide |
| [docs/BudgetBuddy_Final_Report_Draft.docx](docs/BudgetBuddy_Final_Report_Draft.docx) | 4–5 page white-paper style report draft in Microsoft Word format |
| [database/schema.sql](database/schema.sql) | PostgreSQL schema with RLS policies |
---

## 🙏 Acknowledgments

- **Groq** — Fast LLM inference
- **Google Gemini** — Vision + OCR capabilities
- **Supabase** — Backend infrastructure
- **RapidAPI** — Cost-of-living data
- **Radix UI / MUI** — Accessible components
- **Tailwind CSS** — Rapid styling
- **FastAPI** — Modern Python framework
- **Vite** — Lightning-fast dev server

---

## 📊 Project Metrics

- **Backend Endpoints**: 20+
- **Frontend Components**: 10+
- **Database Tables**: 3 (users, expenses, budgets)
- **LLM Providers**: 2 (Groq, Gemini)
- **Companion Personalities**: 4
- **Cafe Endpoints**: 4 (gossip, context, memory read, memory reset)
- **Supported Cities**: 54 (via RapidAPI)

---

**Built with ❤️ for DSBA 6010 — Spring 2026**

**Version:** 1.0.0 | **Status:** ✅ Production Ready | **Last Updated:** April 2026
