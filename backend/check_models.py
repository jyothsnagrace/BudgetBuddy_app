import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Import the pipeline
from llm_pipeline import LLMPipeline

# Create instance and inspect
pipeline = LLMPipeline()
print(f"Extraction model: {pipeline.extraction_model._model_name}")
print(f"Normalization model: {pipeline.normalization_model._model_name}")
print(f"Chat model: {pipeline.chat_model._model_name}")
