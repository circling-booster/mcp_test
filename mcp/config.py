import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    # MCP 서버 설정
    MCP_SERVER_NAME = "youtube-sponsor-analyst"
    
    # 전송 모드: "stdio", "sse", "both"
    # 기본값은 기존 호환성을 위해 stdio로 설정하지만, .env에서 변경 가능
    TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    # SSE(Online) 설정
    SSE_HOST = os.getenv("MCP_SSE_HOST", "0.0.0.0")
    SSE_PORT = int(os.getenv("MCP_SSE_PORT", "8000"))
    
    # 외부 API 키
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

config = Config()