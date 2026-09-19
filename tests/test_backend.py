"""
MediMind AI - Comprehensive Backend & AI Engine Test Suite (tests/test_backend.py)
Tests:
1. Database initialization and CRUD operations (backend/db.py)
2. AI prescription parsing on Korean prescription phrases (backend/ai_engine.py)
3. DUR interaction detection (duplicate acetaminophen, NSAID+aspirin, food/grapefruit)
4. AI Pharmacist Q&A logic (1/2 golden rule for missed dose, alcohol warning)
5. REST API endpoint responses, status codes, and UTF-8 JSON encoding (backend/server.py)
"""

import os
import sys
import json
import socket
import tempfile
import threading
import unittest
import urllib.request
import urllib.parse
from http.server import HTTPServer
from pathlib import Path

# Setup paths to import backend modules
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import db
import dur_database
import ai_engine
import server


class TestDatabaseCRUD(unittest.TestCase):
    """Test suite for SQLite3 database operations and schema integrity."""

    def setUp(self):
        # Create a dedicated temporary SQLite DB file for isolation
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()
        db.init_db(db_path=self.temp_db_path, force_reset=True)

    def tearDown(self):
        # Clean up temporary database file
        try:
            if self.temp_db_path.exists():
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_01_init_db_and_seed_data(self):
        """Verify database initialization populates 3 default medications and profile."""
        meds = db.get_all_medications(db_path=self.temp_db_path)
        self.assertGreaterEqual(len(meds), 3, "Initial database should have at least 3 seed medications")

        # Verify seed medications include blood pressure, diabetes, and gastrointestinal
        names = [m["name"] for m in meds]
        self.assertTrue(any("노바스크" in n for n in names), "Seed data should include 노바스크 (혈압약)")
        self.assertTrue(any("메트포르민" in n for n in names), "Seed data should include 메트포르민 (당뇨약)")
        self.assertTrue(any("파모티딘" in n for n in names), "Seed data should include 파모티딘 (위장약)")

        # Verify user profile seeded
        profile = db.get_user_profile(db_path=self.temp_db_path)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "김정숙")
        self.assertEqual(profile["senior_mode"], 1)

    def test_02_medication_crud(self):
        """Verify Create, Read, Update, and Delete on medications."""
        # 1. Create (Add)
        schedules = [
            {"time_slot": "아침", "specific_time": "08:00", "is_active": 1},
            {"time_slot": "저녁", "specific_time": "19:00", "is_active": 1}
        ]
        new_id = db.add_medication(
            name="테스트약정",
            dosage="10mg",
            frequency="1일 2회",
            meal_timing="식후 30분",
            category="테스트약",
            schedules=schedules,
            instructions="테스트 복용 안내",
            db_path=self.temp_db_path
        )
        self.assertIsInstance(new_id, int)
        self.assertGreater(new_id, 0)

        # 2. Read (Get by ID)
        med = db.get_medication_by_id(new_id, db_path=self.temp_db_path)
        self.assertIsNotNone(med)
        self.assertEqual(med["name"], "테스트약정")
        self.assertEqual(med["dosage"], "10mg")
        self.assertEqual(len(med["schedules"]), 2)

        # 3. Update
        updated = db.update_medication(
            med_id=new_id,
            dosage="20mg",
            instructions="용량 20mg으로 증량됨",
            schedules=[{"time_slot": "아침", "specific_time": "09:00", "is_active": 1}],
            db_path=self.temp_db_path
        )
        self.assertTrue(updated)
        med_after = db.get_medication_by_id(new_id, db_path=self.temp_db_path)
        self.assertEqual(med_after["dosage"], "20mg")
        self.assertEqual(len(med_after["schedules"]), 1)
        self.assertEqual(med_after["schedules"][0]["specific_time"], "09:00")

        # 4. Delete
        deleted = db.delete_medication(new_id, db_path=self.temp_db_path)
        self.assertTrue(deleted)
        med_deleted = db.get_medication_by_id(new_id, db_path=self.temp_db_path)
        self.assertIsNone(med_deleted)

    def test_03_intake_log_crud_and_adherence(self):
        """Verify adding intake logs and calculating adherence statistics."""
        meds = db.get_all_medications(db_path=self.temp_db_path)
        med_id = meds[0]["id"]
        today_str = "2026-09-10"

        # Record a 'taken' log
        log_id_taken = db.add_intake_log(
            medication_id=med_id,
            scheduled_date=today_str,
            scheduled_time="08:00",
            status="taken",
            notes="아침 식후 제시간 복용 완료",
            db_path=self.temp_db_path
        )
        self.assertIsInstance(log_id_taken, int)

        # Record a 'skipped' log
        log_id_skipped = db.add_intake_log(
            medication_id=med_id,
            scheduled_date=today_str,
            scheduled_time="19:00",
            status="skipped",
            notes="속쓰림으로 건너뜀",
            db_path=self.temp_db_path
        )
        self.assertIsInstance(log_id_skipped, int)

        # Retrieve logs for today
        logs_today = db.get_intake_logs(date=today_str, db_path=self.temp_db_path)
        self.assertGreaterEqual(len(logs_today), 2)
        statuses = [l["status"] for l in logs_today if l["medication_id"] == med_id]
        self.assertIn("taken", statuses)
        self.assertIn("skipped", statuses)

        # Calculate adherence stats
        stats = db.get_adherence_stats(days=7, db_path=self.temp_db_path)
        self.assertIn("adherence_rate", stats)
        self.assertIn("taken_count", stats)
        self.assertIn("skipped_count", stats)
        self.assertGreater(stats["taken_count"], 0)

    def test_04_user_profile_crud(self):
        """Verify getting and updating the user profile."""
        updated_profile = db.update_user_profile(
            name="이영희",
            age=72,
            conditions="고혈압, 관절염",
            senior_mode=1,
            notification_enabled=1,
            db_path=self.temp_db_path
        )
        self.assertEqual(updated_profile["name"], "이영희")
        self.assertEqual(updated_profile["age"], 72)
        self.assertEqual(updated_profile["conditions"], "고혈압, 관절염")


class TestAIPrescriptionParsing(unittest.TestCase):
    """Test suite for Natural Language Processing of Korean prescriptions."""

    def test_01_parse_tylenol_3_times_daily(self):
        """Test: '타이레놀정 500mg 하루 3회 3일분 식후 30분'"""
        text = "타이레놀정 500mg 하루 3회 3일분 식후 30분"
        result = ai_engine.parse_prescription(text)

        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["parsed_count"], 1)

        med = result["medications"][0]
        self.assertIn("타이레놀", med["name"])
        self.assertEqual(med["dosage"], "500mg")
        self.assertEqual(med["frequency"], "1일 3회")
        self.assertEqual(med["meal_timing"], "식후 30분")
        self.assertEqual(med["duration_days"], 3)
        self.assertEqual(len(med["schedules"]), 3)

    def test_02_parse_tylenol_variation(self):
        """Test variation: '타이레놀 500mg 하루 3회 식후 30분 3일분'"""
        text = "타이레놀 500mg 하루 3회 식후 30분 3일분"
        result = ai_engine.parse_prescription(text)

        self.assertTrue(result["success"])
        med = result["medications"][0]
        self.assertIn("타이레놀", med["name"])
        self.assertEqual(med["dosage"], "500mg")
        self.assertEqual(med["frequency"], "1일 3회")
        self.assertEqual(med["meal_timing"], "식후 30분")
        self.assertEqual(med["duration_days"], 3)

    def test_03_parse_norvasc_hypertension(self):
        """Test: '노바스크정 5mg 1일 1회 아침 식후'"""
        text = "노바스크정 5mg 1일 1회 아침 식후"
        result = ai_engine.parse_prescription(text)

        self.assertTrue(result["success"])
        med = result["medications"][0]
        self.assertIn("노바스크", med["name"])
        self.assertEqual(med["dosage"], "5mg")
        self.assertEqual(med["frequency"], "1일 1회")
        self.assertIn("식후", med["meal_timing"])
        self.assertEqual(med["category"], "혈압약")
        # Chronotherapy slot for morning blood pressure meds
        self.assertTrue(any(s["time_slot"] == "아침" for s in med["schedules"]))

    def test_04_parse_norvasc_variation(self):
        """Test variation: '노바스크 5mg 1일 1회 아침 식후'"""
        text = "노바스크 5mg 1일 1회 아침 식후"
        result = ai_engine.parse_prescription(text)

        self.assertTrue(result["success"])
        med = result["medications"][0]
        self.assertIn("노바스크", med["name"])
        self.assertEqual(med["dosage"], "5mg")
        self.assertEqual(med["frequency"], "1일 1회")

    def test_05_parse_metformin_diabetes(self):
        """Test: '메트포르민 500mg 1일 2회 아침 저녁 식사직후'"""
        text = "메트포르민 500mg 1일 2회 아침 저녁 식사직후"
        result = ai_engine.parse_prescription(text)

        self.assertTrue(result["success"])
        med = result["medications"][0]
        self.assertIn("메트포르민", med["name"])
        self.assertEqual(med["dosage"], "500mg")
        self.assertEqual(med["frequency"], "1일 2회")
        self.assertEqual(med["meal_timing"], "식사 직후")
        self.assertEqual(med["category"], "당뇨약")
        self.assertEqual(len(med["schedules"]), 2)

    def test_06_parse_metformin_variation(self):
        """Test variation: '메트포르민 500mg 아침 저녁 식사직후'"""
        text = "메트포르민 500mg 아침 저녁 식사직후"
        result = ai_engine.parse_prescription(text)

        self.assertTrue(result["success"])
        med = result["medications"][0]
        self.assertIn("메트포르민", med["name"])
        self.assertEqual(med["dosage"], "500mg")
        self.assertEqual(med["frequency"], "1일 2회")
        self.assertEqual(med["meal_timing"], "식사 직후")


class TestDURInteractions(unittest.TestCase):
    """Test suite for Korean DUR interaction detection engine."""

    def test_01_duplicate_acetaminophen_tylenol_and_pancall(self):
        """
        Duplicate acetaminophen detection:
        Combining '타이레놀' (Acetaminophen) + '판콜' (Acetaminophen combo).
        Expect: CRITICAL duplicate ingredient warning.
        """
        meds = [
            {"name": "타이레놀정 500mg", "dosage": "500mg", "category": "진통제"},
            {"name": "판콜에이내복액", "dosage": "30ml", "category": "감기약"}
        ]
        dur_result = ai_engine.check_dur(meds)

        self.assertEqual(dur_result["overall_safety"], "CRITICAL")
        self.assertGreater(len(dur_result["duplicate_warnings"]), 0)

        dup = dur_result["duplicate_warnings"][0]
        self.assertEqual(dup["ingredient"], "아세트아미노펜")
        self.assertEqual(dup["severity"], "CRITICAL")
        self.assertIn("타이레놀", dup["involved_drugs"][0] + dup["involved_drugs"][1])
        self.assertIn("판콜", dup["involved_drugs"][0] + dup["involved_drugs"][1])

    def test_02_nsaid_and_aspirin_bleeding_risk(self):
        """
        NSAID + Aspirin combination:
        Combining '애드빌' (Ibuprofen - NSAID) + '아스피린' (Antithrombotic).
        Expect: Major/Critical gastrointestinal bleeding risk warning.
        """
        meds = [
            {"name": "애드빌연질캡슐", "dosage": "200mg", "category": "진통소염제"},
            {"name": "아스피린프로텍트정", "dosage": "100mg", "category": "혈관/항혈전제"}
        ]
        dur_result = ai_engine.check_dur(meds)

        self.assertIn(dur_result["overall_safety"], ["CRITICAL", "MAJOR"])
        self.assertGreater(len(dur_result["interaction_warnings"]), 0)

        # Check that the interaction mentions bleeding risk
        interaction = dur_result["interaction_warnings"][0]
        self.assertTrue(
            "출혈" in interaction["title"] or "출혈" in interaction.get("risk", "") or "출혈" in interaction.get("mechanism", ""),
            "Warning must highlight bleeding risk for NSAID + Aspirin"
        )

    def test_03_food_interaction_amlodipine_and_grapefruit(self):
        """
        Food interaction test:
        Hypertension medication (노바스크 / 암로디핀) with Grapefruit.
        Expect: Critical food warning regarding Grapefruit / Grapefruit juice.
        """
        meds = [
            {"name": "노바스크정", "dosage": "5mg", "category": "혈압약"}
        ]
        dur_result = ai_engine.check_dur(meds)

        self.assertGreater(len(dur_result["food_warnings"]), 0)
        grapefruit_warnings = [
            w for w in dur_result["food_warnings"] if "자몽" in w["food"] or "자몽" in w["title"]
        ]
        self.assertGreater(len(grapefruit_warnings), 0, "Should contain grapefruit interaction warning")

        gw = grapefruit_warnings[0]
        self.assertEqual(gw["severity"], "CRITICAL")
        self.assertIn("노바스크정", gw["involved_drugs"])
        self.assertTrue("저혈압" in gw["consequences"] or "대사" in gw["summary"])


class TestAIPharmacistQA(unittest.TestCase):
    """Test suite for AI Pharmacist consultation logic."""

    def test_01_missed_dose_halfway_rule(self):
        """
        Verify AI Pharmacist response on missed dose inquiry.
        Expect: Missed dose golden rule (1/2 rule) and strict warning against double dosing.
        """
        question = "혈압약을 깜빡하고 안 먹었는데 지금 먹어도 되나요?"
        current_meds = [{"name": "노바스크정", "dosage": "5mg", "category": "혈압약"}]
        profile = {"senior_mode": 1}

        response = ai_engine.ask_pharmacist(question, current_medications=current_meds, user_profile=profile)

        self.assertEqual(response["intent"], "MISSED_DOSE")
        self.assertTrue(response.get("double_dose_warning", False))

        # Check content of the answer
        ans = response["answer"]
        self.assertTrue(
            "반" in ans or "1/2" in ans or "절반" in ans,
            "Answer must mention the halfway (1/2) principle"
        )
        self.assertTrue(
            "두 알" in ans or "2회분" in ans or "몰아서" in ans or "한 번에" in ans,
            "Answer must warn against taking double doses"
        )

    def test_02_alcohol_compatibility_warning(self):
        """Verify AI Pharmacist alcohol incompatibility advice with acetaminophen/metformin."""
        question = "오늘 회식이 있어서 술을 마셔야 하는데 타이레놀이랑 당뇨약 먹어도 되나요?"
        current_meds = [
            {"name": "타이레놀정 500mg", "dosage": "500mg"},
            {"name": "메트포르민정", "dosage": "500mg"}
        ]
        response = ai_engine.ask_pharmacist(question, current_medications=current_meds)

        self.assertEqual(response["intent"], "ALCOHOL_WARNING")
        ans = response["answer"]
        self.assertIn("간", ans)
        self.assertIn("금주", ans)


class QuietHandler(server.MediMindRequestHandler):
    """Subclass of MediMindRequestHandler that suppresses standard HTTP access logs during testing."""
    def log_message(self, format, *args):
        pass


class TestRESTAPIEndpoints(unittest.TestCase):
    """Test suite for REST API endpoints and UTF-8 JSON response handling."""

    server_thread = None
    httpd = None
    port = None
    base_url = None

    @classmethod
    def setUpClass(cls):
        """Find an available port and spin up an HTTPServer in a background thread."""
        # Find ephemeral free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            cls.port = s.getsockname()[1]

        cls.base_url = f"http://127.0.0.1:{cls.port}"
        server_address = ("127.0.0.1", cls.port)

        # Initialize DB
        db.init_db()

        cls.httpd = HTTPServer(server_address, QuietHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Shut down the background test HTTP server."""
        if cls.httpd:
            cls.httpd.shutdown()
            cls.httpd.server_close()

    def _get(self, path: str):
        """Helper to send a GET request and return parsed JSON and headers."""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            data = json.loads(resp.read().decode("utf-8"))
            return status, content_type, data

    def _post(self, path: str, payload: dict):
        """Helper to send a POST request with JSON payload and return parsed JSON."""
        url = f"{self.base_url}{path}"
        encoded_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=encoded_data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            data = json.loads(resp.read().decode("utf-8"))
            return status, content_type, data

    def test_01_get_medications(self):
        """Test GET /api/medications returns 200 and UTF-8 JSON with medication list."""
        status, ctype, data = self._get("/api/medications")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        self.assertIn("charset=utf-8", ctype.lower())
        self.assertTrue(data["success"])
        self.assertIsInstance(data["medications"], list)
        self.assertGreater(len(data["medications"]), 0)

    def test_02_post_ai_parse_prescription(self):
        """Test POST /api/ai/parse-prescription parses Korean sentence accurately."""
        payload = {"text": "노바스크정 5mg 1일 1회 아침 식후"}
        status, ctype, data = self._post("/api/ai/parse-prescription", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["parsed_count"], 1)
        med = data["medications"][0]
        self.assertIn("노바스크", med["name"])
        self.assertEqual(med["dosage"], "5mg")

    def test_03_post_ai_check_interactions(self):
        """Test POST /api/ai/check-interactions returns DUR analysis."""
        payload = {
            "medications": [
                {"name": "타이레놀정 500mg", "dosage": "500mg"},
                {"name": "판콜에이내복액", "dosage": "30ml"}
            ]
        }
        status, ctype, data = self._post("/api/ai/check-interactions", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        dur = data["dur_result"]
        self.assertEqual(dur["overall_safety"], "CRITICAL")
        self.assertGreater(len(dur["duplicate_warnings"]), 0)

    def test_04_post_ai_chat(self):
        """Test POST /api/ai/chat returns AI pharmacist consultation."""
        payload = {
            "question": "혈압약 복용을 깜빡 잊었는데 지금 먹어도 될까요?",
            "medications": [{"name": "노바스크정 5mg"}]
        }
        status, ctype, data = self._post("/api/ai/chat", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["intent"], "MISSED_DOSE")
        self.assertTrue(len(data["answer"]) > 0)

    def test_05_get_report(self):
        """Test GET /api/report returns adherence statistics and score."""
        status, ctype, data = self._get("/api/report?days=7")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("adherence_stats", data)
        self.assertIn("chronotherapy_score", data)
        self.assertIn("ai_clinical_summary", data)

    def test_06_post_intake_log(self):
        """Test POST /api/logs records intake action."""
        payload = {
            "medication_id": 1,
            "scheduled_date": "2026-09-10",
            "scheduled_time": "08:00",
            "status": "taken",
            "notes": "API 테스트 복용 기록"
        }
        status, ctype, data = self._post("/api/logs", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("log_id", data)


def run_tests():
    """Runs the full automated test suite and reports formatted results."""
    print("=" * 70)
    print(" 🧪 MediMind AI Backend & AI Clinical Engine Automated Test Suite")
    print("=" * 70)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestAIPrescriptionParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestDURInteractions))
    suite.addTests(loader.loadTestsFromTestCase(TestAIPharmacistQA))
    suite.addTests(loader.loadTestsFromTestCase(TestRESTAPIEndpoints))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print(f" [PASS] All {result.testsRun} tests passed successfully with 0 errors / 0 failures!")
        print("=" * 70)
        return 0
    else:
        print(f" [FAIL] Tests completed with {len(result.failures)} failures and {len(result.errors)} errors.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
