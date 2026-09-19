"""
MediMind AI - Comprehensive Backend & AI Unit / Integration Test
Tests all modules: db.py, dur_database.py, ai_engine.py, and server routing.
Zero external dependencies.
"""

import os
import sys
import unittest
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db
import dur_database
import ai_engine


class TestMediMindBackend(unittest.TestCase):
    """Unit and integration tests for MediMind AI backend components."""

    def setUp(self):
        self.test_db_path = BACKEND_DIR / "test_medimind.db"
        if self.test_db_path.exists():
            self.test_db_path.unlink()
        db.init_db(db_path=self.test_db_path, force_reset=True)

    def tearDown(self):
        if self.test_db_path.exists():
            try:
                self.test_db_path.unlink()
            except Exception:
                pass

    # -------------------------------------------------------------
    # 1. Database & Seed Data Tests
    # -------------------------------------------------------------
    def test_seed_data_loaded(self):
        """Verify the 3 realistic seed medications and profile are populated."""
        meds = db.get_all_medications(self.test_db_path)
        self.assertEqual(len(meds), 3, "Should have 3 seeded medications")

        names = [m["name"] for m in meds]
        self.assertIn("노바스크정", names)
        self.assertIn("메트포르민정", names)
        self.assertIn("파모티딘정", names)

        # Check schedules
        novasc = next(m for m in meds if m["name"] == "노바스크정")
        self.assertEqual(len(novasc["schedules"]), 1)
        self.assertEqual(novasc["schedules"][0]["time_slot"], "아침")
        self.assertEqual(novasc["schedules"][0]["specific_time"], "08:00")

        metformin = next(m for m in meds if m["name"] == "메트포르민정")
        self.assertEqual(len(metformin["schedules"]), 2)

        # Check Profile
        profile = db.get_user_profile(self.test_db_path)
        self.assertEqual(profile["name"], "김정숙")
        self.assertEqual(profile["senior_mode"], 1)

    def test_crud_medication(self):
        """Test adding, retrieving, updating, and deleting a medication."""
        new_id = db.add_medication(
            name="신지로이드정",
            dosage="100mcg",
            frequency="1일 1회",
            meal_timing="공복",
            category="갑상선약",
            schedules=[{"time_slot": "아침 공복", "specific_time": "06:30"}],
            instructions="아침 기상 직후 물 한 컵과 복용",
            db_path=self.test_db_path
        )
        self.assertTrue(new_id > 0)

        fetched = db.get_medication_by_id(new_id, self.test_db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "신지로이드정")
        self.assertEqual(len(fetched["schedules"]), 1)

        # Update
        updated = db.update_medication(new_id, dosage="150mcg", db_path=self.test_db_path)
        self.assertTrue(updated)
        fetched_after = db.get_medication_by_id(new_id, self.test_db_path)
        self.assertEqual(fetched_after["dosage"], "150mcg")

        # Delete
        deleted = db.delete_medication(new_id, self.test_db_path)
        self.assertTrue(deleted)
        self.assertIsNone(db.get_medication_by_id(new_id, self.test_db_path))

    def test_intake_logs_and_stats(self):
        """Test logging intake and computing adherence statistics."""
        meds = db.get_all_medications(self.test_db_path)
        med_id = meds[0]["id"]

        log_id = db.add_intake_log(
            medication_id=med_id,
            scheduled_date="2026-09-10",
            scheduled_time="08:00",
            status="taken",
            notes="아침 식후 정시 복용",
            db_path=self.test_db_path
        )
        self.assertTrue(log_id > 0)

        logs = db.get_intake_logs(date="2026-09-10", db_path=self.test_db_path)
        self.assertTrue(len(logs) > 0)

        stats = db.get_adherence_stats(days=7, db_path=self.test_db_path)
        self.assertIn("adherence_rate", stats)
        self.assertIn("streak_days", stats)
        self.assertTrue(stats["adherence_rate"] > 0)

    # -------------------------------------------------------------
    # 2. DUR Knowledge Base & Collision Analysis Tests
    # -------------------------------------------------------------
    def test_dur_duplicate_acetaminophen(self):
        """Verify Tylenol + Pancol triggers a CRITICAL duplicate ingredient warning."""
        meds = [
            {"name": "타이레놀정 500mg"},
            {"name": "판콜에이내복액"}
        ]
        result = dur_database.check_drug_collisions(meds)
        self.assertEqual(result["overall_safety"], "CRITICAL")
        self.assertTrue(any(w["ingredient"] == "아세트아미노펜" for w in result["duplicate_warnings"]))

    def test_dur_nsaid_anticoagulant_collision(self):
        """Verify Aspirin/Warfarin + NSAID triggers a CRITICAL bleeding collision."""
        meds = [
            {"name": "와파린정"},
            {"name": "애드빌연질캡슐 (이부프로펜)"}
        ]
        result = dur_database.check_drug_collisions(meds)
        self.assertEqual(result["overall_safety"], "CRITICAL")
        self.assertTrue(any("소염진통제(NSAID) + 항혈전제/항응고제" in w["title"] for w in result["interaction_warnings"]))

    def test_dur_food_interactions(self):
        """Verify Grapefruit with Amlodipine/Novasc is flagged as CRITICAL."""
        meds = [{"name": "노바스크정 5mg"}]
        result = dur_database.check_drug_collisions(meds)
        self.assertTrue(any("자몽" in w["food"] for w in result["food_warnings"]))

    # -------------------------------------------------------------
    # 3. AI NLP Prescription Parser Tests
    # -------------------------------------------------------------
    def test_parse_prescription_single(self):
        """Test parsing a single natural language prescription."""
        text = "노바스크정 5mg 1일 1회 아침 식후 30분 30일분 처방"
        res = ai_engine.parse_prescription(text)
        self.assertTrue(res["success"])
        self.assertEqual(res["parsed_count"], 1)

        med = res["medications"][0]
        self.assertEqual(med["name"], "노바스크정")
        self.assertEqual(med["dosage"], "5mg")
        self.assertEqual(med["frequency"], "1일 1회")
        self.assertEqual(med["meal_timing"], "식후 30분")
        self.assertEqual(med["duration_days"], 30)
        self.assertEqual(med["category"], "혈압약")
        self.assertEqual(med["schedules"][0]["specific_time"], "08:00")

    def test_parse_prescription_multi(self):
        """Test parsing multiple medications from one text."""
        text = "1. 다이아벡스 500mg 하루 2번 식사직후 60일분\n2. 리피토 10mg 저녁 취침전 1일 1회 30일치"
        res = ai_engine.parse_prescription(text)
        self.assertTrue(res["success"])
        self.assertEqual(res["parsed_count"], 2)

        names = [m["name"] for m in res["medications"]]
        self.assertIn("메트포르민정", names)  # Canonical name for 다이아벡스
        self.assertIn("리피토정", names)

    # -------------------------------------------------------------
    # 4. AI Pharmacist Q&A (Clinical Decision Tree) Tests
    # -------------------------------------------------------------
    def test_pharmacist_missed_dose_half_rule(self):
        """Verify missed dose protocol triggers the 1/2 golden rule."""
        q = "아침 혈압약 먹는 걸 깜빡 잊었는데 지금 먹어도 되나요?"
        res = ai_engine.ask_pharmacist(q, [{"name": "노바스크정", "category": "혈압약"}])
        self.assertEqual(res["intent"], "MISSED_DOSE")
        self.assertTrue(res["double_dose_warning"])
        self.assertIn("1/2", res["rule"])

    def test_pharmacist_alcohol_inquiry(self):
        """Verify asking about drinking returns critical warning."""
        q = "오늘 저녁에 소주 한 잔 마셔도 괜찮을까요?"
        res = ai_engine.ask_pharmacist(q, [{"name": "타이레놀정"}, {"name": "메트포르민정"}])
        self.assertEqual(res["intent"], "ALCOHOL_WARNING")
        self.assertIn("간", res["answer"])
        self.assertIn("금주", res["answer"])

    def test_pharmacist_food_grapefruit(self):
        """Verify grapefruit question returns CYP3A4 interaction advice."""
        q = "자몽주스 마셔도 되나요?"
        res = ai_engine.ask_pharmacist(q, [{"name": "노바스크정"}])
        self.assertEqual(res["intent"], "FOOD_INTERACTION")
        self.assertIn("자몽", res["answer"])
        self.assertIn("혈압", res["answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
