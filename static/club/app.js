const tg = window.Telegram?.WebApp;
const state = {
  user: null,
  tasks: [],
  leaderboard: [],
  rankings: {},
  telegramUser: null,
  runWatchId: null,
  runTimerId: null,
};

const screenTitles = {
  home: "Bugungi hisobot",
  rating: "Reyting",
  history: "Kunlik tarix",
  profile: "Profil",
};

const taskDescriptions = {
  wake_early: "Kunni vaqtida boshladim",
  prayer: "Kunlik ibodat bajarildi",
  sport: "Tana uchun harakat qildim",
  book: "Kitob yoki foydali o'qish",
  goal_written: "Bugungi maqsad yozildi",
};

const $ = (id) => document.getElementById(id);

function showToast(text) {
  const toast = $("toast");
  toast.textContent = text;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2600);
}

function appUrl(path) {
  return `${window.location.origin}${path}`;
}

function storyImageUrl() {
  const url = appUrl(`/api/story-image/${encodeURIComponent(state.user.telegram_id)}.png?v=${Date.now()}`);
  return url.replace(/^http:\/\//, "https://");
}

async function copyText(text) {
  if (!text) return false;
  try {
    if (tg?.writeTextToClipboard) {
      await new Promise((resolve) => tg.writeTextToClipboard(text, resolve));
      return true;
    }
  } catch (error) {
    console.debug("Telegram clipboard failed", error);
  }
  try {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (error) {
    console.debug("Browser clipboard failed", error);
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch (error) {
    console.debug("execCommand copy failed", error);
  }
  textarea.remove();
  return copied;
}

function telegramPayload() {
  const params = new URLSearchParams(window.location.search);
  const unsafe = tg?.initDataUnsafe || {};
  const user = unsafe.user || {};
  const startParam = unsafe.start_param || params.get("start") || "";
  return {
    telegram_id: user.id || params.get("telegram_id") || "10001",
    first_name: user.first_name || params.get("first_name") || "Demo",
    username: user.username || "",
    referral_code: startParam,
  };
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw data;
  return data;
}

async function bootstrap() {
  tg?.ready();
  tg?.expand();
  state.telegramUser = telegramPayload();
  const data = await postJSON("/api/bootstrap/", state.telegramUser);
  state.user = data.user;
  state.tasks = data.tasks;
  state.leaderboard = data.leaderboard;
  renderAll();
}

function renderAll() {
  renderHeader();
  renderRegistration();
  renderTasks();
  renderAchievements();
  renderLeaderboard(state.leaderboard);
  renderProfile();
  renderHistory();
}

function renderHeader() {
  $("heroName").textContent = state.user.full_name ? `Salom, ${state.user.full_name}` : "Salom";
  $("xpValue").textContent = state.user.xp;
  $("streakValue").textContent = state.user.streak;
  $("rankValue").textContent = `#${state.user.rank}`;
  $("leagueValue").textContent = state.user.league;
  renderLeagueProgress();
}

function renderLeagueProgress() {
  const xp = state.user.xp || 0;
  const leagues = [
    {name: "Bronze", min: 0, next: 3001},
    {name: "Silver", min: 3001, next: 7001},
    {name: "Gold", min: 7001, next: 12001},
    {name: "Diamond", min: 12001, next: 18000},
    {name: "Legend", min: 18000, next: null},
  ];
  const current = leagues.find((item) => item.name === state.user.league) || leagues[0];
  if (!current.next) {
    $("leagueProgress").style.width = "100%";
    $("nextLeagueText").textContent = "Eng yuqori liga";
    return;
  }
  const width = Math.max(4, Math.min(100, ((xp - current.min) / (current.next - current.min)) * 100));
  $("leagueProgress").style.width = `${width}%`;
  $("nextLeagueText").textContent = `${current.next - xp} XP keyingi ligagacha`;
}

function renderRegistration() {
  const needsProfile = !state.user.age || !state.user.region;
  $("registerPanel").classList.toggle("hidden", !needsProfile);
  $("fullNameInput").value = state.user.full_name || "";
  $("ageInput").value = state.user.age || "";
  $("genderInput").value = state.user.gender || "other";
  $("regionInput").value = state.user.region || "";
  $("goalInput").value = state.user.main_goal || "discipline";
}

function runTrackerMarkup() {
  return `
    <div class="run-tracker" id="runTracker">
      <div class="run-head">
        <div>
          <span>GPS sport tekshiruvi</span>
          <strong id="runStatusText">Yugurish tasdiqlanmagan</strong>
          <small id="runRuleText">Kamida 800 m va 6 daqiqa yugurish kerak.</small>
        </div>
      </div>
      <div class="run-stats">
        <div><b id="runDistance">0 m</b><small>Masofa</small></div>
        <div><b id="runDuration">0:00</b><small>Vaqt</small></div>
        <div><b id="runSpeed">0 km/s</b><small>Tezlik</small></div>
      </div>
      <div class="run-actions">
        <button class="ghost-button compact" id="startRunBtn" type="button">Yugurishni boshlash</button>
        <button class="ghost-button compact hidden" id="finishRunBtn" type="button">Tugatish</button>
      </div>
    </div>
  `;
}

function renderTasks() {
  const list = $("taskList");
  list.innerHTML = "";
  const reported = state.user.reported_today;
  const selectedCodes = new Set(state.user.today_report?.tasks?.map((item) => item.code) || []);
  const sportVerified = state.user.run_today?.is_verified;

  $("reportStatus").textContent = reported ? "Topshirildi" : "Kutilmoqda";
  $("reportStatus").classList.toggle("done", reported);
  $("submitReportBtn").disabled = reported;
  $("submitReportBtn").textContent = reported ? "Bugun hisobot topshirilgan" : "Bugungi hisobotni topshirish";

  state.tasks.forEach((task) => {
    const needsGps = task.code === "sport" && !sportVerified && !reported;
    const checked = selectedCodes.has(task.code) || (task.code === "sport" && sportVerified && !reported);
    if (task.code === "sport") {
      const item = document.createElement("div");
      item.className = `task-item task-item-expanded ${needsGps ? "gps-required sport-trigger" : ""}`;
      item.innerHTML = `
        <label class="task-row">
          <input type="checkbox" value="${task.code}" ${reported || needsGps ? "disabled" : ""} ${checked ? "checked" : ""}>
          <span class="task-check">✓</span>
          <span class="task-copy">
            <strong>${task.label}</strong>
            <small>${needsGps ? "Sportni bosib GPS yugurishni boshlang" : "GPS orqali tasdiqlangan sport"}</small>
          </span>
          <span class="task-xp">+${task.xp}</span>
        </label>
        ${reported ? "" : runTrackerMarkup()}
      `;
      list.appendChild(item);
      return;
    }
    const label = document.createElement("label");
    label.className = `task-item ${needsGps ? "gps-required" : ""}`;
    label.innerHTML = `
      <input type="checkbox" value="${task.code}" ${reported || needsGps ? "disabled" : ""} ${checked ? "checked" : ""}>
      <span class="task-check">✓</span>
      <span class="task-copy">
        <strong>${task.label}</strong>
        <small>${needsGps ? "Avval GPS orqali yugurishni tasdiqlang" : taskDescriptions[task.code] || "Kunlik vazifa"}</small>
      </span>
      <span class="task-xp">+${task.xp}</span>
    `;
    list.appendChild(label);
  });

  renderRunTracker();
  updateSelectedProgress();
  list.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", updateSelectedProgress);
  });

  $("storyPanel").classList.toggle("hidden", !state.user.today_report);
  if (state.user.today_report) renderStory(state.user.today_report);
}

function formatDuration(seconds) {
  const safe = Math.max(0, Number(seconds || 0));
  const minutes = Math.floor(safe / 60);
  const rest = String(safe % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function renderRunTracker() {
  const run = state.user.run_today;
  const panel = $("runTracker");
  if (!panel) return;
  panel.classList.toggle("active", run?.status === "active");
  panel.classList.toggle("verified", run?.status === "verified");
  panel.classList.toggle("rejected", run?.status === "rejected");

  const distance = run?.distance_m || 0;
  let duration = run?.duration_s || 0;
  if (run?.status === "active" && run.started_at) {
    duration = Math.max(0, Math.floor((Date.now() - new Date(run.started_at).getTime()) / 1000));
  }
  $("runDistance").textContent = distance >= 1000 ? `${(distance / 1000).toFixed(2)} km` : `${distance} m`;
  $("runDuration").textContent = formatDuration(duration);
  $("runSpeed").textContent = `${run?.avg_speed_kmh || 0} km/s`;

  if (run?.status === "verified") {
    $("runStatusText").textContent = "Sport GPS orqali tasdiqlandi";
    $("runRuleText").textContent = "Endi Sport vazifasi avtomatik belgilandi.";
    $("startRunBtn").classList.add("hidden");
    $("finishRunBtn").classList.add("hidden");
  } else if (run?.status === "active") {
    $("runStatusText").textContent = state.runWatchId ? "Yugurish kuzatilmoqda" : "Yugurish sessiyasi aktiv";
    $("runRuleText").textContent = "Telefon lokatsiyasini yoqib, finishgacha yuguring.";
    $("startRunBtn").textContent = state.runWatchId ? "GPS kuzatyapti" : "Davom ettirish";
    $("startRunBtn").disabled = Boolean(state.runWatchId);
    $("startRunBtn").classList.remove("hidden");
    $("finishRunBtn").classList.remove("hidden");
  } else if (run?.status === "rejected") {
    $("runStatusText").textContent = "Yugurish tasdiqlanmadi";
    $("runRuleText").textContent = run.rejection_reason || "Masofa, vaqt yoki tezlik shartlari bajarilmadi.";
    $("startRunBtn").textContent = "Qayta boshlash";
    $("startRunBtn").disabled = false;
    $("startRunBtn").classList.remove("hidden");
    $("finishRunBtn").classList.add("hidden");
  } else {
    $("runStatusText").textContent = "Yugurish tasdiqlanmagan";
    $("runRuleText").textContent = "Sport XP olish uchun kamida 800 m va 6 daqiqa GPS yugurish kerak.";
    $("startRunBtn").textContent = "Yugurishni boshlash";
    $("startRunBtn").disabled = false;
    $("startRunBtn").classList.remove("hidden");
    $("finishRunBtn").classList.add("hidden");
  }
}

function updateSelectedProgress() {
  const checked = [...document.querySelectorAll("#taskList input:checked")];
  const xp = Math.min(checked.length * 20, 100);
  $("selectedTaskCount").textContent = `${checked.length}/5 vazifa`;
  $("selectedXp").textContent = `${xp} XP`;
  $("selectedXpBar").style.width = `${xp}%`;
}

function renderStory(report) {
  $("storyTasks").textContent = report.tasks.map((task) => task.label).join(" / ");
  $("storyXp").textContent = `+${report.xp_earned} XP`;
  $("storyMeta").textContent = `Streak: ${state.user.streak} kun | Reyting: #${state.user.rank}`;
}

function renderAchievements() {
  const list = $("achievementList");
  list.innerHTML = "";
  $("achievementCount").textContent = state.user.achievements.length;
  if (!state.user.achievements.length) {
    list.innerHTML = `<p>Hali badge ochilmagan. 7 kun streak bilan birinchi badge ochiladi.</p>`;
    return;
  }
  state.user.achievements.forEach((item) => {
    const row = document.createElement("div");
    row.className = "badge-item";
    row.innerHTML = `<strong>${item.name}</strong><span>${item.description}</span>`;
    list.appendChild(row);
  });
}

function renderLeaderboard(rows) {
  const list = $("leaderboard");
  list.innerHTML = "";
  if (!rows.length) {
    list.innerHTML = `<p>Hali reyting ma'lumoti yo'q.</p>`;
    return;
  }
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = `leader-row ${row.is_me ? "me" : ""}`;
    item.innerHTML = `
      <div class="leader-rank">${row.rank}</div>
      <div class="leader-user">
        <strong>${row.name}</strong>
        <span>${row.streak} kun streak</span>
      </div>
      <div class="leader-score">${row.xp} XP</div>
    `;
    list.appendChild(item);
  });
}

function renderProfile() {
  $("profileName").textContent = state.user.full_name;
  $("profileGoal").textContent = state.user.main_goal_label;
  $("avatarMark").textContent = (state.user.full_name || "Z").trim().slice(0, 1).toUpperCase();
  $("profileFullNameInput").value = state.user.full_name || "";
  $("profileAgeInput").value = state.user.age || "";
  $("profileGenderInput").value = state.user.gender || "other";
  $("profileRegionInput").value = state.user.region || "";
  $("profileGoalInput").value = state.user.main_goal || "discipline";
  const rows = [
    ["Ism", state.user.full_name],
    ["Viloyat", state.user.region || "Tanlanmagan"],
    ["XP", state.user.xp],
    ["Reyting", `#${state.user.rank}`],
    ["Streak", `${state.user.streak} kun`],
    ["League", state.user.league],
    ["Maqsad", state.user.main_goal_label],
    ["Qo'shilgan sana", state.user.joined_at],
  ];
  $("profileList").innerHTML = rows
    .map(([key, value]) => `<div class="profile-row"><span>${key}</span><strong>${value}</strong></div>`)
    .join("");
  $("referralText").textContent = state.user.referral_url;
}

function formatShortDate(date) {
  return date.toLocaleDateString("uz-UZ", {day: "2-digit", month: "short"});
}

function localIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function renderHistory() {
  const grid = $("calendarLite");
  const list = $("historyList");
  grid.innerHTML = "";
  list.innerHTML = "";

  const reportMap = new Map((state.user.history || []).map((report) => [report.date, report]));
  const today = new Date();
  const todayIso = localIsoDate(today);
  const joinedDate = state.user.joined_date || localIsoDate(today);
  const rows = [];
  let doneCount = 0;
  const currentWeekOffset = (today.getDay() + 6) % 7;
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - currentWeekOffset - 28);

  for (let index = 0; index < 35; index += 1) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + index);
    const iso = localIsoDate(date);
    const report = reportMap.get(iso);
    const isToday = iso === todayIso;
    const beforeJoin = iso < joinedDate;
    const futureDay = iso > todayIso;

    const cell = document.createElement("div");
    cell.className = "day-cell";
    if (report) {
      cell.classList.add("done");
      if (report.xp_earned >= 80) cell.classList.add("level-3");
      else if (report.xp_earned >= 40) cell.classList.add("level-2");
      doneCount += 1;
    } else if (beforeJoin || futureDay) {
      cell.classList.add("empty");
    } else if (isToday) {
      cell.classList.add("today");
    } else {
      cell.classList.add("missed");
    }
    const xpText = report ? `${report.xp_earned} XP` : isToday && !beforeJoin ? "Bugun" : "—";
    cell.innerHTML = `<span class="date-num">${date.getDate()}</span><span class="date-xp">${xpText}</span>`;
    cell.title = report
      ? `${formatShortDate(date)}: ${report.xp_earned} XP`
      : `${formatShortDate(date)}: hisobot yo'q`;
    grid.appendChild(cell);

    if (report || (isToday && !beforeJoin)) {
      rows.push({date, report, isToday});
    }
  }

  $("historyDoneCount").textContent = `${doneCount} kun`;

  rows.slice(-7).reverse().forEach(({date, report, isToday}) => {
    const item = document.createElement("div");
    item.className = `history-row ${report ? "done" : ""} ${isToday ? "today" : ""}`;
    const title = isToday ? "Bugun" : formatShortDate(date);
    const text = report ? report.tasks.map((task) => task.label).join(", ") : "Hali hisobot topshirilmagan";
    const xp = report ? `+${report.xp_earned} XP` : "0 XP";
    item.innerHTML = `
      <div>
        <strong>${title}</strong>
        <span>${text}</span>
      </div>
      <div class="history-xp">${xp}</div>
    `;
    list.appendChild(item);
  });

  if (!list.children.length) {
    list.innerHTML = `<div class="history-row"><div><strong>Hali tarix yo'q</strong><span>Birinchi hisobotdan keyin bu yerda kunlar ko'rinadi.</span></div><div class="history-xp">0 XP</div></div>`;
  }
}

async function saveProfile(source = "register") {
  const ids = source === "profile"
    ? {
        fullName: "profileFullNameInput",
        age: "profileAgeInput",
        gender: "profileGenderInput",
        region: "profileRegionInput",
        goal: "profileGoalInput",
      }
    : {
        fullName: "fullNameInput",
        age: "ageInput",
        gender: "genderInput",
        region: "regionInput",
        goal: "goalInput",
      };
  const payload = {
    telegram_id: state.user.telegram_id,
    full_name: $(ids.fullName).value,
    age: $(ids.age).value,
    gender: $(ids.gender).value,
    region: $(ids.region).value,
    main_goal: $(ids.goal).value,
  };
  const data = await postJSON("/api/register/", payload);
  state.user = data.user;
  renderAll();
  showToast("Profil saqlandi");
}

async function submitReport() {
  const tasks = [...document.querySelectorAll("#taskList input:checked")].map((item) => item.value);
  if (!tasks.length) {
    showToast("Kamida bitta vazifani tanlang");
    return;
  }
  try {
    const data = await postJSON("/api/report/", {telegram_id: state.user.telegram_id, tasks});
    state.user = data.user;
    state.leaderboard = data.leaderboard;
    renderAll();
    showToast(`Hisobot qabul qilindi: +${data.report.xp_earned} XP`);
  } catch (error) {
    if (error.user) {
      state.user = error.user;
      renderAll();
    }
    showToast("Bugungi hisobot allaqachon topshirilgan");
  }
}

function stopRunWatch() {
  if (state.runWatchId !== null && navigator.geolocation?.clearWatch) {
    navigator.geolocation.clearWatch(state.runWatchId);
  }
  state.runWatchId = null;
  if (state.runTimerId) clearInterval(state.runTimerId);
  state.runTimerId = null;
}

async function sendRunPoint(position) {
  const run = state.user.run_today;
  if (!run?.id) return;
  try {
    const data = await postJSON("/api/run/point/", {
      telegram_id: state.user.telegram_id,
      run_id: run.id,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy,
    });
    state.user.run_today = data.run;
    renderRunTracker();
  } catch (error) {
    console.debug("run point failed", error);
  }
}

async function startRun() {
  if (!navigator.geolocation) {
    showToast("Bu telefonda GPS topilmadi");
    return;
  }
  try {
    const data = await postJSON("/api/run/start/", {telegram_id: state.user.telegram_id});
    state.user.run_today = data.run;
    renderRunTracker();
    navigator.geolocation.getCurrentPosition(sendRunPoint, () => {
      showToast("GPS ruxsatini bering");
    }, {enableHighAccuracy: true, timeout: 12000, maximumAge: 0});
    state.runWatchId = navigator.geolocation.watchPosition(sendRunPoint, () => {
      showToast("GPS lokatsiya olinmadi");
    }, {enableHighAccuracy: true, timeout: 15000, maximumAge: 0});
    state.runTimerId = setInterval(renderRunTracker, 1000);
    renderRunTracker();
    showToast("Yugurish boshlandi");
  } catch (error) {
    console.debug("run start failed", error);
    showToast("Yugurishni boshlashda xatolik");
  }
}

async function finishRun() {
  const run = state.user.run_today;
  if (!run?.id) return;
  stopRunWatch();
  try {
    const data = await postJSON("/api/run/finish/", {
      telegram_id: state.user.telegram_id,
      run_id: run.id,
    });
    state.user = data.user;
    renderAll();
    showToast(data.run.is_verified ? "Sport GPS orqali tasdiqlandi" : "Yugurish shartlari bajarilmadi");
  } catch (error) {
    console.debug("run finish failed", error);
    showToast("Yugurishni tugatishda xatolik");
  }
}

async function loadRanking() {
  const response = await fetch(`/api/ranking/?telegram_id=${state.user.telegram_id}`);
  const data = await response.json();
  state.rankings = data;
  const activePeriod = document.querySelector(".rating-tab.active")?.dataset.period || "all";
  renderLeaderboard(data[activePeriod] || []);
}

document.addEventListener("click", (event) => {
  const tab = event.target.closest(".nav-item");
  if (!tab) return;
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  tab.classList.add("active");
  document.querySelectorAll(".tab-view").forEach((item) => item.classList.add("hidden"));
  $(`${tab.dataset.tab}Tab`).classList.remove("hidden");
  $("screenTitle").textContent = screenTitles[tab.dataset.tab] || "ZIYO";
  if (tab.dataset.tab === "rating") loadRanking();
});

$("saveProfileBtn").addEventListener("click", () => saveProfile("register"));
$("saveProfileDetailsBtn").addEventListener("click", () => saveProfile("profile"));
$("submitReportBtn").addEventListener("click", submitReport);
$("refreshBtn").addEventListener("click", bootstrap);
document.addEventListener("click", (event) => {
  if (event.target.closest("#startRunBtn")) startRun();
  if (event.target.closest("#finishRunBtn")) finishRun();
  const sportCard = event.target.closest(".sport-trigger");
  if (sportCard && !event.target.closest("#startRunBtn") && !event.target.closest("#finishRunBtn")) {
    startRun();
  }
});
$("ratingPeriod").addEventListener("click", (event) => {
  const button = event.target.closest(".rating-tab");
  if (!button) return;
  document.querySelectorAll(".rating-tab").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  renderLeaderboard(state.rankings[button.dataset.period] || state.leaderboard);
});
$("copyReferralBtn").addEventListener("click", async () => {
  const copied = await copyText(state.user.referral_url);
  showToast(copied ? "Referral link nusxalandi" : "Nusxa olish ishlamadi. Linkni bosib ushlab ko'chiring.");
});
$("shareStoryBtn").addEventListener("click", () => {
  const text = `ZIYO | INTIZOM CLUB\nBugun +${state.user.today_report?.xp_earned || 0} XP\nStreak: ${state.user.streak}`;
  if (!tg?.shareToStory) {
    showToast("Story ulashish faqat Telegram mobil ilovasida ishlaydi. Telegramni yangilang.");
    return;
  }
  try {
    tg.shareToStory(storyImageUrl(), {
      text,
      widget_link: {
        url: state.user.referral_url,
        name: "ZIYO botga qo'shilish",
      },
    });
  } catch (error) {
    console.debug("shareToStory failed", error);
    showToast("Story oynasi ochilmadi. Telegram mobil ilovasini yangilang.");
  }
});

bootstrap().catch(() => showToast("Ilovani yuklashda xatolik"));
