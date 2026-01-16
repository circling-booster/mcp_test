import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    # MCP 서버 설정
    MCP_SERVER_NAME = "youtube-sponsor-analyst"
    
    # 전송 모드: "stdio", "sse", "both"
    TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    # SSE(Online) 설정
    SSE_HOST = os.getenv("MCP_SSE_HOST", "0.0.0.0")
    SSE_PORT = int(os.getenv("MCP_SSE_PORT", "8000"))
    
    # [수정] LLM 설정 (Ollama vs OpenAI)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    
    # OpenAI API 키
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # [신규] 감시 허용 도메인 목록 (Whitelist)
    # 이 도메인들에 포함된 문자열이 호스트명에 있으면 감시합니다.
    ALLOWED_DOMAINS = [
        "youtube.com",
        "googlevideo.com",
        "youtube-nocookie.com"
    ]

config = Config()