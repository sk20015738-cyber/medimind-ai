"""
MediMind AI - REST API & Static File Server (server.py)
High performance HTTP server built with standard library http.server.
Zero external dependencies.
"""

import http.server
import json
import os
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db
import dur_database
import ai_engine

# Potential frontend directories
FRONTEND_DIRS = [
    PROJECT_ROOT / "frontend",
    BACKEND_DIR / "frontend",
    BACKEND_DIR / "static",
    PROJECT_ROOT / "static"
]


def find_frontend_dir() -> Optional[Path]:
    """Finds the existing frontend directory, or defaults to PROJECT_ROOT / 'frontend'."""
    for p in FRONTEND_DIRS:
        if p.exists() and p.is_dir():
            return p
    return PROJECT_ROOT / "frontend"


FRONTEND_DIR = find_frontend_dir()


class MediMindRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler supporting REST API endpoints and frontend static assets."""

    server_version = "MediMindServer/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    # -------------------------------------------------------------
    # Header & CORS Utilities
    # -------------------------------------------------------------
    def _set_cors_headers(self):
        """Sets Cross-Origin Resource Sharing (CORS) headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def _send_json(self, data: Any, status_code: int = 200):
        """Encodes and sends a JSON response with UTF-8 encoding."""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status_code: int = 400):
        """Sends an error message formatted as JSON."""
        self._send_json({"success": False, "error": message}, status_code=status_code)

    def _read_json_body(self) -> Dict[str, Any]:
        """Reads and parses the JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw_data = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw_data) if raw_data.strip() else {}

    def do_OPTIONS(self):
        """Handles CORS preflight OPTIONS requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    # -------------------------------------------------------------
    # GET Routing
    # -------------------------------------------------------------
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        try:
            # API Endpoints
            if path == "/api/medications":
                self._handle_get_medications()
            elif path.startswith("/api/medications/"):
                med_id = int(path.split("/")[-1])
                self._handle_get_medication_by_id(med_id)
            elif path == "/api/logs":
                self._handle_get_logs(query)
            elif path == "/api/report":
                self._handle_get_report(query)
            elif path == "/api/profile":
                self._handle_get_profile()
            elif path.startswith("/api/"):
                self._send_error(f"존재하지 않는 API 경로입니다: {path}", 404)
            else:
                # Serve Static Frontend Files
                self._serve_static_file(path)
        except Exception as e:
            self._send_error(f"서버 내부 오류: {str(e)}", 500)

    # -------------------------------------------------------------
    # POST Routing
    # -------------------------------------------------------------
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            body = self._read_json_body()

            if path == "/api/medications":
                self._handle_create_medication(body)
            elif path == "/api/logs":
                self._handle_record_log(body)
            elif path == "/api/ai/parse-prescription":
                self._handle_ai_parse_prescription(body)
            elif path == "/api/ai/check-interactions":
                self._handle_ai_check_interactions(body)
            elif path == "/api/ai/chat":
                self._handle_ai_chat(body)
            elif path == "/api/profile":
                self._handle_update_profile(body)
            elif path == "/api/seed-reset":
                self._handle_seed_reset()
            else:
                self._send_error(f"존재하지 않는 POST 엔드포인트: {path}", 404)
        except Exception as e:
            self._send_error(f"요청 처리 중 오류: {str(e)}", 400)

    # -------------------------------------------------------------
    # DELETE Routing
    # -------------------------------------------------------------
    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            if path.startswith("/api/medications/"):
                med_id = int(path.split("/")[-1])
                self._handle_delete_medication(med_id)
            else:
                self._send_error(f"존재하지 않는 DELETE 엔드포인트: {path}", 404)
        except Exception as e:
            self._send_error(f"삭제 처리 오류: {str(e)}", 400)

    # -------------------------------------------------------------
    # Static File Handling
    # -------------------------------------------------------------
    def _serve_static_file(self, path: str):
        """Serves HTML, CSS, JS and asset files from the frontend directory."""
        if not FRONTEND_DIR.exists():
            # If frontend directory doesn't exist yet, return friendly placeholder
            self._send_json({
                "service": "MediMind AI Backend Server",
                "status": "online",
                "frontend_path": str(FRONTEND_DIR),
                "message": "백엔드 API 서버가 정상 실행 중입니다. 프론트엔드 정적 파일이 준비되면 UI가 표시됩니다.",
                "endpoints": [
                    "/api/medications",
                    "/api/logs",
                    "/api/ai/parse-prescription",
                    "/api/ai/check-interactions",
                    "/api/ai/chat",
                    "/api/report"
                ]
            })
            return

        # Map root to index.html
        if path == "/" or path == "":
            path = "/index.html"

        # Sanitize path to prevent directory traversal
        clean_path = path.lstrip("/").replace("..", "")
        file_path = FRONTEND_DIR / clean_path

        if file_path.exists() and file_path.is_file():
            # Let SimpleHTTPRequestHandler serve it
            self.path = "/" + clean_path
            super().do_GET()
        else:
            # Fallback to index.html for SPA routing if available
            fallback = FRONTEND_DIR / "index.html"
            if fallback.exists():
                self.path = "/index.html"
                super().do_GET()
            else:
                self._send_error(f"요청한 파일을 찾을 수 없습니다: {path}", 404)

    # -------------------------------------------------------------
    # API Controllers
    # -------------------------------------------------------------

    def _handle_get_medications(self):
        """GET /api/medications"""
        meds = db.get_all_medications()
        self._send_json({"success": True, "count": len(meds), "medications": meds})

    def _handle_get_medication_by_id(self, med_id: int):
        """GET /api/medications/<id>"""
        med = db.get_medication_by_id(med_id)
        if not med:
            self._send_error(f"ID {med_id} 약물을 찾을 수 없습니다.", 404)
            return
        self._send_json({"success": True, "medication": med})

    def _handle_create_medication(self, body: Dict[str, Any]):
        """POST /api/medications"""
        name = body.get("name", "").strip()
        dosage = body.get("dosage", "1정").strip()
        frequency = body.get("frequency", "1일 1회").strip()
        meal_timing = body.get("meal_timing", "식후 30분").strip()
        category = body.get("category", "일반약").strip()
        instructions = body.get("instructions", "").strip()
        schedules = body.get("schedules", [])

        if not name:
            self._send_error("약물 이름(name)은 필수 항목입니다.")
            return

        if not schedules:
            # Generate default schedule
            schedules = [{"time_slot": "아침", "specific_time": "08:00", "is_active": 1}]

        med_id = db.add_medication(
            name=name,
            dosage=dosage,
            frequency=frequency,
            meal_timing=meal_timing,
            category=category,
            schedules=schedules,
            instructions=instructions
        )

        # Run instant DUR check with newly added medication
        all_meds = db.get_all_medications()
        dur_result = ai_engine.check_dur(all_meds)

        created_med = db.get_medication_by_id(med_id)

        self._send_json({
            "success": True,
            "message": f"'{name}' 약물이 성공적으로 등록되었습니다.",
            "medication_id": med_id,
            "medication": created_med,
            "dur_check": dur_result
        }, 201)

    def _handle_delete_medication(self, med_id: int):
        """DELETE /api/medications/<id>"""
        med = db.get_medication_by_id(med_id)
        if not med:
            self._send_error(f"ID {med_id} 약물이 존재하지 않습니다.", 404)
            return

        deleted = db.delete_medication(med_id)
        self._send_json({
            "success": deleted,
            "deleted_id": med_id,
            "message": f"'{med['name']}' 약물이 삭제되었습니다."
        })

    def _handle_get_logs(self, query: Dict[str, Any]):
        """GET /api/logs?days=7&date=YYYY-MM-DD"""
        days = int(query.get("days", ["7"])[0])
        date = query.get("date", [None])[0]

        logs = db.get_intake_logs(date=date)
        stats = db.get_adherence_stats(days=days)

        # Get today's schedule status
        today_str = datetime.now().date().isoformat()
        meds = db.get_all_medications()

        today_tasks = []
        today_logs = db.get_intake_logs(date=today_str)
        log_map = {(l["medication_id"], l["scheduled_time"]): l["status"] for l in today_logs}

        for m in meds:
            for s in m["schedules"]:
                if s.get("is_active", 1):
                    time_val = s["specific_time"]
                    status = log_map.get((m["id"], time_val), "pending")
                    today_tasks.append({
                        "medication_id": m["id"],
                        "medication_name": m["name"],
                        "dosage": m["dosage"],
                        "category": m["category"],
                        "meal_timing": m["meal_timing"],
                        "time_slot": s["time_slot"],
                        "scheduled_time": time_val,
                        "status": status
                    })

        self._send_json({
            "success": True,
            "stats": stats,
            "today_tasks": today_tasks,
            "recent_logs": logs[:30]
        })

    def _handle_record_log(self, body: Dict[str, Any]):
        """POST /api/logs"""
        med_id = body.get("medication_id")
        scheduled_date = body.get("scheduled_date") or datetime.now().date().isoformat()
        scheduled_time = body.get("scheduled_time") or datetime.now().strftime("%H:%M")
        status = body.get("status", "taken")  # 'taken', 'skipped', 'snoozed'
        notes = body.get("notes", "")

        if not med_id:
            self._send_error("medication_id는 필수 항목입니다.")
            return

        if status not in ["taken", "skipped", "snoozed"]:
            self._send_error("status는 'taken', 'skipped', 'snoozed' 중 하나여야 합니다.")
            return

        log_id = db.add_intake_log(
            medication_id=int(med_id),
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            status=status,
            notes=notes
        )

        # Return updated adherence stats
        stats = db.get_adherence_stats(days=7)

        self._send_json({
            "success": True,
            "log_id": log_id,
            "status": status,
            "message": f"복약 상태가 '{status}'(으)로 기록되었습니다.",
            "stats": stats
        })

    def _handle_ai_parse_prescription(self, body: Dict[str, Any]):
        """POST /api/ai/parse-prescription"""
        text = body.get("text", "")
        if not text:
            self._send_error("처방전 텍스트(text)가 비어 있습니다.")
            return

        parse_result = ai_engine.parse_prescription(text)
        self._send_json(parse_result)

    def _handle_ai_check_interactions(self, body: Dict[str, Any]):
        """POST /api/ai/check-interactions"""
        medications = body.get("medications")
        if not medications:
            # Use active medications currently registered in DB
            medications = db.get_all_medications()

        dur_report = ai_engine.check_dur(medications)
        self._send_json({"success": True, "dur_report": dur_report})

    def _handle_ai_chat(self, body: Dict[str, Any]):
        """POST /api/ai/chat"""
        message = body.get("message", "").strip()
        if not message:
            self._send_error("메시지 내용(message)이 비어 있습니다.")
            return

        # Fetch context
        medications = db.get_all_medications()
        profile = db.get_user_profile()

        consult_response = ai_engine.ask_pharmacist(
            question=message,
            current_medications=medications,
            user_profile=profile
        )

        self._send_json({
            "success": True,
            "response": consult_response
        })

    def _handle_get_report(self, query: Dict[str, Any]):
        """GET /api/report"""
        days = int(query.get("days", ["7"])[0])
        stats = db.get_adherence_stats(days=days)
        meds = db.get_all_medications()
        dur_report = ai_engine.check_dur(meds)
        profile = db.get_user_profile()

        # Chronotherapy Adherence Score Calculation
        chrono_score = 95
        if dur_report["overall_safety"] == "CRITICAL":
            chrono_score = 65
        elif dur_report["overall_safety"] == "MAJOR":
            chrono_score = 80
        elif dur_report["overall_safety"] == "MODERATE":
            chrono_score = 90

        self._send_json({
            "success": True,
            "generated_at": datetime.now().isoformat(),
            "profile": profile,
            "adherence_stats": stats,
            "active_medications_count": len(meds),
            "safety_overview": {
                "overall_safety": dur_report["overall_safety"],
                "badge": dur_report["safety_badge"],
                "color": dur_report["status_color"],
                "warnings_count": dur_report["warnings_count"]
            },
            "chronotherapy_score": chrono_score,
            "ai_clinical_summary": dur_report["ai_summary"],
            "chronotherapy_tips": dur_report["chronotherapy_tips"]
        })

    def _handle_get_profile(self):
        """GET /api/profile"""
        profile = db.get_user_profile()
        self._send_json({"success": True, "profile": profile})

    def _handle_update_profile(self, body: Dict[str, Any]):
        """POST /api/profile"""
        profile = db.update_user_profile(
            name=body.get("name"),
            age=body.get("age"),
            conditions=body.get("conditions"),
            senior_mode=body.get("senior_mode"),
            notification_enabled=body.get("notification_enabled")
        )
        self._send_json({
            "success": True,
            "message": "프로필 설정이 업데이트되었습니다.",
            "profile": profile
        })

    def _handle_seed_reset(self):
        """POST /api/seed-reset"""
        db.init_db(force_reset=True)
        meds = db.get_all_medications()
        self._send_json({
            "success": True,
            "message": "데이터베이스가 초기 시드 데이터로 재설정되었습니다.",
            "medications_count": len(meds)
        })


def run_server(port: int = 8000, host: str = "0.0.0.0"):
    """Starts the MediMind HTTP Server."""
    # Ensure database is initialized
    db.init_db()

    server_address = (host, port)
    httpd = http.server.HTTPServer(server_address, MediMindRequestHandler)
    print("=" * 60)
    print(f" MediMind AI Backend & Clinical Engine")
    print(f" - Running at: http://localhost:{port}")
    print(f" - Serving frontend from: {FRONTEND_DIR}")
    print(f" - SQLite DB: {db.DEFAULT_DB_PATH}")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[MediMind] Server shutting down gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = 8000
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port=port_arg)
