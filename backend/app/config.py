import os
from dotenv import load_dotenv

load_dotenv()

# MySQL Configuration
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "academic_copilot_db")
MYSQL_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# Neo4j AuraDB Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d6e4cf18.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d6e4cf18")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Local Ollama settings only. No paid API is used.
LLM_PROVIDER = "ollama"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
