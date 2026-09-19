---
name: medication-ai-assistant
description: AI medication scheduling, chronotherapy dosage timing, Korean DUR interaction checking, and patient adherence guidance skill.
---

# Medication AI Assistant Skill

This skill defines domain knowledge, clinical safety rules, and operational guidelines for building and running an intelligent medication reminder and advisory system.

## 1. Medication Scheduling & Chronotherapy Guidelines
Medications should be scheduled according to circadian rhythms (chronotherapy) to maximize efficacy and minimize adverse effects:

- **Hypertension (Blood Pressure) Meds**:
  - ACE inhibitors, ARBs, Calcium Channel Blockers (e.g., Amlodipine, Losartan)
  - Usually taken in the morning (07:00 ~ 08:30) with or without food, or bedtime if nocturnal hypertension is targeted.
- **Lipid-lowering agents (Statins)**:
  - Atorvastatin, Simvastatin, Rosuvastatin
  - Best taken in the evening or before bedtime (21:00 ~ 22:30), as cholesterol synthesis in the liver peaks at night.
- **Diabetes Meds (Hypoglycemic agents)**:
  - Metformin: Taken with or immediately after meals to reduce GI irritation.
  - Sulfonylureas (Glimepiride): Taken 30 minutes before breakfast to synchronize with postprandial glucose spike.
- **NSAIDs & Analgesics (Pain/Inflammation)**:
  - Ibuprofen, Naproxen, Celecoxib, Acetaminophen
  - Must be taken 30 minutes after meals with a full glass of water to avoid gastric ulcers/bleeding (Acetaminophen can be taken on empty stomach, but liver toxicity alert needed if exceeding 4000mg/day).
- **Antibiotics**:
  - Amoxicillin, Cephalosporins: Strict interval adherence (every 8 or 12 hours) to maintain minimum inhibitory concentration (MIC).
- **Thyroid Hormones (Levothyroxine)**:
  - Strictly taken on an empty stomach with plain water at least 30-60 minutes before breakfast.

## 2. Drug-Drug Interactions & DUR (Drug Utilization Review)
Core collision detection criteria for safety alerts:

| Primary Drug / Class | Secondary Drug / Class | Interaction Severity | Risk / Advisory |
| :--- | :--- | :--- | :--- |
| **Acetaminophen (Tylenol)** | **Cold combo remedies (판콜, 판피린, 종합감기약)** | **CRITICAL (중복주의)** | Duplicate active ingredient: Risk of severe hepatotoxicity (liver failure). Total daily dose must not exceed 4,000 mg. |
| **NSAID (Ibuprofen, Naproxen)** | **Aspirin or other NSAIDs** | **MAJOR (병용금기/주의)** | Additive gastrointestinal toxicity, severe bleeding, peptic ulcer risk. |
| **ACEI / ARB (Blood Pressure)** | **Potassium-sparing diuretics / K+ supplements** | **MAJOR (주의)** | Hyperkalemia risk (cardiac arrhythmia). |
| **Warfarin / Direct Anticoagulants** | **NSAIDs / Ginkgo extract** | **CRITICAL (출혈위험)** | Significantly increased risk of systemic bleeding. |
| **Ciprofloxacin / Tetracycline** | **Antacids (Al, Mg, Ca), Milk, Iron** | **MODERATE (흡수저하)** | Chelation complexes prevent antibiotic absorption. Space by at least 2 hours. |

## 3. Food-Drug Interactions
- **Grapefruit / Grapefruit Juice**:
  - Inhibits CYP3A4 enzyme.
  - Contraindicated with: Amlodipine, Felodipine, Simvastatin, Atorvastatin (causes sudden hypotension or severe rhabdomyolysis).
- **Dairy / Milk / High Calcium**:
  - Forms insoluble chelates with Tetracycline, Fluoroquinolones, Iron supplements.
- **Alcohol**:
  - Strictly avoid with Acetaminophen (liver toxicity), Metformin (lactic acidosis risk), Sedatives/Antihistamines (extreme drowsiness/CNS depression).

## 4. Missed Dose Protocol (1/2 Golden Rule)
When a user asks: "I missed my pill, should I take it now?"
1. Calculate the total interval between doses (e.g., twice daily = 12 hours interval, once daily = 24 hours interval).
2. Find the halfway point (e.g., 6 hours for 12h interval, 12 hours for 24h interval).
3. **If less than half the interval has passed**: Take the missed dose immediately, then resume normal schedule.
4. **If more than half the interval has passed**: Skip the missed dose completely. Wait for the next scheduled dose.
5. **NEVER** take a double dose to make up for a missed one.

## 5. UI/UX Accessibility for Senior Patients
- High contrast color themes (Navy/White or Dark/Bright Yellow) with large typography (minimum 18px body, 24px headings).
- Audio cues (chime sound on alert) and clear Korean Text-to-Speech (TTS).
- Simple three-button choices: [복용 완료], [10분 후 다시 알림], [건너뛰기].
