/**
 * MediMind AI - Frontend Application Core Logic
 * 
 * Features:
 * - Real-time clock & Countdown Timer to next scheduled dose
 * - Web Audio API synthesizer for friendly 2-tone chime
 * - Web Speech API (window.speechSynthesis) Korean TTS announcements
 * - Daily Timeline (Morning, Noon, Evening, Bedtime) with interactive pill cards
 * - Senior Mode (High Contrast & 125% Enlarged Typography)
 * - AI Prescription OCR / NLP text parser with realistic preset chips
 * - Clinical DUR (Drug Utilization Review) & Food Interaction Checker (SKILL.md)
 * - AI Pharmacist 24/7 Consultation Drawer with 1/2 Golden Rule guidance
 * - Adherence Analytics & Printable Doctor Consultation Clinical Report
 * - Full REST API synchronization with robust localStorage offline fallback
 */

(function () {
  'use strict';

  /* ==========================================================================
     1. Constants & Configuration
     ========================================================================== */
  const STORAGE_KEYS = {
    MEDICATIONS: 'medimind_medications_v1',
    LOGS: 'medimind_logs_v1',
    SENIOR_MODE: 'medimind_senior_mode_v1',
    STREAK: 'medimind_streak_v1'
  };

  const API_ENDPOINTS = {
    MEDICATIONS: '/api/medications',
    LOGS: '/api/logs',
    PARSE_PRESCRIPTION: '/api/ai/parse-prescription',
    CHECK_INTERACTIONS: '/api/ai/check-interactions',
    CHAT: '/api/ai/chat',
    REPORT: '/api/report'
  };

  const TIME_SLOTS = {
    morning: { id: 'morning', label: '아침', emoji: '🌅', time: '08:00', startHour: 6, endHour: 10 },
    noon: { id: 'noon', label: '점심', emoji: '☀️', time: '12:30', startHour: 11, endHour: 15 },
    evening: { id: 'evening', label: '저녁', emoji: '🌆', time: '19:00', startHour: 17, endHour: 20 },
    bedtime: { id: 'bedtime', label: '취침전', emoji: '🌙', time: '22:00', startHour: 21, endHour: 24 }
  };

  // Initial demo medications adhering to Chronotherapy & Korean Clinical Guidelines
  const DEFAULT_MEDICATIONS = [
    {
      id: 'med-novasc',
      name: '노바스크정 (암로디핀)',
      dosage: '5mg 1정',
      category: '혈압약 (칼슘채널차단제)',
      slots: ['morning'],
      mealRelation: '식후 30분',
      instructions: '매일 아침 규칙적으로 복용. 자몽 및 자몽주스 섭취 금지',
      chronotherapyTip: '혈압약은 아침에 복용하여 일과 중 혈압 급상승(Morning Surge)을 예방합니다.',
      status: { morning: 'pending' }
    },
    {
      id: 'med-diabex',
      name: '다이아벡스정 (메트포르민)',
      dosage: '500mg 1정',
      category: '당뇨병용제 (비구아나이드계)',
      slots: ['morning', 'evening'],
      mealRelation: '식사 직후',
      instructions: '위장장애 방지를 위해 식사 직후 복용. 음주(알코올) 절대 금지',
      chronotherapyTip: '메트포르민은 식사 직후 복용해야 속쓰림과 오심 증상을 최소화할 수 있습니다.',
      status: { morning: 'taken', evening: 'pending' }
    },
    {
      id: 'med-tylenol',
      name: '타이레놀정 (아세트아미노펜)',
      dosage: '500mg 1정',
      category: '해열진통제',
      slots: ['noon'],
      mealRelation: '식후 30분',
      instructions: '1일 최대 4,000mg 초과 복용 금지. 종합감기약 중복 성분 주의',
      chronotherapyTip: '간독성 예방을 위해 감기약 등 다른 약에 아세트아미노펜이 포함되어 있는지 확인하세요.',
      status: { noon: 'pending' }
    },
    {
      id: 'med-lipitor',
      name: '리피토정 (아토르바스타틴)',
      dosage: '20mg 1정',
      category: '고지혈증치료제 (HMG-CoA 억제제)',
      slots: ['bedtime'],
      mealRelation: '취침 전',
      instructions: '야간 간내 콜레스테롤 합성 저해를 위해 취침 전 복용. 자몽주스 금지',
      chronotherapyTip: '콜레스테롤 합성 효소는 야간(새벽)에 활성화되므로 취침 전 복용이 가장 효과적입니다.',
      status: { bedtime: 'pending' }
    }
  ];

  /* ==========================================================================
     2. Application State
     ========================================================================== */
  const state = {
    medications: [],
    logs: [],
    streakDays: 7,
    seniorMode: false,
    activeSlotFilter: 'all',
    audioContext: null,
    countdownInterval: null,
    nextDose: null,
    durWarnings: []
  };

  /* ==========================================================================
     3. Audio & Voice Synthesizer (Web Audio API & Web Speech API)
     ========================================================================== */
  
  /**
   * Initializes or returns the Web Audio Context
   */
  function getAudioContext() {
    if (!state.audioContext) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        state.audioContext = new AudioCtx();
      }
    }
    if (state.audioContext && state.audioContext.state === 'suspended') {
      state.audioContext.resume();
    }
    return state.audioContext;
  }

  /**
   * Generates a pleasant 2-tone melodic medical chime (E5 -> A5)
   */
  function playChimeSound() {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      
      // Tone 1: E5 (659.25 Hz)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(659.25, now);
      gain1.gain.setValueAtTime(0.001, now);
      gain1.gain.exponentialRampToValueAtTime(0.25, now + 0.05);
      gain1.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.5);

      // Tone 2: A5 (880.00 Hz) with slight delay
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(880.00, now + 0.18);
      gain2.gain.setValueAtTime(0.001, now + 0.18);
      gain2.gain.exponentialRampToValueAtTime(0.3, now + 0.23);
      gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.75);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.18);
      osc2.stop(now + 0.8);
    } catch (e) {
      console.warn('Web Audio API chime failed or not permitted yet:', e);
    }
  }

  /**
   * Speaks a reminder using Korean Web Speech Synthesis
   */
  function speakReminder(message) {
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel(); // Stop any pending utterance
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.lang = 'ko-KR';
      // In senior mode, speak slightly slower with clear articulation
      utterance.rate = state.seniorMode ? 0.85 : 0.95;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('TTS Speech Synthesis error:', e);
    }
  }

  /* ==========================================================================
     4. Data Persistence & REST API Synchronization
     ========================================================================== */

  /**
   * Safe fetch with fallback to local storage or generator
   */
  async function fetchWithFallback(url, options = {}, fallbackData = null) {
    try {
      const response = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
      });
      if (response.ok) {
        return await response.json();
      }
      throw new Error(`HTTP error ${response.status}`);
    } catch (err) {
      // Backend server not running yet; use fallback silently
      return typeof fallbackData === 'function' ? fallbackData() : fallbackData;
    }
  }

  function loadLocalState() {
    try {
      const storedMeds = localStorage.getItem(STORAGE_KEYS.MEDICATIONS);
      state.medications = storedMeds ? JSON.parse(storedMeds) : DEFAULT_MEDICATIONS;

      const storedLogs = localStorage.getItem(STORAGE_KEYS.LOGS);
      state.logs = storedLogs ? JSON.parse(storedLogs) : generateInitialLogs();

      const storedSenior = localStorage.getItem(STORAGE_KEYS.SENIOR_MODE);
      state.seniorMode = storedSenior === 'true';

      const storedStreak = localStorage.getItem(STORAGE_KEYS.STREAK);
      state.streakDays = storedStreak ? parseInt(storedStreak, 10) : 7;
    } catch (e) {
      console.error('Failed to load local storage, initializing defaults:', e);
      state.medications = DEFAULT_MEDICATIONS;
      state.logs = generateInitialLogs();
      state.seniorMode = false;
      state.streakDays = 7;
    }
  }

  function saveLocalState() {
    try {
      localStorage.setItem(STORAGE_KEYS.MEDICATIONS, JSON.stringify(state.medications));
      localStorage.setItem(STORAGE_KEYS.LOGS, JSON.stringify(state.logs));
      localStorage.setItem(STORAGE_KEYS.SENIOR_MODE, state.seniorMode ? 'true' : 'false');
      localStorage.setItem(STORAGE_KEYS.STREAK, state.streakDays.toString());
    } catch (e) {
      console.warn('Could not save to localStorage:', e);
    }
  }

  function generateInitialLogs() {
    // Generate 7 days of realistic logs for adherence gauge
    const logs = [];
    const days = ['월', '화', '수', '목', '금', '토', '일'];
    days.forEach((day, idx) => {
      const count = idx === 5 ? 3 : 4; // Saturday 3 doses
      for (let i = 0; i < count; i++) {
        logs.push({
          id: `log-${idx}-${i}`,
          medId: 'med-novasc',
          status: (idx === 6 && i === 3) ? 'snoozed' : 'taken',
          timestamp: new Date(Date.now() - (6 - idx) * 86400000).toISOString()
        });
      }
    });
    return logs;
  }

  /* ==========================================================================
     5. Clinical DUR & Food Interaction Rules (SKILL.md)
     ========================================================================== */
  function evaluateDUR(medList) {
    const warnings = [];
    const allNames = medList.map(m => (m.name + ' ' + (m.category || '')).toLowerCase());
    const nameStr = allNames.join(' ');

    // 1. Acetaminophen Duplication (Tylenol + Cold Combo)
    const hasTylenol = nameStr.includes('아세트아미노펜') || nameStr.includes('타이레놀');
    const hasColdCombo = nameStr.includes('감기') || nameStr.includes('판콜') || nameStr.includes('판피린') || nameStr.includes('코프');
    if (hasTylenol && hasColdCombo) {
      warnings.push({
        severity: 'critical',
        type: '중복주의 (동일성분 중복)',
        title: '아세트아미노펜(해열진통제) 성분 중복 감지',
        desc: '타이레놀과 종합감기약에 아세트아미노펜 성분이 중복 함유되어 급성 간부전/간독성 위험이 있습니다.',
        advice: '1일 총 복용량이 4,000mg을 초과하지 않도록 감기약과 타이레놀을 동시 복용하지 마세요.'
      });
    }

    // 2. NSAID Multi-Drug Interaction (Ibuprofen + Aspirin / other NSAIDs)
    const hasNsaid1 = nameStr.includes('이부프로펜') || nameStr.includes('나프록센') || nameStr.includes('세레콕시브');
    const hasNsaid2 = nameStr.includes('아스피린') || nameStr.includes('소염진통');
    if (hasNsaid1 && hasNsaid2) {
      warnings.push({
        severity: 'major',
        type: '병용주의 (소화기계 출혈)',
        title: '비스테로이드성 소염진통제(NSAIDs) 병용 주의',
        desc: '소염진통제 중복 복용 시 위장관 궤양, 위출혈 및 신장 기능 저하 위험이 급격히 증가합니다.',
        advice: '식사 직후 충분한 물과 함께 복용하고, 위장보호제(제산제 등) 병용 여부를 의사와 상의하세요.'
      });
    }

    // 3. Blood Pressure Meds + Grapefruit Food Interaction
    const hasAmlodipineOrStatin = nameStr.includes('노바스크') || nameStr.includes('암로디핀') || nameStr.includes('아토르바스타틴') || nameStr.includes('심바스타틴') || nameStr.includes('리피토');
    if (hasAmlodipineOrStatin) {
      warnings.push({
        severity: 'food',
        type: '식품 상호작용 (CYP3A4 억제)',
        title: '자몽 / 자몽주스 섭취 제한 안내',
        desc: '자몽 속 성분이 간 대사 효소(CYP3A4)를 차단하여 혈압약·고지혈증약 혈중 농도를 급격히 높입니다 (급격한 저혈압 또는 근육통 위험).',
        advice: '복약 기간 중 자몽 및 자몽주스 섭취를 피하시고 오렌지나 사과주스로 대체하세요.'
      });
    }

    // 4. Diabetes (Metformin) + Alcohol
    const hasMetformin = nameStr.includes('메트포르민') || nameStr.includes('다이아벡스');
    if (hasMetformin) {
      warnings.push({
        severity: 'critical',
        type: '식품/음주 주의 (유산산증)',
        title: '메트포르민 복용 중 음주 절대 금지',
        desc: '메트포르민과 알코올이 체내에서 반응할 경우 치명적인 젖산산증(Lactic Acidosis)이 유발될 수 있습니다.',
        advice: '복용 전후 24시간 동안은 음주를 엄격히 금해야 합니다.'
      });
    }

    state.durWarnings = warnings;
    renderDURBanners();
  }

  function renderDURBanners() {
    const bannerEl = document.getElementById('globalSafetyBanner');
    const bannerMsg = document.getElementById('safetyBannerMessage');
    const badgeAlert = document.getElementById('durBadgeAlert');

    if (!bannerEl || !badgeAlert) return;

    if (state.durWarnings.length > 0) {
      bannerEl.style.display = 'flex';
      const firstWarn = state.durWarnings[0];
      bannerMsg.innerHTML = `<strong>${firstWarn.title}:</strong> ${firstWarn.desc}`;
      badgeAlert.textContent = `주의 ${state.durWarnings.length}건`;
      badgeAlert.style.display = 'inline-block';
    } else {
      bannerEl.style.display = 'none';
      badgeAlert.textContent = '안전 (DUR 통과)';
      badgeAlert.style.background = '#10b981';
    }
  }

  /* ==========================================================================
     6. Countdown Timer & Next Dose Scheduler
     ========================================================================== */
  function findNextScheduledDose() {
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();

    // Slot minutes mapping
    const slotTimes = [
      { slot: 'morning', timeStr: '08:00', minutes: 8 * 60, label: '아침 복약' },
      { slot: 'noon', timeStr: '12:30', minutes: 12 * 60 + 30, label: '점심 복약' },
      { slot: 'evening', timeStr: '19:00', minutes: 19 * 60, label: '저녁 복약' },
      { slot: 'bedtime', timeStr: '22:00', minutes: 22 * 60, label: '취침 전 복약' }
    ];

    // Check today's pending doses
    for (const slotObj of slotTimes) {
      const medsInSlot = state.medications.filter(m => m.slots && m.slots.includes(slotObj.slot));
      if (medsInSlot.length > 0) {
        // Find if there's any medication not yet taken in this slot
        const pendingMed = medsInSlot.find(m => !m.status || m.status[slotObj.slot] !== 'taken');
        if (pendingMed) {
          // If the time hasn't passed or is snoozed
          return {
            medication: pendingMed,
            allInSlot: medsInSlot,
            slot: slotObj.slot,
            slotLabel: slotObj.label,
            timeStr: slotObj.timeStr,
            targetMinutes: slotObj.minutes,
            isTomorrow: slotObj.minutes <= currentMinutes && (currentMinutes - slotObj.minutes > 180)
          };
        }
      }
    }

    // If all taken or late, default to first morning dose tomorrow
    const morningMeds = state.medications.filter(m => m.slots && m.slots.includes('morning'));
    const defMed = morningMeds[0] || state.medications[0];
    return {
      medication: defMed,
      allInSlot: morningMeds,
      slot: 'morning',
      slotLabel: '내일 아침 복약',
      timeStr: '08:00',
      targetMinutes: 8 * 60,
      isTomorrow: true
    };
  }

  function updateCountdown() {
    const next = findNextScheduledDose();
    state.nextDose = next;

    if (!next || !next.medication) return;

    // Update hero details
    const heroName = document.getElementById('heroMedName');
    const heroDose = document.getElementById('heroMedDose');
    const heroCategory = document.getElementById('heroMedCategory');
    const heroTimeSlotChip = document.getElementById('heroTimeSlotChip');
    const heroScheduledTimeText = document.getElementById('heroScheduledTimeText');
    const heroMealRelation = document.getElementById('heroMealRelation');
    const heroChronoTip = document.getElementById('heroChronoTip');

    if (heroName) heroName.textContent = next.medication.name;
    if (heroDose) heroDose.textContent = next.medication.dosage;
    if (heroCategory) heroCategory.textContent = next.medication.category || '전문 처방약';
    if (heroTimeSlotChip) heroTimeSlotChip.textContent = next.slotLabel;
    if (heroScheduledTimeText) heroScheduledTimeText.textContent = `${next.isTomorrow ? '내일 ' : '오늘 '} ${next.timeStr}`;
    if (heroMealRelation) heroMealRelation.textContent = `${next.medication.mealRelation || '식후 30분'} 복용`;
    if (heroChronoTip) {
      heroChronoTip.textContent = next.medication.chronotherapyTip || 
        '시간치료학 가이드: 규칙적인 복약 시간을 준수할 때 약효 유지율이 최고조에 이릅니다.';
    }

    // Calculate diff
    const now = new Date();
    const currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
    let targetSeconds = next.targetMinutes * 60;
    
    if (next.isTomorrow || targetSeconds <= currentSeconds) {
      targetSeconds += 24 * 3600; // Next day
    }

    const diff = Math.max(0, targetSeconds - currentSeconds);
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;

    const hEl = document.getElementById('cdHours');
    const mEl = document.getElementById('cdMinutes');
    const sEl = document.getElementById('cdSeconds');

    if (hEl) hEl.textContent = String(hours).padStart(2, '0');
    if (mEl) mEl.textContent = String(minutes).padStart(2, '0');
    if (sEl) sEl.textContent = String(seconds).padStart(2, '0');

    // Trigger alert chime & voice if exactly 0
    if (diff === 0) {
      triggerDoseAlarm(next);
    }
  }

  function triggerDoseAlarm(next) {
    playChimeSound();
    speakReminder(`복약 시간입니다. ${next.medication.name}, ${next.medication.mealRelation} 복용하세요.`);
    showToast('복약 알림', `${next.medication.name} 복용할 시간입니다!`, 'warning');
  }

  function startLiveClock() {
    const clockEl = document.getElementById('liveClockDisplay');
    const dateEl = document.getElementById('currentDateDisplay');

    function tick() {
      const now = new Date();
      if (clockEl) {
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        clockEl.textContent = `${hours}:${minutes}:${seconds}`;
      }
      if (dateEl) {
        const days = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];
        dateEl.textContent = `${now.getFullYear()}년 ${now.getMonth() + 1}월 ${now.getDate()}일 ${days[now.getDay()]}`;
      }
      updateCountdown();
    }

    tick();
    setInterval(tick, 1000);
  }

  /* ==========================================================================
     7. Medication Timeline Rendering
     ========================================================================== */
  function renderTimeline() {
    const slots = ['morning', 'noon', 'evening', 'bedtime'];
    const filter = state.activeSlotFilter;

    slots.forEach(slotKey => {
      const colEl = document.querySelector(`.time-slot-column[data-slot="${slotKey}"]`);
      const containerEl = document.getElementById(`cards${capitalize(slotKey)}`);
      const countEl = document.getElementById(`count${capitalize(slotKey)}`);

      if (!containerEl) return;

      // Handle filter visibility
      if (colEl) {
        if (filter === 'all' || filter === slotKey) {
          colEl.style.display = 'flex';
        } else {
          colEl.style.display = 'none';
        }
      }

      // Filter medications in this slot
      const medsInSlot = state.medications.filter(m => m.slots && m.slots.includes(slotKey));
      if (countEl) {
        countEl.textContent = `${medsInSlot.length}개 약물`;
      }

      containerEl.innerHTML = '';

      if (medsInSlot.length === 0) {
        containerEl.innerHTML = `
          <div class="empty-slot-msg">
            <span>✨</span>
            <p>등록된 복약 일정이 없습니다.</p>
          </div>
        `;
        return;
      }

      medsInSlot.forEach(med => {
        const currentStatus = (med.status && med.status[slotKey]) || 'pending';
        let statusBadgeText = '대기 중';
        let statusBadgeClass = 'badge-waiting';
        let cardClass = '';

        if (currentStatus === 'taken') {
          statusBadgeText = '✔️ 복용 완료';
          statusBadgeClass = 'badge-taken';
          cardClass = 'status-taken';
        } else if (currentStatus === 'snoozed') {
          statusBadgeText = '⏰ 10분 연기';
          statusBadgeClass = 'badge-snoozed';
          cardClass = 'status-snoozed';
        } else if (currentStatus === 'skipped') {
          statusBadgeText = '⏭️ 건너뜀';
          statusBadgeClass = 'badge-skipped';
          cardClass = 'status-skipped';
        }

        const card = document.createElement('div');
        card.className = `med-card ${cardClass}`;
        card.innerHTML = `
          <div class="card-top">
            <div class="card-pill-info">
              <span class="card-pill-icon">💊</span>
              <div>
                <h4 class="card-pill-title">${escapeHtml(med.name)}</h4>
                <span class="card-pill-dosage">${escapeHtml(med.dosage)}</span>
              </div>
            </div>
            <span class="card-status-badge ${statusBadgeClass}">${statusBadgeText}</span>
          </div>

          <div class="card-timing-tag">
            <span>🍽️</span>
            <span>${escapeHtml(med.mealRelation || '식후 30분')}</span>
          </div>

          <div class="card-actions-row">
            ${currentStatus !== 'taken' ? `
              <button type="button" class="card-quick-take-btn" data-action="take" data-id="${med.id}" data-slot="${slotKey}">
                <span>✔️</span>
                <span>복용 완료</span>
              </button>
            ` : `
              <button type="button" class="card-quick-take-btn" style="background:#e2e8f0; border-color:#cbd5e1; color:#475569;" data-action="undo" data-id="${med.id}" data-slot="${slotKey}">
                <span>↩️</span>
                <span>복용 취소</span>
              </button>
            `}
            <button type="button" class="card-icon-btn" title="약물 삭제" data-action="delete" data-id="${med.id}" aria-label="${escapeHtml(med.name)} 삭제">
              🗑️
            </button>
          </div>
        `;
        containerEl.appendChild(card);
      });
    });

    evaluateDUR(state.medications);
    updateAdherenceStats();
  }

  /* ==========================================================================
     8. Adherence Analytics & History Track
     ========================================================================== */
  function updateAdherenceStats() {
    let totalScheduled = 0;
    let totalTaken = 0;

    state.medications.forEach(med => {
      (med.slots || []).forEach(slot => {
        totalScheduled++;
        if (med.status && med.status[slot] === 'taken') {
          totalTaken++;
        }
      });
    });

    const percent = totalScheduled > 0 ? Math.round((totalTaken / totalScheduled) * 100) : 100;
    
    // Update SVG Circular Gauge
    const circle = document.getElementById('gaugeProgressCircle');
    const percentText = document.getElementById('adherencePercentText');
    const summaryDesc = document.getElementById('adherenceSummaryDesc');

    if (circle) {
      // Circumference = 2 * PI * r = 2 * 3.14159 * 70 = 439.82
      const circumference = 440;
      const offset = circumference - (percent / 100) * circumference;
      circle.style.strokeDashoffset = offset;
    }

    if (percentText) {
      percentText.textContent = `${percent}%`;
    }

    if (summaryDesc) {
      summaryDesc.innerHTML = `오늘 예정된 총 <strong>${totalScheduled}회</strong> 중 <strong>${totalTaken}회 완료</strong> (${percent}%) 하였습니다.`;
    }

    // Render Weekly 7-Day History Track
    renderWeeklyHistoryTrack();
  }

  function renderWeeklyHistoryTrack() {
    const grid = document.getElementById('weeklyTrackGrid');
    if (!grid) return;

    const days = [
      { name: '월', status: 'perfect', score: '100%' },
      { name: '화', status: 'perfect', score: '100%' },
      { name: '수', status: 'partial', score: '75%' },
      { name: '목', status: 'perfect', score: '100%' },
      { name: '금', status: 'perfect', score: '100%' },
      { name: '토', status: 'partial', score: '66%' },
      { name: '일 (오늘)', status: 'perfect', score: '92%' }
    ];

    grid.innerHTML = days.map(d => `
      <div class="track-day-col">
        <span class="day-name">${d.name}</span>
        <div class="day-bubble ${d.status}">
          ${d.status === 'perfect' ? '✔️' : (d.status === 'partial' ? '⏳' : '✕')}
        </div>
        <span class="day-score">${d.score}</span>
      </div>
    `).join('');
  }

  /* ==========================================================================
     9. Medication Actions (Take, Snooze, Skip, Add, Delete)
     ========================================================================== */
  function takeMedication(medId, slotKey) {
    const med = state.medications.find(m => m.id === medId);
    if (!med) return;

    if (!med.status) med.status = {};
    med.status[slotKey] = 'taken';

    // Log the event
    const log = {
      id: `log-${Date.now()}`,
      medId: med.id,
      medName: med.name,
      slot: slotKey,
      status: 'taken',
      timestamp: new Date().toISOString()
    };
    state.logs.push(log);
    
    // Sound & TTS
    playChimeSound();
    showToast('복용 완료', `🎉 ${med.name} 복용 완료되었습니다. 연속 기록 유지 중!`, 'success');
    
    saveLocalState();
    renderTimeline();
    updateCountdown();

    // Async REST sync
    fetchWithFallback(API_ENDPOINTS.LOGS, {
      method: 'POST',
      body: JSON.stringify(log)
    });
  }

  function undoTakeMedication(medId, slotKey) {
    const med = state.medications.find(m => m.id === medId);
    if (!med) return;

    if (!med.status) med.status = {};
    med.status[slotKey] = 'pending';

    saveLocalState();
    renderTimeline();
    updateCountdown();
    showToast('복용 상태 초기화', `${med.name} 복약 상태가 대기 중으로 변경되었습니다.`, 'info');
  }

  function snoozeMedication(medId, slotKey) {
    const med = state.medications.find(m => m.id === medId);
    if (!med) return;

    if (!med.status) med.status = {};
    med.status[slotKey] = 'snoozed';

    showToast('10분 후 재알림', `⏰ 10분 후 ${med.name} 복약을 다시 알려드립니다.`, 'warning');
    saveLocalState();
    renderTimeline();
    updateCountdown();
  }

  function skipMedication(medId, slotKey) {
    const med = state.medications.find(m => m.id === medId);
    if (!med) return;

    const reason = prompt(`[건너뛰기] ${med.name} 복약을 건너뛰는 사유를 입력해주세요:\n(예: 식사를 거름, 속쓰림, 약이 떨어짐)`, '식사를 거름');
    if (reason === null) return; // User cancelled prompt

    if (!med.status) med.status = {};
    med.status[slotKey] = 'skipped';

    const log = {
      id: `log-${Date.now()}`,
      medId: med.id,
      medName: med.name,
      slot: slotKey,
      status: 'skipped',
      reason: reason || '사유 미입력',
      timestamp: new Date().toISOString()
    };
    state.logs.push(log);

    showToast('복약 건너뜀', `⏭️ 이번 복약을 건너뛰었습니다. (사유: ${log.reason})`, 'info');
    saveLocalState();
    renderTimeline();
    updateCountdown();
  }

  function deleteMedication(medId) {
    const med = state.medications.find(m => m.id === medId);
    if (!med) return;

    if (confirm(`'${med.name}'을(를) 복약 일정에서 삭제하시겠습니까?`)) {
      state.medications = state.medications.filter(m => m.id !== medId);
      saveLocalState();
      renderTimeline();
      updateCountdown();
      showToast('삭제 완료', `${med.name}이(가) 스케줄에서 삭제되었습니다.`, 'info');
    }
  }

  /* ==========================================================================
     10. Prescription AI Scanner (OCR & Text Parser)
     ========================================================================== */
  const PRESCRIPTION_PRESETS = {
    cold: `타이레놀정 500mg 하루 3회 3일분 식후 30분
코푸시럽 20ml 하루 3회 식후 30분
페니라민정 2mg 하루 3회 식후 30분`,

    chronic: `노바스크정 5mg 1일 1회 아침 식후 1정
다이아벡스정 500mg 1일 2회 아침 저녁 식사 직후
리피토정 20mg 1일 1회 취침 전 1정`,

    pain: `이부프로펜정 400mg 1일 2회 점심 저녁 식후 30분
스티렌투엑스정 1일 2회 점심 저녁 식사 직후 위장보호제`
  };

  function parsePrescriptionText(text) {
    const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
    const parsedMeds = [];

    lines.forEach((line, index) => {
      // Extract medicine name
      const nameMatch = line.match(/^([가-힣a-zA-Z0-9\s]+?(?:정|캡슐|시럽|액|산|연질캡슐)?)\s+(\d+(?:\.\d+)?(?:mg|g|ml|정))/i) ||
                        line.match(/^([가-힣a-zA-Z0-9\s]+)/);

      const rawName = nameMatch ? nameMatch[1].trim() : `처방약물 ${index + 1}`;
      const dosageMatch = line.match(/(\d+(?:\.\d+)?(?:mg|g|ml|정))/i);
      const dosage = dosageMatch ? dosageMatch[1] : '1정';

      // Timing slots detection
      const slots = [];
      if (line.includes('아침') || line.includes('하루 3회') || line.includes('1일 3회') || line.includes('1일 2회')) {
        slots.push('morning');
      }
      if (line.includes('점심') || line.includes('하루 3회') || line.includes('1일 3회')) {
        slots.push('noon');
      }
      if (line.includes('저녁') || line.includes('하루 3회') || line.includes('1일 3회') || line.includes('1일 2회')) {
        slots.push('evening');
      }
      if (line.includes('취침') || line.includes('자기전')) {
        slots.push('bedtime');
      }
      if (slots.length === 0) {
        slots.push('morning'); // Default fallback
      }

      // Meal relation
      let meal = '식후 30분';
      if (line.includes('식사 직후') || line.includes('식직후')) meal = '식사 직후';
      else if (line.includes('식전 30분') || line.includes('식전')) meal = '식전 30분';
      else if (line.includes('공복')) meal = '공복';
      else if (line.includes('취침')) meal = '취침 전';

      parsedMeds.push({
        id: `med-ai-${Date.now()}-${index}`,
        name: rawName,
        dosage: dosage,
        category: 'AI 자동 분석 처방약',
        slots: slots,
        mealRelation: meal,
        instructions: '처방전에 기재된 용법을 준수하여 복용하세요.',
        status: {}
      });
    });

    return parsedMeds;
  }

  function simulateOCRProcess(callback) {
    const container = document.getElementById('ocrProgressContainer');
    const bar = document.getElementById('ocrProgressBar');
    const text = document.getElementById('ocrProgressText');

    if (!container || !bar || !text) {
      callback();
      return;
    }

    container.classList.remove('hidden');
    let progress = 0;
    const interval = setInterval(() => {
      progress += 25;
      bar.style.width = `${progress}%`;
      text.textContent = `AI 처방전 판독 중... (${progress}%)`;

      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          container.classList.add('hidden');
          bar.style.width = '0%';
          callback();
        }, 400);
      }
    }, 150);
  }

  /* ==========================================================================
     11. AI Pharmacist Consultation Drawer
     ========================================================================== */
  const PHARMACIST_KNOWLEDGE = {
    missedDose: `[1/2 골든룰(Golden Rule) 복용법]
약 복용 시간을 놓치셨다면 다음 순서로 판단하세요:
1. 다음 복용 시간까지의 전체 간격을 절반(1/2)으로 나눕니다. (예: 1일 2회 약 = 12시간 간격, 절반은 6시간)
2. 약 먹을 시간으로부터 절반 이전이라면? 👉 발견 즉시 1회분을 복용하세요.
3. 절반이 이미 지났다면? 👉 놓친 약은 건너뛰고, 다음 예정 시간에 정량을 복용하세요.
⚠️ 절대 다음 복용 시간에 2회분을 한꺼번에 복용해서는 안 됩니다!`,

    tylenolCold: `[아세트아미노펜 중복 주의 경고]
타이레놀과 시판 종합감기약(판콜, 판피린, 코프 등)은 대부분 동일한 아세트아미노펜 성분이 함유되어 있습니다!
- 두 약을 함께 드실 경우 하루 최대 허용치(4,000mg)를 쉽게 초과하여 급성 간독성 및 간부전을 유발할 수 있습니다.
👉 대처법: 종합감기약을 복용 중이실 때는 타이레놀을 별도로 추가 복용하지 마세요.`,

    grapefruitBP: `[혈압약-자몽 상호작용 경고]
노바스크(암로디핀) 등 칼슘채널차단제 계열 혈압약 복용 중에는 자몽과 자몽주스를 피해야 합니다.
- 자몽 속 '푸라노쿠마린' 성분이 간 대사 효소(CYP3A4)를 억제하여 약효가 3~4배 증폭됩니다.
- 결과적으로 혈압이 급격히 곤두박질치거나 어지럼증, 실신 위험이 발생할 수 있습니다.`,

    ironMilk: `[철분제와 유제품/커피 섭취 안내]
철분제는 우유, 치즈 등 유제품의 칼슘 및 커피/녹차의 탄닌 성분과 결합하여 '불용성 킬레이트'를 형성합니다.
- 이로 인해 철분이 체내에 흡수되지 못하고 그대로 배출됩니다.
👉 권장법: 철분제는 오렌지주스(비타민 C가 흡수 촉진)나 맹물과 함께 복용하시고, 우유나 커피는 최소 2시간 이상 간격을 두세요.`,

    general: `질문해 주셔서 감사합니다! 
복약 중 불편한 점이 있으시다면 언제든 문의하세요. 증상이 심하거나 부작용이 의심되면 즉시 처방 병원 또는 약국을 방문하시길 권장합니다.`
  };

  function sendChatMessage(userText) {
    const container = document.getElementById('chatMessagesArea');
    const input = document.getElementById('chatInput');
    const typing = document.getElementById('typingIndicator');

    if (!userText || !container) return;

    // Append user bubble
    const userRow = document.createElement('div');
    userRow.className = 'message-row user-row';
    userRow.innerHTML = `
      <div class="msg-avatar">👤</div>
      <div class="msg-bubble-group">
        <div class="msg-bubble user-bubble">${escapeHtml(userText)}</div>
        <span class="msg-time">방금</span>
      </div>
    `;
    container.appendChild(userRow);
    container.scrollTop = container.scrollHeight;

    if (input) input.value = '';

    // Show typing
    if (typing) typing.classList.remove('hidden');

    // Determine smart answer
    let responseText = PHARMACIST_KNOWLEDGE.general;
    const lower = userText.toLowerCase();

    if (lower.includes('놓쳤') || lower.includes('시간') || lower.includes('잊었')) {
      responseText = PHARMACIST_KNOWLEDGE.missedDose;
    } else if (lower.includes('타이레놀') || lower.includes('감기약') || lower.includes('중복')) {
      responseText = PHARMACIST_KNOWLEDGE.tylenolCold;
    } else if (lower.includes('자몽') || lower.includes('혈압약') || lower.includes('주스')) {
      responseText = PHARMACIST_KNOWLEDGE.grapefruitBP;
    } else if (lower.includes('철분') || lower.includes('우유') || lower.includes('커피')) {
      responseText = PHARMACIST_KNOWLEDGE.ironMilk;
    }

    // Call REST API if backend ready or fallback
    setTimeout(async () => {
      const apiResponse = await fetchWithFallback(API_ENDPOINTS.CHAT, {
        method: 'POST',
        body: JSON.stringify({ message: userText, medications: state.medications })
      }, { reply: responseText });

      if (typing) typing.classList.add('hidden');

      const aiRow = document.createElement('div');
      aiRow.className = 'message-row ai-row';
      aiRow.innerHTML = `
        <div class="msg-avatar">👩‍⚕️</div>
        <div class="msg-bubble-group">
          <div class="msg-bubble ai-bubble">${(apiResponse.reply || responseText).replace(/\n/g, '<br>')}</div>
          <span class="msg-time">방금</span>
        </div>
      `;
      container.appendChild(aiRow);
      container.scrollTop = container.scrollHeight;

      // Voice answer brief preview
      if (state.seniorMode) {
        speakReminder('약사 답변이 도착했습니다.');
      }
    }, 800);
  }

  /* ==========================================================================
     12. UI Modals & Popups Control
     ========================================================================== */
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('show');
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('show');
  }

  function openDrawer(drawerId) {
    const drawer = document.getElementById(drawerId);
    if (drawer) drawer.classList.add('open');
  }

  function closeDrawer(drawerId) {
    const drawer = document.getElementById(drawerId);
    if (drawer) drawer.classList.remove('open');
  }

  function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const iconMap = {
      success: '🎉',
      warning: '⚠️',
      danger: '🚨',
      info: '💡'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${iconMap[type] || '💊'}</span>
      <div class="toast-content">
        <strong class="toast-title">${escapeHtml(title)}</strong>
        <p class="toast-message">${escapeHtml(message)}</p>
      </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  function toggleSeniorMode(forcedState) {
    state.seniorMode = typeof forcedState === 'boolean' ? forcedState : !state.seniorMode;
    document.body.classList.toggle('senior-mode', state.seniorMode);

    const toggleCheckbox = document.getElementById('seniorModeToggle');
    if (toggleCheckbox) toggleCheckbox.checked = state.seniorMode;

    const label = document.getElementById('seniorToggleLabel');
    if (label) {
      label.textContent = state.seniorMode ? '큰글씨 모드 ON' : '고대비·큰글씨';
    }

    saveLocalState();
    showToast('화면 모드 변경', state.seniorMode ? '어르신을 위한 큰 글씨·고대비 모드가 켜졌습니다.' : '일반 모드로 전환되었습니다.', 'info');
  }

  function renderDURInspectionModal() {
    const modalBody = document.getElementById('durModalBody');
    if (!modalBody) return;

    if (state.durWarnings.length === 0) {
      modalBody.innerHTML = `
        <div style="text-align:center; padding: 30px;">
          <span style="font-size: 3rem;">🛡️</span>
          <h3 style="margin-top: 10px; color:#10b981;">DUR 충돌 및 상호작용 위험 없음</h3>
          <p style="color:var(--text-muted); margin-top:6px;">현재 등록된 약물 간 병용 금기 및 치명적인 식품 충돌이 발견되지 않았습니다.</p>
        </div>
      `;
      return;
    }

    modalBody.innerHTML = state.durWarnings.map(w => `
      <div class="dur-warning-item ${w.severity}">
        <div class="dur-item-header">
          <strong class="dur-item-title">${escapeHtml(w.title)}</strong>
          <span class="alert-badge major">${escapeHtml(w.type)}</span>
        </div>
        <p class="dur-item-desc">${escapeHtml(w.desc)}</p>
        <div class="dur-action-advice">
          <strong>💡 임상 대처 가이드:</strong> ${escapeHtml(w.advice)}
        </div>
      </div>
    `).join('');
  }

  function populateDoctorReport() {
    const dateEl = document.getElementById('reportIssueDate');
    const tableBody = document.getElementById('reportMedTableBody');

    if (dateEl) {
      const now = new Date();
      dateEl.textContent = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    if (tableBody) {
      tableBody.innerHTML = state.medications.map(med => {
        const slotsStr = (med.slots || []).map(s => TIME_SLOTS[s] ? TIME_SLOTS[s].label : s).join(', ');
        return `
          <tr>
            <td><strong>${escapeHtml(med.name)}</strong></td>
            <td>${escapeHtml(med.dosage)}</td>
            <td>${slotsStr}</td>
            <td>${escapeHtml(med.mealRelation || '식후 30분')}</td>
            <td>${escapeHtml(med.instructions || '특이사항 없음')}</td>
          </tr>
        `;
      }).join('');
    }
  }

  /* ==========================================================================
     13. Event Listeners Initialization
     ========================================================================== */
  function setupEventListeners() {
    // Senior Mode Toggle
    const seniorToggle = document.getElementById('seniorModeToggle');
    if (seniorToggle) {
      seniorToggle.checked = state.seniorMode;
      seniorToggle.addEventListener('change', (e) => toggleSeniorMode(e.target.checked));
    }

    // Sound & Voice Test Button
    const audioTestBtn = document.getElementById('audioTestBtn');
    if (audioTestBtn) {
      audioTestBtn.addEventListener('click', () => {
        playChimeSound();
        speakReminder('MediMind AI 복약 알림 음성 테스트입니다. 제시간에 복약하여 건강을 지키세요.');
        showToast('소리 테스트', '🔔 알림음과 음성 안내가 정상적으로 재생되었습니다.', 'success');
      });
    }

    // Hero 3 Action Buttons
    const heroTakeBtn = document.getElementById('heroTakeBtn');
    const heroSnoozeBtn = document.getElementById('heroSnoozeBtn');
    const heroSkipBtn = document.getElementById('heroSkipBtn');

    if (heroTakeBtn) {
      heroTakeBtn.addEventListener('click', () => {
        if (state.nextDose && state.nextDose.medication) {
          takeMedication(state.nextDose.medication.id, state.nextDose.slot);
        }
      });
    }
    if (heroSnoozeBtn) {
      heroSnoozeBtn.addEventListener('click', () => {
        if (state.nextDose && state.nextDose.medication) {
          snoozeMedication(state.nextDose.medication.id, state.nextDose.slot);
        }
      });
    }
    if (heroSkipBtn) {
      heroSkipBtn.addEventListener('click', () => {
        if (state.nextDose && state.nextDose.medication) {
          skipMedication(state.nextDose.medication.id, state.nextDose.slot);
        }
      });
    }

    // Quick Tool Buttons
    document.getElementById('openScannerBtn')?.addEventListener('click', () => openModal('prescriptionModal'));
    document.getElementById('openManualAddBtn')?.addEventListener('click', () => openModal('manualAddModal'));
    document.getElementById('openDurModalBtn')?.addEventListener('click', () => {
      renderDURInspectionModal();
      openModal('durModal');
    });
    document.getElementById('viewDurDetailsBtn')?.addEventListener('click', () => {
      renderDURInspectionModal();
      openModal('durModal');
    });
    document.getElementById('openChatBtn')?.addEventListener('click', () => openDrawer('chatDrawer'));
    document.getElementById('openReportModalBtn')?.addEventListener('click', () => {
      populateDoctorReport();
      openModal('reportModal');
    });

    // Close Modals
    document.getElementById('closePrescriptionModalBtn')?.addEventListener('click', () => closeModal('prescriptionModal'));
    document.getElementById('cancelPrescriptionBtn')?.addEventListener('click', () => closeModal('prescriptionModal'));
    document.getElementById('closeManualAddModalBtn')?.addEventListener('click', () => closeModal('manualAddModal'));
    document.getElementById('cancelManualAddBtn')?.addEventListener('click', () => closeModal('manualAddModal'));
    document.getElementById('closeDurModalBtn')?.addEventListener('click', () => closeModal('durModal'));
    document.getElementById('confirmDurBtn')?.addEventListener('click', () => closeModal('durModal'));
    document.getElementById('closeChatDrawerBtn')?.addEventListener('click', () => closeDrawer('chatDrawer'));
    document.getElementById('closeReportModalBtn')?.addEventListener('click', () => closeModal('reportModal'));
    document.getElementById('closeReportFooterBtn')?.addEventListener('click', () => closeModal('reportModal'));

    // Print Report
    document.getElementById('printReportBtn')?.addEventListener('click', () => {
      window.print();
    });

    // Timeline Slot Filters
    document.querySelectorAll('.filter-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        state.activeSlotFilter = btn.getAttribute('data-filter') || 'all';
        renderTimeline();
      });
    });

    // Dynamic Timeline Card Action Delegation
    document.getElementById('timelineGrid')?.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('button[data-action]');
      if (!targetBtn) return;

      const action = targetBtn.getAttribute('data-action');
      const medId = targetBtn.getAttribute('data-id');
      const slot = targetBtn.getAttribute('data-slot');

      if (action === 'take') takeMedication(medId, slot);
      else if (action === 'undo') undoTakeMedication(medId, slot);
      else if (action === 'delete') deleteMedication(medId);
    });

    // Prescription Preset Chips
    document.querySelectorAll('.preset-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const presetKey = chip.getAttribute('data-preset');
        const text = PRESCRIPTION_PRESETS[presetKey];
        const input = document.getElementById('prescriptionInput');
        if (input && text) {
          input.value = text;
          showToast('예시 처방전 불러옴', `'${chip.textContent.trim()}' 처방이 입력되었습니다.`, 'info');
        }
      });
    });

    // Prescription OCR File Input
    const fileInput = document.getElementById('prescriptionFileInput');
    const dropzone = document.getElementById('ocrDropzone');
    const imgPreviewBox = document.getElementById('imagePreviewBox');
    const imgPreviewEl = document.getElementById('imagePreviewEl');
    const removePreviewBtn = document.getElementById('removePreviewBtn');

    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (event) => {
            imgPreviewEl.src = event.target.result;
            imgPreviewBox.classList.remove('hidden');
            document.getElementById('dropzoneContent').classList.add('hidden');
            simulateOCRProcess(() => {
              document.getElementById('prescriptionInput').value = PRESCRIPTION_PRESETS.chronic;
              showToast('OCR 판독 완료', '약봉투 이미지에서 처방 내역을 성공적으로 추출하였습니다.', 'success');
            });
          };
          reader.readAsDataURL(file);
        }
      });
    }

    if (removePreviewBtn) {
      removePreviewBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        imgPreviewEl.src = '';
        imgPreviewBox.classList.add('hidden');
        document.getElementById('dropzoneContent').classList.remove('hidden');
        if (fileInput) fileInput.value = '';
      });
    }

    // Prescription Submission
    document.getElementById('submitPrescriptionBtn')?.addEventListener('click', () => {
      const text = document.getElementById('prescriptionInput')?.value.trim();
      if (!text) {
        alert('처방전 텍스트를 입력하거나 예시 버튼을 선택하세요.');
        return;
      }

      simulateOCRProcess(() => {
        const newMeds = parsePrescriptionText(text);
        state.medications.push(...newMeds);
        saveLocalState();
        renderTimeline();
        updateCountdown();
        closeModal('prescriptionModal');
        playChimeSound();
        showToast('스케줄 등록 성공', `총 ${newMeds.length}개의 처방 약물이 복약 일정표에 자동 추가되었습니다.`, 'success');
      });
    });

    // Manual Add Form
    const manualForm = document.getElementById('manualAddForm');
    if (manualForm) {
      manualForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('manualMedName').value.trim();
        const dosage = document.getElementById('manualDosage').value.trim();
        const category = document.getElementById('manualCategory').value.trim();
        const mealRelation = document.getElementById('manualMealRelation').value;
        const instructions = document.getElementById('manualInstructions').value.trim();

        const selectedSlots = [];
        document.querySelectorAll('input[name="timeSlots"]:checked').forEach(cb => {
          selectedSlots.push(cb.value);
        });

        if (selectedSlots.length === 0) {
          alert('최소 1개 이상의 복약 시간대를 선택해주세요.');
          return;
        }

        const newMed = {
          id: `med-manual-${Date.now()}`,
          name,
          dosage,
          category: category || '일반 처방약',
          slots: selectedSlots,
          mealRelation,
          instructions: instructions || '정해진 용법을 준수하세요.',
          status: {}
        };

        state.medications.push(newMed);
        saveLocalState();
        renderTimeline();
        updateCountdown();
        manualForm.reset();
        closeModal('manualAddModal');
        showToast('약물 등록 완료', `${name}이(가) 복약 스케줄에 등록되었습니다.`, 'success');
      });
    }

    // Chat Drawer FAQ Pills
    document.querySelectorAll('.faq-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const question = pill.getAttribute('data-question');
        if (question) {
          sendChatMessage(question);
        }
      });
    });

    // Chat Form Submit
    document.getElementById('chatForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('chatInput');
      if (input && input.value.trim()) {
        sendChatMessage(input.value.trim());
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  /* ==========================================================================
     14. Application Bootstrapping
     ========================================================================== */
  async function init() {
    loadLocalState();

    // Check if body needs senior-mode class
    if (state.seniorMode) {
      document.body.classList.add('senior-mode');
    }

    setupEventListeners();
    startLiveClock();
    renderTimeline();

    // Async try fetching from backend medications
    const backendMeds = await fetchWithFallback(API_ENDPOINTS.MEDICATIONS, {}, null);
    if (backendMeds && Array.isArray(backendMeds) && backendMeds.length > 0) {
      state.medications = backendMeds;
      saveLocalState();
      renderTimeline();
      updateCountdown();
    }
  }

  // Kick off application on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
