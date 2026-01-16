import os
import sys
import ctypes
import subprocess
import time
import winreg
import atexit

# ==============================================================================
# [Configuration] Force Settings
# ==============================================================================
PROXY_HOST = "127.0.0.1:8080"
MITM_CERT_PATH = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.cer")

def is_admin():
    """관리자 권한 확인"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def force_admin():
    """관리자 권한으로 재실행 (필수)"""
    if not is_admin():
        print("!!! 관리자 권한 요청 중... (시스템 설정을 위해 필수입니다) !!!")
        # 파라미터를 그대로 넘겨서 관리자 권한으로 다시 실행
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

def ensure_certificate():
    """인증서가 없으면 mitmdump를 잠깐 켰다 꺼서 생성 후 등록"""
    if not os.path.exists(MITM_CERT_PATH):
        print(f"[Setup] 인증서가 없습니다. 생성 중... ({MITM_CERT_PATH})")
        # 1. 인증서 생성을 위해 잠시 실행 (5초 후 종료)
        proc = subprocess.Popen(["mitmdump", "--version"], stdout=subprocess.DEVNULL)
        time.sleep(3)
        proc.terminate()
    
    print("[Setup] Root 인증서 강제 등록 (보안 경고 무시)...")
    # 2. certutil로 강제 등록 (Quiet Mode)
    # -f: 강제, -addstore root: 신뢰할 수 있는 루트 기관에 추가
    cmd = f'certutil -addstore -f "root" "{MITM_CERT_PATH}"'
    os.system(cmd)

def set_proxy(enable=True):
    """레지스트리 직접 수정하여 프록시 On/Off"""
    settings_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, settings_path, 0, winreg.KEY_WRITE)
        
        if enable:
            print(f"[Setup] 윈도우 시스템 프록시 설정 -> {PROXY_HOST}")
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, PROXY_HOST)
            # HTTP/HTTPS 모두 덮어쓰기
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
        else:
            print("[Exit] 윈도우 시스템 프록시 해제 (복구)")
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        
        winreg.CloseKey(key)
        
        # 시스템에 변경 사항 즉시 전파
        import ctypes
        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, 39, 0, 0) # INTERNET_OPTION_SETTINGS_CHANGED
        internet_set_option(0, 37, 0, 0) # INTERNET_OPTION_REFRESH
        
    except Exception as e:
        print(f"[Error] 프록시 설정 실패: {e}")

def main():
    # 1. 관리자 권한 강제
    force_admin()
    
    # 2. 환경 설정
    ensure_certificate()
    set_proxy(True)
    
    # 3. 종료 시 프록시 끄기 예약
    atexit.register(lambda: set_proxy(False))
    
    print("\n" + "="*50)
    print(" [SYSTEM READY] YouTube에 접속하세요.")
    print(" 로그창을 닫으면 프록시가 자동으로 해제됩니다.")
    print("="*50 + "\n")
    
    # 4. Mitmproxy 실행 (현재 창에서)
    # proxy_addon.py를 로드하며 실행
    cmd = ["mitmdump", "-s", "proxy_addon.py"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        set_proxy(False)

if __name__ == "__main__":
    main()