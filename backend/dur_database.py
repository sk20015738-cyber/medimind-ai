"""
MediMind AI - DUR (Drug Utilization Review) Knowledge Base (dur_database.py)
Clinical knowledge base of Korean medications, brand names, active ingredients,
drug-drug collisions, duplicate ingredient alerts, food-drug interactions, and chronotherapy rules.
Zero external dependencies.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import re

# =====================================================================
# 1. BRAND NAME TO ACTIVE INGREDIENTS & METADATA MAPPING
# =====================================================================

DRUG_DATABASE: Dict[str, Dict[str, Any]] = {
    # -------------------- 혈압약 (Antihypertensives) --------------------
    "노바스크": {
        "canonical_name": "노바스크정",
        "brand_synonyms": ["노바스크", "노바스크정", "암로디핀", "아모디핀", "애니디핀", "바로디핀", "바소트롤"],
        "ingredients": ["암로디핀"],
        "classes": ["칼슘채널차단제(CCB)", "혈압약"],
        "default_dosage": "5mg",
        "category": "혈압약",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "08:00",
            "meal_timing": "식후 30분",
            "reason": "기상 직후 아침 혈압 급상승(Morning Surge)을 완화하여 심혈관 사고를 예방합니다."
        },
        "caution": "자몽 및 자몽주스와 함께 드시면 혈압이 급격히 떨어질 수 있습니다."
    },
    "코자": {
        "canonical_name": "코자정",
        "brand_synonyms": ["코자", "코자정", "로사르탄", "살로탄", "로자살탄"],
        "ingredients": ["로사르탄"],
        "classes": ["ARB/ACEI", "혈압약"],
        "default_dosage": "50mg",
        "category": "혈압약",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "08:00",
            "meal_timing": "식후 30분",
            "reason": "안지오텐신 수용체를 차단하여 24시간 안정적으로 혈압을 조절합니다."
        },
        "caution": "칼륨 보충제나 고칼륨 식품(바나나, 시금치) 과다 섭취 시 고칼륨혈증 주의."
    },
    "디오반": {
        "canonical_name": "디오반정",
        "brand_synonyms": ["디오반", "디오반정", "발사르탄", "발사르텐"],
        "ingredients": ["발사르탄"],
        "classes": ["ARB/ACEI", "혈압약"],
        "default_dosage": "80mg",
        "category": "혈압약",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "08:00",
            "meal_timing": "식후 30분",
            "reason": "주간 혈압 변동성을 낮추어 심장 및 신장을 보호합니다."
        },
        "caution": "임의의 칼륨 영양제 섭취를 피하세요."
    },

    # -------------------- 고지혈증약 (Lipid-lowering / Statins) --------------------
    "리피토": {
        "canonical_name": "리피토정",
        "brand_synonyms": ["리피토", "리피토정", "아토르바스타틴", "아토르바", "리피논", "아토젯"],
        "ingredients": ["아토르바스타틴"],
        "classes": ["스타틴(고지혈증)", "고지혈증약"],
        "default_dosage": "10mg",
        "category": "고지혈증약",
        "chronotherapy": {
            "optimal_slot": "저녁",
            "optimal_time": "21:00",
            "meal_timing": "식후 30분",
            "reason": "간에서 콜레스테롤을 합성하는 HMG-CoA 효소는 야간 수면 중 가장 활발하므로 저녁 복용 시 효과가 극대화됩니다."
        },
        "caution": "자몽주스는 간 대사를 방해하여 근육통(횡문근융해증) 위험을 높이므로 금지."
    },
    "크레스토": {
        "canonical_name": "크레스토정",
        "brand_synonyms": ["크레스토", "크레스토정", "로수바스타틴", "로수젯", "비바코"],
        "ingredients": ["로수바스타틴"],
        "classes": ["스타틴(고지혈증)", "고지혈증약"],
        "default_dosage": "10mg",
        "category": "고지혈증약",
        "chronotherapy": {
            "optimal_slot": "저녁",
            "optimal_time": "21:00",
            "meal_timing": "식후 30분",
            "reason": "야간 간 콜레스테롤 합성 피크 타임에 맞춰 강력한 LDL 강하 효과를 발휘합니다."
        },
        "caution": "근육통, 전신 피로감 발생 시 즉시 의사와 상담하세요."
    },

    # -------------------- 당뇨약 (Antidiabetics) --------------------
    "메트포르민": {
        "canonical_name": "메트포르민정",
        "brand_synonyms": ["메트포르민", "메트포르민정", "다이아벡스", "다이아벡스정", "글루코파지", "글루코파지정"],
        "ingredients": ["메트포르민"],
        "classes": ["비구아나이드계(당뇨)", "당뇨약"],
        "default_dosage": "500mg",
        "category": "당뇨약",
        "chronotherapy": {
            "optimal_slot": "아침, 저녁",
            "optimal_time": "08:30",
            "meal_timing": "식사 직후",
            "reason": "속쓰림, 메스꺼움, 소화불량 등 위장 자극을 줄이기 위해 식사 도중이나 식사 직후 복용합니다."
        },
        "caution": "알코올과 함께 복용 시 치명적인 젖산산증 위험이 있으므로 절대 금주하세요."
    },
    "아마릴": {
        "canonical_name": "아마릴정",
        "brand_synonyms": ["아마릴", "아마릴정", "글리메피리드", "디아릴"],
        "ingredients": ["글리메피리드"],
        "classes": ["설포닐우레아(당뇨)", "당뇨약"],
        "default_dosage": "2mg",
        "category": "당뇨약",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "07:30",
            "meal_timing": "식전 30분",
            "reason": "식사 후 급격히 치솟는 식후 혈당 스파이크에 맞춰 인슐린 분비를 자극합니다."
        },
        "caution": "식사를 거르면 저혈당 쇼크(식은땀, 떨림, 어지럼)가 올 수 있으니 반드시 식사를 하세요."
    },
    "자누비아": {
        "canonical_name": "자누비아정",
        "brand_synonyms": ["자누비아", "자누비아정", "시타글립틴", "자누메트"],
        "ingredients": ["시타글립틴"],
        "classes": ["DPP-4억제제", "당뇨약"],
        "default_dosage": "100mg",
        "category": "당뇨약",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "08:00",
            "meal_timing": "식전/식후 무관",
            "reason": "혈당 의존적으로 인슐린 분비를 조절하므로 매일 아침 일정한 시간에 복용합니다."
        },
        "caution": "저혈당 발생률은 낮으나 다른 당뇨약 병용 시 주의 필요."
    },

    # -------------------- 해열진통소염제 (Analgesics / NSAIDs) --------------------
    "타이레놀": {
        "canonical_name": "타이레놀정 500mg",
        "brand_synonyms": ["타이레놀", "타이레놀정", "타세놀", "세토펜", "아세트아미노펜", "타이레놀이알", "타이레놀ER"],
        "ingredients": ["아세트아미노펜"],
        "classes": ["해열진통제"],
        "default_dosage": "500mg",
        "category": "진통제",
        "chronotherapy": {
            "optimal_slot": "필요시",
            "optimal_time": "필요시 4~6시간 간격",
            "meal_timing": "공복 또는 식후 무관",
            "reason": "위장장애가 적어 공복 복용이 가능하나, 1회 1~2정(500~1000mg), 하루 최대 4,000mg을 초과해서는 안 됩니다."
        },
        "caution": "술을 마신 후 복용 시 치명적인 급성 간부전 위험이 있습니다. 종합감기약과 중복 복용 주의!"
    },
    "판콜": {
        "canonical_name": "판콜에이내복액",
        "brand_synonyms": ["판콜", "판콜에이", "판콜에스", "판콜내복액"],
        "ingredients": ["아세트아미노펜", "클로르페니라민", "카페인", "DL-메틸에페드린"],
        "classes": ["해열진통제", "항히스타민제", "감기약"],
        "default_dosage": "30ml (아세트아미노펜 300mg 함유)",
        "category": "감기약",
        "chronotherapy": {
            "optimal_slot": "식후 3회",
            "optimal_time": "08:30, 13:00, 19:30",
            "meal_timing": "식후 30분",
            "reason": "식후 30분에 복용하며 졸음을 유발할 수 있으므로 운전 시 주의합니다."
        },
        "caution": "아세트아미노펜 성분이 함유되어 있으므로 타이레놀과 절대 함께 드시지 마세요."
    },
    "판피린": {
        "canonical_name": "판피린큐액",
        "brand_synonyms": ["판피린", "판피린큐", "판피린티"],
        "ingredients": ["아세트아미노펜", "클로르페니라민", "카페인", "메틸에페드린"],
        "classes": ["해열진통제", "항히스타민제", "감기약"],
        "default_dosage": "20ml (아세트아미노펜 300mg 함유)",
        "category": "감기약",
        "chronotherapy": {
            "optimal_slot": "식후 3회",
            "optimal_time": "08:30, 13:00, 19:30",
            "meal_timing": "식후 30분",
            "reason": "식후 30분에 복용하여 감기 증상을 완화합니다."
        },
        "caution": "타이레놀 등 아세트아미노펜 성분 약제와 중복 복용 금지."
    },
    "게보린": {
        "canonical_name": "게보린정",
        "brand_synonyms": ["게보린", "게보린정"],
        "ingredients": ["아세트아미노펜", "이소프로필안티피린", "카페인"],
        "classes": ["해열진통제", "진통제"],
        "default_dosage": "1정 (아세트아미노펜 300mg 함유)",
        "category": "진통제",
        "chronotherapy": {
            "optimal_slot": "필요시",
            "optimal_time": "식후 30분",
            "meal_timing": "식후 30분",
            "reason": "위장 자극을 줄이기 위해 가급적 식후 복용을 권장합니다."
        },
        "caution": "타이레놀 중복 복용 주의, 알코올 섭취 금지."
    },
    "애드빌": {
        "canonical_name": "애드빌연질캡슐",
        "brand_synonyms": ["애드빌", "애드빌정", "부루펜", "이부프로펜", "모트린", "이지엔6애니"],
        "ingredients": ["이부프로펜"],
        "classes": ["NSAID", "진통소염제"],
        "default_dosage": "200mg",
        "category": "진통소염제",
        "chronotherapy": {
            "optimal_slot": "식후",
            "optimal_time": "08:30, 13:00, 19:30",
            "meal_timing": "식후 30분",
            "reason": "위점막 손상 및 위궤양을 방지하기 위해 반드시 식사 후 충분한 물과 함께 복용합니다."
        },
        "caution": "아스피린, 다른 소염진통제(탁센 등)와 동시 복용 시 위장관 출혈 위험이 급증합니다."
    },
    "탁센": {
        "canonical_name": "탁센연질캡슐",
        "brand_synonyms": ["탁센", "낙센", "나프록센", "아나록스"],
        "ingredients": ["나프록센"],
        "classes": ["NSAID", "진통소염제"],
        "default_dosage": "250mg",
        "category": "진통소염제",
        "chronotherapy": {
            "optimal_slot": "아침, 저녁",
            "optimal_time": "08:30, 19:00",
            "meal_timing": "식후 30분",
            "reason": "반감기가 길어 12시간 지속되므로 아침/저녁 식후에 복용합니다."
        },
        "caution": "위염, 속쓰림 위험이 있으므로 공복 복용 절대 금지."
    },
    "세레브렉스": {
        "canonical_name": "세레브렉스캡슐",
        "brand_synonyms": ["세레브렉스", "세레브렉스캡슐", "세레콕시브", "쎄레브", "콕시브"],
        "ingredients": ["세레콕시브"],
        "classes": ["NSAID", "진통소염제"],
        "default_dosage": "200mg",
        "category": "진통소염제",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "08:30",
            "meal_timing": "식후 30분",
            "reason": "COX-2 선택적 억제제로 위장장애가 덜하지만 식후 복용이 권장됩니다."
        },
        "caution": "심혈관 질환 병력이 있는 환자는 주의가 필요합니다."
    },

    # -------------------- 항혈전제 / 항응고제 (Antithrombotics) --------------------
    "아스피린": {
        "canonical_name": "아스피린프로텍트정 100mg",
        "brand_synonyms": ["아스피린", "아스피린프로텍트", "바이엘아스피린", "아스트릭스", "아스피린장용정"],
        "ingredients": ["아스피린"],
        "classes": ["항혈전제/항응고제"],
        "default_dosage": "100mg",
        "category": "혈관/항혈전제",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "08:00",
            "meal_timing": "식후 30분",
            "reason": "장용정으로 장에서 흡수되나 위장 자극을 줄이기 위해 식후 충분한 물과 함께 삼킵니다(부수지 말 것)."
        },
        "caution": "NSAID 소염진통제(이부프로펜, 탁센)와 병용 시 위장관 대량 출혈 위험."
    },
    "와파린": {
        "canonical_name": "와파린정",
        "brand_synonyms": ["와파린", "와파린정", "쿠마딘"],
        "ingredients": ["와파린"],
        "classes": ["항혈전제/항응고제"],
        "default_dosage": "2mg",
        "category": "혈관/항혈전제",
        "chronotherapy": {
            "optimal_slot": "저녁",
            "optimal_time": "18:00",
            "meal_timing": "식후 일정한 시간",
            "reason": "매일 일정한 저녁 시간에 복용하여 혈중 농도를 일정하게 유지합니다."
        },
        "caution": "소염진통제, 은행엽엑스 병용 시 출혈 위험. 비타민K 풍부 음식(청국장, 시금치, 녹차) 섭취 변동 주의."
    },

    # -------------------- 위장약 (Gastrointestinal Meds) --------------------
    "파모티딘": {
        "canonical_name": "파모티딘정",
        "brand_synonyms": ["파모티딘", "파모티딘정", "가스터", "가스터디", "파모트"],
        "ingredients": ["파모티딘"],
        "classes": ["H2차단제(위장약)", "위장약"],
        "default_dosage": "20mg",
        "category": "위장약",
        "chronotherapy": {
            "optimal_slot": "저녁",
            "optimal_time": "19:30",
            "meal_timing": "식후 30분 또는 취침 전",
            "reason": "야간 수면 중 분비되는 위산을 차단하여 역류성 식도염 증상 및 속쓰림을 예방합니다."
        },
        "caution": "신장 기능 저하 시 용량 조절이 필요합니다."
    },
    "넥시움": {
        "canonical_name": "넥시움정",
        "brand_synonyms": ["넥시움", "넥시움정", "에스오메프라졸", "에소메프라졸", "에소메졸"],
        "ingredients": ["에스오메프라졸"],
        "classes": ["PPI(위장약)", "위장약"],
        "default_dosage": "20mg",
        "category": "위장약",
        "chronotherapy": {
            "optimal_slot": "아침",
            "optimal_time": "07:30",
            "meal_timing": "아침 식전 30분",
            "reason": "아침 식전 공복에 복용해야 식후 활성화되는 위산 분비 펌프(Proton Pump)를 가장 강력하게 차단합니다."
        },
        "caution": "알약을 씹거나 부수지 말고 그대로 삼키세요."
    },
    "겔포스": {
        "canonical_name": "겔포스엠현탁액",
        "brand_synonyms": ["겔포스", "겔포스엠", "겔포스엘", "알마겔", "알마겔에프"],
        "ingredients": ["알루미늄", "마그네슘", "알마게이트"],
        "classes": ["금속양이온제산제", "위장약"],
        "default_dosage": "1포 (20ml)",
        "category": "위장약",
        "chronotherapy": {
            "optimal_slot": "공복 또는 식간",
            "optimal_time": "식후 1~2시간 또는 취침 전",
            "meal_timing": "공복 (식간)",
            "reason": "위산이 과다 분비되어 속이 쓰린 식간 공복에 복용하여 위벽을 코팅하고 산을 중화합니다."
        },
        "caution": "다른 약(항생제, 혈압약, 철분제)과 최소 2시간 이상 간격을 두고 복용하세요."
    },

    # -------------------- 갑상선약 (Thyroid Hormone) --------------------
    "신지로이드": {
        "canonical_name": "신지로이드정",
        "brand_synonyms": ["신지로이드", "신지로이드정", "씬지로이드", "레보티록신", "씬지록신"],
        "ingredients": ["레보티록신"],
        "classes": ["갑상선호르몬"],
        "default_dosage": "0.1mg (100mcg)",
        "category": "갑상선약",
        "chronotherapy": {
            "optimal_slot": "아침 기상 직후",
            "optimal_time": "06:30",
            "meal_timing": "아침 공복 (식전 30분~1시간)",
            "reason": "음식물이나 다른 영양제와 섞이면 흡수가 심각하게 저하되므로 기상 직후 순수한 물 한 컵과 단독 복용합니다."
        },
        "caution": "철분제, 칼슘제, 제산제와는 최소 4시간 간격을 두어야 합니다."
    },

    # -------------------- 항생제 (Antibiotics) --------------------
    "씨프로바이": {
        "canonical_name": "씨프로바이정",
        "brand_synonyms": ["씨프로바이", "시프로플록사신", "큐록신", "싸이프로"],
        "ingredients": ["시프로플록사신"],
        "classes": ["퀴놀론계항생제", "항생제"],
        "default_dosage": "500mg",
        "category": "항생제",
        "chronotherapy": {
            "optimal_slot": "12시간 간격",
            "optimal_time": "08:00, 20:00",
            "meal_timing": "식후 30분",
            "reason": "체내 유효 항균 농도(MIC)를 유지하기 위해 정확히 12시간 주기를 지켜 복용합니다."
        },
        "caution": "우유, 치즈, 칼슘 음료, 제산제와 복용 시 킬레이트 결합으로 흡수가 안 되므로 2시간 이상 띄우세요."
    },
    "오구멘틴": {
        "canonical_name": "오구멘틴정",
        "brand_synonyms": ["오구멘틴", "아모크라", "아목시실린-클라불란산", "크라목신"],
        "ingredients": ["아목시실린", "클라불란산"],
        "classes": ["페니실린계항생제", "항생제"],
        "default_dosage": "625mg",
        "category": "항생제",
        "chronotherapy": {
            "optimal_slot": "8시간 간격",
            "optimal_time": "07:00, 15:00, 23:00",
            "meal_timing": "식사 시작 시점 또는 식후 즉시",
            "reason": "위장 장애를 줄이고 클라불란산의 체내 흡수를 높이기 위해 식사 직전에 복용합니다."
        },
        "caution": "증상이 호전되어도 내성균 방지를 위해 처방된 일수를 모두 완복해야 합니다."
    },

    # -------------------- 영양제 / 보충제 (Supplements) --------------------
    "철분제": {
        "canonical_name": "훼로바유서방정",
        "brand_synonyms": ["철분제", "훼로바", "훼로바유", "훼마틴", "헤모큐", "볼그레"],
        "ingredients": ["철분"],
        "classes": ["철분제", "영양제"],
        "default_dosage": "1정",
        "category": "영양제",
        "chronotherapy": {
            "optimal_slot": "아침 공복",
            "optimal_time": "07:00",
            "meal_timing": "공복 또는 식간",
            "reason": "위장 장애가 없다면 공복 복용 시 흡수율이 가장 높습니다 (비타민C와 함께 복용 시 흡수 촉진)."
        },
        "caution": "녹차(탄닌), 우유/유제품(칼슘), 커피는 철분 흡수를 방해하므로 전후 2시간 동안 피하세요."
    },
    "비타민D": {
        "canonical_name": "비타민D 2000IU",
        "brand_synonyms": ["비타민D", "비타민디", "콜레칼시페롤"],
        "ingredients": ["비타민D"],
        "classes": ["지용성비타민", "영양제"],
        "default_dosage": "2000IU",
        "category": "영양제",
        "chronotherapy": {
            "optimal_slot": "점심 식후",
            "optimal_time": "12:30",
            "meal_timing": "지방이 포함된 식사 직후",
            "reason": "지용성 비타민이므로 식사 중의 지방 성분과 함께 흡수되어 흡수율이 최대 50% 이상 높아집니다."
        },
        "caution": "수면에 영향을 줄 수 있으므로 늦은 밤 복용은 피하세요."
    }
}


# =====================================================================
# 2. DRUG-DRUG COLLISION / INTERACTION RULES
# =====================================================================

DRUG_INTERACTIONS = [
    {
        "id": "INTERACTION_NSAID_ANTICOAGULANT",
        "pair": ("NSAID", "항혈전제/항응고제"),
        "severity": "CRITICAL",
        "title": "소염진통제(NSAID) + 항혈전제/항응고제 병용 위험",
        "mechanism": "소염진통제의 위점막 궤양 유발 작용과 항혈전제의 혈소판 응집 억제 작용이 복합되어 심각한 위장관 대량 출혈 및 전신 출혈 위험을 초래합니다.",
        "risk": "심각한 소화관 출혈, 흑색변, 빈혈 위험",
        "action": "단순 진통 해열이 필요한 경우 출혈 위험이 없는 아세트아미노펜(타이레놀)을 복용하세요. 불가피하게 소염진통제가 필요한 경우 위장보호제(PPI) 병용 처방에 대해 의사와 상담하세요."
    },
    {
        "id": "INTERACTION_NSAID_DUPLICATE",
        "pair": ("NSAID", "NSAID"),
        "severity": "MAJOR",
        "title": "동일 계열 소염진통제(NSAID) 중복 복용 주의",
        "mechanism": "두 가지 이상의 소염진통제를 병용해도 진통 효과는 증가하지 않으며, 위궤양, 천공, 신장 독성(급성 신부전) 부작용만 급증합니다.",
        "risk": "위궤양, 위장관 출혈, 급성 신장 손상",
        "action": "소염진통제는 단일 성분 1종류만 복용해야 합니다. 하나를 즉시 중단하세요."
    },
    {
        "id": "INTERACTION_ACETAMINOPHEN_DUPLICATE",
        "pair": ("아세트아미노펜", "아세트아미노펜"),
        "severity": "CRITICAL",
        "title": "아세트아미노펜(타이레놀/감기약) 성분 중복 복용 위험",
        "mechanism": "타이레놀과 판콜/판피린 등 종합감기약에 공통으로 들어있는 아세트아미노펜의 1일 총 복용량이 4,000mg을 초과하면 간 독성 대사체(NAPQI)가 간세포를 파괴합니다.",
        "risk": "치명적인 급성 간부전, 간세포 괴사",
        "action": "종합감기약을 복용 중이라면 타이레놀을 절대로 추가 복용하지 마세요!"
    },
    {
        "id": "INTERACTION_ACEI_POTASSIUM",
        "pair": ("ARB/ACEI", "칼륨보존이뇨제"),
        "severity": "MAJOR",
        "title": "혈압약(ARB/ACEI) + 칼륨보존이뇨제/보충제 고칼륨혈증 위험",
        "mechanism": "신장에서의 칼륨 배출이 억제되어 혈중 칼륨이 위험 수준까지 올라가는 고칼륨혈증을 일으킵니다.",
        "risk": "치명적 심장 부정맥, 심정지, 근육 무력증",
        "action": "칼륨 보충제 또는 고칼륨 영양제 섭취를 중단하고 혈액 검사로 전해질 수치를 확인하세요."
    },
    {
        "id": "INTERACTION_ANTIBIOTIC_CATION",
        "pair": ("퀴놀론계항생제", "금속양이온제산제"),
        "severity": "MODERATE",
        "title": "퀴놀론 항생제 + 제산제 킬레이트 결합 흡수 억제",
        "mechanism": "제산제의 알루미늄/마그네슘 이온이 항생제와 불용성 킬레이트를 형성하여 약물이 장에서 흡수되지 못하고 배출됩니다.",
        "risk": "항생제 치료 실패 및 세균 감염 악화",
        "action": "항생제와 제산제는 최소 2~3시간 이상의 시간 간격을 두고 복용하세요."
    },
    {
        "id": "INTERACTION_THYROID_CATION",
        "pair": ("갑상선호르몬", "금속양이온제산제"),
        "severity": "MODERATE",
        "title": "갑상선호르몬제(신지로이드) + 제산제/칼슘제 흡수 방해",
        "mechanism": "금속 이온이 레보티록신과 결합하여 소화관 흡수를 크게 떨어뜨립니다.",
        "risk": "갑상선 기능 저하증 치료 효과 상실",
        "action": "신지로이드 복용 후 최소 4시간 이상 지난 뒤에 제산제나 영양제를 복용하세요."
    },
    {
        "id": "INTERACTION_THYROID_IRON",
        "pair": ("갑상선호르몬", "철분제"),
        "severity": "MODERATE",
        "title": "갑상선호르몬제(신지로이드) + 철분제 병용 흡수 방해",
        "mechanism": "철분이 레보티록신과 결합하여 침전물을 형성해 체내 흡수를 차단합니다.",
        "risk": "갑상선 호르몬 수치 불균형",
        "action": "철분제와 신지로이드는 최소 4시간 이상 시간차를 두고 복용하세요."
    },
    {
        "id": "INTERACTION_METFORMIN_CONTRAST",
        "pair": ("비구아나이드계(당뇨)", "요오드조영제"),
        "severity": "MAJOR",
        "title": "당뇨약(메트포르민) + CT 조영제 신기능 저하 위험",
        "mechanism": "요오드 조영제로 인한 일시적 신기능 저하 시 메트포르민이 체내에 축적되어 젖산산증이 일어날 수 있습니다.",
        "risk": "급성 신부전 및 생명을 위협하는 젖산산증",
        "action": "조영제 CT 검사 전후 48시간 동안 메트포르민 복용을 중단해야 합니다."
    }
]


# =====================================================================
# 3. FOOD-DRUG INTERACTIONS
# =====================================================================

FOOD_INTERACTIONS = [
    {
        "food": "자몽 / 자몽주스",
        "targets": ["암로디핀", "아토르바스타틴", "심바스타틴", "펠로디핀"],
        "target_classes": ["칼슘채널차단제(CCB)", "스타틴(고지혈증)"],
        "severity": "CRITICAL",
        "summary": "자몽 속 성분이 간 대사 효소(CYP3A4)를 억제하여 혈중 약물 농도를 최대 수 배까지 증폭시킵니다.",
        "consequences": "급격한 저혈압(어지럼증, 기립성 실신) 및 심각한 근육 손상(횡문근융해증) 위험.",
        "guideline": "약 복용 기간 동안 자몽 및 자몽주스 섭취를 완전히 피하세요. (오렌지 주스는 안전합니다)"
    },
    {
        "food": "우유 / 유제품 / 치즈",
        "targets": ["시프로플록사신", "레보플록사신", "독시사이클린", "철분"],
        "target_classes": ["퀴놀론계항생제", "테트라사이클린계", "철분제"],
        "severity": "MAJOR",
        "summary": "우유 속 풍부한 칼슘이 약물 분자와 킬레이트 복합체를 형성하여 체내 흡수를 차단합니다.",
        "consequences": "항생제가 흡수되지 않아 감염증 치료에 실패하거나 빈혈 치료가 지연됩니다.",
        "guideline": "약 복용 전후 2시간 동안은 우유, 요거트, 치즈 등 유제품 섭취를 피하고 미온수로 복용하세요."
    },
    {
        "food": "알코올 / 술 (소주, 맥주, 와인)",
        "targets": ["아세트아미노펜", "메트포르민", "이부프로펜", "나프록센", "클로르페니라민"],
        "target_classes": ["해열진통제", "비구아나이드계(당뇨)", "NSAID", "항히스타민제"],
        "severity": "CRITICAL",
        "summary": "타이레놀과 술의 결합은 치명적인 급성 간 손상을 초래하며, 당뇨약과 병용 시 젖산산증 및 저혈당을 유발합니다.",
        "consequences": "급성 간부전, 위장관 대량 출혈, 혼수 상태, 저혈당 쇼크.",
        "guideline": "약물 복용 중에는 술을 절대 마시지 마세요. 음주 후 두통 시 타이레놀을 복용하는 것은 매우 위험합니다."
    },
    {
        "food": "커피 / 고카페인 음료",
        "targets": ["판콜", "판피린", "게보린", "시프로플록사신"],
        "target_classes": ["감기약", "해열진통제"],
        "severity": "MODERATE",
        "summary": "복합 감기약 및 진통제에 이미 카페인이 다량 포함되어 있어 카페인 과다 반응이 발생합니다.",
        "consequences": "가슴 두근거림(심계항진), 혈압 상승, 불면증, 불안, 속쓰림 악화.",
        "guideline": "약 복용 시 커피나 에너지 음료 대신 따뜻한 생수와 함께 드세요."
    },
    {
        "food": "고칼륨 식품 (바나나, 시금치, 오렌지, 키위)",
        "targets": ["로사르탄", "발사르탄", "스피로노락톤"],
        "target_classes": ["ARB/ACEI", "칼륨보존이뇨제"],
        "severity": "MODERATE",
        "summary": "신장의 칼륨 배설을 억제하는 혈압약 복용 중 고칼륨 식품을 과다 섭취하면 체내 칼륨이 축적됩니다.",
        "consequences": "손발 저림, 근육 무력감, 맥박 이상.",
        "guideline": "과도한 섭취를 자제하고 적정량만 균형 있게 섭취하세요."
    }
]


# =====================================================================
# 4. CHRONOTHERAPY (시간생물학적 복약 지도) RULES
# =====================================================================

CHRONOTHERAPY_RULES = {
    "혈압약": {
        "recommended_slot": "아침",
        "recommended_time": "08:00",
        "meal_timing": "식후 30분",
        "clinical_rationale": "기상 직후 찾아오는 혈압 급상승(Morning Blood Pressure Surge)을 효과적으로 억제하여 심근경색과 뇌졸중 발생률을 낮춥니다.",
        "senior_friendly_tip": "아침 식사 후 30분에 따뜻한 물과 함께 잊지 말고 드세요."
    },
    "고지혈증약": {
        "recommended_slot": "저녁/취침전",
        "recommended_time": "21:00",
        "meal_timing": "저녁 식후 또는 취침 전",
        "clinical_rationale": "간에서 콜레스테롤을 합성하는 효소(HMG-CoA Reductase)의 활성이 야간(자정 전후)에 가장 높으므로 저녁 복용 시 콜레스테롤 강하 효과가 극대화됩니다.",
        "senior_friendly_tip": "저녁 식사 후 또는 주무시기 전에 복용하시면 약효가 가장 좋습니다."
    },
    "당뇨약": {
        "recommended_slot": "아침/저녁 식사 직후",
        "recommended_time": "08:30, 19:00",
        "meal_timing": "식사 직후",
        "clinical_rationale": "메트포르민은 위점막을 자극해 속쓰림과 메스꺼움을 일으킬 수 있으므로 식사 도중이나 식사 직후에 복용해야 소화기 부작용을 예방합니다.",
        "senior_friendly_tip": "밥을 다 드시자마자 바로 물과 함께 드시면 속이 편안합니다."
    },
    "진통소염제": {
        "recommended_slot": "식후 30분",
        "recommended_time": "08:30, 13:00, 19:30",
        "meal_timing": "식후 30분",
        "clinical_rationale": "소염진통제(NSAID)는 위벽을 보호하는 물질을 차단하므로 공복 복용 시 위염이나 궤양을 일으킵니다. 반드시 식후에 충분한 물과 복용합니다.",
        "senior_friendly_tip": "속이 쓰릴 수 있으니 빈속에 드시지 마시고 꼭 밥을 드신 후 복용하세요."
    },
    "갑상선약": {
        "recommended_slot": "아침 기상 직후",
        "recommended_time": "06:30",
        "meal_timing": "아침 공복 (식전 30분~1시간)",
        "clinical_rationale": "음식물, 커피, 다른 영양제와 섞이면 흡수율이 급감하므로 기상 직후 공복에 순수한 물 한 컵과 단독 복용하고 최소 30분~1시간 금식해야 합니다.",
        "senior_friendly_tip": "아침에 눈뜨자마자 물 한 컵과 먼저 드시고, 30분 뒤에 아침 식사를 하세요."
    },
    "위장약": {
        "recommended_slot": "저녁 식후 또는 취침 전",
        "recommended_time": "19:30",
        "meal_timing": "식후 30분 또는 취침 전",
        "clinical_rationale": "파모티딘 등 H2차단제는 야간에 분비되는 위산을 막아 자는 동안의 속쓰림과 역류성 식도염을 완화합니다.",
        "senior_friendly_tip": "저녁 식후 또는 잠자리에 들기 전에 드시면 밤새 속이 편안합니다."
    }
}


# =====================================================================
# 5. RESOLVER & CLINICAL LOOKUP FUNCTIONS
# =====================================================================

def normalize_text(text: str) -> str:
    """Normalizes Korean text by stripping whitespace and punctuation."""
    return re.sub(r"[\s\-_정캡슐액포mg/()]+", "", text.lower())


def resolve_drug_info(drug_name_or_text: str) -> Optional[Dict[str, Any]]:
    """
    Searches the knowledge base for a drug by brand name, ingredient, or partial text.
    Returns matched entry dictionary with added metadata.
    """
    cleaned_input = normalize_text(drug_name_or_text)

    # 1. Exact or prefix match against DRUG_DATABASE keys
    for key, data in DRUG_DATABASE.items():
        cleaned_key = normalize_text(key)
        if cleaned_key in cleaned_input or cleaned_input in cleaned_key:
            return {
                "key": key,
                "canonical_name": data["canonical_name"],
                "ingredients": list(data["ingredients"]),
                "classes": list(data["classes"]),
                "default_dosage": data["default_dosage"],
                "category": data["category"],
                "chronotherapy": data.get("chronotherapy", {}),
                "caution": data.get("caution", "")
            }

        # Check brand synonyms
        for syn in data.get("brand_synonyms", []):
            cleaned_syn = normalize_text(syn)
            if cleaned_syn and (cleaned_syn in cleaned_input or cleaned_input in cleaned_syn):
                return {
                    "key": key,
                    "canonical_name": data["canonical_name"],
                    "ingredients": list(data["ingredients"]),
                    "classes": list(data["classes"]),
                    "default_dosage": data["default_dosage"],
                    "category": data["category"],
                    "chronotherapy": data.get("chronotherapy", {}),
                    "caution": data.get("caution", "")
                }

    # 2. Fallback heuristic detection if not found in database
    fallback_classes = []
    category = "기타"

    if any(k in drug_name_or_text for k in ["혈압", "암로디핀", "로사르탄", "노바스크", "코자"]):
        fallback_classes.extend(["혈압약", "칼슘채널차단제(CCB)"])
        category = "혈압약"
    elif any(k in drug_name_or_text for k in ["당뇨", "메트포르민", "글리메피리드", "인슐린"]):
        fallback_classes.extend(["당뇨약", "비구아나이드계(당뇨)"])
        category = "당뇨약"
    elif any(k in drug_name_or_text for k in ["고지혈", "스타틴", "콜레스테롤", "리피토", "크레스토"]):
        fallback_classes.extend(["고지혈증약", "스타틴(고지혈증)"])
        category = "고지혈증약"
    elif any(k in drug_name_or_text for k in ["진통", "소염", "이부프로펜", "탁센", "부루펜", "애드빌"]):
        fallback_classes.extend(["진통소염제", "NSAID"])
        category = "진통소염제"
    elif any(k in drug_name_or_text for k in ["타이레놀", "아세트아미노펜"]):
        fallback_classes.extend(["해열진통제"])
        category = "진통제"
    elif any(k in drug_name_or_text for k in ["위장", "속쓰림", "파모티딘", "겔포스", "넥시움"]):
        fallback_classes.extend(["위장약", "H2차단제(위장약)"])
        category = "위장약"
    elif any(k in drug_name_or_text for k in ["항생제", "마이신", "아목시실린"]):
        fallback_classes.extend(["항생제"])
        category = "항생제"

    if fallback_classes:
        chrono = CHRONOTHERAPY_RULES.get(category, {})
        return {
            "key": drug_name_or_text.strip(),
            "canonical_name": drug_name_or_text.strip(),
            "ingredients": [drug_name_or_text.strip()],
            "classes": fallback_classes,
            "default_dosage": "1정",
            "category": category,
            "chronotherapy": {
                "optimal_slot": chrono.get("recommended_slot", "식후"),
                "optimal_time": chrono.get("recommended_time", "08:30"),
                "meal_timing": chrono.get("meal_timing", "식후 30분"),
                "reason": chrono.get("clinical_rationale", "")
            },
            "caution": ""
        }

    return None


def check_drug_collisions(medications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Comprehensive DUR analysis on a list of medications:
    1. Active ingredient duplicate detection (e.g. Acetaminophen).
    2. Class-level duplicate detection (e.g. Dual NSAIDs).
    3. Pairwise drug-drug interactions from DRUG_INTERACTIONS.
    4. Food and lifestyle warnings (Grapefruit, Milk, Alcohol).
    5. Chronotherapy alignment tips.
    """
    resolved_meds: List[Dict[str, Any]] = []
    for med in medications:
        name = med.get("name", "")
        info = resolve_drug_info(name)
        if info:
            info["user_med"] = med
            resolved_meds.append(info)
        else:
            # Create a generic entry
            resolved_meds.append({
                "key": name,
                "canonical_name": name,
                "ingredients": [name],
                "classes": [med.get("category", "일반약")],
                "default_dosage": med.get("dosage", "1정"),
                "category": med.get("category", "일반약"),
                "chronotherapy": {},
                "caution": "",
                "user_med": med
            })

    warnings = []
    duplicate_warnings = []
    food_warnings = []
    chronotherapy_tips = []

    # 1. Duplicate Ingredient Check
    ingredient_count: Dict[str, List[str]] = {}
    for med in resolved_meds:
        for ing in med["ingredients"]:
            ingredient_count.setdefault(ing, []).append(med["canonical_name"])

    for ing, med_names in ingredient_count.items():
        if len(med_names) > 1:
            severity = "CRITICAL" if ing == "아세트아미노펜" else "MAJOR"
            msg = {
                "type": "DUPLICATE_INGREDIENT",
                "severity": severity,
                "ingredient": ing,
                "involved_drugs": med_names,
                "title": f"⚠️ 동일 성분('{ing}') 중복 복용 위험 ({severity})",
                "detail": f"{', '.join(med_names)}에 모두 '{ing}' 성분이 포함되어 있습니다.",
                "action": "동일 성분을 과다 복용할 경우 심각한 부작용(간 손상 등)이 발생할 수 있으니 하나만 선택하여 복용하세요."
            }
            duplicate_warnings.append(msg)
            warnings.append(msg)

    # 2. Duplicate Class Check (e.g. Multiple NSAIDs)
    class_count: Dict[str, List[str]] = {}
    for med in resolved_meds:
        for cls in med["classes"]:
            class_count.setdefault(cls, []).append(med["canonical_name"])

    if "NSAID" in class_count and len(class_count["NSAID"]) > 1:
        drugs = class_count["NSAID"]
        msg = {
            "type": "DUPLICATE_CLASS",
            "severity": "MAJOR",
            "class": "NSAID",
            "involved_drugs": drugs,
            "title": "⚠️ 소염진통제(NSAID) 계열 중복 복용 주의 (MAJOR)",
            "detail": f"{', '.join(drugs)}는 모두 소염진통제(NSAID)입니다. 동시 복용 시 위장관 출혈 및 위궤양 위험이 4배 이상 증가합니다.",
            "action": "소염진통제는 단 1종만 복용하세요. 다른 진통제가 필요하면 아세트아미노펜으로 대체하세요."
        }
        duplicate_warnings.append(msg)
        warnings.append(msg)

    # 3. Drug-Drug Interactions
    n = len(resolved_meds)
    seen_interactions = set()
    for i in range(n):
        for j in range(i + 1, n):
            med_a = resolved_meds[i]
            med_b = resolved_meds[j]
            classes_a = set(med_a["classes"]) | set(med_a["ingredients"])
            classes_b = set(med_b["classes"]) | set(med_b["ingredients"])

            for rule in DRUG_INTERACTIONS:
                p1, p2 = rule["pair"]
                if (p1 in classes_a and p2 in classes_b) or (p2 in classes_a and p1 in classes_b):
                    rule_key = (rule["id"], min(med_a["canonical_name"], med_b["canonical_name"]), max(med_a["canonical_name"], med_b["canonical_name"]))
                    if rule_key not in seen_interactions:
                        seen_interactions.add(rule_key)
                        inter_alert = {
                            "type": "DRUG_INTERACTION",
                            "severity": rule["severity"],
                            "title": f"🚨 {rule['title']}",
                            "involved_drugs": [med_a["canonical_name"], med_b["canonical_name"]],
                            "mechanism": rule["mechanism"],
                            "risk": rule["risk"],
                            "action": rule["action"]
                        }
                        warnings.append(inter_alert)

    # 4. Food Interactions
    all_ingredients = set()
    all_classes = set()
    for med in resolved_meds:
        all_ingredients.update(med["ingredients"])
        all_classes.update(med["classes"])

    for food_rule in FOOD_INTERACTIONS:
        matched_drugs = []
        for med in resolved_meds:
            med_ings = set(med["ingredients"])
            med_clss = set(med["classes"])
            if (med_ings & set(food_rule["targets"])) or (med_clss & set(food_rule["target_classes"])):
                matched_drugs.append(med["canonical_name"])

        if matched_drugs:
            food_alert = {
                "type": "FOOD_INTERACTION",
                "food": food_rule["food"],
                "severity": food_rule["severity"],
                "involved_drugs": matched_drugs,
                "title": f"🍎 음식 상호작용: [{food_rule['food']}] 주의",
                "summary": food_rule["summary"],
                "consequences": food_rule["consequences"],
                "guideline": food_rule["guideline"]
            }
            food_warnings.append(food_alert)

    # 5. Chronotherapy Recommendations
    for med in resolved_meds:
        chrono = med.get("chronotherapy")
        if chrono and chrono.get("optimal_slot"):
            chronotherapy_tips.append({
                "drug": med["canonical_name"],
                "optimal_slot": chrono.get("optimal_slot"),
                "optimal_time": chrono.get("optimal_time"),
                "meal_timing": chrono.get("meal_timing"),
                "reason": chrono.get("reason"),
                "caution": med.get("caution", "")
            })

    # Overall safety evaluation
    severities = [w.get("severity", "SAFE") for w in warnings]
    if "CRITICAL" in severities:
        overall_safety = "CRITICAL"
        status_color = "#e53e3e"
        safety_badge = "위험 (복용 주의)"
    elif "MAJOR" in severities:
        overall_safety = "MAJOR"
        status_color = "#dd6b20"
        safety_badge = "경고 (의사/약사 상담)"
    elif "MODERATE" in severities:
        overall_safety = "MODERATE"
        status_color = "#d69e2e"
        safety_badge = "주의 (시간차 복용)"
    else:
        overall_safety = "SAFE"
        status_color = "#38a169"
        safety_badge = "안전 (상호작용 없음)"

    return {
        "overall_safety": overall_safety,
        "status_color": status_color,
        "safety_badge": safety_badge,
        "warnings_count": len(warnings),
        "duplicate_warnings": duplicate_warnings,
        "interaction_warnings": [w for w in warnings if w["type"] == "DRUG_INTERACTION"],
        "food_warnings": food_warnings,
        "chronotherapy_tips": chronotherapy_tips,
        "analyzed_medications_count": len(resolved_meds)
    }
