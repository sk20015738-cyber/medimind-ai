"""
MediMind AI - Clinical AI Engine (ai_engine.py)
Prescription NLP parsing, DUR safety collision analysis, and AI Pharmacist Q&A.
Zero external dependencies.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime

try:
    from .dur_database import (
        DRUG_DATABASE,
        CHRONOTHERAPY_RULES,
        resolve_drug_info,
        check_drug_collisions,
        normalize_text
    )
except (ImportError, ValueError):
    from dur_database import (
        DRUG_DATABASE,
        CHRONOTHERAPY_RULES,
        resolve_drug_info,
        check_drug_collisions,
        normalize_text
    )


# =====================================================================
# 1. PRESCRIPTION NLP PARSER
# =====================================================================

def parse_prescription(text: str) -> Dict[str, Any]:
    """
    Parses natural language prescription sentences, OCR text, or doctor memos into
    structured medication objects with dosages, frequencies, meal timings, and chronotherapy advice.
    """
    if not text or not text.strip():
        return {
            "success": False,
            "error": "분석할 처방전 내용이 비어 있습니다.",
            "parsed_count": 0,
            "medications": []
        }

    # Split text into logical segments (by lines, commas, semicolons, or sentence terminators)
    raw_lines = re.split(r"[\n\r;]+", text.strip())
    segments = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # If line contains multiple distinct medications separated by commas or '그리고'
        sub_parts = re.split(r",|\s*그리고\s*", line)
        for part in sub_parts:
            part = part.strip()
            if len(part) >= 2:
                segments.append(part)

    parsed_meds = []
    seen_keys = set()

    for seg in segments:
        med_item = _extract_medication_from_segment(seg)
        if med_item and med_item["name"] not in seen_keys:
            seen_keys.add(med_item["name"])
            parsed_meds.append(med_item)

    # If segment splitting missed a multi-drug text (e.g. single long sentence)
    if not parsed_meds:
        # Try full text search across DRUG_DATABASE
        for key, data in DRUG_DATABASE.items():
            for name_variant in [key] + data.get("brand_synonyms", []):
                if name_variant in text and name_variant not in seen_keys:
                    item = _build_med_item(name_variant, text)
                    seen_keys.add(item["name"])
                    parsed_meds.append(item)
                    break

    return {
        "success": len(parsed_meds) > 0,
        "parsed_count": len(parsed_meds),
        "raw_text": text,
        "medications": parsed_meds
    }


def _extract_medication_from_segment(segment: str) -> Optional[Dict[str, Any]]:
    """Extracts medication attributes from a single segment/line."""
    matched_drug = None
    matched_info = None

    # 1. Search knowledge base
    for key, data in DRUG_DATABASE.items():
        if key in segment:
            matched_drug = data["canonical_name"]
            matched_info = data
            break
        for syn in data.get("brand_synonyms", []):
            if syn in segment:
                matched_drug = data["canonical_name"]
                matched_info = data
                break
        if matched_drug:
            break

    # 2. Regex fallback for unknown drug names (e.g., '가나다정 10mg')
    if not matched_drug:
        name_match = re.search(r"([가-힣a-zA-Z0-9]+(?:정|캡슐|시럽|서방정|엑스|연질캡슐|액))", segment)
        if name_match:
            matched_drug = name_match.group(1)
            matched_info = resolve_drug_info(matched_drug)

    if not matched_drug:
        return None

    return _build_med_item(matched_drug, segment, matched_info)


def _build_med_item(
    drug_name: str,
    context: str,
    info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Extracts dosage, frequency, meal timing, and constructs schedules."""
    if not info:
        info = resolve_drug_info(drug_name)

    category = info.get("category", "일반약") if info else "일반약"
    default_dosage = info.get("default_dosage", "1정") if info else "1정"

    # Dosage extraction
    dosage_match = re.search(r"(\d+(?:\.\d+)?\s*(?:mg|g|mcg|μg|정|캡슐|ml|포|iu|IU))", context, re.IGNORECASE)
    dosage = dosage_match.group(1).strip() if dosage_match else default_dosage

    # Frequency extraction
    freq_match = re.search(r"(?:(?:1일|하루|매일)\s*(\d+)\s*(?:회|번)|(\d+)\s*회/일)", context)
    if freq_match:
        count = next(g for g in freq_match.groups() if g)
        frequency = f"1일 {count}회"
        freq_count = int(count)
    elif "하루 세번" in context or "하루 3번" in context or "아침 점심 저녁" in context or "아침, 점심, 저녁" in context:
        frequency = "1일 3회"
        freq_count = 3
    elif "하루 두번" in context or "하루 2번" in context or "아침 저녁" in context or "아침, 저녁" in context:
        frequency = "1일 2회"
        freq_count = 2
    elif "하루 한번" in context or "하루 1번" in context or "1일 1회" in context or "1회" in context or "매일" in context:
        frequency = "1일 1회"
        freq_count = 1
    elif "취침전" in context or "자기전" in context:
        frequency = "1일 1회"
        freq_count = 1
    elif "필요시" in context:
        frequency = "필요시"
        freq_count = 1
    else:
        # Default by category / chronotherapy
        if category in ["고지혈증약", "혈압약", "갑상선약"]:
            frequency = "1일 1회"
            freq_count = 1
        elif category in ["당뇨약"]:
            frequency = "1일 2회"
            freq_count = 2
        elif category in ["감기약"]:
            frequency = "1일 3회"
            freq_count = 3
        else:
            frequency = "1일 1회"
            freq_count = 1

    # Meal Timing extraction
    if any(k in context for k in ["식후 30분", "식후30분", "30분후", "30분 뒤"]):
        meal_timing = "식후 30분"
    elif any(k in context for k in ["식사 직후", "식사직후", "식후 즉시", "식후즉시", "식후바로", "식후 바로"]):
        meal_timing = "식사 직후"
    elif any(k in context for k in ["식전 30분", "식전30분", "30분전"]):
        meal_timing = "식전 30분"
    elif any(k in context for k in ["공복", "기상 직후", "기상직후"]):
        meal_timing = "공복 (기상 직후)"
    elif any(k in context for k in ["취침전", "취침 전", "자기전", "자기 전"]):
        meal_timing = "취침 전"
    elif "식간" in context:
        meal_timing = "식간 (공복)"
    elif any(k in context for k in ["식후", "식사 후"]):
        meal_timing = "식후 30분"
    elif any(k in context for k in ["식전", "식사 전"]):
        meal_timing = "식전 30분"
    else:
        # Fallback to chronotherapy default
        chrono = info.get("chronotherapy", {}) if info else {}
        meal_timing = chrono.get("meal_timing", "식후 30분")

    # Duration extraction (e.g. 30일분, 7일치)
    dur_match = re.search(r"(\d+)\s*(?:일분|일치|일간|일동안)", context)
    duration_days = int(dur_match.group(1)) if dur_match else 30

    # Build Schedules according to Chronotherapy
    schedules = _generate_schedules(category, freq_count, context, info)

    # Chronotherapy Advice & Cautions
    chrono_advice = ""
    caution = info.get("caution", "") if info else ""
    if info and info.get("chronotherapy"):
        chrono_advice = info["chronotherapy"].get("reason", "")
    elif category in CHRONOTHERAPY_RULES:
        chrono_advice = CHRONOTHERAPY_RULES[category]["clinical_rationale"]

    return {
        "name": drug_name,
        "dosage": dosage,
        "frequency": frequency,
        "meal_timing": meal_timing,
        "duration_days": duration_days,
        "category": category,
        "schedules": schedules,
        "chronotherapy_advice": chrono_advice,
        "caution": caution,
        "instructions": f"{meal_timing} 복용. {caution}".strip()
    }


def _generate_schedules(
    category: str,
    freq_count: int,
    context: str,
    info: Optional[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """Synthesizes optimal clock times based on chronobiology and frequency."""
    schedules = []

    # If context explicitly mentions slots
    has_morning = "아침" in context
    has_lunch = "점심" in context
    has_dinner = "저녁" in context
    has_bedtime = "취침" in context or "자기전" in context

    if category == "고지혈증약" or has_bedtime:
        schedules.append({"time_slot": "저녁/취침전", "specific_time": "21:00"})
    elif category == "갑상선약":
        schedules.append({"time_slot": "아침 공복", "specific_time": "06:30"})
    elif freq_count == 1:
        if has_dinner:
            schedules.append({"time_slot": "저녁", "specific_time": "19:00"})
        else:
            schedules.append({"time_slot": "아침", "specific_time": "08:00"})
    elif freq_count == 2:
        schedules.append({"time_slot": "아침", "specific_time": "08:30"})
        schedules.append({"time_slot": "저녁", "specific_time": "19:00"})
    elif freq_count >= 3:
        schedules.append({"time_slot": "아침", "specific_time": "08:00"})
        schedules.append({"time_slot": "점심", "specific_time": "12:30"})
        schedules.append({"time_slot": "저녁", "specific_time": "19:00"})
    else:
        schedules.append({"time_slot": "아침", "specific_time": "08:00"})

    return schedules


# =====================================================================
# 2. DUR INTERACTION CHECKER
# =====================================================================

def check_dur(medications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes medication list for safety, duplicate ingredients, and collisions.
    Generates senior-friendly clinical summary message.
    """
    result = check_drug_collisions(medications)

    # Generate Korean AI Pharmacist Clinical Summary
    safety = result["overall_safety"]
    dup_count = len(result["duplicate_warnings"])
    inter_count = len(result["interaction_warnings"])
    food_count = len(result["food_warnings"])

    lines = []
    if safety == "CRITICAL":
        lines.append("🚨 [긴급 복용 경고] 심각한 약물 상호작용 또는 위험한 성분 중복이 발견되었습니다.")
        if dup_count > 0:
            lines.append(f"• 성분 중복: {result['duplicate_warnings'][0]['title']}")
        if inter_count > 0:
            lines.append(f"• 병용 위험: {result['interaction_warnings'][0]['title']}")
        lines.append("💡 복용하기 전 반드시 주치의 또는 약사와 상의하여 약을 조절하셔야 합니다.")
    elif safety == "MAJOR":
        lines.append("⚠️ [복용 주의] 주의가 필요한 약물 조합이 있습니다.")
        if inter_count > 0:
            lines.append(f"• {result['interaction_warnings'][0]['title']}")
        lines.append("💡 부작용 예방을 위해 복용 시간대를 분리하거나 의사와 상담하시기 바랍니다.")
    elif safety == "MODERATE":
        lines.append("ℹ️ [복용 안내] 안전한 약효 흡수를 위해 복용 시간 간격을 두어야 하는 약물이 있습니다.")
        if food_count > 0:
            lines.append(f"• {result['food_warnings'][0]['title']}")
        lines.append("💡 우유, 제산제, 특정 음식과의 시간차(2시간 이상)를 지켜주세요.")
    else:
        lines.append("✅ [복약 안전 확인] 현재 복용 중인 약물 간 위험한 상호작용이 발견되지 않았습니다.")
        lines.append("정해진 시간에 식후 물 한 컵과 함께 규칙적으로 복용하세요.")

    result["ai_summary"] = "\n".join(lines)
    return result


# =====================================================================
# 3. AI PHARMACIST CLINICAL Q&A (DECISION TREE)
# =====================================================================

def ask_pharmacist(
    question: str,
    current_medications: Optional[List[Dict[str, Any]]] = None,
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    AI Pharmacist Q&A logic implementing:
    1. Missed Dose Protocol (1/2 Golden Rule)
    2. Alcohol & Beverage Compatibility
    3. Food & Grapefruit / Milk Interactions
    4. Side Effects & Red Flags
    5. Chronotherapy & Meal Timing
    """
    q = question.strip()
    is_senior = True
    if user_profile and "senior_mode" in user_profile:
        is_senior = bool(user_profile["senior_mode"])

    med_names = [m.get("name", "") for m in (current_medications or [])]
    med_text = ", ".join(med_names) if med_names else "현재 등록된 약물"

    # -------------------------------------------------------------
    # Intent 1: Missed Dose Protocol (1/2 Golden Rule)
    # -------------------------------------------------------------
    if any(k in q for k in ["깜빡", "놓쳤", "잊었", "못 먹었", "지금 먹어도", "시간 지났", "안 먹었", "놓치면"]):
        return _handle_missed_dose(q, current_medications, is_senior)

    # -------------------------------------------------------------
    # Intent 2: Alcohol & Drinking
    # -------------------------------------------------------------
    if any(k in q for k in ["술", "맥주", "소주", "회식", "알코올", "와인", "음주"]):
        return _handle_alcohol_inquiry(current_medications, is_senior)

    # -------------------------------------------------------------
    # Intent 3: Food Interactions (Grapefruit, Milk, Coffee)
    # -------------------------------------------------------------
    if any(k in q for k in ["자몽", "우유", "커피", "치즈", "바나나", "음식", "주스", "식사"]):
        return _handle_food_inquiry(q, current_medications, is_senior)

    # -------------------------------------------------------------
    # Intent 4: Side Effects & Precautions
    # -------------------------------------------------------------
    if any(k in q for k in ["부작용", "어지러", "속쓰", "위통", "근육통", "메스꺼", "구토", "설사", "발진", "기침", "졸려", "졸림"]):
        return _handle_side_effects_inquiry(q, current_medications, is_senior)

    # -------------------------------------------------------------
    # Intent 5: Chronotherapy & How to take
    # -------------------------------------------------------------
    if any(k in q for k in ["언제 먹", "식전", "식후", "공복", "시간", "어떻게 먹", "먹는 법", "방법"]):
        return _handle_chronotherapy_inquiry(current_medications, is_senior)

    # -------------------------------------------------------------
    # Fallback / General Health Advice
    # -------------------------------------------------------------
    return _handle_general_inquiry(q, current_medications, is_senior)


# ---------------------------------------------------------------------
# Internal Handler Functions for Pharmacist Q&A
# ---------------------------------------------------------------------

def _handle_missed_dose(
    question: str,
    medications: Optional[List[Dict[str, Any]]],
    is_senior: bool
) -> Dict[str, Any]:
    """Applies the clinical 1/2 Golden Rule for missed doses."""
    rule_explanation = (
        "💡 약을 깜빡했을 때는 **'복용 간격의 1/2 원칙'**을 따릅니다.\n\n"
        "1. **1일 1회 복용약 (24시간 주기 - 혈압약, 고지혈증약 등)**:\n"
        "   - 기준 시점: **12시간**\n"
        "   - 복용 시간으로부터 12시간 이내라면: **지금 즉시 1회분을 복용하세요.**\n"
        "   - 12시간이 이미 지났다면: **이번 약은 건너뛰고 다음 정규 시간에 복용하세요.**\n\n"
        "2. **1일 2회 복용약 (12시간 주기 - 당뇨약 등)**:\n"
        "   - 기준 시점: **6시간**\n"
        "   - 복용 시간으로부터 6시간 이내라면: **지금 즉시 복용하세요.**\n"
        "   - 6시간이 지났다면: **이번 복용은 건너뛰세요.**\n\n"
        "🚨 **가장 중요한 주의사항:**\n"
        "절대로 놓친 약을 벌충하기 위해 **한 번에 2회분(두 알)을 몰아서 드시면 안 됩니다!** 혈압 급강하나 저혈당 쇼크 등 치명적인 부작용이 생길 수 있습니다."
    )

    senior_summary = (
        "어르신, 걱정 마세요! 약을 잊으셨을 때는 이렇게 하세요:\n\n"
        "1. 원래 드시던 시간에서 **반나절(반)이 아직 안 지났다면** 지금 바로 드세요.\n"
        "2. 다음 약 먹을 시간이 거의 다 되었다면 이번 약은 과감히 **건너뛰세요**.\n"
        "3. **절대 한 번에 두 알을 몰아서 드시면 안 됩니다!**\n\n"
        "궁금하신 약 이름과 시간을 말씀해주시면 정확히 계산해 드릴게요."
    )

    return {
        "intent": "MISSED_DOSE",
        "title": "약 복용을 깜빡하셨을 때의 대처법 (1/2 황금 원칙)",
        "answer": senior_summary if is_senior else rule_explanation,
        "rule": "1/2 Golden Rule (절반 기준법)",
        "double_dose_warning": True
    }


def _handle_alcohol_inquiry(
    medications: Optional[List[Dict[str, Any]]],
    is_senior: bool
) -> Dict[str, Any]:
    """Clinical advice regarding alcohol and current medications."""
    has_tylenol = False
    has_metformin = False
    has_nsaid = False
    has_bp = False

    if medications:
        for m in medications:
            name = m.get("name", "")
            info = resolve_drug_info(name)
            if info:
                clss = info["classes"]
                ings = info["ingredients"]
                if "아세트아미노펜" in ings:
                    has_tylenol = True
                if "비구아나이드계(당뇨)" in clss or "메트포르민" in ings:
                    has_metformin = True
                if "NSAID" in clss:
                    has_nsaid = True
                if "칼슘채널차단제(CCB)" in clss or "혈압약" in clss:
                    has_bp = True

    specific_warnings = []
    if has_tylenol:
        specific_warnings.append("• **타이레놀/감기약 (아세트아미노펜)**: 알코올 분해 물질과 결합하여 **급성 간부전(간세포 괴사)**을 일으킬 수 있어 절대 금주해야 합니다.")
    if has_metformin:
        specific_warnings.append("• **당뇨약 (메트포르민)**: 음주 시 치명적인 **젖산산증(Lactic Acidosis)**과 저혈당 위험이 급증합니다.")
    if has_nsaid:
        specific_warnings.append("• **소염진통제 (이부프로펜/탁센 등)**: 알코올이 위점막을 손상시켜 **위장관 출혈 및 위궤양** 위험이 커집니다.")
    if has_bp:
        specific_warnings.append("• **혈압약**: 혈관이 과도하게 확장되어 기립성 저혈압(어지러움, 실신)이 발생할 수 있습니다.")

    ans = (
        "🚫 **약물 복용 중 음주는 원칙적으로 금지됩니다.**\n\n"
        + ("\n".join(specific_warnings) if specific_warnings else "대부분의 약물은 간에서 대사되므로 술과 함께 섭취 시 간 손상과 부작용 위험이 매우 높아집니다.\n")
        + "\n\n💡 특히 '술 마신 다음 날 숙취 두통 때문에 타이레놀을 먹는 것'은 간에 치명타를 주므로 절대 금물입니다!"
    )

    return {
        "intent": "ALCOHOL_WARNING",
        "title": "약 복용 중 음주 관련 안내",
        "answer": ans,
        "severity": "CRITICAL"
    }


def _handle_food_inquiry(
    question: str,
    medications: Optional[List[Dict[str, Any]]],
    is_senior: bool
) -> Dict[str, Any]:
    """Advises on grapefruit, dairy, and other food interactions."""
    answers = []

    if "자몽" in question:
        answers.append(
            "🍊 **자몽 및 자몽주스:**\n"
            "- 자몽 속 성분이 혈압약(노바스크 등)과 고지혈증약(리피토 등)의 간 분해를 막아 혈중 농도를 수 배 높입니다.\n"
            "- 급격한 저혈압, 어지럼증, 근육통(횡문근융해증)을 유발하므로 **약 복용 중에는 자몽을 드시지 마세요** (오렌지나 귤은 괜찮습니다)."
        )

    if "우유" in question or "치즈" in question or "유제품" in question:
        answers.append(
            "🥛 **우유 및 유제품:**\n"
            "- 우유의 칼슘 성분이 퀴놀론계 항생제, 철분제와 결합하여 흡수를 방해합니다.\n"
            "- 약 복용 전후 **최소 2시간 이상의 시간 간격**을 두고 드셔야 약효가 제대로 나타납니다."
        )

    if "커피" in question or "카페인" in question:
        answers.append(
            "☕ **커피 및 카페인 음료:**\n"
            "- 판콜, 판피린 등 종합감기약이나 게보린 같은 진통제에는 이미 카페인이 포함되어 있습니다.\n"
            "- 커피와 함께 드시면 가슴 두근거림, 불안, 불면증, 위산 과다가 심해질 수 있으니 따뜻한 물로 복용하세요."
        )

    if not answers:
        answers.append(
            "음식물 상호작용 안내:\n"
            "- **자몽주스**: 혈압약/고지혈증약과 병용 금지\n"
            "- **우유/유제품**: 항생제 및 철분제 복용 2시간 전후 피하기\n"
            "- **술/알코올**: 진통제, 당뇨약 복용 시 절대 금주\n"
            "- 약은 항상 **미온수(따뜻한 물 한 컵)**와 함께 복용하는 것이 가장 안전합니다."
        )

    return {
        "intent": "FOOD_INTERACTION",
        "title": "음식 및 음료 상호작용 안내",
        "answer": "\n\n".join(answers)
    }


def _handle_side_effects_inquiry(
    question: str,
    medications: Optional[List[Dict[str, Any]]],
    is_senior: bool
) -> Dict[str, Any]:
    """Analyzes reported symptoms against active medications."""
    symptom_responses = []

    if "어지러" in question or "현기증" in question:
        symptom_responses.append(
            "🌀 **어지럼증 증상:**\n"
            "- 혈압약 복용 초기나 용량 조절 시 일시적인 기립성 저혈압으로 어지러울 수 있습니다.\n"
            "- 앉아 있거나 누워 있다가 일어날 때는 30초 정도 천천히 일어나세요. 증상이 계속되면 혈압을 측정하고 의사와 상담하세요."
        )

    if "속쓰" in question or "위통" in question or "속이 쓰" in question:
        symptom_responses.append(
            "🔥 **속쓰림 및 소화기 증상:**\n"
            "- 소염진통제(NSAID)나 당뇨약(메트포르민)은 위점막을 자극할 수 있습니다.\n"
            "- 빈속에 드시지 마시고 **식사 직후 또는 식후 30분에 충분한 미온수**와 함께 복용하세요. 증상이 심하면 위보호제 처방을 요청하세요."
        )

    if "근육통" in question or "다리" in question:
        symptom_responses.append(
            "💪 **근육통 및 무력감:**\n"
            "- 고지혈증약(스타틴 계열: 리피토, 크레스토 등) 복용 시 드물게 근육통이나 피로감이 나타날 수 있습니다.\n"
            "- 소변 색이 짙은 갈색(콜라색)으로 변하거나 심한 근육통이 지속되면 복용을 멈추고 즉시 병원을 방문하세요."
        )

    if not symptom_responses:
        symptom_responses.append(
            "약 복용 중 불편한 증상이 있으신가요?\n"
            "- 복용 초기 일시적 증상일 수 있으나, 호흡 곤란, 전신 두드러기, 극심한 어지럼증, 흑색변(검은 변) 등은 즉시 진료가 필요한 위험 신호입니다."
        )

    return {
        "intent": "SIDE_EFFECTS",
        "title": "약물 이상반응 및 부작용 안내",
        "answer": "\n\n".join(symptom_responses)
    }


def _handle_chronotherapy_inquiry(
    medications: Optional[List[Dict[str, Any]]],
    is_senior: bool
) -> Dict[str, Any]:
    """Provides chronotherapy schedule guidance."""
    if not medications:
        return {
            "intent": "CHRONOTHERAPY",
            "title": "시간생물학적 복약 지도",
            "answer": "현재 등록된 약물이 없습니다. 약을 등록하시면 최적의 복용 시간과 식전/식후 방법을 안내해 드립니다."
        }

    lines = ["📋 **현재 복용 중인 약물의 최적 복용법 안내:**\n"]
    for m in medications:
        name = m.get("name", "")
        info = resolve_drug_info(name)
        category = m.get("category", "")
        timing = m.get("meal_timing", "식후 30분")
        schedules = m.get("schedules", [])
        time_str = ", ".join([f"{s.get('time_slot', '')} {s.get('specific_time', '')}" for s in schedules])

        reason = ""
        if info and info.get("chronotherapy"):
            reason = info["chronotherapy"].get("reason", "")
        elif category in CHRONOTHERAPY_RULES:
            reason = CHRONOTHERAPY_RULES[category]["clinical_rationale"]

        lines.append(f"• **{name}** ({category}):")
        lines.append(f"  - 권장 시간: {time_str} ({timing})")
        if reason:
            lines.append(f"  - 이유: {reason}")

    return {
        "intent": "CHRONOTHERAPY",
        "title": "시간생물학적 복약 지도",
        "answer": "\n".join(lines)
    }


def _handle_general_inquiry(
    question: str,
    medications: Optional[List[Dict[str, Any]]],
    is_senior: bool
) -> Dict[str, Any]:
    """Fallback helpful consultation response."""
    return {
        "intent": "GENERAL_CONSULT",
        "title": "메디마인드 AI 약사 상담",
        "answer": (
            f"질문해주신 내용: '{question}'\n\n"
            "올바른 약 복용을 위한 3대 원칙:\n"
            "1. **규칙적인 시간 준수**: 약효가 일정하게 유지되도록 매일 정해진 시각에 드세요.\n"
            "2. **충분한 물과 함께**: 알약이 식도에 달라붙지 않도록 미온수 한 컵(200ml)과 함께 삼키세요.\n"
            "3. **임의 중단 금지**: 증상이 호전되었더라도 처방된 일수를 지켜 복용하시고, 중단 전 의사/약사와 상의하세요."
        )
    }
