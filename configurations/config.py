import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DATABASE_URL= os.getenv("DATABASE_URL")
OPENWHETHER_API_KEY = os.getenv("OPENWHETHER_API_KEY")

def get_llm():
    return ChatOpenAI(model = os.getenv("OPENAI_MODEL", "gpt-5-mini"))