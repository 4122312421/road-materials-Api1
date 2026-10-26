"use strict";

// The browser collects input; the FastAPI server performs all money calculations.
(() => {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "roadmaterials.estimates.v1";
  const MAX_SAVED = 20;
  const state = {
    materials: [], pricing: null, selectedId: null, ready: false,
    pending: false, revision: 0, resultRevision: -1, result: null,
    saved: [], category: "all", deleteId: null, toastTimer: null,
  };
  const viewCopy = {
    calculator: ["Расчёт поставки", "Выберите материал, укажите количество и расстояние. Остальное посчитаем за вас.", "Калькулятор"],
    catalog: ["Каталог материалов", "Сравните материалы и выберите подходящий для вашей задачи.", "Каталог"],
    history: ["Сохранённые расчёты", "Вернитесь к прошлым расчётам, распечатайте их или пересчитайте по текущим ценам.", "Сохранённые"],
  };
  const meta = {
    1: { kind: "asphalt", category: "Асфальт", description: "Для устройства дорожного покрытия" },
    2: { kind: "aggregate", category: "Нерудные", description: "Для оснований и строительных работ" },
    3: { kind: "sand", category: "Нерудные", description: "Для подготовки оснований и смесей" },
  };
  const art = {
    asphalt: `<svg viewBox="0 0 300 154" fill="none" aria-hidden="true"><ellipse cx="151" cy="130" rx="104" ry="12" fill="#172B42" opacity=".08"/><path d="m43 89 111-51 105 48-109 54z" fill="#293545"/><path d="m43 73 111-51 105 48-109 54z" fill="#5B6876"/><path d="m43 73 107 51v16L43 89z" fill="#344252"/><path d="m150 124 109-54v16l-109 54z" fill="#243243"/><path d="m73 59 103 49M132 32l103 49" stroke="#F2F4F5" stroke-width="3"/><path d="m102 47 20 10m17 8 21 10m17 8 21 10" stroke="#FFB17D" stroke-width="4"/><g fill="#F5F7FA" opacity=".26"><circle cx="66" cy="77" r="1.5"/><circle cx="83" cy="85" r="1"/><circle cx="111" cy="78" r="1.5"/><circle cx="166" cy="108" r="1"/><circle cx="205" cy="70" r="1.5"/><circle cx="185" cy="54" r="1"/><circle cx="153" cy="43" r="1.5"/><circle cx="137" cy="105" r="1"/><circle cx="231" cy="80" r="1"/></g><path d="m60 111 90 43 94-46" stroke="#AEBBC9" stroke-dasharray="4 5"/></svg>`,
    aggregate: `<svg viewBox="0 0 300 154" fill="none" aria-hidden="true"><ellipse cx="151" cy="130" rx="104" ry="12" fill="#172B42" opacity=".09"/><path d="m101 53 43-30 46 26-9 49-58 7-32-24z" fill="#7D929A"/><path d="m101 53 43-30 10 42-31 40z" fill="#B3C0C2"/><path d="m154 65 36-16-9 49-58 7z" fill="#617981"/><path d="m172 83 45-27 35 31-11 40-51 10-29-25z" fill="#7B919A"/><path d="m172 83 45-27 6 46-33 35z" fill="#CAD2D1"/><path d="m223 102 29-15-11 40-51 10z" fill="#839CA3"/><path d="m48 91 38-34 48 26-4 44-54 10-34-21z" fill="#9DB0B4"/><path d="m48 91 38-34 10 46-20 34z" fill="#D0DAD8"/><path d="m96 103 38-20-4 44-54 10z" fill="#829A9F"/><path d="m124 107 24-25 34 22-4 27-33 14-26-18z" fill="#526F79"/><path d="m124 107 24-25 3 36-6 27-26-18z" fill="#A8BDBF"/><path d="m59 136 10-9 13 8-5 10-14-1zM231 132l10-5 10 9-7 8-13-3z" fill="#B5C6C7"/></svg>`,
    sand: `<svg viewBox="0 0 300 154" fill="none" aria-hidden="true"><ellipse cx="150" cy="132" rx="109" ry="12" fill="#A96C29" opacity=".1"/><path d="M37 124C60 113 76 86 96 78c29-12 33-47 56-47 26 0 36 39 58 55 19 13 34 29 53 38-52 24-176 26-226 0Z" fill="#E5C38A"/><path d="M152 31c26 0 36 39 58 55 19 13 34 29 53 38-25 11-71 18-105 18 37-36-31-62-6-111Z" fill="#D7AF70"/><path d="M73 119c21-14 34-25 48-43M89 128c28-17 33-31 49-52M170 116c-17-20-8-30-19-48M202 125c-18-21-8-28-27-47" stroke="#F4DDB6" stroke-width="2" stroke-linecap="round"/><g fill="#B98A4C"><circle cx="55" cy="127" r="1.6"/><circle cx="86" cy="136" r="1"/><circle cx="117" cy="122" r="1.4"/><circle cx="138" cy="133" r="1"/><circle cx="187" cy="130" r="1.3"/><circle cx="221" cy="123" r="1.5"/><circle cx="233" cy="131" r="1"/></g><path d="M249 49v31" stroke="#9D7040" stroke-width="2"/><path d="m250 49 17 6-17 7z" fill="#F46B31"/></svg>`,
  };
  const iconPaths = {
    arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    repeat: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.2 7a7 7 0 0 1 11.6-1L20 9M4 15l2.2 3A7 7 0 0 0 17.8 17"/>',
    print: '<path d="M7 8V3h10v5M7 17H4V8h16v9h-3M7 14h10v7H7zM17 11h.01"/>',
    trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
  };
  function icon(name) {
    return `<svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.arrow}</svg>`;
  }
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
  }
  function decimal(value, places = null) {
    // Keep server Decimal strings exact, including amounts above Number.MAX_SAFE_INTEGER.
    let [whole, fraction = ""] = String(value).split(".");
    whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
    fraction = places === null ? fraction.replace(/0+$/, "") : fraction.padEnd(places, "0").slice(0, places);
    return whole + (fraction ? "," + fraction : "");
  }
  function money(value, fixed = false) {
    const cents = String(value).split(".")[1] || "";
    return decimal(value, fixed || /[1-9]/.test(cents) ? 2 : 0) + "\u00a0₽";
  }
  function dateLabel(value) {
    return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  }
  function materialMeta(material) {
    return meta[material.id] || { kind: "aggregate", category: material.category === "asphalt" ? "Асфальт" : "Нерудные", description: "Материал для строительных работ" };
  }
  function toast(message) {
    clearTimeout(state.toastTimer);
    $("toast").textContent = message;
    $("toast").hidden = false;
    state.toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4500);
  }
  function serviceStatus(status, message) {
    $("service-status").dataset.state = status;
    $("service-status").innerHTML = '<span class="status-dot" aria-hidden="true"></span>' + escapeHtml(message);
  }
  function feedback(message = "") {
    $("calculation-feedback").textContent = message;
    $("calculation-feedback").hidden = !message;
  }
  function setView(view, updateUrl = true, focus = false) {
    if (!viewCopy[view]) view = "calculator";
    document.querySelectorAll("[data-panel]").forEach((panel) => { panel.hidden = panel.dataset.panel !== view; });
    document.querySelectorAll("nav [data-view]").forEach((button) => {
      const active = button.dataset.view === view;
      button.classList.toggle("is-active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const [title, description, crumb] = viewCopy[view];
    $("page-title").textContent = title;
    $("page-description").textContent = description;
    $("page-crumb").textContent = crumb;
    document.title = title + " — RoadMaterials";
    if (updateUrl && location.hash !== "#" + view) history.pushState(null, "", "#" + view);
    if (view === "history") renderHistory();
    if (focus) {
      $("page-title").setAttribute("tabindex", "-1");
      $("page-title").focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "instant" });
    }
  }
  function renderPicker() {
    $("material-picker").innerHTML = state.materials.map((material) => {
      const item = materialMeta(material);
      return `<label class="material-option"><input class="material-radio" type="radio" name="material" value="${material.id}" ${state.selectedId === material.id ? "checked" : ""}><div class="material-card"><div class="material-art art-${item.kind}">${art[item.kind]}<span class="selection-mark">${icon("check")}</span></div><div class="material-info"><span class="material-category">${item.category}</span><h3 class="material-name">${escapeHtml(material.name)}</h3><p class="material-description">${item.description}</p><div class="material-price">${money(material.price_per_ton)} <span>/ т</span></div></div></div></label>`;
    }).join("");
  }
  function renderCatalog() {
    const search = $("catalog-search").value.trim().toLocaleLowerCase("ru").replace(/[–—]/g, "-");
    const items = state.materials.filter((material) => {
      const info = materialMeta(material);
      return (state.category === "all" || material.category === state.category) &&
        `${material.name} ${info.category} ${info.description}`.toLocaleLowerCase("ru").replace(/[–—]/g, "-").includes(search);
    });
    $("catalog-count").textContent = String(items.length);
    $("catalog-empty").hidden = items.length !== 0;
    $("catalog-grid").innerHTML = items.map((material) => {
      const info = materialMeta(material);
      return `<article class="catalog-card"><div class="material-art art-${info.kind}">${art[info.kind]}</div><div class="catalog-card-body"><span class="material-category">${info.category}</span><h2 class="material-name">${escapeHtml(material.name)}</h2><p class="material-description">${info.description}</p><div class="material-price">${money(material.price_per_ton)} <span>/ т</span></div><button class="button button-primary button-full" type="button" data-choose-material="${material.id}">Рассчитать поставку ${icon("arrow")}</button></div></article>`;
    }).join("");
  }
  function updatePricing() {
    if (state.pricing) $("tariff-value").textContent = money(state.pricing.delivery_rate, true) + " / т·км";
  }
  async function requestJSON(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(url, { ...options, headers: { Accept: "application/json", ...(options.headers || {}) }, signal: controller.signal });
      let body;
      try { body = await response.json(); } catch { body = null; }
      if (!response.ok) {
        const error = new Error("Request failed");
        error.status = response.status;
        error.body = body;
        throw error;
      }
      if (body === null) throw new Error("Invalid server response");
      return body;
    } finally { clearTimeout(timeout); }
  }
  function isAmount(value) {
    return typeof value === "string" && /^\d{1,30}(?:\.\d{1,3})?$/.test(value);
  }
  function validResult(result) {
    return result && Number.isInteger(result.material_id) && result.material_id > 0 &&
      typeof result.material_name === "string" && result.material_name.length <= 200 && result.currency === "RUB" &&
      ["quantity_tons", "distance_km", "price_per_ton", "delivery_rate", "material_cost", "delivery_cost", "total_cost"].every((key) => isAmount(result[key]));
  }
  async function loadData() {
    state.ready = false;
    $("load-error").hidden = true;
    $("load-retry").disabled = true;
    serviceStatus("loading", "Проверяем сервис");
    updateButtons();
    try {
      const [materials, pricing] = await Promise.all([requestJSON("/materials"), requestJSON("/pricing")]);
      if (!Array.isArray(materials) || !materials.length || !materials.every((m) => Number.isInteger(m.id) && m.id > 0 && typeof m.name === "string" && isAmount(m.price_per_ton) && m.currency === "RUB") || !isAmount(pricing.delivery_rate) || pricing.currency !== "RUB") throw new Error("Invalid catalogue");
      state.materials = materials;
      state.pricing = pricing;
      if (!materials.some((m) => m.id === state.selectedId)) state.selectedId = materials[0].id;
      state.ready = true;
      renderPicker();
      renderCatalog();
      updatePricing();
      serviceStatus("ready", "Готов к расчёту");
    } catch {
      $("load-error-text").textContent = "Не удалось загрузить материалы и тариф. Проверьте, что приложение запущено, и попробуйте ещё раз.";
      $("load-error").hidden = false;
      serviceStatus("error", "Сервис недоступен");
    } finally {
      $("load-retry").disabled = false;
      updateButtons();
    }
  }
  function isStale() { return state.result && state.resultRevision !== state.revision; }
  function updateButtons() {
    $("calculate-button").disabled = !state.ready || state.pending;
    $("clear-button").disabled = state.pending;
    $("calculate-label").textContent = state.pending ? "Рассчитываем…" : "Рассчитать стоимость";
    $("calculate-button").setAttribute("aria-busy", String(state.pending));
    $("example-button").disabled = !state.ready || state.pending;
    const inactive = !state.result || isStale() || state.pending;
    const saved = state.result && state.saved.some((item) => item.id === state.result.id);
    $("save-button").disabled = inactive || saved;
    $("save-button").textContent = saved ? "Расчёт сохранён" : "Сохранить расчёт";
    $("copy-button").disabled = inactive;
    $("print-button").disabled = inactive;
    $("result-stale").hidden = !isStale();
    $("result-panel").classList.toggle("is-stale", Boolean(isStale()));
  }
  function markChanged() {
    state.revision += 1;
    feedback();
    updateButtons();
    document.querySelectorAll("[data-quantity]").forEach((b) => b.classList.toggle("is-active", b.dataset.quantity === $("quantity_tons").value));
    document.querySelectorAll("[data-distance]").forEach((b) => b.classList.toggle("is-active", b.dataset.distance === $("distance_km").value));
  }
  function fieldError(field, message) {
    const kind = field === "quantity_tons" ? "quantity" : "distance";
    $(kind + "-error").textContent = message;
    $(kind + "-error").hidden = !message;
    $(field).setAttribute("aria-invalid", String(Boolean(message)));
  }
  function validateField(field) {
    const value = $(field).value.trim().replace(/[\s\u00a0\u202f]/g, "").replace(",", ".");
    let message = "";
    if (!value) message = field === "quantity_tons" ? "Укажите количество материала." : "Укажите расстояние доставки.";
    else if (!/^\d+(?:\.\d+)?$/.test(value)) message = "Введите положительное число, например 30 или 2,5.";
    else if (Number(value) <= 0) message = "Значение должно быть больше нуля.";
    else if ((value.split(".")[1] || "").length > 3) message = "Используйте не больше трёх знаков после запятой.";
    else if (Number(value) > 9999999.999) message = "Максимальное значение — 9 999 999,999.";
    fieldError(field, message);
    if (message) return null;
    // Canonical decimal text retains precision when sent to the server.
    return value.replace(/^0+(?=\d)/, "");
  }
  function renderResult() {
    if (!state.result) {
      $("result-empty").hidden = false;
      $("result-content").hidden = true;
      updateButtons();
      return;
    }
    const { result, projectName, createdAt } = state.result;
    $("result-empty").hidden = true;
    $("result-content").hidden = false;
    $("total-cost").textContent = money(result.total_cost);
    $("result-material").textContent = result.material_name;
    $("result-quantity").textContent = decimal(result.quantity_tons) + " т";
    $("result-distance").textContent = decimal(result.distance_km) + " км";
    $("result-rate").textContent = money(result.delivery_rate, true) + " / т·км";
    $("material-cost").textContent = money(result.material_cost, true);
    $("delivery-cost").textContent = money(result.delivery_cost, true);
    $("result-project").textContent = projectName;
    $("result-project").hidden = !projectName;
    $("result-date").textContent = dateLabel(createdAt);
    $("result-formula").textContent = `Материал: ${decimal(result.quantity_tons)} т × ${money(result.price_per_ton)} / т. Доставка: ${decimal(result.quantity_tons)} т × ${decimal(result.distance_km)} км × ${money(result.delivery_rate, true)} / т·км.`;
    updateButtons();
  }
  async function calculate() {
    if (!state.ready || state.pending) return;
    const quantity = validateField("quantity_tons");
    const distance = validateField("distance_km");
    if (quantity === null || distance === null) {
      $(quantity === null ? "quantity_tons" : "distance_km").focus();
      return;
    }
    if (!state.materials.some((m) => m.id === state.selectedId)) {
      feedback("Выберите материал из каталога.");
      return;
    }
    const revision = state.revision;
    const projectName = $("project-name").value.trim().slice(0, 80);
    state.pending = true;
    feedback();
    updateButtons();
    try {
      const result = await requestJSON("/delivery/calculate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ material_id: state.selectedId, quantity_tons: quantity, distance_km: distance }),
      });
      if (!validResult(result)) throw new Error("Invalid calculation response");
      state.result = {
        id: typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        createdAt: new Date().toISOString(), projectName, result,
      };
      state.resultRevision = revision;
      state.pricing.delivery_rate = result.delivery_rate;
      updatePricing();
      renderResult();
      serviceStatus("ready", "Готов к расчёту");
      if (!isStale()) {
        toast("Расчёт готов. Его можно сохранить или распечатать.");
        if (window.matchMedia("(max-width: 1050px)").matches) $("result-panel").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
      }
    } catch (error) {
      if (error.status === 422) {
        feedback("Проверьте параметры: количество и расстояние должны быть положительными числами с точностью до трёх знаков после запятой.");
      } else if (error.status === 404) {
        feedback("Этот материал больше не найден в каталоге. Обновите страницу и выберите материал снова.");
      } else {
        feedback("Не удалось выполнить расчёт. Проверьте, что приложение запущено, и нажмите «Рассчитать стоимость» ещё раз.");
        serviceStatus("error", "Нет ответа от сервиса");
      }
    } finally {
      state.pending = false;
      updateButtons();
    }
  }
  function isSnapshot(item) {
    return item && typeof item.id === "string" && /^[\w-]{1,80}$/.test(item.id) &&
      typeof item.createdAt === "string" && Number.isFinite(Date.parse(item.createdAt)) &&
      typeof item.projectName === "string" && item.projectName.length <= 80 && validResult(item.result);
  }
  function readSaved() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const items = JSON.parse(raw);
      if (!Array.isArray(items)) throw new Error("Invalid saved data");
      return items.filter(isSnapshot).slice(0, MAX_SAVED);
    } catch {
      toast("Не удалось прочитать сохранённые расчёты. Проверить стоимость всё равно можно.");
      return [];
    }
  }
  function writeSaved(items) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
      state.saved = items;
      renderHistory();
      updateButtons();
      return true;
    } catch {
      toast("Браузер не разрешил сохранение. Можно скопировать результат или сохранить его в PDF.");
      return false;
    }
  }
  function renderHistory() {
    $("history-count").textContent = String(state.saved.length);
    $("history-empty").hidden = state.saved.length !== 0;
    $("history-list").innerHTML = state.saved.map((item) => {
      const result = item.result;
      return `<article class="history-card"><div class="history-main"><div class="history-topline"><h2>${escapeHtml(item.projectName || "Расчёт поставки")}</h2><time datetime="${escapeHtml(item.createdAt)}">${dateLabel(item.createdAt)}</time></div><p class="history-material">${escapeHtml(result.material_name)}</p><div class="history-meta"><span>${decimal(result.quantity_tons)} т</span><span>${decimal(result.distance_km)} км</span><span>Тариф ${money(result.delivery_rate, true)} / т·км</span></div><div class="history-total">${money(result.total_cost)}</div></div><div class="history-actions"><button class="button button-secondary button-small" data-repeat="${escapeHtml(item.id)}" type="button">${icon("repeat")} Повторить</button><button class="button button-secondary button-small" data-print-saved="${escapeHtml(item.id)}" type="button">${icon("print")} Печать</button><button class="button button-quiet button-small" data-delete="${escapeHtml(item.id)}" type="button">${icon("trash")} Удалить</button></div></article>`;
    }).join("");
  }
  function summaryText(snapshot) {
    const { result: r, projectName, createdAt } = snapshot;
    return ["RoadMaterials · Расчёт стоимости поставки", projectName ? `Объект: ${projectName}` : "", `Дата: ${dateLabel(createdAt)}`, `Материал: ${r.material_name}`, `Количество: ${decimal(r.quantity_tons)} т`, `Расстояние: ${decimal(r.distance_km)} км`, `Цена материала: ${money(r.price_per_ton, true)} / т`, `Тариф доставки: ${money(r.delivery_rate, true)} / т·км`, `Материал: ${money(r.material_cost, true)}`, `Доставка: ${money(r.delivery_cost, true)}`, `ИТОГО: ${money(r.total_cost, true)}`, "Демонстрационные цены. Расчёт не является коммерческим предложением."].filter(Boolean).join("\n");
  }
  async function copyResult() {
    if (!state.result || isStale() || state.pending) return;
    const text = summaryText(state.result);
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      toast("Расчёт скопирован. Можно вставить его в сообщение или документ.");
    } catch {
      const field = document.createElement("textarea");
      field.value = text;
      field.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.append(field);
      field.select();
      let copied = false;
      try { copied = document.execCommand("copy"); } catch { /* Report unavailable access below. */ }
      field.remove();
      $("copy-button").focus();
      toast(copied ? "Расчёт скопирован." : "Копирование недоступно в этом браузере. Используйте «Печать / PDF».");
    }
  }
  function printSnapshot(snapshot) {
    const { result: r, projectName, createdAt } = snapshot;
    $("print-sheet").innerHTML = `<header class="print-header"><strong>RoadMaterials</strong><span>Материалы и доставка</span></header><h1>Расчёт стоимости поставки</h1><p>${dateLabel(createdAt)}</p>${projectName ? `<p><strong>Объект:</strong> ${escapeHtml(projectName)}</p>` : ""}<table class="print-table"><tbody><tr><th>Материал</th><td>${escapeHtml(r.material_name)}</td></tr><tr><th>Количество</th><td>${decimal(r.quantity_tons)} т</td></tr><tr><th>Расстояние доставки</th><td>${decimal(r.distance_km)} км</td></tr><tr><th>Цена за тонну</th><td>${money(r.price_per_ton, true)}</td></tr><tr><th>Тариф доставки</th><td>${money(r.delivery_rate, true)} / т·км</td></tr><tr><th>Стоимость материала</th><td>${money(r.material_cost, true)}</td></tr><tr><th>Стоимость доставки</th><td>${money(r.delivery_cost, true)}</td></tr></tbody></table><div class="print-total"><span>Итого</span><strong>${money(r.total_cost, true)}</strong></div><p class="print-note">Материал: ${decimal(r.quantity_tons)} т × ${money(r.price_per_ton, true)} / т.<br>Доставка: ${decimal(r.quantity_tons)} т × ${decimal(r.distance_km)} км × ${money(r.delivery_rate, true)} / т·км.</p><p class="print-note">Демонстрационные цены. Расчёт не является коммерческим предложением. Обратный пробег, простои и дополнительные услуги не учитываются.</p>`;
    window.print();
  }
  function resetForm() {
    $("estimate-form").reset();
    state.selectedId = state.materials[0]?.id || null;
    state.result = null;
    state.revision += 1;
    renderPicker();
    fieldError("quantity_tons", "");
    fieldError("distance_km", "");
    feedback();
    markChanged();
    renderResult();
    $("quantity_tons").focus();
  }
  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-view]");
    if (nav) { event.preventDefault(); setView(nav.dataset.view, true, true); }
    const quick = event.target.closest("[data-quantity], [data-distance]");
    if (quick) {
      const field = quick.hasAttribute("data-quantity") ? "quantity_tons" : "distance_km";
      $(field).value = quick.dataset.quantity || quick.dataset.distance;
      fieldError(field, ""); markChanged();
    }
    const filter = event.target.closest("[data-category]");
    if (filter) {
      state.category = filter.dataset.category;
      document.querySelectorAll("[data-category]").forEach((b) => { b.classList.toggle("is-active", b === filter); b.setAttribute("aria-pressed", String(b === filter)); });
      renderCatalog();
    }
    const select = event.target.closest("[data-choose-material]");
    if (select) {
      state.selectedId = Number(select.dataset.chooseMaterial);
      renderPicker(); markChanged(); setView("calculator", true, true); $("quantity_tons").focus();
    }
    const repeat = event.target.closest("[data-repeat]");
    if (repeat) {
      if (state.pending) { toast("Подождите завершения текущего расчёта."); return; }
      const item = state.saved.find((s) => s.id === repeat.dataset.repeat);
      if (item && state.ready && state.materials.some((m) => m.id === item.result.material_id)) {
        state.selectedId = item.result.material_id;
        $("quantity_tons").value = decimal(item.result.quantity_tons);
        $("distance_km").value = decimal(item.result.distance_km);
        $("project-name").value = item.projectName;
        renderPicker(); markChanged(); setView("calculator", true, true); calculate();
      } else toast("Материал недоступен. Обновите страницу, чтобы загрузить каталог.");
    }
    const print = event.target.closest("[data-print-saved]");
    if (print) { const item = state.saved.find((s) => s.id === print.dataset.printSaved); if (item) printSnapshot(item); }
    const remove = event.target.closest("[data-delete]");
    if (remove) { state.deleteId = remove.dataset.delete; $("delete-dialog").showModal(); }
    const close = event.target.closest("[data-close-dialog]");
    if (close) close.closest("dialog")?.close();
  });
  $("estimate-form").addEventListener("submit", (event) => { event.preventDefault(); calculate(); });
  $("material-picker").addEventListener("change", (event) => {
    if (event.target.matches("input[name=material]")) { state.selectedId = Number(event.target.value); markChanged(); }
  });
  ["quantity_tons", "distance_km"].forEach((field) => {
    $(field).addEventListener("input", () => { fieldError(field, ""); markChanged(); });
    $(field).addEventListener("blur", () => { if ($(field).value.trim()) validateField(field); });
  });
  $("project-name").addEventListener("input", markChanged);
  $("catalog-search").addEventListener("input", renderCatalog);
  $("clear-button").addEventListener("click", resetForm);
  $("example-button").addEventListener("click", () => {
    state.selectedId = state.materials.some((m) => m.id === 1) ? 1 : state.materials[0].id;
    $("quantity_tons").value = "30";
    $("distance_km").value = "50";
    $("project-name").value = "";
    renderPicker(); markChanged(); calculate();
  });
  $("save-button").addEventListener("click", () => {
    if (!state.result || isStale() || state.pending || state.saved.some((item) => item.id === state.result.id)) return;
    const items = [state.result, ...state.saved].slice(0, MAX_SAVED);
    if (writeSaved(items)) toast("Расчёт сохранён в этом браузере. Он доступен в разделе «Мои расчёты».");
  });
  $("copy-button").addEventListener("click", copyResult);
  $("print-button").addEventListener("click", () => { if (state.result && !isStale() && !state.pending) printSnapshot(state.result); });
  $("help-button").addEventListener("click", () => $("help-dialog").showModal());
  $("load-retry").addEventListener("click", loadData);
  $("cancel-delete").addEventListener("click", () => $("delete-dialog").close());
  $("confirm-delete").addEventListener("click", () => {
    if (state.deleteId && writeSaved(state.saved.filter((item) => item.id !== state.deleteId))) toast("Сохранённый расчёт удалён.");
    state.deleteId = null;
    $("delete-dialog").close();
  });
  window.addEventListener("popstate", () => setView(location.hash.slice(1), false));
  window.addEventListener("storage", (event) => { if (event.key === STORAGE_KEY || event.key === null) { state.saved = readSaved(); renderHistory(); updateButtons(); } });
  state.saved = readSaved();
  renderHistory();
  setView(location.hash.slice(1), false);
  loadData();
})();
