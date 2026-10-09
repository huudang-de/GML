import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
from app.agents.rag_agent import RAGAgent

if __name__ == "__main__":
    print("Building vector store...")
    agent = RAGAgent()
    agent._build_vectorstore()
    print("Vector store built successfully at ./chroma_db")
