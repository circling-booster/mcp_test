import asyncio
import logging
import json
import yt_dlp
from mcp.server import Server
from openai import AsyncOpenAI
from .config import config

# Logger 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# 1. Server 인스턴스 생성 (Singleton)
server = Server(config.MCP_SERVER_NAME)

# 2. 공유 상태 (Resource Caching)
transcript_cache = {}

# 3. [수정] 외부 클라이언트 설정 (Ollama 지원)
openai_client = None

if config.LLM_PROVIDER == "ollama":
    logger.info(f"Connecting to Local LLM (Ollama) at {config.OLLAMA_BASE_URL} [{config.LLM_MODEL}]")
    # Ollama는 OpenAI API와 호환되므로 AsyncOpenAI 클라이언트를 그대로 사용합니다.
    # api_key는 필수값이지만 Ollama에서는 무시되므로 더미 값을 넣습니다.
    openai_client = AsyncOpenAI(
        base_url=config.OLLAMA_BASE_URL,
        api_key="ollama" 
    )
elif config.OPENAI_API_KEY:
    logger.info("Connecting to OpenAI API")
    openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
else:
    logger.warning("No valid LLM configuration found. Mock mode will be used.")

# 4. 공통 유틸리티 함수
async def fetch_transcript(video_id: str) -> str:
    """yt-dlp를 사용하여 자막 메타데이터를 가져옵니다."""
    def _download():
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_id, download=False)
                return f"Title: {info.get('title')}\nDesc: {info.get('description')[:500]}..."
            except Exception as e:
                return f"Error: {str(e)}"

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download)