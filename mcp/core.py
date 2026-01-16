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

# 3. 외부 클라이언트 설정
openai_client = None
if config.OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

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