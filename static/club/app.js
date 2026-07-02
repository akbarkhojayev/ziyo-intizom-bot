const tg = window.Telegram?.WebApp;
const state = {
  user: null,
  tasks: [],
  leaderboard: [],
  rankings: {},
  telegramUser: null,
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

function renderTasks() {
  const list = $("taskList");
  list.innerHTML = "";
  const reported = state.user.reported_today;
  const selectedCodes = new Set(state.user.today_report?.tasks?.map((item) => item.code) || []);

  $("reportStatus").textContent = reported ? "Topshirildi" : "Kutilmoqda";
  $("reportStatus").classList.toggle("done", reported);
  $("submitReportBtn").disabled = reported;
  $("submitReportBtn").textContent = reported ? "Bugun hisobot topshirilgan" : "Bugungi hisobotni topshirish";

  state.tasks.forEach((task) => {
    const label = document.createElement("label");
    label.className = "task-item";
    label.innerHTML = `
      <input type="checkbox" value="${task.code}" ${reported ? "disabled" : ""} ${selectedCodes.has(task.code) ? "checked" : ""}>
      <span class="task-check">✓</span>
      <span class="task-copy">
        <strong>${task.label}</strong>
        <small>${taskDescriptions[task.code] || "Kunlik vazifa"}</small>
      </span>
      <span class="task-xp">+${task.xp}</span>
    `;
    list.appendChild(label);
  });

  updateSelectedProgress();
  list.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", updateSelectedProgress);
  });

  $("storyPanel").classList.toggle("hidden", !state.user.today_report);
  if (state.user.today_report) renderStory(state.user.today_report);
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
  const rows = [
    ["Ism", state.user.full_name],
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

async function saveProfile() {
  const payload = {
    telegram_id: state.user.telegram_id,
    full_name: $("fullNameInput").value,
    age: $("ageInput").value,
    gender: $("genderInput").value,
    region: $("regionInput").value,
    main_goal: $("goalInput").value,
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

$("saveProfileBtn").addEventListener("click", saveProfile);
$("submitReportBtn").addEventListener("click", submitReport);
$("refreshBtn").addEventListener("click", bootstrap);
$("ratingPeriod").addEventListener("click", (event) => {
  const button = event.target.closest(".rating-tab");
  if (!button) return;
  document.querySelectorAll(".rating-tab").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  renderLeaderboard(state.rankings[button.dataset.period] || state.leaderboard);
});
$("copyReferralBtn").addEventListener("click", async () => {
  await navigator.clipboard?.writeText(state.user.referral_url);
  showToast("Referral link nusxalandi");
});
$("shareStoryBtn").addEventListener("click", () => {
  const text = `ZIYO | INTIZOM CLUB\nBugun +${state.user.today_report?.xp_earned || 0} XP\nStreak: ${state.user.streak}`;
  tg?.openTelegramLink?.(`https://t.me/share/url?url=${encodeURIComponent(state.user.referral_url)}&text=${encodeURIComponent(text)}`);
  if (!tg) showToast(text);
});

bootstrap().catch(() => showToast("Ilovani yuklashda xatolik"));
