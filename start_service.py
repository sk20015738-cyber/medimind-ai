"""
MediMind AI - One-Click Service Launcher (start_service.py)
Starts backend/server.py, polls until port 8000 is ready, and automatically launches the web browser.
"""

import sys
import os
import time
import socket
import webbrowser
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = ROOT_DIR / "backend" / "server.py"
HOST = "localhost"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Checks whether a TCP port is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except (socket.error, OSError):
            return False


def main():
    print("=" * 60)
    print(" 🏥 MediMind AI - 스마트 복약 관리 및 DUR 상호작용 알림 시스템")
    print("=" * 60)
    print(f"[*] 루트 경로: {ROOT_DIR}")
    print(f"[*] 서버 스크립트: {SERVER_SCRIPT}")

    if not SERVER_SCRIPT.exists():
        print(f"[!] 오류: 서버 스크립트를 찾을 수 없습니다: {SERVER_SCRIPT}")
        sys.exit(1)

    # Check if already running
    if is_port_open(HOST, PORT, timeout=0.5):
        print(f"[*] 포트 {PORT}가 이미 열려 있습니다. 웹 브라우저를 바로 엽니다...")
        webbrowser.open(URL)
        print(f"[+] 브라우저가 열렸습니다: {URL}")
        return

    # Start backend/server.py as a subprocess
    print(f"[*] 백엔드 서버를 시작합니다... (Python: {sys.executable})")
    server_process = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT), str(PORT)],
        cwd=str(ROOT_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    # Wait for the server to be ready
    max_wait = 15  # seconds
    start_time = time.time()
    server_ready = False

    print(f"[*] 서버 준비 대기 중 (최대 {max_wait}초)...", end="", flush=True)
    while time.time() - start_time < max_wait:
        # Check if process died early
        if server_process.poll() is not None:
            print(f"\n[!] 백엔드 프로세스가 예기치 않게 종료되었습니다. (종료 코드: {server_process.returncode})")
            sys.exit(server_process.returncode)

        if is_port_open(HOST, PORT, timeout=0.5):
            server_ready = True
            break
        print(".", end="", flush=True)
        time.sleep(0.5)

    print()
    if server_ready:
        print(f"[✔] MediMind AI 서버가 성공적으로 시작되었습니다! ({URL})")
        print(f"[*] 기본 브라우저를 실행합니다...")
        webbrowser.open(URL)
        print(f"[*] 서버가 실행 중입니다. 종료하려면 이 창에서 Ctrl+C를 누르세요.\n")
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n[*] 사용자에 의해 종료 요청됨. 서버 프로세스를 안전하게 종료합니다...")
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("[+] MediMind AI 서버가 정상 종료되었습니다.")
    else:
        print(f"[!] {max_wait}초 내에 서버에 연결하지 못했습니다.")
        server_process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()
