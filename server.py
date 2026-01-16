import os
import asyncio
import json
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
import yt_dlp
from openai import AsyncOpenAI

load_dotenv()
server = Server("youtube-analyst")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(
        name="analyze_sponsor_block",
        description="Analyze YouTube video for sponsors",
        inputSchema={"type": "object", "properties": {"video_id": {"type": "string"}}, "required": ["video_id"]}
    )]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "analyze_sponsor_block": raise ValueError("Unknown tool")
    video_id = arguments["video_id"]
    
    # 1. Fetch Metadata (Mocking actual download for speed)
    # 실제로는 yt-dlp로 다운로드 받아야 하지만, 빠른 테스트를 위해 Mock 처리
    # 필요시 yt_dlp 로직 활성화 가능
    transcript_mock = f"This is a transcript for video {video_id}. Today's sponsor is NordVPN..."
    
    # 2. AI Analysis
    if openai_client:
        try:
            res = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Find sponsors: {transcript_mock}"}]
            )
            text = res.choices[0].message.content
        except:
            text = "Error calling OpenAI."
    else:
        text = f"[MOCK] Detected Sponsor: NordVPN (Video: {video_id})"

    return [types.TextContent(type="text", text=text)]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    # Windows 필수 설정: SelectorEventLoop 사용 금지 -> 기본값 유지
    asyncio.run(main())