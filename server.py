import os
import asyncio
import json
import logging
from typing import Any
from dotenv import load_dotenv

# MCP Core Imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

import yt_dlp
from openai import AsyncOpenAI

# 환경 변수 로드
load_dotenv()

# Logger 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# [MCP Concept: Server Initialization]
# MCP 서버 인스턴스 생성
server = Server("youtube-sponsor-analyst")

# OpenAI 클라이언트 (API Key가 없으면 None 처리하여 Mock 모드 지원)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Resource 캐싱을 위한 메모리 저장소
transcript_cache = {}

async def fetch_transcript(video_id: str) -> str:
    """yt-dlp를 사용하여 자막 메타데이터를 가져옵니다 (Helper)."""
    def _download():
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'quiet': True,
        }
        # Blocking I/O를 비동기 루프에서 실행하지 않도록 Executor 사용
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_id, download=False)
                return f"Title: {info.get('title')}\nDesc: {info.get('description')[:500]}..."
            except Exception as e:
                return f"Error: {str(e)}"

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download)

# ------------------------------------------------------------------------------
# 1. [MCP Concept: Tools] - 모델이 실행할 수 있는 함수 정의
# ------------------------------------------------------------------------------
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="analyze_sponsor_block",
            description="유튜브 영상 ID를 받아 스폰서 광고 구간을 분석합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {"type": "string", "description": "Youtube Video ID (e.g. dQw4w9WgXcQ)"},
                },
                "required": ["video_id"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name != "analyze_sponsor_block":
        raise ValueError(f"Unknown tool: {name}")

    video_id = arguments.get("video_id")
    if not video_id:
        raise ValueError("video_id is required")

    # 1. 자막 데이터 확보
    transcript = await fetch_transcript(video_id)
    transcript_cache[video_id] = transcript  # Resource 조회를 위해 캐싱

    # 2. AI 분석 (OpenAI or Mock)
    analysis_text = ""
    if openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Analyze for sponsors. Return JSON summary."},
                    {"role": "user", "content": transcript}
                ]
            )
            analysis_text = response.choices[0].message.content
        except Exception as e:
            analysis_text = f"OpenAI API Error: {str(e)}"
    else:
        # Mock Data Generation
        analysis_text = json.dumps({
            "status": "mock_success",
            "sponsor": "NordVPN (Simulated)",
            "segments": ["02:30 - 03:15"],
            "summary": "This is a simulated analysis because OPENAI_API_KEY is missing."
        }, indent=2)

    return [types.TextContent(type="text", text=analysis_text)]

# ------------------------------------------------------------------------------
# 2. [MCP Concept: Resources] - 클라이언트가 읽을 수 있는 데이터 소스
# ------------------------------------------------------------------------------
@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=types.AnyUrl(f"youtube://transcript/{vid}"),
            name=f"Transcript for {vid}",
            mimeType="text/plain",
        )
        for vid in transcript_cache.keys()
    ]

@server.read_resource()
async def handle_read_resource(uri: types.AnyUrl) -> str | bytes:
    # URI 파싱: youtube://transcript/{video_id}
    parsed = str(uri).split("/")
    if len(parsed) < 4 or parsed[2] != "transcript":
        raise ValueError("Invalid Resource URI")
    
    video_id = parsed[3]
    return transcript_cache.get(video_id, "Transcript not found (Analyze first).")

# ------------------------------------------------------------------------------
# 3. [MCP Concept: Prompts] - 재사용 가능한 프롬프트 템플릿
# ------------------------------------------------------------------------------
@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="sponsor_detective",
            description="스폰서 탐정 페르소나",
            arguments=[
                types.PromptArgument(name="video_id", description="Target Video ID", required=True)
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name != "sponsor_detective":
        raise ValueError(f"Unknown prompt: {name}")
    
    video_id = arguments.get("video_id", "UNKNOWN")
    return types.GetPromptResult(
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Please act as a meticulous detective analyzing video {video_id} for hidden marketing."
                )
            )
        ]
    )

async def main():
    # Stdio Transport 실행
    async with stdio_server() as (read, write):
        await server.run(
            read, write,
            server.create_initialization_options()
        )

# server.py의 마지막 부분 수정 권장
if __name__ == "__main__":
    # Windows에서 MCP Stdio 통신을 위해서는 ProactorEventLoop(기본값)가 필요합니다.
    # 따라서 WindowsSelectorEventLoopPolicy 설정 코드는 삭제합니다.
    asyncio.run(main())