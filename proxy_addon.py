import sys
import os
import threading
import queue
import asyncio
import tkinter as tk
from tkinter import scrolledtext

# Mitmproxy Imports
from mitmproxy import http, ctx

# MCP Client Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ==============================================================================
# Shared State (Bridge between Mitmproxy and Tkinter)
# ==============================================================================
GUI_QUEUE = queue.Queue()

# ==============================================================================
# 1. MCP Client Logic (Execution Layer)
# ==============================================================================
async def mcp_client_task(video_id: str, log_callback):
    """MCP 서버와 연결하고 Tool을 호출하는 비동기 작업"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 서버 환경 변수 설정
    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "stdio" 
    env["PYTHONPATH"] = current_dir # 현재 폴더를 Path에 추가하여 mcp_test 패키지 인식

    # [수정됨] 폴더 이름을 'mcp' -> 'mcp_test'로 변경했다고 가정하고 실행
    # 이렇게 해야 설치된 라이브러리 'mcp'와 이름이 충돌하지 않습니다.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_test.server"], 
        env=env
    )

    log_callback(f"Connecting to MCP Server... (Target: {video_id})")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # [MCP Concept: Tool Execution]
                log_callback(">> Calling Tool: analyze_sponsor_block")
                result = await session.call_tool(
                    "analyze_sponsor_block",
                    arguments={"video_id": video_id}
                )
                
                # 결과 출력
                content = result.content[0].text
                log_callback(f"\n[Analysis Result]\n{content}\n")
                
                # [MCP Concept: Resource Reading]
                log_callback(">> Reading Resource: youtube://transcript/...")
                try:
                    res = await session.read_resource(f"youtube://transcript/{video_id}")
                    log_callback(f"[Resource Content Preview]: {str(res.contents[0].text)[:100]}...\n")
                except Exception as e:
                    log_callback(f"[Resource Error]: {e}")

    except Exception as e:
        log_callback(f"[MCP Error]: {str(e)}")

# ==============================================================================
# 2. Tkinter GUI (Interaction Layer)
# ==============================================================================
class InspectorGUI:
    def __init__(self):
        self.root = None
        self.current_video_id = None
        
    def start(self):
        """GUI 메인 루프 실행"""
        self.root = tk.Tk()
        self.root.title("MCP YouTube Inspector")
        self.root.geometry("500x600")
        
        tk.Label(self.root, text="Waiting for YouTube Video...", font=("Arial", 12, "bold")).pack(pady=10)
        self.status_lbl = tk.Label(self.root, text="Status: Idle", fg="gray")
        self.status_lbl.pack()
        
        self.btn_analyze = tk.Button(self.root, text="Analyze via MCP", state=tk.DISABLED, 
                                     command=self.on_analyze, bg="#dddddd", height=2)
        self.btn_analyze.pack(fill=tk.X, padx=20, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(self.root, height=20)
        self.log_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.check_queue()
        self.root.mainloop()

    def check_queue(self):
        """Mitmproxy 스레드로부터 데이터 수신"""
        try:
            while True:
                video_id = GUI_QUEUE.get_nowait()
                self.handle_detection(video_id)
        except queue.Empty:
            pass
        finally:
            self.root.after(500, self.check_queue)

    def handle_detection(self, video_id):
        self.current_video_id = video_id
        self.status_lbl.config(text=f"Detected: {video_id}", fg="blue")
        self.btn_analyze.config(state=tk.NORMAL, bg="#4CAF50", fg="white")
        self.log(f"Captured Video ID: {video_id}")
        self.root.deiconify()
        self.root.lift()

    def log(self, msg):
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def on_analyze(self):
        if not self.current_video_id: return
        self.btn_analyze.config(state=tk.DISABLED)
        threading.Thread(target=self.run_async_bridge, daemon=True).start()

    def run_async_bridge(self):
        asyncio.run(mcp_client_task(self.current_video_id, self.safe_log))
        self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))

    def safe_log(self, msg):
        self.root.after(0, lambda: self.log(msg))

gui_app = InspectorGUI()

# ==============================================================================
# 3. Mitmproxy Addon (Detection Layer)
# ==============================================================================
class SponsorDetector:
    def running(self):
        """Mitmproxy 시작 시 GUI 스레드 실행"""
        ctx.log.info("Starting GUI Thread...")
        t = threading.Thread(target=gui_app.start, daemon=True)
        t.start()

    def request(self, flow: http.HTTPFlow):
        if "youtube.com" in flow.request.pretty_host and "/watch" in flow.request.path:
            query = flow.request.query
            if "v" in query:
                video_id = query["v"]
                GUI_QUEUE.put(video_id)
                ctx.log.info(f"YouTube Video Detected: {video_id}")

addons = [
    SponsorDetector()
]