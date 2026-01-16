import json
import mcp.types as types
from .core import server, transcript_cache, openai_client, fetch_transcript, logger
from .config import config  # [추가] 설정 가져오기

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

    logger.info(f"[Tool] Analyzing video: {video_id}")

    # 1. 자막 데이터 확보
    transcript = await fetch_transcript(video_id)
    transcript_cache[video_id] = transcript  # Resource 조회를 위해 캐싱

    # 2. AI 분석 (OpenAI or Ollama)
    analysis_text = ""
    if openai_client:
        try:
            # [수정] 설정된 모델(config.LLM_MODEL)을 사용하도록 변경
            response = await openai_client.chat.completions.create(
                model=config.LLM_MODEL, 
                messages=[
                    {"role": "system", "content": "Analyze for sponsors. Return JSON summary."},
                    {"role": "user", "content": transcript}
                ]
            )
            analysis_text = response.choices[0].message.content
        except Exception as e:
            analysis_text = f"LLM API Error: {str(e)}"
    else:
        # Mock Data Generation
        analysis_text = json.dumps({
            "status": "mock_success",
            "sponsor": "NordVPN (Simulated)",
            "segments": ["02:30 - 03:15"],
            "summary": "This is a simulated analysis because LLM Client is missing."
        }, indent=2)

    return [types.TextContent(type="text", text=analysis_text)]