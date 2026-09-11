
import os
import streamlit as st

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load local .env file
load_dotenv()

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENWHETHER_API_KEY = os.getenv("OPENWHETHER_API_KEY")

# Database configuration
# Streamlit Cloud → Supabase
# Local PC → local PostgreSQL from .env

if "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]
else:
    DATABASE_URL = os.getenv("DATABASE_URL")


def get_llm():
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini")
    )

