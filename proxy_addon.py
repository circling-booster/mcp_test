import sys
import os
import threading
import queue
import asyncio
import tkinter as tk
from tkinter import scrolledtext

# Mitmproxy
from mitmproxy import http, ctx

# MCP Client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Shared Queue
GUI_QUEUE = queue.Queue()

# --- MCP Client Logic ---
async def mcp_client_task(video_id: str, log_callback):
    # server.py 경로 계산
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    
    log_callback(f"[MCP] Connecting to Server for {video_id}...")
    
    # Windows 환경 변수 등 상속
    env = os.environ.copy()
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                log_callback("[MCP] Requesting Analysis (Tool Call)...")
                result = await session.call_tool(
                    "analyze_sponsor_block",
                    arguments={"video_id": video_id}
                )
                
                content = result.content[0].text
                log_callback(f"\n== RESULT ==\n{content}\n")

    except Exception as e:
        log_callback(f"[ERROR] MCP Fail: {str(e)}")

# --- GUI Logic ---
class InspectorGUI:
    def __init__(self):
        self.root = None
        self.current_video_id = None
        
    def start(self):
        self.root = tk.Tk()
        self.root.title("YouTube MCP Inspector")
        self.root.geometry("400x500")
        self.root.attributes("-topmost", True) # 창을 항상 위로
        
        tk.Label(self.root, text="Waiting for Video...", font=("Consolas", 12)).pack(pady=10)
        
        self.btn = tk.Button(self.root, text="Analyze", state=tk.DISABLED, 
                             command=self.on_analyze, bg="gray", fg="white", font=("Arial", 10, "bold"))
        self.btn.pack(fill=tk.X, padx=10)
        
        self.log_area = scrolledtext.ScrolledText(self.root)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.check_queue()
        self.root.mainloop()

    def check_queue(self):
        try:
            while True:
                vid = GUI_QUEUE.get_nowait()
                self.current_video_id = vid
                self.btn.config(state=tk.NORMAL, bg="red", text=f"Analyze: {vid}")
                self.log(f"Detected: {vid}")
        except queue.Empty:
            pass
        finally:
            self.root.after(500, self.check_queue)

    def log(self, msg):
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def on_analyze(self):
        if not self.current_video_id: return
        self.btn.config(state=tk.DISABLED, text="Analyzing...")
        threading.Thread(target=self.run_bridge, daemon=True).start()

    def run_bridge(self):
        asyncio.run(mcp_client_task(self.current_video_id, self.safe_log))
        self.root.after(0, lambda: self.btn.config(state=tk.NORMAL, text="Analyze Again"))

    def safe_log(self, msg):
        self.root.after(0, lambda: self.log(msg))

gui = InspectorGUI()

# --- Mitmproxy Addon ---
class Detector:
    def running(self):
        threading.Thread(target=gui.start, daemon=True).start()

    def request(self, flow: http.HTTPFlow):
        # YouTube Video ID 감지 로직
        if "youtube.com" in flow.request.pretty_host and "/watch" in flow.request.path:
            if "v" in flow.request.query:
                vid = flow.request.query["v"]
                if vid != gui.current_video_id:
                    GUI_QUEUE.put(vid)
                    ctx.log.info(f"Detected: {vid}")

addons = [Detector()]