"""
BudgetBuddy Backend - Main FastAPI Application
Graduate-level LLM Course Project
"""

import os
import re
from dotenv import load_dotenv

# Load environment variables BEFORE importing modules that use them
# Use explicit path so .env is found regardless of working directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# Import custom modules (after environment variables are loaded)
from llm_pipeline import LLMPipeline
from function_calling import FunctionCallingSystem
from receipt_parser import ReceiptParser
from cost_of_living import CostOfLivingAPI
from database import DatabaseClient
from auth import AuthManager
from cafe_agents import run_cafe_continue_turn, run_cafe_group_chat
from cafe_tools import fetch_cafe_context, load_cafe_memory, save_cafe_memory

# Initialize FastAPI app
app = FastAPI(
    title="BudgetBuddy API",
    description="LLM-powered expense tracking backend",
    version="1.0.0"
)

# CORS origins can be provided as comma-separated list in CORS_ORIGINS,
# or as a single URL in FRONTEND_URL for backward compatibility.
local_dev_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
]

cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    frontend_url = os.getenv("FRONTEND_URL")
    cors_origins = [frontend_url.strip()] if frontend_url else []

for origin in local_dev_origins:
    if origin not in cors_origins:
        cors_origins.append(origin)

# CORS Configuration (allows frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
llm_pipeline = LLMPipeline()
function_system = FunctionCallingSystem()
receipt_parser = ReceiptParser()
col_api = CostOfLivingAPI()
db = DatabaseClient()
auth_manager = AuthManager(db=db)  # Pass shared db instance

# ============================================
# PYDANTIC MODELS
# ============================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)

class LoginResponse(BaseModel):
    user_id: str
    username: str
    token: str
    display_name: Optional[str] = None

class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0)
    category: str
    description: Optional[str] = ""
    date: str  # ISO format date

    @validator('category')
    def validate_category(cls, v):
        valid_categories = [
            'Food', 'Transportation', 'Entertainment', 
            'Shopping', 'Bills', 'Healthcare', 'Education', 'Other'
        ]
        if v not in valid_categories:
            raise ValueError(f'Category must be one of {valid_categories}')
        return v

class ExpenseResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    category: str
    description: str
    expense_date: str  # Changed from 'date' to match database field
    created_at: str

class NaturalLanguageInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    city: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}


class CafeGossipRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)

class BudgetCreate(BaseModel):
    monthly_limit: float = Field(..., gt=0)
    category: Optional[str] = None
    month: Optional[str] = None  # YYYY-MM format

class UserProfileResponse(BaseModel):
    id: str
    username: str
    display_name: str
    selected_pet: str
    friendship_level: int
    last_activity: str
    created_at: str

class UpdatePetRequest(BaseModel):
    selected_pet: str = Field(..., pattern='^(penguin|dragon|capybara|cat)$')


def infer_city_from_message(message: str) -> Optional[str]:
    """Infer a supported city from the free-form chat message."""
    lowered_message = message.lower()
    for city in col_api.get_supported_cities():
        city_name = city["name"].split(",")[0].lower()
        if re.search(rf"\b{re.escape(city_name)}\b", lowered_message):
            return city["name"]
    return None

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "healthy",
        "service": "BudgetBuddy API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "database": await db.health_check(),
            "llm": llm_pipeline.health_check(),
            "col_api": col_api.health_check()
        }
    }

# ============================================
# AUTHENTICATION
# ============================================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Username-only login (no password)
    Creates user if doesn't exist
    """
    try:
        user = await auth_manager.login_or_create(request.username)
        return LoginResponse(**user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/verify")
async def verify_token(token: str):
    """Verify JWT token validity"""
    try:
        user = await auth_manager.verify_token(token)
        return {"valid": True, "user": user}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============================================
# USER PROFILE
# ============================================

@app.get("/api/user/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str = Depends(auth_manager.get_current_user)
):
    """Get current user's profile"""
    try:
        user = await db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfileResponse(**user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/user/profile")
async def update_user_profile(
    update: UpdatePetRequest,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """Update user's selected pet"""
    try:
        await db.update_user_pet(user_id, update.selected_pet)
        return {"success": True, "selected_pet": update.selected_pet}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# EXPENSE MANAGEMENT
# ============================================

@app.post("/api/expenses", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """Manually add an expense"""
    try:
        result = await db.create_expense(user_id, expense.dict())
        return ExpenseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expenses")
async def get_expenses(
    user_id: str = Depends(auth_manager.get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
):
    """Get user's expenses with optional filters"""
    try:
        expenses = await db.get_expenses(
            user_id, 
            start_date=start_date,
            end_date=end_date,
            category=category,
            limit=limit
        )
        return {"expenses": expenses, "count": len(expenses)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """Delete an expense"""
    try:
        await db.delete_expense(user_id, expense_id)
        return {"success": True, "message": "Expense deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# NATURAL LANGUAGE PROCESSING
# ============================================

@app.post("/api/parse-expense")
async def parse_expense_natural_language(
    input_data: NaturalLanguageInput,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """
    Parse natural language to expense data
    Uses two-LLM pipeline
    """
    try:
        # LLM Pipeline: Extract → Normalize → Validate
        parsed_data = await llm_pipeline.parse_expense(input_data.text)
        
        return {
            "success": True,
            "parsed_data": parsed_data,
            "message": "Expense parsed successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=422, 
            detail=f"Failed to parse expense: {str(e)}"
        )

# ============================================
# RECEIPT PARSING (VISION)
# ============================================

@app.post("/api/parse-receipt")
async def parse_receipt(
    file: UploadFile = File(...),
    user_id: str = Depends(auth_manager.get_current_user)
):
    """
    Parse receipt image using Groq + Tesseract OCR (primary) or Gemini Vision (fallback)
    Extracts structured expense data
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Read image
        image_data = await file.read()
        
        # Create fresh parser instance to avoid module caching issues
        parser = ReceiptParser()
        
        print(f"\n[API] ReceiptParser initialized:")
        print(f"  - Groq: {'yes' if parser.use_groq else 'no'}")
        print(f"  - Tesseract: {'yes' if parser.use_tesseract else 'no'}")
        print(f"  - Gemini Vision: {'yes' if parser.use_gemini else 'no'}")
        
        # Parse receipt using Groq + OCR (primary) or Gemini Vision (fallback)
        parsed_data = await parser.parse_receipt(image_data)
        
        print(f"[API] Receipt parsed successfully: ${parsed_data.get('amount', 0):.2f}")
        
        return {
            "success": True,
            "parsed_data": parsed_data,
            "message": "Receipt parsed successfully"
        }
    except Exception as e:
        print(f"[API] Receipt parsing error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse receipt: {str(e)}"
        )

# ============================================
# FUNCTION CALLING
# ============================================

@app.post("/api/function-call")
async def handle_function_call(
    message: str,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """
    Process function calling from LLM
    Supports: add_expense, set_budget, query_expenses
    """
    try:
        result = await function_system.execute(message, user_id)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Function call failed: {str(e)}"
        )

# ============================================
# BUDGET MANAGEMENT
# ============================================

@app.post("/api/budgets")
async def create_budget(
    budget: BudgetCreate,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """Set a budget for a category"""
    try:
        result = await db.create_budget(user_id, budget.dict())
        return {"success": True, "budget": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budgets")
async def get_budgets(
    user_id: str = Depends(auth_manager.get_current_user),
    month: Optional[str] = None
):
    """Get user's budgets"""
    try:
        budgets = await db.get_budgets(user_id, month=month)
        return {"budgets": budgets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budget-comparison")
async def get_budget_comparison(
    user_id: str = Depends(auth_manager.get_current_user),
    month: Optional[str] = None
):
    """Get budget vs actual spending comparison"""
    try:
        comparison = await db.get_budget_comparison(user_id, month=month)
        return {"comparison": comparison}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CALENDAR
# ============================================

@app.get("/api/calendar")
async def get_calendar_entries(
    user_id: str = Depends(auth_manager.get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get calendar entries with expenses"""
    try:
        entries = await db.get_calendar_entries(
            user_id,
            start_date=start_date,
            end_date=end_date
        )
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CHATBOT
# ============================================

@app.post("/api/chat")
async def chat_with_buddy(
    chat_data: ChatMessage,
    user_id: str = Depends(auth_manager.get_current_user)
):
    """
    Smart Money Avatar Chatbot
    City-aware, context-aware responses
    """
    try:
        # Get user context
        user_context = await db.get_user_context(user_id)
        
        # Get cost of living data if city provided or detected in the message
        effective_city = chat_data.city or infer_city_from_message(chat_data.message)
        col_data = None
        if effective_city:
            col_data = await col_api.get_city_data(effective_city)
        
        # Generate response using LLM
        response = await llm_pipeline.chat_response(
            message=chat_data.message,
            user_context=user_context,
            col_data=col_data,
            chat_context=chat_data.context
        )
        
        # Save chat history
        await db.save_chat_message(user_id, chat_data.message, "user")
        await db.save_chat_message(user_id, response, "assistant")
        
        return {
            "response": response,
            "context": {
                "city": effective_city,
                "col_data": col_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# COST OF LIVING
# ============================================

@app.get("/api/cost-of-living/{city}")
async def get_cost_of_living(city: str):
    """Get cost of living data for a city"""
    try:
        data = await col_api.get_city_data(city)
        return {
            "city": city,
            "data": data,
            "cached": data.get("cached", False)
        }
    except Exception as e:
        # Graceful degradation
        return {
            "city": city,
            "data": None,
            "error": "Data temporarily unavailable",
            "message": str(e)
        }

@app.post("/api/cafe/gossip")
async def generate_cafe_gossip(payload: CafeGossipRequest):
    """Run the Pet Community Cafe multi-agent conversation for a user."""
    try:
        safe_uid = re.sub(r"[^a-zA-Z0-9_-]", "_", payload.user_id)
        mem_path = os.path.join(os.path.dirname(__file__), "rag_cache", f"cafe_memory_{safe_uid}.json")
        history = run_cafe_continue_turn(user_id=payload.user_id, memory_path=mem_path)
        return {
            "success": True,
            "user_id": payload.user_id,
            "conversation": history,
            "count": len(history),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cafe gossip failed: {str(e)}")

@app.get("/api/cafe/context/{user_id}")
async def get_cafe_context(user_id: str):
    """Return aggregated budget + Reddit context for a user's cafe session."""
    if not re.match(r"^[a-zA-Z0-9_@.\-]{1,100}$", user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    try:
        ctx = fetch_cafe_context(user_id)
        return {"success": True, "user_id": user_id, "context": ctx}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context fetch failed: {str(e)}")

@app.get("/api/cafe/memory/{user_id}")
async def get_cafe_memory(user_id: str):
    """Return the stored conversation history for a user."""
    if not re.match(r"^[a-zA-Z0-9_@.\-]{1,100}$", user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    safe_uid = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)
    mem_path = os.path.join(os.path.dirname(__file__), "rag_cache", f"cafe_memory_{safe_uid}.json")
    history = load_cafe_memory(mem_path)
    return {"success": True, "user_id": user_id, "history": history, "count": len(history)}

@app.delete("/api/cafe/memory/{user_id}")
async def reset_cafe_memory(user_id: str):
    """Clear the conversation history for a user (start a fresh cafe session)."""
    if not re.match(r"^[a-zA-Z0-9_@.\-]{1,100}$", user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    safe_uid = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)
    mem_path = os.path.join(os.path.dirname(__file__), "rag_cache", f"cafe_memory_{safe_uid}.json")
    save_cafe_memory([], mem_path)
    return {"success": True, "user_id": user_id, "message": "Cafe memory cleared."}

@app.get("/api/cities")
async def get_cities():
    """Get list of supported cities"""
    return {
        "cities": col_api.get_supported_cities()
    }

# ============================================
# INSIGHTS & ANALYTICS
# ============================================

@app.get("/api/insights")
async def get_insights(
    user_id: str = Depends(auth_manager.get_current_user)
):
    """
    Get AI-generated insights about spending patterns
    """
    try:
        # Get user data
        user_context = await db.get_user_context(user_id)
        
        # Generate insights using LLM
        insights = await llm_pipeline.generate_insights(user_context)
        
        return {
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================
# STARTUP & SHUTDOWN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global llm_pipeline
    print(">> BudgetBuddy API starting...")
    await db.connect()
    print(">> Database connected")
    print(">> LLM pipeline initialized")
    print(f">> LLM Provider: {llm_pipeline.provider}")
    print(f">> Server ready on port {os.getenv('PORT', 8000)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print(">> BudgetBuddy API shutting down...")
    await db.disconnect()
    print(">> Cleanup complete")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
