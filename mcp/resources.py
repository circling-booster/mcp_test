import mcp.types as types
from .core import server, transcript_cache

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