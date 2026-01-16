import mcp.types as types
from .core import server

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