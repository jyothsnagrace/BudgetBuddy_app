# BudgetBuddy — Setup Guide

## Live Deployments

| Service | URL |
|---|---|
| Frontend (Vercel) | https://budget-buddy-llm-app.vercel.app |
| Backend (Railway) | https://budgetbuddy-group3.up.railway.app |
| API Docs | https://budgetbuddy-group3.up.railway.app/docs |

---

## Deployment Prerequisites

### Required Accounts

1. **Railway** (backend hosting): https://railway.app
2. **Vercel** (frontend hosting): https://vercel.com
3. **Supabase** (database): https://supabase.com
4. **Groq** (LLM): https://console.groq.com/keys
5. **Google AI Studio** (Gemini vision): https://aistudio.google.com/app/apikey
6. **RapidAPI** (optional cost-of-living data): https://rapidapi.com

### Required Environment Variables

Backend (Railway service):
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `JWT_SECRET_KEY`
- `RAPIDAPI_KEY` (optional)
- `CORS_ORIGINS=https://budget-buddy-llm-app.vercel.app`
- `FRONTEND_URL=https://budget-buddy-llm-app.vercel.app`

Frontend (Vercel project):
- `VITE_API_URL=https://budgetbuddy-group3.up.railway.app`

---

## Troubleshooting (Deployment)

### Backend startup failures on Railway

- Confirm Railway service **Root Directory** is `/backend`.
- Confirm start command matches `railway.toml`.
- Verify all required backend environment variables are set.

### Frontend cannot reach backend

- Confirm `VITE_API_URL` points to your Railway backend URL.
- Confirm backend `CORS_ORIGINS` includes the deployed Vercel URL.

### LLM / external API issues

- Verify `GEMINI_API_KEY` and `GROQ_API_KEY` are valid.
- If `RAPIDAPI_KEY` is missing, cost-of-living falls back gracefully.

---

## Production Deployment

### Backend (Railway)

1. Create account at https://railway.app
2. New project → **Deploy from GitHub** → select this repo
3. Configure service **Root Directory** as `/backend`
4. Start command is configured via `railway.toml`: `python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `GEMINI_API_KEY`, `GROQ_API_KEY`
   - `SUPABASE_URL`, `SUPABASE_KEY`
   - `JWT_SECRET_KEY`, `RAPIDAPI_KEY`
   - `CORS_ORIGINS=https://budget-buddy-llm-app.vercel.app`
6. Deploy

**Live backend:** https://budgetbuddy-group3.up.railway.app

### Frontend (Vercel)

1. Create account at https://vercel.com
2. **Import GitHub repository**
3. Build settings:
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. Add environment variable:
   - `VITE_API_URL=https://budgetbuddy-group3.up.railway.app`
5. Deploy

**Live frontend:** https://budget-buddy-llm-app.vercel.app

---

## API Reference

Interactive docs: https://budgetbuddy-group3.up.railway.app/docs

### Key Endpoints

```
POST   /api/auth/login                   # Username login, returns JWT
GET    /api/auth/verify                  # Verify JWT token
GET    /api/expenses                     # List expenses
POST   /api/expenses                     # Create expense
POST   /api/parse-expense                # Natural language -> expense
POST   /api/parse-receipt                # Receipt image -> expense
POST   /api/chat                         # Companion chatbot
POST   /api/cafe/gossip                  # Pet Community Cafe next turn
GET    /api/cafe/memory/{user_id}        # Read cafe memory
POST   /api/agent/execute                # Planner-executor-reviewer flow
GET    /api/cost-of-living/{city}        # Cost of living data
```

---

## Course Project Features

| Feature | Status |
|---|---|
| Two-LLM pipeline (Groq + Gemini) | Done |
| Function calling with JSON Schema | Done |
| Multimodal receipt parsing (Vision) | Done |
| RAG and fallback memory paths | Done |
| Cost of Living API integration | Done |
| Supabase persistent storage | Done |
| JWT authentication | Done |
| Vercel + Railway deployment | Done |

---

## Notes

### Free Tier Limits

| Service | Limit |
|---|---|
| Groq (LLaMA 3.1-8b) | 30 req/min |
| Gemini 2.5 Flash | 15 req/min |
| Supabase | 500 MB storage, 2 GB bandwidth |
| RapidAPI | 500 req/month (optional) |

### Security

This is a course project. For production hardening:
- Use hashed passwords + refresh tokens
- Add rate limiting middleware
- Enable HTTPS-only cookies
- Rotate `JWT_SECRET_KEY` regularly

---

## Support

1. Check [Issues](https://github.com/uncc-llm/Spring-2026-DSBA-6010-Group-3-Budget-Buddy/issues)
2. Test backend at https://budgetbuddy-group3.up.railway.app/docs
3. Check browser console for frontend errors