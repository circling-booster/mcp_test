import asyncio
import sys

# 모듈 임포트를 통해 데코레이터(@server.tool 등)가 실행되게 함
from . import tools, resources, prompts
from .core import server, logger
from .config import config

from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

async def run_stdio():
    """Stdio Transport 실행 (로컬 프로세스 통신용)"""
    logger.info("Starting STDIO Server...")
    async with stdio_server() as (read, write):
        await server.run(
            read, write,
            server.create_initialization_options()
        )

async def run_sse():
    """SSE Transport 실행 (HTTP/웹 통신용)"""
    logger.info(f"Starting SSE Server at http://{config.SSE_HOST}:{config.SSE_PORT}...")
    
    sse = SseServerTransport("/sse")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(
                streams[0], streams[1],
                server.create_initialization_options()
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
    )

    # Uvicorn 서버 설정 (stdout 오염 방지를 위해 로그 레벨 조정 가능)
    # Stdio와 함께 실행 시 로그가 섞이지 않도록 주의해야 합니다.
    log_config = uvicorn.config.LOGGING_CONFIG
    if config.TRANSPORT == "both":
        # Both 모드일 때 Uvicorn 로그가 Stdio JSON을 깨뜨리지 않도록 stderr로 보내거나 끔
        pass 

    conf = uvicorn.Config(app, host=config.SSE_HOST, port=config.SSE_PORT, log_level="info")
    server_uvicorn = uvicorn.Server(conf)
    await server_uvicorn.serve()

async def main():
    mode = config.TRANSPORT
    tasks = []

    if mode in ["stdio", "both"]:
        tasks.append(run_stdio())
    
    if mode in ["sse", "online", "both"]:
        tasks.append(run_sse())

    if not tasks:
        logger.error(f"Invalid TRANSPORT config: {mode}")
        return

    # 선택된 모드 동시 실행
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Windows SelectorEventLoopPolicy 이슈 해결 (Python 3.8+ Windows)
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass