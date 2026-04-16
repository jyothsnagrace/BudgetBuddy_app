"""
BudgetBuddy Backend Package
Python-based LLM-powered expense tracking backend
"""

__version__ = "1.0.0"
__author__ = "BudgetBuddy Team"

from .llm_pipeline import LLMPipeline
from .function_calling import FunctionCallingSystem
from .receipt_parser import ReceiptParser
from .cost_of_living import CostOfLivingAPI
from .database import DatabaseClient
from .auth import AuthManager

__all__ = [
    'LLMPipeline',
    'FunctionCallingSystem',
    'ReceiptParser',
    'CostOfLivingAPI',
    'DatabaseClient',
    'AuthManager'
]
