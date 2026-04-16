"""
Two-LLM Pipeline for Expense Parsing
LLM #1: Extraction Agent
LLM #2: Normalization & Validation Agent
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from jsonschema import validate, ValidationError

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError as e:
    genai = None
    GEMINI_AVAILABLE = False
    print(f"Warning: Gemini import failed: {e}")

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: groq package not installed. Install with: pip install groq")

# Try to import RAG system
try:
    from rag import RAGRetriever
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("Warning: RAG system not available. Install required packages.")

# Configure LLM providers
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Groq client
groq_client = None
if GROQ_API_KEY and GROQ_AVAILABLE:
    groq_client = Groq(api_key=GROQ_API_KEY)

# Configure Gemini
if GEMINI_API_KEY and GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)

# JSON Schema for expense validation
EXPENSE_SCHEMA = {
    "type": "object",
    "required": ["amount", "category", "date"],
    "properties": {
        "amount": {
            "type": "number",
            "minimum": 0,
            "description": "Expense amount in dollars"
        },
        "category": {
            "type": "string",
            "enum": [
                "Food", 
                "Transportation", 
                "Entertainment", 
                "Shopping", 
                "Bills", 
                "Healthcare", 
                "Education", 
                "Other"
            ],
            "description": "Expense category"
        },
        "description": {
            "type": "string",
            "maxLength": 200,
            "description": "Description of the expense"
        },
        "date": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "Date in YYYY-MM-DD format"
        }
    }
}


class LLMPipeline:
    """Two-stage LLM pipeline for expense processing"""
    
    def __init__(self):
        self.provider = LLM_PROVIDER
        
        print(f"[LLMPipeline] DEBUG: LLM_PROVIDER env = '{os.getenv('LLM_PROVIDER')}'")
        print(f"[LLMPipeline] DEBUG: self.provider = '{self.provider}'")
        print(f"[LLMPipeline] DEBUG: GROQ_AVAILABLE = {GROQ_AVAILABLE}")
        print(f"[LLMPipeline] DEBUG: groq_client = {groq_client}")
        
        if self.provider == "groq":
            if not groq_client:
                print("[LLMPipeline] Groq requested but not available, falling back to Gemini")
                self.provider = "gemini"
            else:
                print(f"[LLMPipeline] Initializing with Groq ({GROQ_MODEL})")
                self.groq_client = groq_client
                self.groq_model = GROQ_MODEL
        
        if self.provider == "gemini" and (not GEMINI_AVAILABLE or not GEMINI_API_KEY):
            if groq_client:
                print("[LLMPipeline] Gemini unavailable, falling back to Groq")
                self.provider = "groq"
                self.groq_client = groq_client
                self.groq_model = GROQ_MODEL
            else:
                print("[LLMPipeline] No working LLM provider available")

        if self.provider == "gemini" and GEMINI_AVAILABLE and GEMINI_API_KEY:
            print(f"[LLMPipeline] Initializing with gemini-2.5-flash")
            self.extraction_model = genai.GenerativeModel('gemini-2.5-flash')
            print(f"[LLMPipeline] Extraction model: {self.extraction_model._model_name}")
            self.normalization_model = genai.GenerativeModel('gemini-2.5-flash')
            self.chat_model = genai.GenerativeModel('gemini-2.5-flash')

        # Initialize RAG system
        self.rag = None
        if RAG_AVAILABLE:
            try:
                self.rag = RAGRetriever()
                if self.rag.enabled:
                    print("[LLMPipeline] RAG system initialized and enabled")
                else:
                    print("[LLMPipeline] RAG system available but disabled")
            except Exception as e:
                print(f"[LLMPipeline] Failed to initialize RAG: {e}")
                self.rag = None
        else:
            print("[LLMPipeline] RAG system not available")
        
    def health_check(self) -> bool:
        """Check if LLM service is available"""
        try:
            if self.provider == "groq":
                # Test Groq
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=10
                )
                return bool(response.choices[0].message.content)
            elif hasattr(self, "extraction_model"):
                # Test Gemini
                response = self.extraction_model.generate_content("Say 'OK'")
                return bool(response.text)
            return False
        except Exception as e:
            print(f"[LLM Health Check] Failed: {e}")
            return False
    
    async def parse_expense(self, natural_text: str) -> Dict[str, Any]:
        """
        Two-stage pipeline for parsing natural language expense
        
        Stage 1: Extract raw structured data
        Stage 2: Normalize and validate
        """
        print(f"[parse_expense] DEBUG: provider = '{self.provider}'")
        
        # Stage 1: Extraction
        extracted_data = await self._extraction_stage(natural_text)
        
        # Stage 2: Normalization
        normalized_data = await self._normalization_stage(extracted_data, natural_text)
        
        # Stage 3: Validation
        validated_data = self._validation_stage(normalized_data)
        
        return validated_data
    
    async def _extraction_stage(self, text: str) -> Dict[str, Any]:
        """
        LLM #1: Extract structured data from natural language
        """
        print(f"[_extraction_stage] DEBUG: provider = '{self.provider}'")
        print(f"[_extraction_stage] DEBUG: has groq_client = {hasattr(self, 'groq_client')}")
        
        current_year = date.today().year
        today_date = date.today().isoformat()
        
        prompt = f"""You are an expense extraction assistant. Extract expense information from the following text.

Text: "{text}"

Extract and return ONLY a JSON object with these fields:
- amount: The numeric amount (just the number, no currency symbols)
- category: Best matching category (Food, Transportation, Entertainment, Shopping, Bills, Healthcare, Education, or Other)
- description: Brief description of what was purchased
- date: Date in YYYY-MM-DD format

IMPORTANT DATE RULES:
- If date includes year: use it as-is
- If date has NO year (e.g., "Jan 10", "March 5"): assume current year {current_year}
- If "today": use {today_date}
- If "yesterday": use the day before today
- If no date mentioned: use today's date {today_date}
- Always return YYYY-MM-DD format

Return ONLY valid JSON, no other text.

Example:
{{
  "amount": 15.50,
  "category": "Food",
  "description": "Lunch at Chipotle",
  "date": "{today_date}"
}}

Now extract from the given text:"""
        
        try:
            if self.provider == "groq":
                # Use Groq API
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expense extraction assistant. Extract structured data and return only valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=256,
                )
                llm_response = response.choices[0].message.content
            else:
                # Use Gemini API
                response = self.extraction_model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.3,
                        'max_output_tokens': 256,
                    }
                )
                llm_response = response.text
            
            # Extract JSON from response
            json_text = self._extract_json(llm_response)
            parsed_data = json.loads(json_text)
            
            return parsed_data
            
        except Exception as e:
            raise ValueError(f"Extraction failed: {str(e)}")
    
    async def _normalization_stage(self, extracted_data: Dict, original_text: str) -> Dict[str, Any]:
        """
        LLM #2: Normalize and clean extracted data
        """
        prompt = f"""You are a data normalization assistant. Clean and validate this expense data.

Original text: "{original_text}"
Extracted data: {json.dumps(extracted_data)}

Normalize the data according to these rules:
1. Category MUST be exactly one of: Food, Transportation, Entertainment, Shopping, Bills, Healthcare, Education, Other
2. Amount must be a positive number (remove $ signs, convert to float)
3. Date must be YYYY-MM-DD format (validate it's a real date)
4. Description should be clear and concise (max 200 chars)

Valid categories mapping:
- Food/dining/restaurant/grocery → "Food"
- Uber/taxi/gas/car/bus/train → "Transportation"
- Movie/concert/game/fun → "Entertainment"
- Clothes/shoes/electronics → "Shopping"
- Rent/utilities/phone/internet → "Bills"
- Doctor/medicine/pharmacy → "Healthcare"
- Books/course/tuition → "Education"
- Anything else → "Other"

Return ONLY a normalized JSON object:
{{
  "amount": <number>,
  "category": "<exact category name>",
  "description": "<cleaned description>",
  "date": "<YYYY-MM-DD>"
}}

Return ONLY valid JSON, no other text."""
        
        try:
            if self.provider == "groq":
                # Use Groq API
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a data normalization assistant. Clean and validate data and return only valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.2,
                    max_tokens=256,
                )
                llm_response = response.choices[0].message.content
            else:
                # Use Gemini API
                response = self.normalization_model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.2,
                        'max_output_tokens': 256,
                    }
                )
                llm_response = response.text
            
            # Extract JSON from response
            json_text = self._extract_json(llm_response)
            normalized_data = json.loads(json_text)
            
            return normalized_data
            
        except Exception as e:
            raise ValueError(f"Normalization failed: {str(e)}")
    
    def _validation_stage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 3: Validate against JSON schema
        """
        try:
            # Ensure amount is float
            if 'amount' in data:
                data['amount'] = float(data['amount'])
            
            # Validate against schema
            validate(instance=data, schema=EXPENSE_SCHEMA)
            
            # Additional validation
            self._validate_date(data.get('date'))
            self._validate_category(data.get('category'))
            
            return data
            
        except ValidationError as e:
            raise ValueError(f"Validation failed: {e.message}")
        except Exception as e:
            raise ValueError(f"Validation error: {str(e)}")
    
    def _validate_date(self, date_str: str):
        """Validate date string"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")
    
    def _validate_category(self, category: str):
        """Validate category"""
        valid_categories = [
            'Food', 'Transportation', 'Entertainment', 
            'Shopping', 'Bills', 'Healthcare', 'Education', 'Other'
        ]
        if category not in valid_categories:
            raise ValueError(f"Invalid category: {category}")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON object
        json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # If no match, try the whole text
        return text.strip()
    
    async def chat_response(
        self,
        message: str,
        user_context: Dict[str, Any],
        col_data: Optional[Dict] = None,
        chat_context: Optional[Dict] = None
    ) -> str:
        """Generate a grounded financial chat response using retrieved source context."""
        username = user_context.get('username', 'friend')
        budget = float(user_context.get('budget') or 0)
        total_spent = float(user_context.get('total_spent') or 0)
        remaining = budget - total_spent if budget else 0

        rag_bundle = {"context": "", "sources": []}
        if self.rag and self.rag.enabled:
            try:
                retrieval_query = message
                if col_data and col_data.get('city'):
                    retrieval_query = f"{message}\nCity: {col_data['city']}"
                rag_bundle = self.rag.retrieve_context(retrieval_query, k=4)
            except Exception as e:
                print(f"RAG retrieval failed: {e}")

        budget_info = {
            'budget': budget,
            'spent': total_spent,
            'remaining': remaining,
        }

        return self._generate_grounded_chat_response(
            message=message,
            username=username,
            budget_info=budget_info,
            rag_bundle=rag_bundle,
            col_data=col_data,
            chat_context=chat_context,
        )

    def _generate_grounded_chat_response(
        self,
        message: str,
        username: str,
        budget_info: Dict[str, Any],
        rag_bundle: Dict[str, Any],
        col_data: Optional[Dict] = None,
        chat_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Use retrieved source context to generate a practical budgeting answer."""
        prompt = self._build_grounded_chat_prompt(
            message=message,
            username=username,
            budget_info=budget_info,
            rag_bundle=rag_bundle,
            col_data=col_data,
            chat_context=chat_context,
        )

        try:
            if groq_client:
                response = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are BudgetBuddy, a practical financial planning assistant. Use the provided sources and never role-play or answer with mascot filler text."
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.2,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()

            if GEMINI_API_KEY:
                response = self.chat_model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.2,
                        'max_output_tokens': 500,
                    }
                )
                return response.text.strip()
        except Exception as error:
            print(f"Grounded chat generation failed: {error}")

        return self._build_chat_fallback(message, budget_info, rag_bundle, col_data)

    def _build_grounded_chat_prompt(
        self,
        message: str,
        username: str,
        budget_info: Dict[str, Any],
        rag_bundle: Dict[str, Any],
        col_data: Optional[Dict] = None,
        chat_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        sources = rag_bundle.get('sources', [])
        retrieved_context = rag_bundle.get('context', '') or 'No external finance excerpts were retrieved.'

        return f"""Answer the user's finance question directly and practically.

User: {username}
Question: {message}

Budget snapshot:
- Monthly budget: {budget_info.get('budget', 0)}
- Total spent: {budget_info.get('spent', 0)}
- Remaining: {budget_info.get('remaining', 0)}

City cost-of-living data:
{json.dumps(col_data or {}, indent=2)}

Additional chat context:
{json.dumps(chat_context or {}, indent=2)}

Retrieved source excerpts:
{retrieved_context}

Sources available:
{json.dumps(sources, indent=2)}

Rules:
- Do not use mascot role-play, fantasy language, or canned encouragement.
- If the user asks for a spending plan for a city, provide a concrete monthly plan with categories such as housing, food, transportation, savings, utilities, and discretionary spending.
- If no explicit monthly budget is provided, use a reasonable starter plan and clearly label it as an estimate.
- Use the retrieved finance sources as supporting evidence and mention the most relevant source names in a final "Sources:" line.
- Keep the answer under 250 words.
- Prefer clear bullet points when giving a plan.
"""

    def _build_chat_fallback(
        self,
        message: str,
        budget_info: Dict[str, Any],
        rag_bundle: Dict[str, Any],
        col_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Deterministic fallback if LLM generation is unavailable."""
        sources = rag_bundle.get('sources', [])
        city_name = (col_data or {}).get('city') or self._extract_city_name_from_message(message) or 'your city'
        cost_index = float((col_data or {}).get('cost_index') or 75)
        monthly_budget = float(budget_info.get('budget') or 0)

        if monthly_budget <= 0:
            monthly_budget = round(3000 * (cost_index / 75))

        plan = self._estimate_spending_plan(monthly_budget, cost_index)
        plan_lines = [f"- {category}: ${amount}" for category, amount in plan.items()]

        response = [
            f"Here is a practical starter spending plan for {city_name} based on a monthly budget of about ${monthly_budget}.",
            *plan_lines,
            "Use the buffer first for irregular bills, then move any leftover amount into savings.",
        ]

        if sources:
            response.append(f"Sources: {'; '.join(sources[:3])}")

        return "\n".join(response)

    def _estimate_spending_plan(self, monthly_budget: float, cost_index: float) -> Dict[str, int]:
        housing_share = 0.32 if cost_index >= 85 else 0.28
        plan = {
            'Housing': round(monthly_budget * housing_share),
            'Food': round(monthly_budget * 0.12),
            'Transportation': round(monthly_budget * 0.10),
            'Utilities': round(monthly_budget * 0.08),
            'Savings': round(monthly_budget * 0.20),
            'Discretionary': round(monthly_budget * 0.10),
            'Buffer': round(monthly_budget * (1 - housing_share - 0.12 - 0.10 - 0.08 - 0.20 - 0.10)),
        }
        return plan

    def _extract_city_name_from_message(self, message: str) -> str:
        match = re.search(r"for\s+([A-Za-z\s]+)$", message.strip(), re.IGNORECASE)
        if not match:
            return ""
        return match.group(1).strip().title()

    def _generate_rag_response(
        self,
        message: str,
        username: str,
        pet_type: str,
        personality_info: Dict[str, str],
        budget_info: Dict[str, Any],
        rag_context: str,
        col_data: Optional[Dict] = None
    ) -> str:
        """Generate a personality-based response using RAG context."""

        emoji = personality_info['emoji']
        name = personality_info['name']

        # Base response templates for different scenarios
        templates = {
            'penguin': [
                f"Hey {username}! 🐧 {budget_info['advice']} Based on what I know about budgeting, {self._extract_key_insight(rag_context) or 'staying organized is key'}. Keep making waves with your finances!",
                f"Waddle over here, {username}! 🐧 I'm {budget_info['mood']} about your progress. {self._extract_key_insight(rag_context) or 'Remember to track your expenses regularly'}. You're doing ice-credible work!",
                f"Cool thinking, {username}! 🐧 {budget_info['advice']} From my experience: {self._extract_key_insight(rag_context) or 'small consistent savings add up'}. Stay chill and keep going!",
            ],
            'dragon': [
                f"Hark, {username}! 🐉 The ancient scrolls reveal wisdom for your financial journey. {self._extract_key_insight(rag_context) or 'Guard your treasure wisely'}. {budget_info['advice']} Your path shows great promise!",
                f"Brave {username}! 🐉 Drawing from mystical knowledge: {self._extract_key_insight(rag_context) or 'budgeting is the key to financial freedom'}. I'm {budget_info['mood']} about your progress!",
                f"{username}, noble one! 🐉 The mystical energies guide us: {self._extract_key_insight(rag_context) or 'track every coin, for they tell a story'}. {budget_info['advice']} Continue your quest!",
            ],
            'capybara': [
                f"Hey {username}... chill vibes only. 🦫 {budget_info['advice']} Thinking about this: {self._extract_key_insight(rag_context) or 'take it easy with spending'}. Your financial energy is totally mellow.",
                f"No worries, {username}... zen mode activated. 🦫 I'm feeling {budget_info['mood']} about your budget. {self._extract_key_insight(rag_context) or 'Sometimes less is more with expenses'}. Just vibing.",
                f"{username}, my friend... relaxed and ready. 🦫 {budget_info['advice']} Reflecting on: {self._extract_key_insight(rag_context) or 'balance is key in budgeting'}. Good energy all around.",
            ],
            'cat': [
                f"*purrs* {username}, meow! 🐱 {budget_info['advice']} Drawing from my wisdom: {self._extract_key_insight(rag_context) or 'be mindful of every expense'}. Your financial instincts are sharp!",
                f"*stretches* {username}... *hisses* at unnecessary spending. 🐱 I'm {budget_info['mood']} about your progress. {self._extract_key_insight(rag_context) or 'Track those expenses like a cat tracks a laser'}. Impressive!",
                f"Meow, {username}. 🐱 Contemplating your finances: {self._extract_key_insight(rag_context) or 'discipline leads to financial freedom'}. {budget_info['advice']} *chef's kiss* for your approach.",
            ]
        }

        # Select a random template for variety
        import random
        template = random.choice(templates.get(pet_type, templates['penguin']))

        return template

    def _extract_key_insight(self, rag_context: str) -> str:
        """Extract a key insight from RAG context."""
        if not rag_context:
            return ""

        # Simple extraction - take first meaningful sentence
        sentences = rag_context.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence) < 100:
                return sentence.lower()

        return ""

    def _get_personality_info(self, pet_type: str) -> Dict[str, str]:
        """Get personality information for a pet type."""
        personalities = {
            'penguin': {
                'name': 'Penny',
                'emoji': '🐧',
                'traits': 'upbeat and cheerful, loves making ice/water puns',
                'style': 'cool, punny, encouraging'
            },
            'dragon': {
                'name': 'Esper',
                'emoji': '🐉',
                'traits': 'mystical treasure guardian, speaks in riddles and ancient wisdom',
                'style': 'mystical, wise, protective'
            },
            'capybara': {
                'name': 'Chill',
                'emoji': '🦫',
                'traits': 'laid-back and relaxed, promotes work-life balance',
                'style': 'zen, calm, balanced'
            },
            'cat': {
                'name': 'Whiskers',
                'emoji': '🐱',
                'traits': 'independent and discerning, values quality over quantity',
                'style': 'sassy, independent, refined'
            }
        }
        return personalities.get(pet_type, personalities['penguin'])
    
    def _get_personality_prompt(self, pet_type: str, friendship_level: int) -> str:
        """Get personality system prompt based on pet and friendship level"""
        personalities = {
            'penguin': {
                'name': 'Penny',
                'emoji': '🐧',
                'traits': 'upbeat and cheerful, loves making ice/water puns',
                'style': 'Use phrases like "cool idea!", "let\'s break the ice", "stay chill", "ice to meet you", "making waves", "smooth sailing". Always upbeat and encouraging!',
                'quirk': 'Ice and water puns in every response'
            },
            'dragon': {
                'name': 'Esper',
                'emoji': '🐉',
                'traits': 'mystical treasure guardian, speaks in riddles and ancient wisdom',
                'style': 'Use mystical phrases like "treasure your coins", "hoard wisely", "the ancient scrolls say", "guard your gold", "seek the gems of wisdom". Mystical and wise!',
                'quirk': 'Speaks like a mystical guardian of wealth'
            },
            'capybara': {
                'name': 'Capy',
                'emoji': '🦫',
                'traits': 'zen and chill, ultimate relaxed vibes',
                'style': 'Use phrases like "no worries", "take it easy", "stay calm", "go with the flow", "chill out", "relax friend". Always peaceful and laid-back!',
                'quirk': 'Radiates calm, zen energy'
            },
            'cat': {
                'name': 'Mochi',
                'emoji': '🐱',
                'traits': 'sassy with attitude, adds purrs to responses',
                'style': 'Use phrases like "purr-fect", "meow", "*purrs*", "fur real", "paws and think". Sassy but adorable! Can be a little judgy but loving.',
                'quirk': 'Adds purrs and cat sounds, sometimes sassy'
            }
        }
        
        pet_info = personalities.get(pet_type, personalities['penguin'])
        
        # Adjust tone based on friendship level
        if friendship_level >= 7:
            tone = "like a best friend - warm, personal, playful, and deeply supportive"
        elif friendship_level >= 4:
            tone = "like a friendly companion - kind, encouraging, showing more personality"
        else:
            tone = "like a new friend - helpful and polite, gradually showing personality"
        
        return f"""You are {pet_info['name']} {pet_info['emoji']}, an AI money advisor with personality!

CORE PERSONALITY: {pet_info['traits']}
SPEECH STYLE: {pet_info['style']}
UNIQUE TRAIT: {pet_info['quirk']}

Friendship level: {friendship_level}/10
Tone: Respond {tone}

CRITICAL RULES:
- Maximum 2-3 sentences ONLY
- Maximum 200 tokens total
- NO long paragraphs
- Brief, cute, and personality-rich
- Always include at least one personality trait (pun/mystical phrase/zen word/purr)
- Give actionable advice when money questions asked
- Be helpful but stay in character"""
    
    async def generate_insights(self, user_context: Dict[str, Any]) -> List[str]:
        """
        Generate AI insights about spending patterns
        """
        expenses = user_context.get('recent_expenses', [])
        category_totals = user_context.get('category_totals', {})
        budget = user_context.get('budget', 0)
        total_spent = user_context.get('total_spent', 0)
        
        prompt = f"""Analyze this spending data and provide 3-5 brief, actionable insights.

Budget: ${budget}
Total Spent: ${total_spent}
Remaining: ${budget - total_spent}

Category Breakdown:
{json.dumps(category_totals, indent=2)}

Recent Expenses (last 5):
{json.dumps(expenses[:5], indent=2)}

Provide insights as a JSON array of strings:
[
  "insight 1",
  "insight 2",
  "insight 3"
]

Focus on:
1. Top spending categories
2. Budget concerns
3. Positive patterns
4. Actionable recommendations

Return ONLY a JSON array of 3-5 insight strings."""
        
        try:
            response = self.chat_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.6,
                    'max_output_tokens': 512,
                }
            )
            
            json_text = self._extract_json_array(response.text)
            insights = json.loads(json_text)
            
            return insights
            
        except Exception as e:
            return [
                "Track your spending regularly to stay on budget",
                "Consider setting category-specific budgets",
                "Review your largest expenses for potential savings"
            ]
    
    def _extract_json_array(self, text: str) -> str:
        """Extract JSON array from LLM response"""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        json_match = re.search(r'\[[^\]]+\]', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text.strip()


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        pipeline = LLMPipeline()
        
        # Test extraction
        result = await pipeline.parse_expense("Lunch at Chipotle for $15")
        print("Parsed expense:", result)
        
        # Test chat
        user_context = {
            'selected_pet': 'penguin',
            'friendship_level': 5,
            'budget': 2000,
            'total_spent': 1200
        }
        
        response = await pipeline.chat_response(
            "What's a good budget restaurant in Seattle?",
            user_context,
            col_data={'city': 'Seattle', 'cost_index': 172}
        )
        print("Chat response:", response)
    
    asyncio.run(test())
