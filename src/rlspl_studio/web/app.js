"use strict";

const state = {
  catalog: null,
  mode: "product",
  studyManifest: null,
  splTrace: null,
  monitorExecutions: [],
  monitorCounts: { products: 0, studies: 0 },
  monitorExecution: null,
  monitorExecutionId: null,
  monitorRunId: null,
  monitorHpoRunId: null,
  monitorHpo: null,
  monitorRefreshing: false,
};
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function request(path, payload) {
  const response = await fetch(path, {
    method: payload === undefined ? "GET" : "POST",
    cache: payload === undefined ? "no-store" : "default",
    headers: payload === undefined ? {} : { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const body = await response.json();
  return { response, body };
}

function selectedValues(container) {
  return $$(`#${container} input:checked`).map((input) => input.value);
}

function parseSeeds(value, label = "seeds") {
  const tokens = value.split(",").map((item) => item.trim()).filter(Boolean);
  const invalid = tokens.find((item) => !/^[+-]?\d+$/.test(item));
  if (invalid !== undefined) throw new Error(`${label} contains an invalid integer: ${invalid}`);
  const seeds = tokens.map(Number);
  if (seeds.some((seed) => !Number.isSafeInteger(seed))) {
    throw new Error(`${label} must contain safe integers`);
  }
  if (new Set(seeds).size !== seeds.length) {
    throw new Error(`${label} must not contain duplicates`);
  }
  return seeds;
}

function coerce(value, type) {
  if (type === "integer") return Number.parseInt(value, 10);
  if (type === "float") return Number.parseFloat(value);
  if (type === "boolean") return value === "true";
  return value;
}

function theorySection(name) {
  return state.catalog?.theory?.[name] || {};
}

function sourceMarkup(sourceIds = []) {
  const sources = theorySection("sources");
  const links = sourceIds.map((id) => sources[id]).filter(Boolean).map((source) => `
    <a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">
      ${escapeHtml(source.authors)} (${escapeHtml(source.year)}) · ${escapeHtml(source.title)}
    </a>`);
  return links.length
    ? `<p class="source-heading">Learn from the sources</p><div class="source-list">${links.join("")}</div>`
    : "";
}

function environmentIllustration(kind) {
  const common = 'viewBox="0 0 360 150" role="img" class="theory-visual"';
  if (kind === "mountain_car") return `<svg ${common} aria-label="Car building momentum between two hills">
    <path class="visual-ground" d="M0 52 Q85 154 178 96 Q266 22 360 62 V150 H0Z"/>
    <path class="visual-line" d="M0 52 Q85 154 178 96 Q266 22 360 62"/>
    <g transform="translate(108 111) rotate(-13)"><rect class="visual-object" x="-21" y="-12" width="42" height="15" rx="5"/><circle class="visual-wheel" cx="-13" cy="5" r="6"/><circle class="visual-wheel" cx="14" cy="5" r="6"/></g>
    <path class="visual-accent" d="M305 39V83M305 40h33l-8 12h-25"/><path class="visual-arrow" d="M75 92h36m-28-9-9 9 9 9"/>
    <text x="16" y="25">gain momentum</text><text x="284" y="104">goal</text>
  </svg>`;
  if (kind === "mountain_car_continuous") return `<svg ${common} aria-label="Car controlling continuous force between two hills">
    <path class="visual-ground" d="M0 52 Q85 154 178 96 Q266 22 360 62 V150 H0Z"/>
    <path class="visual-line" d="M0 52 Q85 154 178 96 Q266 22 360 62"/>
    <g transform="translate(108 111) rotate(-13)"><rect class="visual-object" x="-21" y="-12" width="42" height="15" rx="5"/><circle class="visual-wheel" cx="-13" cy="5" r="6"/><circle class="visual-wheel" cx="14" cy="5" r="6"/></g>
    <path class="visual-accent" d="M305 39V83M305 40h33l-8 12h-25"/><path class="visual-arrow" d="M60 86h52m-42-10-11 10 11 10M155 109h-31m22-8 10 8-10 8"/>
    <text x="16" y="25">force −1 … +1</text><text x="284" y="104">goal</text>
  </svg>`;
  if (kind === "acrobot") return `<svg ${common} aria-label="Two-link Acrobot swinging toward a target height">
    <path class="visual-accent" d="M36 39h288"/><text x="248" y="29">target height</text>
    <g transform="translate(174 126)"><circle class="visual-joint" cx="0" cy="0" r="7"/><path class="visual-limb" d="M0 0L-42-50L-7-101"/><circle class="visual-joint" cx="-42" cy="-50" r="7"/><circle class="visual-object" cx="-7" cy="-101" r="6"/></g>
    <path class="visual-arrow" d="M117 85c-19-21-13-48 7-61m-16 4 17-5-2 17"/>
    <text x="191" y="105">one actuated joint</text><text x="18" y="139">build energy to swing upward</text>
  </svg>`;
  if (kind === "pendulum") return `<svg ${common} aria-label="Pendulum swinging upright under continuous torque">
    <path class="visual-line" d="M125 34h110"/><path class="visual-line" d="M180 34L132 113"/><circle class="visual-joint" cx="180" cy="34" r="7"/><circle class="visual-object" cx="132" cy="113" r="10"/>
    <path class="visual-arrow" d="M208 69c22 11 28 36 15 57m13-5-14 7-5-15"/>
    <path class="visual-accent" d="M180 34V115" stroke-dasharray="5 7"/><text x="20" y="27">continuous torque −2 … +2</text><text x="245" y="117">swing up, then balance</text>
  </svg>`;
  if (kind === "lunar_lander") return `<svg ${common} aria-label="Lunar lander descending toward a landing pad">
    <circle class="visual-moon" cx="300" cy="32" r="17"/><path class="visual-ground" d="M0 125L70 111 126 126 195 110 255 124 360 105V150H0Z"/>
    <path class="visual-line" d="M0 125L70 111 126 126 195 110 255 124 360 105"/><path class="visual-accent" d="M143 114h75M151 114v-23M210 114V91"/>
    <g transform="translate(180 54)"><path class="visual-object" d="M-17 11L-10-15H10L17 11 7 19H-7Z"/><path class="visual-line" d="M-10 15l-15 22m35-22 15 22M-30 37h12m36 0h12"/><path class="visual-flame" d="M-8 20L0 42 8 20Z"/></g>
    <path class="visual-arrow" d="M180 12v20m-8-8 8 9 8-9"/><text x="18" y="26">position · speed · tilt</text><text x="153" y="139">landing zone</text>
  </svg>`;
  if (kind === "bipedal_walker") return `<svg ${common} aria-label="Two-legged walker moving across terrain">
    <path class="visual-ground" d="M0 125L88 117 158 124 229 108 360 119V150H0Z"/><path class="visual-line" d="M0 125L88 117 158 124 229 108 360 119"/>
    <g transform="translate(166 48)"><rect class="visual-object" x="-29" y="0" width="58" height="24" rx="8"/><circle class="visual-joint" cx="-18" cy="28" r="5"/><circle class="visual-joint" cx="18" cy="28" r="5"/><path class="visual-limb" d="M-18 28l-14 31 18 25M18 28l16 29-8 28"/><circle class="visual-joint" cx="-32" cy="59" r="4"/><circle class="visual-joint" cx="34" cy="57" r="4"/><path class="visual-limb" d="M-22 84h19M20 85h20"/></g>
    <path class="visual-arrow" d="M242 63h57m-10-10 11 10-11 10"/><text x="14" y="25">4 motor commands</text><text x="250" y="91">forward</text>
  </svg>`;
  if (kind === "cart_pole") return `<svg ${common} aria-label="Cart balancing an upright pole">
    <path class="visual-ground" d="M0 123H360V150H0Z"/><path class="visual-line" d="M18 122h324"/>
    <g transform="translate(180 102)"><rect class="visual-object" x="-39" y="-17" width="78" height="24" rx="4"/><circle class="visual-wheel" cx="-23" cy="12" r="8"/><circle class="visual-wheel" cx="23" cy="12" r="8"/><circle class="visual-joint" cx="0" cy="-17" r="6"/><path class="visual-limb" d="M0-17L-18-91"/></g>
    <path class="visual-arrow" d="M83 81h46m-36-9-10 9 10 9M277 81h-46m36-9 10 9-10 9"/><text x="126" y="25">keep angle small</text>
  </svg>`;
  return `<svg ${common} aria-label="Agent and environment interaction loop">
    <rect class="visual-object" x="35" y="49" width="105" height="49" rx="10"/><rect class="visual-object" x="220" y="49" width="105" height="49" rx="10"/>
    <text x="70" y="78">agent</text><text x="235" y="78">environment</text><path class="visual-arrow" d="M143 62h70l-10-9m10 9-10 9M217 88h-70l10-9m-10 9 10 9"/><text x="161" y="47">action</text><text x="151" y="111">state, reward</text>
  </svg>`;
}

function algorithmIllustration(kind) {
  const common = 'viewBox="0 0 520 128" role="img" class="theory-visual algorithm-visual"';
  const box = (x, width, title, detail) => `<g><rect class="visual-object" x="${x}" y="35" width="${width}" height="56" rx="9"/><text class="visual-title" x="${x + width / 2}" y="59" text-anchor="middle">${title}</text><text class="visual-small" x="${x + width / 2}" y="76" text-anchor="middle">${detail}</text></g>`;
  const arrow = (x1, x2, label) => `<path class="visual-arrow" d="M${x1} 63H${x2 - 7}l-8-7m8 7-8 7"/><text class="visual-small" x="${(x1 + x2) / 2}" y="49" text-anchor="middle">${label}</text>`;
  if (kind === "q_table") return `<svg ${common} aria-label="Q-learning table update flow">${box(18, 112, "discretizer", "vector → cell")}${arrow(133, 194, "state")}${box(194, 126, "Q table", "values by action")}${arrow(323, 384, "expose")}${box(384, 118, "Q scores", "interface")}</svg>`;
  if (kind === "dqn") return `<svg ${common} aria-label="DQN replay and target-network architecture">${box(12, 103, "replay", "transitions")}${arrow(118, 166, "batch")}${box(166, 111, "Q network", "online")}${arrow(280, 329, "copy")}${box(329, 105, "target Q", "delayed")}${arrow(437, 502, "loss")}</svg>`;
  if (kind === "ddpg") return `<svg ${common} aria-label="DDPG actor critic architecture">${box(14, 98, "actor", "action μ(s)")}${arrow(115, 171, "action")}${box(171, 102, "critic", "Q(s,a)")}${arrow(276, 337, "gradient")}${box(337, 166, "target pair", "soft update τ")}</svg>`;
  if (kind === "sac") return `<svg ${common} aria-label="SAC stochastic actor and twin critics">${box(12, 111, "policy", "sample action")}${arrow(126, 181, "a")}${box(181, 116, "twin critics", "min Q₁, Q₂")}${arrow(300, 355, "target")}${box(355, 148, "entropy", "temperature α")}</svg>`;
  return `<svg ${common} aria-label="Generic algorithm pipeline">${box(30, 120, "observation", "input")}${arrow(153, 205, "learn")}${box(205, 120, "policy", "component")}${arrow(328, 380, "choose")}${box(380, 110, "action", "output")}</svg>`;
}

function renderEnvironmentTheory() {
  const id = $("#environment-select").value;
  const item = theorySection("environments")[id];
  if (!item) return;
  $("#environment-theory").innerHTML = `
    <div class="theory-illustration">${environmentIllustration(item.visual)}</div>
    <div class="theory-copy"><p class="theory-label">How this environment works</p><p>${escapeHtml(item.summary)}</p>
    <div class="micro-facts"><span><b>Observe</b>${escapeHtml(item.observation)}</span><span><b>Act</b>${escapeHtml(item.actions)}</span></div>
    <button type="button" class="learn-link" data-theory-kind="environment" data-theory-id="${escapeHtml(id)}">Reward, challenge, and shaping →</button></div>`;
}

function renderAlgorithmTheory() {
  const id = $("#algorithm-select").value;
  const item = theorySection("algorithms")[id];
  if (!item) return;
  $("#algorithm-theory").innerHTML = `
    <div class="theory-illustration wide">${algorithmIllustration(item.visual)}</div>
    <div class="theory-copy"><p class="theory-label">${escapeHtml(item.family)}</p><p>${escapeHtml(item.summary)}</p>
    <div class="equation-preview">${escapeHtml(item.equation)}</div>
    <button type="button" class="learn-link" data-theory-kind="algorithm" data-theory-id="${escapeHtml(id)}">Architecture, exploration, and trade-offs →</button></div>`;
}

function renderBehaviorTheory() {
  const id = $("#behavior-select").value;
  const item = theorySection("behaviors")[id];
  const descriptor = state.catalog.behaviors.find((candidate) => candidate.id === id);
  if (!item || !descriptor) return;
  $("#behavior-theory").innerHTML = `
    <div class="theory-copy"><p class="theory-label">${escapeHtml(descriptor.category)}</p><p>${escapeHtml(item.summary)}</p>
    <div class="equation-preview">${escapeHtml(item.equation)}</div>
    <button type="button" class="learn-link" data-theory-kind="behavior" data-theory-id="${escapeHtml(id)}">Mechanism, fit, and trade-off →</button></div>`;
}

function renderOptimizerTheory() {
  const id = $("#optimizer-select").value;
  const item = theorySection("optimizers")[id];
  const descriptor = state.catalog.optimizers.find((candidate) => candidate.id === id);
  if (!item || !descriptor) return;
  $("#optimizer-theory").innerHTML = `
    <div class="theory-copy"><p class="theory-label">${escapeHtml(descriptor.category)}</p><p>${escapeHtml(item.summary)}</p>
    <div class="equation-preview">${escapeHtml(item.equation)}</div>
    <button type="button" class="learn-link" data-theory-kind="optimizer" data-theory-id="${escapeHtml(id)}">Mechanism, fit, and trade-off →</button></div>`;
}

function renderMetricTheoryLinks() {
  const metricNames = {
    average_reward: "Average reward", cumulative_reward: "Cumulative reward",
    success_rate: "Success rate", reward_auc: "Reward AUC",
    training_time: "Training time", environment_steps: "Environment steps",
    episodes_to_threshold: "Episodes to threshold",
  };
  $("#metric-theory-links").innerHTML = Object.entries(metricNames).map(([id, label]) => `
    <button type="button" data-theory-kind="concept" data-theory-id="metric.${id}">${escapeHtml(label)} <span aria-hidden="true">?</span></button>`).join("");
}

function openTheory(kind, id) {
  let item;
  let kicker;
  if (kind === "environment") {
    item = theorySection("environments")[id];
    kicker = "Environment lesson";
  } else if (kind === "algorithm") {
    item = theorySection("algorithms")[id];
    kicker = "Algorithm lesson";
  } else if (kind === "behavior") {
    item = theorySection("behaviors")[id];
    kicker = "Action-behavior lesson";
  } else if (kind === "optimizer") {
    item = theorySection("optimizers")[id];
    kicker = "Optimizer lesson";
  } else if (kind === "parameter") {
    item = theorySection("parameters")[id];
    kicker = "Parameter lesson";
  } else if (kind === "glossary") {
    item = theorySection("exploration_glossary")[id];
    kicker = "Explore glossary";
  } else if (kind === "concept") {
    item = theorySection("concepts")[id];
    kicker = "Studio concept";
  } else {
    openLearningOverview();
    return;
  }
  if (!item) return;
  $("#learning-kicker").textContent = kicker;
  $("#learning-title").textContent = item.title || item.label || componentDisplayName(id);
  if (kind === "environment") {
    const descriptor = (state.catalog?.environments || []).find((candidate) => candidate.id === id);
    const successText = descriptor?.capabilities?.success_signal
      ? descriptor.capabilities.success_definition || "The adapter declares an episode-level success event."
      : "No native binary success event exists; use return-based evidence instead of success rate.";
    $("#learning-dialog-body").innerHTML = `${environmentIllustration(item.visual)}
      <p class="lead">${escapeHtml(item.summary)}</p>
      ${factList([
        ["Goal", item.goal], ["Observation", item.observation], ["Actions", item.actions],
        ["Native reward", item.native_reward], ["Episode end", item.episode_end],
        ["Environment success signal", successText],
        ["Why it is challenging", item.why_challenging], ["Beginner reading", item.beginner_tip],
      ])}
      <section class="shaping-box"><p class="theory-label">Reward shaping</p><strong>${escapeHtml(item.reward_shaping.status)}</strong><p>${escapeHtml(item.reward_shaping.idea)}</p><p class="caution">${escapeHtml(item.reward_shaping.caution)}</p></section>`;
  } else if (kind === "algorithm") {
    $("#learning-dialog-body").innerHTML = `${algorithmIllustration(item.visual)}
      <p class="lead">${escapeHtml(item.summary)}</p><div class="equation-card"><strong>${escapeHtml(item.equation)}</strong><p>${escapeHtml(item.equation_legend)}</p></div>
      ${factList([["What it learns", item.learns], ["Action behavior interface", item.exploration], ["Optimizer interface", item.optimizer], ["Experience memory", item.memory], ["Good fit", item.best_fit], ["Trade-off", item.trade_off], ["Beginner tip", item.beginner_tip]])}`;
  } else if (kind === "behavior") {
    $("#learning-dialog-body").innerHTML = `<p class="lead">${escapeHtml(item.summary)}</p><div class="equation-card"><strong>${escapeHtml(item.equation)}</strong></div>
      ${factList([["Mechanism", item.mechanism], ["Good fit", item.best_fit], ["Trade-off", item.trade_off]])}`;
  } else if (kind === "optimizer") {
    $("#learning-dialog-body").innerHTML = `<p class="lead">${escapeHtml(item.summary)}</p><div class="equation-card"><strong>${escapeHtml(item.equation)}</strong></div>
      ${factList([["Mechanism", item.mechanism], ["Good fit", item.best_fit], ["Trade-off", item.trade_off]])}`;
  } else if (kind === "parameter") {
    $("#learning-dialog-body").innerHTML = `<p class="lead">${escapeHtml(item.summary)}</p>${factList([["If you increase it", item.increase], ["If you decrease it", item.decrease], ["Watch the interaction", item.interaction]])}`;
  } else if (kind === "glossary") {
    $("#learning-dialog-body").innerHTML = `<p class="lead">${escapeHtml(item.definition)}</p><div class="example-box"><strong>Example</strong><p>${escapeHtml(item.example)}</p></div>`;
  } else {
    $("#learning-dialog-body").innerHTML = `<p class="lead">${escapeHtml(item.summary)}</p>${item.details?.length ? `<ul class="lesson-list">${item.details.map((detail) => `<li>${escapeHtml(detail)}</li>`).join("")}</ul>` : ""}`;
  }
  $("#learning-dialog-sources").innerHTML = sourceMarkup(item.sources || []);
  showLearningDialog();
}

function openLearningOverview() {
  const glossary = theorySection("exploration_glossary");
  $("#learning-kicker").textContent = "Beginner map";
  $("#learning-title").textContent = "How to read RLSPL Studio";
  $("#learning-dialog-body").innerHTML = `
    <p class="lead">RLSPL separates <strong>what may vary</strong>, <strong>which combinations are valid</strong>, and <strong>what happened during execution</strong>.</p>
    <div class="learning-map">
      <div><span>1</span><strong>Configure</strong><p>Choose an environment, algorithm, action behavior, optimizer/update rule, training values, and evaluation evidence.</p></div>
      <div><span>2</span><strong>Resolve</strong><p>Capability and parameter constraints explain validity; advisories preserve theoretically feasible choices.</p></div>
      <div><span>3</span><strong>Explore</strong><p>Expand finite axes, retain exclusions, deduplicate equivalent products, and add replication seeds.</p></div>
      <div><span>4</span><strong>Execute</strong><p>Record status, platform, seeds, and artifacts as metadata rather than product-line features.</p></div>
    </div>
    <p class="theory-label glossary-heading">Explore glossary</p>
    <div class="glossary-grid">${Object.entries(glossary).map(([termId, term]) => `<button type="button" data-theory-kind="glossary" data-theory-id="${escapeHtml(termId)}"><strong>${escapeHtml(term.title)}</strong><span>${escapeHtml(term.definition)}</span></button>`).join("")}</div>`;
  $("#learning-dialog-sources").innerHTML = sourceMarkup(["sutton_barto", "rlspl", "deep_rl_matters"]);
  showLearningDialog();
}

function factList(items) {
  return `<dl class="lesson-facts">${items.filter(([, value]) => value).map(([term, value]) => `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>`;
}

function componentDisplayName(id) {
  const component = [...(state.catalog?.environments || []), ...(state.catalog?.algorithms || []), ...(state.catalog?.behaviors || []), ...(state.catalog?.optimizers || [])].find((candidate) => candidate.id === id);
  return component?.display_name || id;
}

function showLearningDialog() {
  const dialog = $("#learning-dialog");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeLearningDialog() {
  const dialog = $("#learning-dialog");
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function parameterDefinitions() {
  const algorithm = state.catalog.algorithms.find((item) => item.id === $("#algorithm-select").value);
  const behavior = state.catalog.behaviors.find((item) => item.id === $("#behavior-select").value);
  const optimizer = state.catalog.optimizers.find((item) => item.id === $("#optimizer-select").value);
  return [...state.catalog.training_parameters, ...(algorithm?.parameters || []), ...(behavior?.parameters || []), ...(optimizer?.parameters || [])];
}

function renderParameters() {
  const root = $("#parameter-editor");
  root.innerHTML = "";
  for (const definition of parameterDefinitions()) {
    const lesson = theorySection("parameters")[definition.id] || {};
    const row = document.createElement("div");
    row.className = "parameter-row";
    row.dataset.parameterId = definition.id;
    row.dataset.parameterType = definition.type;
    row.dataset.minimum = definition.minimum ?? "";
    row.dataset.maximum = definition.maximum ?? "";
    row.innerHTML = `
      <div class="parameter-meta">
        <strong>${escapeHtml(lesson.label || definition.id)}</strong>
        <small class="parameter-id">${escapeHtml(definition.id)}</small>
        <span>${escapeHtml(lesson.summary || definition.description || "Component parameter")}</span>
        <small>${escapeHtml(definition.type)} · ${escapeHtml(definition.owner)}</small>
      </div>
      <select class="parameter-mode" ${definition.tunable ? "" : "disabled"}>
        <option value="fixed">Fixed</option>
        ${definition.tunable ? '<option value="tunable">Tunable</option>' : ""}
      </select>
      <div class="parameter-value"></div>
      <button type="button" class="help-dot parameter-help" aria-label="Explain ${escapeHtml(lesson.label || definition.id)}" data-theory-kind="parameter" data-theory-id="${escapeHtml(definition.id)}">?</button>`;
    root.appendChild(row);
    renderParameterValue(row, definition);
  }
}

function renderParameterValue(row, definition) {
  const holder = row.querySelector(".parameter-value");
  const mode = row.querySelector(".parameter-mode").value;
  if (mode === "fixed") {
    if (definition.type === "boolean") {
      holder.innerHTML = `<select class="fixed-value"><option value="true">True</option><option value="false">False</option></select>`;
      holder.querySelector("select").value = String(definition.default).toLowerCase();
    } else if (definition.type === "categorical") {
      holder.innerHTML = `<select class="fixed-value">${(definition.choices || []).map((choice) => `<option value="${escapeHtml(choice)}">${escapeHtml(choice)}</option>`).join("")}</select>`;
      holder.querySelector("select").value = String(definition.default);
    } else {
      const type = ["integer", "float"].includes(definition.type) ? "number" : "text";
      const step = definition.type === "integer" ? "1" : "any";
      holder.innerHTML = `<input class="fixed-value" type="${type}" step="${step}" value="${escapeHtml(String(definition.default))}">`;
    }
    return;
  }
  if (definition.type === "categorical" || definition.type === "boolean" || definition.type === "string") {
    const choices = definition.choices?.length ? definition.choices.join(", ") : "true, false";
    holder.innerHTML = `<div class="domain-fields"><input class="domain-choices choices" value="${escapeHtml(choices)}" aria-label="Choices"></div>`;
  } else {
    const lower = definition.minimum ?? Math.max(Number(definition.default) / 10, Number.EPSILON);
    const upper = definition.maximum ?? Math.max(Number(definition.default) * 10, Number(lower) + 1);
    const kind = definition.type === "integer"
      ? '<input class="domain-kind" type="hidden" value="integer">'
      : '<select class="domain-kind" aria-label="Search scale"><option value="float">Linear scale</option><option value="log_float">Log scale</option></select>';
    holder.innerHTML = `<div class="domain-fields numeric-domain-fields">${kind}<input class="domain-lower" type="number" step="any" value="${lower}" aria-label="Lower bound"><input class="domain-upper" type="number" step="any" value="${upper}" aria-label="Upper bound"></div>`;
  }
}

function buildParameters() {
  const definitions = new Map(parameterDefinitions().map((item) => [item.id, item]));
  const parameters = {};
  for (const row of $$(".parameter-row")) {
    const id = row.dataset.parameterId;
    const definition = definitions.get(id);
    const mode = row.querySelector(".parameter-mode").value;
    if (mode === "fixed") {
      parameters[id] = { mode, value: coerce(row.querySelector(".fixed-value").value, definition.type) };
    } else if (["categorical", "boolean", "string"].includes(definition.type)) {
      parameters[id] = {
        mode,
        domain: {
          kind: "categorical",
          choices: row.querySelector(".domain-choices").value.split(",").map((item) => coerce(item.trim(), definition.type)),
        },
      };
    } else {
      parameters[id] = {
        mode,
        domain: {
          kind: row.querySelector(".domain-kind").value,
          lower: coerce(row.querySelector(".domain-lower").value, definition.type),
          upper: coerce(row.querySelector(".domain-upper").value, definition.type),
        },
      };
    }
  }
  return parameters;
}

function buildConfiguration() {
  const checkpointPolicy = $("#checkpoint-policy").value;
  const evaluationMetrics = selectedValues("metrics");
  const searchEnabled = $("#search-enabled").checked;
  const timeout = Number.parseInt($("#search-timeout").value, 10);
  return {
    schema_version: "1.0",
    name: $("#project-name").value.trim(),
    environment: { source: "catalog", component_id: $("#environment-select").value, parameters: {} },
    algorithm: { component_id: $("#algorithm-select").value },
    behavior: { component_id: $("#behavior-select").value },
    optimizer: { component_id: $("#optimizer-select").value },
    training: {
      budget_unit: $("#budget-unit").value,
      budget: Number.parseInt($("#budget").value, 10),
      parameters: buildParameters(),
      checkpoint_policy: checkpointPolicy,
      checkpoint_interval: checkpointPolicy === "periodic" ? Number.parseInt($("#checkpoint-interval").value, 10) : null,
    },
    search: searchEnabled ? {
      sampler: $("#search-sampler").value,
      objective: $("#search-objective").value,
      trials: Number.parseInt($("#search-trials").value, 10),
      seeds: parseSeeds($("#search-seeds").value, "search seeds"),
      sampler_seed: Number.parseInt($("#search-sampler-seed").value, 10),
      aggregation: $("#search-aggregation").value,
      top_k: Number.parseInt($("#search-top-k").value, 10),
      ...(Number.isFinite(timeout) ? { timeout_seconds: timeout } : {}),
    } : null,
    evaluation: {
      protocol: "configurable",
      metrics: evaluationMetrics,
      summaries: selectedValues("summaries"),
      visualizations: selectedValues("visualizations"),
      export_formats: selectedValues("exports"),
      seeds: parseSeeds($("#evaluation-seeds").value, "evaluation seeds"),
      episodes_per_seed: Number.parseInt($("#episodes-per-seed").value, 10),
      collect_reward_trace: evaluationMetrics.includes("reward_auc") || selectedValues("visualizations").some((item) => ["learning_curve", "convergence"].includes(item)),
      comparison_run_ids: [],
      action_mode: $("#evaluation-action-mode").value,
    },
  };
}

function updateHpoWorkload() {
  const note = $("#hpo-workload-note");
  if (!note) return;
  if (!$("#search-enabled").checked) {
    note.textContent = "Enable search and mark at least one parameter as tunable to derive an HPO product.";
    return;
  }
  try {
    const trials = Number.parseInt($("#search-trials").value, 10);
    const seeds = parseSeeds($("#search-seeds").value, "trial training seeds");
    const fits = trials * seeds.length;
    note.textContent = `${trials} trials × ${seeds.length} trial seed${seeds.length === 1 ? "" : "s"} = ${fits} trial training run${fits === 1 ? "" : "s"}, followed by one final fit and independent evaluation.`;
  } catch (error) {
    note.textContent = error.message;
  }
}

function studySelections(containerId) {
  return $$(`#${containerId} input:checked`).map((input) => input.value);
}

function explorationDefinition(target) {
  return state.catalog.exploration_axes.find((item) => item.target === target);
}

function parseAxisValues(value, definition) {
  const tokens = value.split(",").map((item) => item.trim()).filter(Boolean);
  return tokens.map((item) => coerce(item, definition.type));
}

function additionalAxisDefinitions() {
  return state.catalog.exploration_axes.filter((item) => ![
    "environment.component_id", "algorithm.component_id", "behavior.component_id", "optimizer.component_id",
  ].includes(item.target));
}

function defaultAxisValues(definition) {
  if (definition.choices?.length >= 2) return definition.choices.slice(0, 2).join(", ");
  if (definition.type === "boolean") return "true, false";
  if (["integer", "float"].includes(definition.type) && Number.isFinite(Number(definition.default))) {
    const first = Number(definition.default);
    let second = definition.type === "integer"
      ? first + Math.max(1, Math.round(Math.abs(first) * 0.25))
      : (first === 0 ? 0.1 : first * 2);
    if (definition.maximum !== null && definition.maximum !== undefined) {
      second = Math.min(second, Number(definition.maximum));
    }
    if (second === first) {
      second = definition.type === "integer"
        ? first - Math.max(1, Math.round(Math.abs(first) * 0.25))
        : first / 2;
    }
    if (definition.minimum !== null && definition.minimum !== undefined) {
      second = Math.max(second, Number(definition.minimum));
    }
    return `${first}, ${second}`;
  }
  if (definition.type === "integer") {
    const lower = definition.minimum ?? 1;
    return `${lower}, ${Math.max(lower + 1, lower * 2)}`;
  }
  const lower = definition.minimum ?? 0.001;
  const upper = definition.maximum ?? Math.max(lower * 10, 0.01);
  return `${lower}, ${upper}`;
}

function derivedAxisConditions(definition) {
  if (!definition.owner) return [];
  if (state.catalog.algorithms.some((item) => item.id === definition.owner)) {
    return [{ target: "algorithm.component_id", values: [definition.owner] }];
  }
  if (state.catalog.environments.some((item) => item.id === definition.owner)) {
    return [{ target: "environment.component_id", values: [definition.owner] }];
  }
  if (state.catalog.behaviors.some((item) => item.id === definition.owner)) {
    return [{ target: "behavior.component_id", values: [definition.owner] }];
  }
  if (state.catalog.optimizers.some((item) => item.id === definition.owner)) {
    return [{ target: "optimizer.component_id", values: [definition.owner] }];
  }
  return [];
}

function updateAxisCondition(row, definition) {
  const conditions = derivedAxisConditions(definition);
  const label = row.querySelector(".study-axis-condition");
  const explanation = row.querySelector(".study-axis-explanation");
  if (explanation) {
    const parameterLesson = theorySection("parameters")[definition.target];
    const conceptKeys = {
      "training.budget": "training_budget",
      "training.budget_unit": "budget_unit",
      "training.checkpoint_policy": "checkpoint_policy",
      "training.checkpoint_interval": "checkpoint_policy",
      "evaluation.episodes_per_seed": "evaluation",
    };
    const conceptLesson = theorySection("concepts")[conceptKeys[definition.target]];
    explanation.textContent = parameterLesson?.summary || conceptLesson?.summary || "Each explicit value creates a branch in this finite axis.";
  }
  if (!conditions.length) {
    label.textContent = "Applies to every candidate";
    return;
  }
  const condition = conditions[0];
  const component = [...state.catalog.environments, ...state.catalog.algorithms, ...state.catalog.behaviors, ...state.catalog.optimizers]
    .find((item) => item.id === condition.values[0]);
  const kind = condition.target.startsWith("algorithm")
    ? "algorithm"
    : condition.target.startsWith("behavior")
      ? "behavior"
      : condition.target.startsWith("optimizer") ? "optimizer" : "environment";
  label.textContent = `Only when ${kind} is ${component?.display_name || condition.values[0]}`;
}

function addStudyAxis(target = "training.budget") {
  const definitions = additionalAxisDefinitions();
  const row = document.createElement("div");
  row.className = "study-axis-row";
  row.innerHTML = `
    <label>Target
      <select class="study-axis-target">${definitions.map((item) => `
        <option value="${escapeHtml(item.target)}">${escapeHtml(item.display_name)} · ${escapeHtml(item.kind)}</option>`).join("")}</select>
      <small class="study-axis-condition"></small>
      <small class="study-axis-explanation"></small>
    </label>
    <label>Values
      <input class="study-axis-values" aria-label="Axis values">
    </label>
    <button class="remove-study-axis" type="button" aria-label="Remove variability axis">×</button>`;
  $("#study-axis-list").appendChild(row);
  row.querySelector(".study-axis-target").value = target;
  const definition = explorationDefinition(row.querySelector(".study-axis-target").value);
  row.querySelector(".study-axis-values").value = defaultAxisValues(definition);
  updateAxisCondition(row, definition);
  $("#empty-study-axes").hidden = true;
  updateStudyJsonPreview();
}

function buildStudy() {
  const axes = [];
  const environments = studySelections("study-environments");
  const algorithms = studySelections("study-algorithms");
  const behaviors = studySelections("study-behaviors");
  const optimizers = studySelections("study-optimizers");
  if (!environments.length || !algorithms.length || !behaviors.length || !optimizers.length) {
    throw new Error("select at least one environment, algorithm, action behavior, and optimizer");
  }
  axes.push({ target: "environment.component_id", label: "Environment", values: environments });
  axes.push({ target: "algorithm.component_id", label: "Algorithm", values: algorithms });
  axes.push({ target: "behavior.component_id", label: "Action behavior", values: behaviors });
  axes.push({ target: "optimizer.component_id", label: "Optimizer / update rule", values: optimizers });

  for (const row of $$(".study-axis-row")) {
    const target = row.querySelector(".study-axis-target").value;
    const definition = explorationDefinition(target);
    const values = parseAxisValues(row.querySelector(".study-axis-values").value, definition);
    if (!values.length) throw new Error(`${target} requires at least one value`);
    axes.push({
      target,
      label: definition.display_name,
      values,
      when: derivedAxisConditions(definition),
    });
  }
  const seeds = parseSeeds($("#study-seeds").value, "training replication seeds");
  const evaluationSeeds = parseSeeds($("#study-evaluation-seeds").value, "evaluation seeds");
  if (!seeds.length) throw new Error("provide at least one training replication seed");
  if (!evaluationSeeds.length) throw new Error("provide at least one evaluation seed");
  return {
    schema_version: "2.0",
    name: $("#study-name").value.trim(),
    axes,
    replications: { seeds, evaluation_seeds: evaluationSeeds },
  };
}

function renderStudySeedSummary() {
  const summary = $("#study-seed-summary");
  if (!summary) return;
  try {
    const trainingSeeds = parseSeeds($("#study-seeds").value, "training replication seeds");
    const evaluationSeeds = parseSeeds($("#study-evaluation-seeds").value, "evaluation seeds");
    const trainingLabel = trainingSeeds.length === 1 ? "training run" : "training runs";
    const evaluationLabel = evaluationSeeds.length === 1 ? "evaluation seed" : "evaluation seeds";
    summary.className = "seed-plan-note";
    summary.textContent = `${trainingSeeds.length} ${trainingLabel} per valid configuration [${trainingSeeds.join(", ")}] · ${evaluationSeeds.length} ${evaluationLabel} per trained agent [${evaluationSeeds.join(", ")}]`;
  } catch (error) {
    summary.className = "seed-plan-note invalid";
    summary.textContent = error.message;
  }
}

function markStudyPlanStale() {
  if (!state.studyManifest) return;
  state.studyManifest = null;
  $("#study-status").className = "compatibility-status pending";
  $("#study-status").textContent = "Study changed — preview again";
  $("#study-summary-detail").textContent = "The visible definition differs from the last computed manifest.";
  for (const id of ["candidate-count", "configuration-count", "invalid-count", "run-count"]) {
    $(`#${id}`).textContent = "—";
  }
  $("#study-run-formula").textContent = "Preview the edited study to recompute valid configurations × training seeds.";
  $("#variant-count").textContent = "Preview required";
  $("#variant-rows").innerHTML = '<tr><td colspan="6" class="muted">The study changed. Preview it to refresh this matrix.</td></tr>';
  $("#rejected-count").textContent = "Preview required";
  $("#study-issues").innerHTML = '<p class="muted">The study changed. Preview it to recompute exclusions.</p>';
  $("#study-save-result").hidden = true;
}

function updateStudyJsonPreview() {
  if (!state.catalog) return;
  renderStudySeedSummary();
  try {
    $("#study-json-preview").textContent = JSON.stringify(buildStudy(), null, 2);
  } catch (error) {
    $("#study-json-preview").textContent = `Study incomplete: ${error.message}`;
  }
}

function updatePreview() {
  updateHpoWorkload();
  try {
    $("#json-preview").textContent = JSON.stringify(buildConfiguration(), null, 2);
    updateCompatibility();
  } catch (error) {
    $("#json-preview").textContent = `Configuration incomplete: ${error.message}`;
  }
  updateStudyJsonPreview();
}

function updateCapabilities() {
  const environment = state.catalog.environments.find((item) => item.id === $("#environment-select").value);
  const algorithm = state.catalog.algorithms.find((item) => item.id === $("#algorithm-select").value);
  const behavior = state.catalog.behaviors.find((item) => item.id === $("#behavior-select").value);
  const optimizer = state.catalog.optimizers.find((item) => item.id === $("#optimizer-select").value);
  $("#environment-capabilities").innerHTML = environment ? [
    `${environment.capabilities.action_kind} actions`,
    `${environment.capabilities.observation_kind} observations`,
    environment.capabilities.action_bounded ? "bounded" : null,
    environment.capabilities.success_signal ? "success signal" : null,
  ].filter(Boolean).map(pill).join("") : "";
  $("#algorithm-capabilities").innerHTML = algorithm ? [
    `${algorithm.requirements.action_kinds.join(" / ")} actions`,
    `${algorithm.requirements.observation_kinds.join(" / ")} observations`,
    `${algorithm.requirements.supports_budget_units.join(" / ")} budget`,
  ].map(pill).join("") : "";
  $("#behavior-capabilities").innerHTML = behavior ? [
    behavior.category,
    `${behavior.requirements.policy_interfaces.join(" / ")} interface`,
    `${behavior.requirements.action_kinds.join(" / ")} actions`,
    behavior.requirements.requires_bounded_actions ? "needs bounds" : null,
    behavior.requirements.requires_perturbable_policy ? "needs perturbable model" : null,
  ].filter(Boolean).map(pill).join("") : "";
  $("#optimizer-capabilities").innerHTML = optimizer ? [
    optimizer.category,
    `${optimizer.requirements.interfaces.join(" / ")} interface`,
    `${optimizer.parameters.length} owned parameters`,
  ].map(pill).join("") : "";
  updateEvaluationAvailability(environment);
  updateEvaluationActionModes(algorithm);
  renderEnvironmentTheory();
  renderAlgorithmTheory();
  renderBehaviorTheory();
  renderOptimizerTheory();
  updateSelectionCommentary(environment, algorithm, behavior, optimizer);
}

function updateEvaluationActionModes(algorithm) {
  if (!algorithm) return;
  const supported = new Set(algorithm.composition.evaluation_modes || ["deterministic"]);
  for (const option of $("#evaluation-action-mode").options) {
    option.disabled = !supported.has(option.value);
  }
  if (!supported.has($("#evaluation-action-mode").value)) {
    $("#evaluation-action-mode").value = supported.has("deterministic")
      ? "deterministic"
      : [...supported][0];
  }
}

function behaviorMismatchReasons(environment, algorithm, behavior) {
  if (!environment || !algorithm || !behavior) return ["a component is missing"];
  const reasons = [];
  if (!behavior.requirements.policy_interfaces.includes(algorithm.composition.policy_interface)) {
    reasons.push(`${behavior.display_name} needs ${behavior.requirements.policy_interfaces.join(" / ")} but ${algorithm.display_name} exposes ${algorithm.composition.policy_interface}`);
  }
  if (!behavior.requirements.action_kinds.includes(environment.capabilities.action_kind)) {
    reasons.push(`${behavior.display_name} does not produce ${environment.capabilities.action_kind} actions`);
  }
  if (behavior.requirements.requires_bounded_actions && !environment.capabilities.action_bounded) {
    reasons.push(`${behavior.display_name} requires finite action bounds`);
  }
  if (behavior.requirements.requires_perturbable_policy && !algorithm.composition.perturbable_policy) {
    reasons.push(`${algorithm.display_name} does not expose a perturbable policy model`);
  }
  return reasons;
}

function optimizerMismatchReasons(algorithm, optimizer) {
  if (!algorithm || !optimizer) return ["a component is missing"];
  if (!optimizer.requirements.interfaces.includes(algorithm.composition.optimizer_interface)) {
    return [`${optimizer.display_name} needs ${optimizer.requirements.interfaces.join(" / ")} but ${algorithm.display_name} exposes ${algorithm.composition.optimizer_interface}`];
  }
  return [];
}

function updateEvaluationAvailability(environment) {
  if (!environment) return;
  const hasSuccessSignal = Boolean(environment.capabilities.success_signal);
  for (const metricId of ["success_rate", "episodes_to_threshold"]) {
    const input = $(`#metrics input[value="${metricId}"]`);
    if (!input) continue;
    input.disabled = !hasSuccessSignal;
    if (!hasSuccessSignal) input.checked = false;
    input.closest("label")?.classList.toggle("metric-unavailable", !hasSuccessSignal);
    input.closest("label")?.setAttribute(
      "title",
      hasSuccessSignal
        ? environment.capabilities.success_definition || "This environment declares an episode-level success signal."
        : "Unavailable because this environment has no native binary success event.",
    );
  }
  const note = $("#success-metric-note");
  if (note) note.hidden = hasSuccessSignal;
}

function updateSelectionCommentary(environment, algorithm, behavior, optimizer) {
  if (!environment || !algorithm || !behavior || !optimizer) return;
  const actionFit = algorithm.requirements.action_kinds.includes(environment.capabilities.action_kind);
  const observationFit = algorithm.requirements.observation_kinds.includes(environment.capabilities.observation_kind);
  const boundsFit = !algorithm.requirements.requires_bounded_actions || environment.capabilities.action_bounded;
  const algorithmLesson = theorySection("algorithms")[algorithm.id] || {};
  const adapter = algorithm.requirements.vector_observation_adapter;
  const observationText = observationFit
    ? `${environment.capabilities.observation_kind} observations satisfy the algorithm contract${adapter ? `; ${adapter} converts the vector to table cells` : ""}.`
    : `${environment.capabilities.observation_kind} observations are outside the algorithm's accepted ${algorithm.requirements.observation_kinds.join(" / ")} contract.`;
  const qTableNote = algorithm.id === "rlspl.q_learning"
    ? "Discretization makes this composable, while table growth remains a visible resource advisory rather than a rejection."
    : "Function approximation avoids a dense state table, but adds optimizer and seed sensitivity.";
  $("#selection-commentary").innerHTML = `<ul class="compatibility-list">
    <li class="${actionFit ? "fits" : "fails"}"><strong>Action contract</strong><span>${escapeHtml(actionFit ? `Both sides use ${environment.capabilities.action_kind} actions.` : `The environment needs ${environment.capabilities.action_kind} actions; ${algorithm.display_name} produces ${algorithm.requirements.action_kinds.join(" / ")}.`)}</span></li>
    <li class="${observationFit ? "fits" : "fails"}"><strong>Observation contract</strong><span>${escapeHtml(observationText)}</span></li>
    ${algorithm.requirements.requires_bounded_actions ? `<li class="${boundsFit ? "fits" : "fails"}"><strong>Action bounds</strong><span>${boundsFit ? "Finite bounds are declared for safe policy scaling." : "The algorithm requires finite bounds, but the environment does not declare them."}</span></li>` : ""}
    <li class="neutral"><strong>Learning representation</strong><span>${escapeHtml(qTableNote)}</span></li>
    <li class="neutral"><strong>Evaluation signal</strong><span>${escapeHtml(environment.capabilities.success_signal ? (environment.capabilities.success_definition || "The adapter declares an episode-level task-success event, so success-based metrics are available.") : "This task has no native binary success event; compare return-based metrics instead.")}</span></li>
    <li class="${behaviorMismatchReasons(environment, algorithm, behavior).length ? "fails" : "fits"}"><strong>Behavior contract</strong><span>${escapeHtml(behaviorMismatchReasons(environment, algorithm, behavior).length ? behaviorMismatchReasons(environment, algorithm, behavior).join("; ") : `${behavior.display_name} composes through the algorithm's ${algorithm.composition.policy_interface} interface.`)}</span></li>
    <li class="neutral"><strong>Action behavior</strong><span>${escapeHtml((theorySection("behaviors")[behavior.id] || {}).mechanism || behavior.description)}</span></li>
    <li class="${optimizerMismatchReasons(algorithm, optimizer).length ? "fails" : "fits"}"><strong>Optimizer contract</strong><span>${escapeHtml(optimizerMismatchReasons(algorithm, optimizer).length ? optimizerMismatchReasons(algorithm, optimizer).join("; ") : `${optimizer.display_name} implements the algorithm's ${algorithm.composition.optimizer_interface} update interface.`)}</span></li>
    <li class="neutral"><strong>Update rule</strong><span>${escapeHtml((theorySection("optimizers")[optimizer.id] || {}).mechanism || optimizer.description)}</span></li>
    <li class="neutral"><strong>Algorithm defaults</strong><span>${escapeHtml(`${algorithmLesson.exploration || algorithm.composition.default_behavior_id || algorithm.composition.exploration_role}; optimizer: ${algorithm.composition.default_optimizer_id || "algorithm-owned"}`)}</span></li>
  </ul>`;
}

function updateCompatibility() {
  if (!state.catalog) return;
  const environment = state.catalog.environments.find((item) => item.id === $("#environment-select").value);
  const algorithm = state.catalog.algorithms.find((item) => item.id === $("#algorithm-select").value);
  const behavior = state.catalog.behaviors.find((item) => item.id === $("#behavior-select").value);
  const optimizer = state.catalog.optimizers.find((item) => item.id === $("#optimizer-select").value);
  if (!environment || !algorithm || !behavior || !optimizer) return;
  const componentPairCompatible = algorithm.requirements.action_kinds.includes(environment.capabilities.action_kind)
    && algorithm.requirements.observation_kinds.includes(environment.capabilities.observation_kind)
    && (!algorithm.requirements.requires_bounded_actions || environment.capabilities.action_bounded);
  const behaviorMismatches = componentPairCompatible
    ? behaviorMismatchReasons(environment, algorithm, behavior)
    : [];
  const optimizerMismatches = optimizerMismatchReasons(algorithm, optimizer);
  const compatible = componentPairCompatible && !behaviorMismatches.length && !optimizerMismatches.length;
  const generatable = state.catalog.generation_compositions.some((item) => item.environment_id === environment.id && item.algorithm_id === algorithm.id && item.behavior_id === behavior.id && item.optimizer_id === optimizer.id);
  const status = $("#compatibility-status");
  status.className = `compatibility-status ${compatible ? "valid" : "invalid"}`;
  status.textContent = compatible ? "Capability-compatible" : "Incompatible selection";
  const mismatches = [];
  if (!algorithm.requirements.action_kinds.includes(environment.capabilities.action_kind)) {
    mismatches.push(`${environment.capabilities.action_kind} environment actions are not accepted by ${algorithm.display_name}`);
  }
  if (!algorithm.requirements.observation_kinds.includes(environment.capabilities.observation_kind)) {
    mismatches.push(`${environment.capabilities.observation_kind} observations are not accepted by ${algorithm.display_name}`);
  }
  if (algorithm.requirements.requires_bounded_actions && !environment.capabilities.action_bounded) {
    mismatches.push("the algorithm requires bounded actions");
  }
  mismatches.push(...behaviorMismatches);
  mismatches.push(...optimizerMismatches);
  $("#compatibility-detail").textContent = !compatible
    ? `${mismatches.join("; ")}. Capability mismatches are structural, so hyperparameter tuning cannot repair them.`
    : generatable
      ? "Environment, algorithm, action behavior, and optimizer satisfy their contracts and all four runtime assets are installed."
      : "The composition is theoretically compatible, but one executable runtime component is not installed yet.";
}

function issueMarkup(issues, emptyMessage) {
  return issues.length ? issues.map((issue) => `
    <div class="issue ${issue.severity}"><strong>${escapeHtml(issue.severity.toUpperCase())} · ${escapeHtml(issue.code)}</strong>
    <div>${escapeHtml(issue.path)} — ${escapeHtml(issue.message)}</div>
    ${issue.suggestion ? `<small>${escapeHtml(issue.suggestion)}</small>` : ""}
    ${theorySection("issue_explanations")[issue.code] ? `<p class="issue-explanation"><b>Why this matters:</b> ${escapeHtml(theorySection("issue_explanations")[issue.code])}</p>` : ""}</div>`).join("")
    : `<div class="issue"><strong>No issues</strong><div>${escapeHtml(emptyMessage)}</div></div>`;
}

function renderIssues(issues) {
  $("#issue-count").textContent = `${issues.length} issue${issues.length === 1 ? "" : "s"}`;
  $("#issues").innerHTML = issueMarkup(
    issues, "The configuration satisfies all active constraints."
  );
}

async function validateConfiguration() {
  setBusy(true);
  try {
    const { body } = await request("/api/validate", buildConfiguration());
    renderIssues(body.issues || [{ severity: "error", code: "HTTP", path: "request", message: body.error || "Validation failed" }]);
    setConnection(body.valid ? "Valid configuration" : "Configuration invalid", body.valid ? "valid" : "invalid");
    return body.valid;
  } catch (error) {
    showToast(`Validation request failed: ${error.message}`);
    return false;
  } finally {
    setBusy(false);
  }
}

async function generateProduct() {
  setBusy(true);
  try {
    const { body } = await request("/api/generate", { configuration: buildConfiguration() });
    if (!body.generated) {
      renderIssues(body.issues || []);
      setConnection("Generation blocked", "invalid");
      return;
    }
    renderIssues(body.issues || []);
    setConnection("Product generated", "valid");
    const destination = body.product.destination;
    const commands = [
      `cd ${JSON.stringify(destination)}`,
      "python3 -m pip install -e .",
      body.product.entry_command,
    ].join("\n");
    $("#generation-path").textContent = destination;
    $("#run-commands").textContent = commands;
    $("#generation-result").hidden = false;
    showToast(`Generated ${body.product.files.length} files in ${body.product.destination}`);
  } catch (error) {
    showToast(`Generation request failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function renderStudyErrors(issues) {
  $("#study-status").className = "compatibility-status invalid";
  $("#study-status").textContent = "Study invalid";
  $("#study-summary-detail").textContent = "Correct the study definition before planning.";
  $("#study-issues").innerHTML = issueMarkup(issues, "No study-level errors.");
  setConnection("Study invalid", "invalid");
}

function renderStudyManifest(manifest) {
  state.studyManifest = manifest;
  const summary = manifest.summary;
  $("#candidate-count").textContent = summary.candidate_count;
  $("#configuration-count").textContent = summary.unique_configuration_count;
  $("#invalid-count").textContent = summary.invalid_candidate_count;
  $("#run-count").textContent = summary.planned_run_count;
  const seeds = manifest.study?.replications?.seeds?.length || 0;
  $("#study-run-formula").innerHTML = `<strong>${summary.unique_configuration_count}</strong> valid configurations × <strong>${seeds}</strong> training seeds = <strong>${summary.planned_run_count}</strong> planned runs`;
  $("#study-status").className = `compatibility-status ${summary.unique_configuration_count ? "valid" : "invalid"}`;
  $("#study-status").textContent = summary.unique_configuration_count
    ? `${summary.unique_configuration_count} valid configurations`
    : "No valid configurations";
  $("#study-summary-detail").textContent = summary.expansion_complete
    ? `All ${summary.candidate_count} candidates were evaluated; ${summary.duplicate_candidate_count} equivalent candidate(s) were deduplicated.`
    : `${summary.evaluated_candidate_count} of ${summary.candidate_count} candidates are materialized in this preview.`;

  const variants = manifest.variants.slice(0, 100);
  $("#variant-count").textContent = manifest.variants.length > variants.length
    ? `${variants.length} of ${manifest.variants.length} shown`
    : `${variants.length} shown`;
  $("#variant-rows").innerHTML = variants.length ? variants.map((variant) => {
    const configuration = variant.configuration;
    const axes = Object.entries(variant.axis_values)
      .map(([target, value]) => `<span><b>${escapeHtml(target)}</b> ${escapeHtml(JSON.stringify(value))}</span>`)
      .join("");
    return `<tr>
      <td><code>${escapeHtml(variant.configuration_id)}</code></td>
      <td>${escapeHtml(configuration.environment_id)}</td>
      <td>${escapeHtml(configuration.algorithm_id)}</td>
      <td>${escapeHtml(configuration.behavior_id)}</td>
      <td>${escapeHtml(configuration.optimizer_id)}</td>
      <td><div class="axis-values">${axes}</div></td>
    </tr>`;
  }).join("") : '<tr><td colspan="6" class="muted">No valid configurations in the evaluated candidates.</td></tr>';

  const rejected = manifest.rejected_candidates;
  $("#rejected-count").textContent = rejected.length > 50
    ? `50 of ${rejected.length} shown`
    : `${rejected.length} excluded`;
  const excludedMarkup = rejected.slice(0, 50).map((candidate) => {
    const axes = Object.entries(candidate.axis_values)
      .map(([target, value]) => `${target}=${JSON.stringify(value)}`).join(", ");
    const codes = [...new Set(candidate.issues.map((issue) => issue.code))].join(", ");
    return `<div class="issue error"><strong>Candidate ${candidate.candidate_index} · ${escapeHtml(codes)}</strong><div>${escapeHtml(axes)}</div><small>${escapeHtml(candidate.issues.map((issue) => issue.message).join(" · "))}</small></div>`;
  });
  const advisoryMarkup = (manifest.advisories || []).map((issue) => `
    <div class="issue advisory"><strong>ADVISORY · ${escapeHtml(issue.code)}</strong><div>${escapeHtml(issue.message)}</div></div>`);
  $("#study-issues").innerHTML = [...advisoryMarkup, ...excludedMarkup].join("")
    || '<div class="issue"><strong>No exclusions</strong><div>Every evaluated candidate satisfies the active constraints.</div></div>';
}

async function planStudy(save) {
  setBusy(true);
  try {
    const payload = {
      study: buildStudy(),
      limit: Number.parseInt($("#study-limit").value, 10),
    };
    const { body } = await request(save ? "/api/studies/save" : "/api/studies/preview", payload);
    if ((!save && !body.planned) || (save && !body.saved)) {
      renderStudyErrors(body.issues || []);
      return;
    }
    renderStudyManifest(body.manifest);
    setConnection(save ? "Study manifest saved" : "Study planned", "valid");
    if (save) {
      $("#study-manifest-path").textContent = body.path;
      const complete = body.manifest.summary.expansion_complete;
      $("#study-run-command").textContent = complete
        ? body.run_command
        : "This preview is truncated. Increase the preview limit and save a complete manifest before execution.";
      $("#copy-study-run-button").hidden = !complete;
      $("#study-save-result").hidden = false;
      showToast(body.existing ? "Existing frozen manifest reused" : "Study manifest saved");
    } else {
      showToast(`Planned ${body.manifest.summary.unique_configuration_count} valid configurations`);
    }
  } catch (error) {
    renderStudyErrors([{ severity: "error", code: "EXP-UI", path: "study", message: error.message }]);
  } finally {
    setBusy(false);
  }
}

function statusBadge(status) {
  const label = String(status || "unknown").replaceAll("_", " ");
  return `<span class="run-status ${escapeHtml(status || "unknown")}">${escapeHtml(label)}</span>`;
}

function formatMetric(value, digits = 3) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    return Math.abs(value) >= 10000 ? value.toLocaleString() : Number(value.toFixed(digits)).toLocaleString();
  }
  if (Array.isArray(value)) return value.map((item) => formatMetric(item, digits)).join(" – ");
  return String(value);
}

function environmentSuccessContext(signal, environmentId) {
  const catalogEnvironment = (state.catalog?.environments || []).find(
    (item) => item.id === environmentId
  );
  const catalogCapabilities = catalogEnvironment?.capabilities || {};
  let available = signal?.available;
  if (available === undefined || available === null) {
    if (typeof catalogCapabilities.success_signal === "boolean") {
      available = catalogCapabilities.success_signal;
    } else {
      available = null;
    }
  }
  if (available === true) {
    return {
      available: true,
      kind: "environment_episode_signal",
      label: "Environment success signal",
      definition: catalogCapabilities.success_definition
        || signal?.definition
        || "The environment adapter reports an episode-level success event; its component did not provide a more specific description.",
    };
  }
  if (available === false) {
    return {
      available: false,
      kind: "return_only",
      label: "No native binary success signal",
      definition: signal?.definition
        || "This environment has no native binary success event. Interpret reward and return directly; success rate is not applicable.",
    };
  }
  return {
    available: null,
    kind: "undeclared",
    label: "Success signal not declared",
    definition: signal?.definition
      || "This environment component did not declare whether it exposes a binary success event.",
  };
}

function environmentSuccessMarkup(signal, environmentId, compact = false) {
  const context = environmentSuccessContext(signal, environmentId);
  return `<div class="environment-success-context ${escapeHtml(context.kind)}${compact ? " compact" : ""}">
    <strong>${escapeHtml(context.label)}</strong>
    <span>${escapeHtml(context.definition)}</span>
  </div>`;
}

function rewardMetricMarkup(value, signal, environmentId, compact = true) {
  return `<div class="reward-with-context">
    <b>${escapeHtml(formatMetric(value))}</b>
    ${environmentSuccessMarkup(signal, environmentId, compact)}
  </div>`;
}

function isRewardMetric(name) {
  return String(name).includes("reward") || String(name) === "return";
}

function formatSuccessRate(value) {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${formatMetric(numeric * 100, 1)}%` : "—";
}

function formatSettingValue(target, value) {
  if (value === "(not active)") return "not active";
  if (["environment.component_id", "algorithm.component_id", "behavior.component_id", "optimizer.component_id"].includes(target)) {
    return componentDisplayName(value);
  }
  if (value === null || value === undefined) return "none";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function variedSettingsMarkup(values, emptyText = "No changing settings", limit = 6) {
  const dimensions = state.monitorExecution?.variability?.dimensions || [];
  const dimensionByTarget = new Map(dimensions.map((item) => [item.target, item]));
  const entries = Object.entries(values || {}).sort(([left], [right]) => {
    const leftExplicit = dimensionByTarget.get(left)?.source === "explicit_axis" ? 0 : 1;
    const rightExplicit = dimensionByTarget.get(right)?.source === "explicit_axis" ? 0 : 1;
    return leftExplicit - rightExplicit;
  });
  if (!entries.length) return `<span class="no-varied-settings">${escapeHtml(emptyText)}</span>`;
  const visible = entries.slice(0, limit);
  return `<div class="varied-settings">${visible.map(([target, value]) => `
    <span class="varied-setting"><b>${escapeHtml(dimensionByTarget.get(target)?.label || target)}</b><em>${escapeHtml(formatSettingValue(target, value))}</em></span>`).join("")}${entries.length > visible.length ? `<span class="more-varied-settings">+${entries.length - visible.length} more in variability map</span>` : ""}</div>`;
}

function variationDimensionMarkup(dimension) {
  const source = dimension.source === "explicit_axis" ? "selected axis" : "component-dependent";
  return `<article class="variation-dimension ${escapeHtml(dimension.kind)}">
    <span class="dimension-kind">${escapeHtml(dimension.kind)} · ${escapeHtml(source)}</span>
    <strong>${escapeHtml(dimension.label)}</strong>
    <code>${escapeHtml(dimension.target)}</code>
    <div>${dimension.values.map((value) => `<span>${escapeHtml(formatSettingValue(dimension.target, value))}</span>`).join("")}</div>
  </article>`;
}

function renderMonitorVariability() {
  const variability = state.monitorExecution?.variability || {};
  const dimensions = variability.dimensions || [];
  $("#monitor-dimension-count").textContent = `${dimensions.length} changing setting${dimensions.length === 1 ? "" : "s"}`;
  if (dimensions.length) {
    const explicit = dimensions.filter((item) => item.source === "explicit_axis");
    const derived = dimensions.filter((item) => item.source !== "explicit_axis");
    $("#monitor-variability-map").innerHTML = `
      ${explicit.map(variationDimensionMarkup).join("")}
      ${derived.length ? `<details class="derived-variability"><summary>${derived.length} component-dependent setting${derived.length === 1 ? "" : "s"} also change</summary><p>These differences come from the defaults owned by the selected algorithms or environments.</p><div>${derived.map(variationDimensionMarkup).join("")}</div></details>` : ""}`;
    return;
  }
  const comparison = state.monitorExecution?.comparisons?.[0];
  const hyperparameters = Object.entries(comparison?.hyperparameters || {});
  const composition = comparison
    ? `${componentDisplayName(comparison.environment_id)} + ${componentDisplayName(comparison.algorithm_id)} + ${componentDisplayName(comparison.behavior_id)} + ${componentDisplayName(comparison.optimizer_id)}`
    : "No resolved configuration";
  $("#monitor-variability-map").innerHTML = `<div class="single-configuration-note">
    <strong>One resolved configuration</strong>
    <span>${escapeHtml(composition)} · ${hyperparameters.length} active hyperparameters</span>
    ${hyperparameters.length ? `<details><summary>View effective hyperparameters</summary><div class="fixed-parameter-list">${hyperparameters.map(([target, value]) => `<span><b>${escapeHtml(target)}</b><em>${escapeHtml(formatSettingValue(target, value))}</em></span>`).join("")}</div></details>` : ""}
  </div>`;
}

function studySummaryLeaderMarkup(leader, label, percentage = false) {
  if (!leader) {
    return `<div class="study-result-metric unavailable"><span>${escapeHtml(label)}</span><strong>Not collected</strong><small>No completed run exposed this metric.</small></div>`;
  }
  const value = percentage ? formatSuccessRate(leader.value) : formatMetric(leader.value);
  const identities = (leader.configuration_ids || []).map((id, index) => {
    const name = leader.configuration_names?.[index];
    return name && name !== id ? `${name} (${id})` : id;
  });
  const tie = leader.tie_count > 1 ? ` · ${leader.tie_count}-way observed tie` : "";
  return `<div class="study-result-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(identities.join(", ") || "Unknown configuration")} · ${escapeHtml(leader.completed_seeds)} completed seed${leader.completed_seeds === 1 ? "" : "s"}${escapeHtml(tie)}</small></div>`;
}

function renderMonitorStudySummary() {
  const card = $("#monitor-study-summary");
  if (!card) return;
  const execution = state.monitorExecution;
  const summary = execution?.study_summary;
  card.hidden = execution?.kind !== "study";
  if (card.hidden) return;
  const status = summary?.status || execution.status || "pending";
  $("#monitor-study-summary-status").className = `run-status ${escapeHtml(status)}`;
  $("#monitor-study-summary-status").textContent = summary?.available ? "Final" : status;
  $("#monitor-study-summary-message").textContent = summary?.message
    || "The final study summary appears after execution stops.";
  const variability = summary?.variability || {};
  const facts = [
    [`${summary?.completed_runs || 0} / ${summary?.total_runs || execution.total_runs || 0}`, "Completed runs"],
    [`${summary?.completed_configuration_count || 0} / ${summary?.configuration_count || execution.configuration_count || 0}`, "Configurations with evidence"],
    [summary?.fully_replicated_configuration_count || 0, "Fully replicated configurations"],
    [variability.dimension_count ?? execution.variability?.dimension_count ?? 0, "Changing settings"],
    [variability.explicit_dimension_count ?? execution.variability?.explicit_dimension_count ?? 0, "Explicit study axes"],
    [(summary?.failed_runs || 0) + (summary?.interrupted_runs || 0), "Incomplete runs"],
  ];
  $("#monitor-study-summary-facts").innerHTML = facts.map(([value, label]) =>
    `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`
  ).join("");
  const componentGroups = [
    ["Environments", execution.environments || []],
    ["Algorithms", execution.algorithms || []],
    ["Action behaviors", execution.behaviors || []],
    ["Optimizers", execution.optimizers || []],
  ];
  $("#monitor-study-summary-components").innerHTML = componentGroups.map(([label, ids]) => `
    <div><strong>${escapeHtml(label)}</strong><span>${ids.map((id) => `<b>${escapeHtml(componentDisplayName(id))}</b>`).join("") || "<b>None</b>"}</span></div>`
  ).join("");
  const results = summary?.environment_results || [];
  $("#monitor-study-summary-environments").innerHTML = summary?.available
    ? results.map((result) => {
      const success = environmentSuccessContext(result.environment_success, result.environment_id);
      return `<article class="study-environment-result">
        <div class="study-environment-heading"><div><p class="eyebrow">Environment-level comparison</p><h4>${escapeHtml(componentDisplayName(result.environment_id))}</h4></div><span>${escapeHtml(result.completed_runs)} / ${escapeHtml(result.total_runs)} runs</span></div>
        <div class="study-result-metrics">
          ${studySummaryLeaderMarkup(result.highest_mean_reward, "Highest observed mean reward")}
          ${success.available === true
            ? studySummaryLeaderMarkup(result.highest_success_rate, "Highest observed success rate", true)
            : '<div class="study-result-metric unavailable"><span>Success rate</span><strong>Not applicable</strong><small>This is a return-only environment.</small></div>'}
        </div>
        ${environmentSuccessMarkup(result.environment_success, result.environment_id)}
      </article>`;
    }).join("") || '<p class="muted">No completed configuration exposed comparable evaluation metrics.</p>'
    : '<div class="study-summary-waiting"><strong>Summary pending</strong><span>Live run evidence remains available below. Environment-level conclusions are withheld until execution stops.</span></div>';
  $("#monitor-study-summary-note").textContent = summary?.available
    ? `${summary.comparison_note} These are descriptive observations, not statistical significance claims.`
    : "Reward leaders are calculated only from completed runs and only within the same environment.";
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function formatTimestamp(value) {
  if (!value) return "unknown time";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

async function refreshMonitoring() {
  if (state.monitorRefreshing) return;
  state.monitorRefreshing = true;
  $("#refresh-monitor-button").disabled = true;
  try {
    const { response, body } = await request("/api/monitor/executions");
    if (!response.ok) throw new Error(body.error || "Monitoring catalog could not be loaded");
    state.monitorExecutions = body.executions || [];
    state.monitorCounts = body.counts || { products: 0, studies: 0 };
    renderExecutionList();
    const selectable = state.monitorExecutions.filter((item) => item.status !== "unreadable");
    if (!selectable.length) {
      state.monitorExecutionId = null;
      state.monitorExecution = null;
      state.monitorRunId = null;
      state.monitorHpoRunId = null;
      state.monitorHpo = null;
      renderMonitorEmpty();
      if (state.mode === "monitor") setConnection("No executions yet", "valid");
      return;
    }
    if (!selectable.some((item) => item.id === state.monitorExecutionId)) {
      state.monitorExecutionId = selectable[0].id;
    }
    await loadMonitorExecution(state.monitorExecutionId, true);
    if (state.mode === "monitor") setConnection("Monitor synced", "valid");
  } catch (error) {
    showToast(`Monitoring refresh failed: ${error.message}`);
    setConnection("Monitor unavailable", "invalid");
  } finally {
    state.monitorRefreshing = false;
    $("#refresh-monitor-button").disabled = false;
  }
}

function renderExecutionList() {
  const products = state.monitorCounts.products || 0;
  const studies = state.monitorCounts.studies || 0;
  $("#monitor-execution-count").textContent = `${products} product${products === 1 ? "" : "s"} · ${studies} stud${studies === 1 ? "y" : "ies"}`;
  if (!state.monitorExecutions.length) {
    $("#monitor-execution-list").innerHTML = '<p class="empty-state">No generated products or study executions found.</p>';
    return;
  }
  const groups = [
    ["product", "Generated products"],
    ["study", "Study executions"],
  ];
  $("#monitor-execution-list").innerHTML = groups.map(([kind, label]) => {
    const items = state.monitorExecutions.filter((item) => item.kind === kind);
    if (!items.length) return "";
    return `<section class="execution-group">
      <div class="execution-group-heading"><span>${escapeHtml(label)}</span><b>${items.length}</b></div>
      ${items.map((execution) => {
        const composition = execution.environment_id && execution.algorithm_id
          ? `${componentDisplayName(execution.environment_id)} + ${componentDisplayName(execution.algorithm_id)}${execution.behavior_id ? ` + ${componentDisplayName(execution.behavior_id)}` : ""}${execution.optimizer_id ? ` + ${componentDisplayName(execution.optimizer_id)}` : ""}`
          : `${execution.configuration_count || 0} configurations`;
        const runText = execution.total_runs
          ? `${execution.completed_runs} / ${execution.total_runs} runs complete`
          : "Generated · no runs yet";
        return `<button type="button" class="execution-button ${execution.id === state.monitorExecutionId ? "active" : ""}"
          data-monitor-execution="${escapeHtml(execution.id)}" ${execution.status === "unreadable" ? "disabled" : ""}>
          <span class="execution-card-meta"><span class="execution-kind ${escapeHtml(kind)}">${escapeHtml(execution.kind_label || kind)}</span>${statusBadge(execution.status)}</span>
          <strong>${escapeHtml(execution.name)}</strong>
          ${execution.hpo_enabled ? '<span class="hpo-execution-label">HPO</span>' : ""}
          <small class="execution-composition">${escapeHtml(composition)}</small>
          <span class="execution-card-foot"><small>${escapeHtml(runText)}</small><time>${escapeHtml(formatTimestamp(execution.updated_at))}</time></span>
          <span class="mini-progress"><span style="width:${Math.max(0, Math.min(100, Number(execution.progress_percent) || 0))}%"></span></span>
          ${execution.error ? `<small class="monitor-error">${escapeHtml(execution.error)}</small>` : ""}
        </button>`;
      }).join("")}
    </section>`;
  }).join("");
}

function renderMonitorEmpty() {
  $("#monitor-empty").hidden = false;
  $("#monitor-dashboard").hidden = true;
  state.monitorHpo = null;
  state.monitorHpoRunId = null;
  $("#monitor-run-detail").innerHTML = '<div class="empty-detail"><h3>Run details</h3><p>Select a run to inspect its reward curve, metrics, configuration, artifacts, and process log.</p></div>';
}

async function loadMonitorExecution(executionId, preserveRun = false) {
  const { response, body } = await request(`/api/monitor/execution?execution_id=${encodeURIComponent(executionId)}`);
  if (!response.ok) throw new Error(body.error || "Execution could not be loaded");
  state.monitorExecutionId = executionId;
  state.monitorExecution = body;
  if (!preserveRun || !body.runs.some((item) => item.run_id === state.monitorRunId)) {
    state.monitorRunId = null;
  }
  const hpoRuns = body.runs.filter((item) => item.hpo_enabled);
  let selectedHpoRun = hpoRuns.find((item) => item.run_id === state.monitorHpoRunId);
  if (!selectedHpoRun && state.monitorRunId) {
    selectedHpoRun = hpoRuns.find((item) => item.run_id === state.monitorRunId);
  }
  selectedHpoRun ||= hpoRuns[0];
  state.monitorHpoRunId = selectedHpoRun?.run_id || null;
  state.monitorHpo = selectedHpoRun?.hpo_progress || (body.hpo_enabled ? {
    enabled: true,
    available: false,
    status: "pending",
    progress_percent: 0,
    completed_trials: 0,
    failed_trials: 0,
  } : null);
  renderExecutionList();
  renderMonitorDashboard();
  if (state.monitorHpoRunId) await loadMonitorHpo(state.monitorHpoRunId);
  if (state.monitorRunId) await loadMonitorRun(state.monitorRunId);
}

function renderMonitorDashboard() {
  const execution = state.monitorExecution;
  if (!execution) {
    renderMonitorEmpty();
    return;
  }
  $("#monitor-empty").hidden = true;
  $("#monitor-dashboard").hidden = false;
  $("#monitor-kind-label").textContent = `Selected ${execution.kind || "execution"}`;
  $("#monitor-study-name").textContent = execution.name;
  $("#monitor-study-status").className = `run-status ${execution.status}`;
  $("#monitor-study-status").textContent = execution.status;
  $("#monitor-study-meta").textContent = execution.kind === "product"
    ? `${componentDisplayName(execution.environment_id)} + ${componentDisplayName(execution.algorithm_id)} + ${componentDisplayName(execution.behavior_id)} + ${componentDisplayName(execution.optimizer_id)} · generated product · ${execution.total_runs} recorded run${execution.total_runs === 1 ? "" : "s"} · updated ${formatTimestamp(execution.updated_at)}`
    : `${execution.execution_id} · updated ${formatTimestamp(execution.updated_at)} · ${execution.configuration_count} configurations × ${execution.seed_count} seeds`;
  const lifecycleNote = $("#monitor-lifecycle-note");
  lifecycleNote.hidden = !execution.lifecycle_message;
  lifecycleNote.textContent = execution.lifecycle_message || "";
  $("#monitor-progress-fill").style.width = `${Math.max(0, Math.min(100, Number(execution.progress_percent) || 0))}%`;
  const counts = execution.counts || {};
  const activeHyperparameters = Object.keys(execution.comparisons?.[0]?.hyperparameters || {}).length;
  const summaryItems = execution.kind === "product" ? [
    [execution.configuration_count, "Configuration"],
    [execution.total_runs, "Recorded runs"],
    [counts.running || 0, "Running"],
    [counts.completed || 0, "Completed"],
    [activeHyperparameters, "Active hyperparams"],
  ] : [
    [execution.configuration_count, "Configurations"],
    [execution.total_runs, "Planned runs"],
    [counts.running || 0, "Running"],
    [counts.completed || 0, "Completed"],
    [counts.pending || 0, "Pending"],
    [(counts.failed || 0) + (counts.interrupted || 0), "Needs attention"],
  ];
  $("#monitor-summary-grid").innerHTML = summaryItems.map(([value, label]) => `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join("");
  const previousAlgorithm = $("#monitor-algorithm-filter").value;
  $("#monitor-algorithm-filter").innerHTML = '<option value="all">All algorithms</option>' + execution.algorithms.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(componentDisplayName(id))}</option>`).join("");
  if (execution.algorithms.includes(previousAlgorithm)) $("#monitor-algorithm-filter").value = previousAlgorithm;
  const previousBehavior = $("#monitor-behavior-filter").value;
  const behaviors = execution.behaviors || [];
  $("#monitor-behavior-filter").innerHTML = '<option value="all">All behaviors</option>' + behaviors.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(componentDisplayName(id))}</option>`).join("");
  if (behaviors.includes(previousBehavior)) $("#monitor-behavior-filter").value = previousBehavior;
  const previousOptimizer = $("#monitor-optimizer-filter").value;
  const optimizers = execution.optimizers || [];
  $("#monitor-optimizer-filter").innerHTML = '<option value="all">All optimizers</option>' + optimizers.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(componentDisplayName(id))}</option>`).join("");
  if (optimizers.includes(previousOptimizer)) $("#monitor-optimizer-filter").value = previousOptimizer;
  renderMonitorRuns();
  renderMonitorHpoDashboard();
  renderMonitorStudySummary();
  renderMonitorVariability();
  renderMonitorComparisons();
  if (!state.monitorRunId) {
    $("#monitor-run-detail").innerHTML = '<div class="empty-detail"><h3>Run details</h3><p>Select a row to inspect its reward curve, metrics, configuration, artifacts, and process log.</p></div>';
  }
}

async function loadMonitorHpo(runId) {
  if (!state.monitorExecutionId) return;
  const executionId = state.monitorExecutionId;
  try {
    const query = new URLSearchParams({ execution_id: executionId, run_id: runId });
    const { response, body } = await request(`/api/monitor/hpo?${query}`);
    if (!response.ok) throw new Error(body.error || "HPO evidence could not be loaded");
    if (state.monitorExecutionId === executionId && state.monitorHpoRunId === runId) {
      state.monitorHpo = body;
      renderMonitorHpoDashboard();
    }
  } catch (error) {
    if (state.monitorExecutionId === executionId && state.monitorHpoRunId === runId) {
      state.monitorHpo = { ...(state.monitorHpo || {}), enabled: true, error: error.message };
      renderMonitorHpoDashboard();
    }
  }
}

function hpoSamplerName(value) {
  if (value === "bayesian_tpe") return "Bayesian TPE";
  if (value === "random") return "Random search";
  return String(value || "Not started");
}

function hpoParameterPairs(parameters, emptyText = "No parameter values yet") {
  const entries = Object.entries(parameters || {});
  if (!entries.length) return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  return `<div class="hpo-parameter-pairs">${entries.map(([name, value]) => `<div><span>${escapeHtml(name)}</span><strong>${escapeHtml(formatSettingValue(name, value))}</strong></div>`).join("")}</div>`;
}

function hpoDomainText(domain) {
  if (!domain) return "Unknown domain";
  if (domain.kind === "categorical") {
    return `{${(domain.choices || []).map((value) => formatSettingValue("", value)).join(", ")}}`;
  }
  const scale = domain.kind === "log_float" ? "log" : domain.kind === "integer" ? "integer" : "linear";
  return `${formatSettingValue("", domain.lower)} … ${formatSettingValue("", domain.upper)} · ${scale}`;
}

function hpoHistoryChart(history) {
  const points = (history || []).filter((item) =>
    Number.isFinite(Number(item.objective_value)) && Number.isFinite(Number(item.best_so_far))
  );
  if (!points.length) {
    return '<div class="chart-empty">The objective curve appears after the first completed trial.</div>';
  }
  const width = 700;
  const height = 220;
  const margin = { left: 55, right: 18, top: 18, bottom: 34 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const values = points.flatMap((item) => [Number(item.objective_value), Number(item.best_so_far)]);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const padding = maximum === minimum
    ? Math.max(1, Math.abs(maximum) * .05)
    : (maximum - minimum) * .1;
  const yMin = minimum - padding;
  const yMax = maximum + padding;
  const x = (index) => margin.left + (
    points.length === 1 ? plotWidth / 2 : index / (points.length - 1) * plotWidth
  );
  const y = (value) => margin.top + (yMax - value) / (yMax - yMin) * plotHeight;
  const path = (field) => points.map((item, index) =>
    `${index ? "L" : "M"}${x(index).toFixed(1)} ${y(Number(item[field])).toFixed(1)}`
  ).join(" ");
  const grid = [0, .5, 1].map((fraction) => {
    const value = yMax - fraction * (yMax - yMin);
    const vertical = margin.top + fraction * plotHeight;
    return `<line class="chart-grid" x1="${margin.left}" y1="${vertical}" x2="${width - margin.right}" y2="${vertical}"/><text class="chart-label" x="${margin.left - 7}" y="${vertical + 3}" text-anchor="end">${escapeHtml(formatMetric(value))}</text>`;
  }).join("");
  const dots = points.map((item, index) =>
    `<circle class="hpo-trial-dot" cx="${x(index)}" cy="${y(Number(item.objective_value))}" r="3.6"><title>Trial ${escapeHtml(item.trial_number)}: ${escapeHtml(formatMetric(item.objective_value))}</title></circle>`
  ).join("");
  const last = points[points.length - 1];
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="HPO objective by completed trial">
    ${grid}<line class="chart-axis" x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}"/>
    <path class="hpo-objective-line" d="${path("objective_value")}"/><path class="hpo-best-line" d="${path("best_so_far")}"/>${dots}
    <text class="chart-label" x="${margin.left}" y="${height - 10}">trial ${escapeHtml(points[0].trial_number)}</text><text class="chart-label" x="${width - margin.right}" y="${height - 10}" text-anchor="end">trial ${escapeHtml(last.trial_number)}</text>
  </svg><div class="chart-legend hpo-chart-legend"><span>Trial objective</span><span>Best so far</span></div>`;
}

function renderMonitorHpoDashboard() {
  const card = $("#monitor-hpo-dashboard");
  if (!card) return;
  const hpo = state.monitorHpo;
  const enabled = Boolean(state.monitorExecution?.hpo_enabled || hpo?.enabled);
  card.hidden = !enabled;
  if (!enabled) return;
  const selectedRun = (state.monitorExecution?.runs || []).find(
    (run) => run.run_id === state.monitorHpoRunId
  );
  const environmentId = selectedRun?.environment_id;
  const environmentSuccess = hpo?.environment_success || selectedRun?.environment_success;

  const status = hpo?.status || "pending";
  $("#monitor-hpo-status").className = `run-status ${status}`;
  $("#monitor-hpo-status").textContent = status;
  const seeds = hpo?.search_seeds || [];
  const phase = String(hpo?.phase || "waiting to start").replaceAll("_", " ");
  $("#monitor-hpo-meta").textContent = hpo?.available
    ? `${state.monitorHpoRunId} · ${hpoSamplerName(hpo.sampler)} · maximize ${String(hpo.objective || "objective").replaceAll("_", " ")} with ${hpo.aggregation || "mean"} across seeds [${seeds.join(", ")}] · ${phase}`
    : "This configuration contains HPO. Its live trial dashboard appears when the generated product starts running.";
  $("#monitor-hpo-progress-fill").style.width = `${Math.max(0, Math.min(100, Number(hpo?.progress_percent) || 0))}%`;

  const best = hpo?.best;
  const summary = [
    [`${hpo?.completed_trials || 0} / ${hpo?.trial_budget ?? "—"}`, "Completed trials"],
    [hpo?.failed_trials || 0, "Failed trials"],
    [`${hpo?.completed_seed_runs || 0} / ${hpo?.planned_seed_runs ?? "—"}`, "Trial seed fits"],
    [best ? formatMetric(best.objective_value) : "—", "Best objective"],
    [seeds.length || "—", "Seeds per trial"],
    [hpo?.sampler_seed ?? "—", "Sampler seed"],
  ];
  $("#monitor-hpo-summary").innerHTML = summary.map(([value, label]) =>
    `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`
  ).join("");
  $("#monitor-hpo-success-context").innerHTML = environmentSuccessMarkup(
    environmentSuccess, environmentId
  );
  $("#monitor-hpo-history").innerHTML = hpoHistoryChart(hpo?.history);
  $("#monitor-hpo-best-label").textContent = best
    ? `Trial ${best.trial_number} · ${formatMetric(best.objective_value)}`
    : "No completed trial";
  $("#monitor-hpo-best").innerHTML = hpoParameterPairs(
    best?.parameters, "Waiting for a successful trial."
  );

  const domains = Object.entries(hpo?.search_space || {});
  $("#monitor-hpo-space").innerHTML = domains.length
    ? domains.map(([name, domain]) => `<div><span>${escapeHtml(name)}</span><strong>${escapeHtml(hpoDomainText(domain))}</strong></div>`).join("")
    : '<p class="muted">Search domains will appear when execution starts.</p>';

  const leading = hpo?.top_trials || [];
  $("#monitor-hpo-trial-count").textContent = `${hpo?.completed_trials || 0} completed · showing ${leading.length}`;
  $("#monitor-hpo-trials").innerHTML = leading.length ? leading.map((trial, index) => {
    const seedScores = (trial.seed_results || []).map((item) =>
      `${item.seed}: ${formatMetric(item.objective_value)}`
    ).join(" · ");
    const duration = Number.isFinite(Number(trial.duration_seconds))
      ? `${formatMetric(trial.duration_seconds, 1)} s`
      : "—";
    return `<tr><td><strong>#${index + 1}</strong></td><td>${escapeHtml(trial.trial_number)}</td><td class="metric-value">${escapeHtml(formatMetric(trial.objective_value))}</td><td>${escapeHtml(seedScores || "—")}</td><td>${escapeHtml(duration)}</td><td>${hpoParameterPairs(trial.parameters)}</td></tr>`;
  }).join("") : '<tr><td colspan="6" class="muted">Trial evidence will appear while search runs.</td></tr>';

  const failures = (hpo?.trials || []).filter((trial) => trial.status === "failed");
  $("#monitor-hpo-failures").hidden = failures.length === 0;
  $("#monitor-hpo-failure-count").textContent = `${failures.length} failed`;
  $("#monitor-hpo-failure-list").innerHTML = failures.map((trial) => `<article><div><strong>Trial ${escapeHtml(trial.trial_number)}</strong><span>${escapeHtml(trial.error || "No error message was recorded.")}</span></div>${hpoParameterPairs(trial.parameters)}</article>`).join("");

  const finalMetrics = Object.entries(hpo?.final_evaluation_metrics || {});
  $("#monitor-hpo-final-status").textContent = hpo?.phase === "completed"
    ? "Best parameters refitted and evaluated on the final seeds"
    : hpo?.phase === "final_fit"
      ? "Search complete · training the selected configuration"
      : "Waiting for the selected configuration";
  $("#monitor-hpo-final-metrics").innerHTML = finalMetrics.map(([name, value]) =>
    `<div><span>${escapeHtml(name.replaceAll("_", " "))}</span><strong>${escapeHtml(formatMetric(value))}</strong></div>`
  ).join("");
  if (hpo?.error) {
    $("#monitor-hpo-final-metrics").innerHTML += `<p class="monitor-error">${escapeHtml(hpo.error)}</p>`;
  }
}

function filteredMonitorRuns() {
  if (!state.monitorExecution) return [];
  const status = $("#monitor-status-filter").value;
  const algorithm = $("#monitor-algorithm-filter").value;
  const behavior = $("#monitor-behavior-filter").value;
  const optimizer = $("#monitor-optimizer-filter").value;
  const query = $("#monitor-run-search").value.trim().toLowerCase();
  return state.monitorExecution.runs.filter((run) => {
    if (status !== "all" && run.status !== status) return false;
    if (algorithm !== "all" && run.algorithm_id !== algorithm) return false;
    if (behavior !== "all" && run.behavior_id !== behavior) return false;
    if (optimizer !== "all" && run.optimizer_id !== optimizer) return false;
    if (!query) return true;
    return [run.run_id, run.configuration_id, run.configuration_name, run.environment_id, run.algorithm_id, run.behavior_id, run.optimizer_id, run.training_seed, JSON.stringify(run.varied_values || {})]
      .some((value) => String(value).toLowerCase().includes(query));
  });
}

function renderMonitorRuns() {
  const runs = filteredMonitorRuns();
  $("#monitor-visible-run-count").textContent = `${runs.length} shown`;
  $("#monitor-run-rows").innerHTML = runs.length ? runs.map((run) => {
    const progress = run.progress || {};
    const hpo = run.hpo_progress || {};
    const percent = run.status === "completed"
      ? 100
      : run.hpo_enabled ? hpo.progress_percent : progress.budget_percent;
    const unitValue = run.training_budget_unit === "timesteps" ? progress.total_steps : progress.episode;
    const trainingText = run.hpo_enabled
      ? `${hpo.completed_trials || 0} / ${hpo.trial_budget ?? "—"} trials · ${hpo.completed_seed_runs || 0} seed fits`
      : Number.isFinite(Number(percent))
        ? `${formatMetric(unitValue, 0)} / ${formatMetric(run.training_budget, 0)} ${run.training_budget_unit}`
        : run.status;
    const seedText = run.hpo_enabled
      ? `${(hpo.search_seeds || []).length || "—"} / trial`
      : run.training_seed;
    const latestMetric = run.hpo_enabled ? hpo.best?.objective_value : progress.latest_reward;
    return `<tr data-monitor-run="${escapeHtml(run.run_id)}" class="${run.run_id === state.monitorRunId ? "selected" : ""}">
      <td>${statusBadge(run.status)}</td>
      <td><strong>${escapeHtml(run.configuration_name)}</strong>${run.hpo_enabled ? '<span class="hpo-run-label">HPO</span>' : ""}<br><small>${escapeHtml(componentDisplayName(run.environment_id))}</small></td>
      <td><strong>${escapeHtml(componentDisplayName(run.algorithm_id))}</strong><br><small>${escapeHtml(componentDisplayName(run.behavior_id))} · ${escapeHtml(componentDisplayName(run.optimizer_id))}</small></td>
      <td>${variedSettingsMarkup(run.varied_values, "Fixed configuration")}</td>
      <td>${escapeHtml(seedText)}</td>
      <td><div class="run-progress-cell"><span>${escapeHtml(trainingText)}</span><span class="mini-progress"><span style="width:${Number.isFinite(Number(percent)) ? Math.max(0, Math.min(100, Number(percent))) : 0}%"></span></span></div></td>
      <td class="metric-value">${rewardMetricMarkup(latestMetric, run.environment_success, run.environment_id)}</td>
    </tr>`;
  }).join("") : '<tr><td colspan="7" class="muted">No runs match these filters. A newly generated product appears here before its first run.</td></tr>';
}

function renderMonitorComparisons() {
  const comparisons = state.monitorExecution?.comparisons || [];
  $("#monitor-comparison-rows").innerHTML = comparisons.length ? comparisons.map((item) => `
    <tr>
      <td><code>${escapeHtml(item.configuration_id)}</code></td>
      <td><strong>${escapeHtml(componentDisplayName(item.algorithm_id))}</strong><br><small>${escapeHtml(componentDisplayName(item.environment_id))} · ${escapeHtml(componentDisplayName(item.behavior_id))} · ${escapeHtml(componentDisplayName(item.optimizer_id))}</small></td>
      <td>${variedSettingsMarkup(item.varied_values, "Single resolved configuration")}</td>
      <td>${escapeHtml(item.completed_seeds)} / ${escapeHtml(item.total_seeds)}</td>
      <td class="metric-value">${rewardMetricMarkup(item.metric_means.average_reward, item.environment_success, item.environment_id)}</td>
      <td class="metric-value">${escapeHtml(formatSuccessRate(item.metric_means.success_rate))}</td>
    </tr>`).join("") : '<tr><td colspan="6" class="muted">No configurations are available for comparison.</td></tr>';
}

async function loadMonitorRun(runId) {
  if (!state.monitorExecutionId) return;
  state.monitorRunId = runId;
  renderMonitorRuns();
  const detailPanel = $("#monitor-run-detail");
  detailPanel.scrollTop = 0;
  detailPanel.innerHTML = '<div class="empty-detail"><p>Loading run evidence…</p></div>';
  try {
    const { response, body } = await request(`/api/monitor/run?execution_id=${encodeURIComponent(state.monitorExecutionId)}&run_id=${encodeURIComponent(runId)}`);
    if (!response.ok) throw new Error(body.error || "Run details could not be loaded");
    if (state.monitorRunId === runId) {
      if (body.hpo?.enabled) {
        state.monitorHpoRunId = runId;
        state.monitorHpo = body.hpo;
        renderMonitorHpoDashboard();
      }
      renderMonitorRunDetail(body);
    }
  } catch (error) {
    $("#monitor-run-detail").innerHTML = `<div class="monitor-error">${escapeHtml(error.message)}</div>`;
  }
}

function resolvedHyperparameters(configuration) {
  return Object.entries(configuration?.effective_parameters || {}).map(([target, binding]) => ({
    target,
    value: binding?.mode === "fixed" ? binding.value : { mode: binding?.mode, domain: binding?.domain },
    mode: binding?.mode || "unknown",
  }));
}

function runConfigurationMarkup(configuration, run) {
  if (!configuration) return '<p class="muted">The resolved configuration is not available yet.</p>';
  const parameters = resolvedHyperparameters(configuration);
  const variedTargets = new Set(Object.keys(run.varied_values || {}));
  return `
    <div class="configuration-facts">
      <div><span>Environment</span><strong>${escapeHtml(componentDisplayName(configuration.environment_id))}</strong></div>
      <div><span>Algorithm</span><strong>${escapeHtml(componentDisplayName(configuration.algorithm_id))}</strong></div>
      <div><span>Action behavior</span><strong>${escapeHtml(componentDisplayName(configuration.behavior_id))}</strong></div>
      <div><span>Optimizer / update rule</span><strong>${escapeHtml(componentDisplayName(configuration.optimizer_id))}</strong></div>
      <div><span>Training budget</span><strong>${escapeHtml(configuration.training_budget)} ${escapeHtml(configuration.training_budget_unit)}</strong></div>
      <div><span>Checkpoint</span><strong>${escapeHtml(configuration.checkpoint_policy || "disabled")}</strong></div>
    </div>
    <div class="selected-variation"><span>Values that distinguish this configuration</span>${variedSettingsMarkup(run.varied_values, "This execution contains one resolved configuration")}</div>
    <div class="detail-section-heading hyperparameter-heading"><h4>Effective hyperparameters</h4><span>${parameters.length} resolved</span></div>
    <div class="hyperparameter-list">${parameters.map((parameter) => `
      <div class="${variedTargets.has(parameter.target) ? "varied" : ""}">
        <span>${escapeHtml(parameter.target)}${variedTargets.has(parameter.target) ? '<b>VARIES</b>' : ""}</span>
        <strong>${escapeHtml(formatSettingValue(parameter.target, parameter.value))}</strong>
      </div>`).join("")}</div>`;
}

function hpoRunDetailMarkup(hpo, environmentId) {
  if (!hpo?.enabled) return "";
  const best = hpo.best;
  return `<section class="detail-section hpo-run-detail-section">
    <div class="detail-section-heading"><h4>HPO selection evidence</h4><span>${escapeHtml(hpoSamplerName(hpo.sampler))}</span></div>
    <div class="detail-metrics">
      <div><span>Search progress</span><strong>${escapeHtml(`${hpo.completed_trials || 0} / ${hpo.trial_budget ?? "—"} trials`)}</strong></div>
      <div><span>Best objective</span><strong>${escapeHtml(best ? formatMetric(best.objective_value) : "—")}</strong></div>
      <div><span>Aggregation</span><strong>${escapeHtml(hpo.aggregation || "—")}</strong></div>
      <div><span>Trial seeds</span><strong>${escapeHtml((hpo.search_seeds || []).join(", ") || "—")}</strong></div>
    </div>
    ${environmentSuccessMarkup(hpo.environment_success, environmentId)}
    <div class="detail-section-heading hyperparameter-heading"><h4>Selected parameters</h4><span>${best ? `trial ${escapeHtml(best.trial_number)}` : "pending"}</span></div>
    ${hpoParameterPairs(best?.parameters, "No successful trial yet.")}
  </section>`;
}

function renderMonitorRunDetail(detail) {
  const run = detail.run;
  const metricEntries = [
    ...Object.entries(detail.metrics?.metrics || {}).map(([name, value]) => ({
      name, value, reward: isRewardMetric(name),
    })),
    ...Object.entries(detail.metrics?.reward_summaries || {}).map(([name, value]) => ({
      name, value, reward: true,
    })),
  ];
  const progress = run.progress || {};
  const artifacts = detail.artifacts || [];
  const isHpo = Boolean(detail.hpo?.enabled);
  $("#monitor-run-detail").innerHTML = `
    <div class="run-detail-header">
      <div><p class="eyebrow">${isHpo ? "HPO-selected agent" : "Run evidence"}</p><h3>${escapeHtml(run.run_id)}</h3><p class="run-detail-subtitle">${escapeHtml(componentDisplayName(run.environment_id))} · ${escapeHtml(componentDisplayName(run.algorithm_id))} · ${escapeHtml(componentDisplayName(run.behavior_id))} · ${escapeHtml(componentDisplayName(run.optimizer_id))} · ${isHpo ? "final-fit seed" : "seed"} ${escapeHtml(run.training_seed)}</p></div>
      ${statusBadge(run.status)}
    </div>
    ${run.error ? `<p class="monitor-error">${escapeHtml(run.error)}</p>` : ""}
    ${hpoRunDetailMarkup(detail.hpo, run.environment_id)}
    <section class="detail-section configuration-detail-section">
      <div class="detail-section-heading"><h4>${isHpo ? "Selected fixed configuration" : "Resolved product configuration"}</h4><span>${isHpo ? "Materialized from the winning trial" : "Exact run input"}</span></div>
      ${runConfigurationMarkup(detail.configuration, run)}
    </section>
    <section class="detail-section reward-detail-section">
      <div class="detail-section-heading"><h4>${isHpo ? "Final-fit training reward" : "Training reward"}</h4><span>${escapeHtml(detail.trace.length)} plotted points</span></div>
      <div class="reward-chart">${rewardChart(detail.trace)}</div>
      <div class="chart-legend"><span>Episode reward</span><span>Rolling mean</span></div>
      ${environmentSuccessMarkup(run.environment_success, run.environment_id)}
    </section>
    <section class="detail-section progress-detail-section">
      <div class="detail-section-heading"><h4>Latest progress</h4><span>Observational telemetry</span></div>
      <div class="detail-metrics">
        <div><span>Episode</span><strong>${escapeHtml(formatMetric(progress.episode, 0))}</strong></div>
        <div><span>Environment steps</span><strong>${escapeHtml(formatMetric(progress.total_steps, 0))}</strong></div>
        <div class="reward-metric-card"><span>Latest reward</span><strong>${escapeHtml(formatMetric(progress.latest_reward))}</strong><small>Interpret with the environment signal above.</small></div>
        <div class="reward-metric-card"><span>25-point reward mean</span><strong>${escapeHtml(formatMetric(progress.rolling_reward))}</strong><small>Interpret with the environment signal above.</small></div>
        <div><span>Observed success</span><strong>${escapeHtml(formatSuccessRate(progress.success_rate))}</strong></div>
        <div><span>Duration</span><strong>${escapeHtml(run.duration_seconds === null ? "—" : `${formatMetric(run.duration_seconds, 1)} s`)}</strong></div>
      </div>
    </section>
    <section class="detail-section evaluation-detail-section">
      <div class="detail-section-heading"><h4>Evaluation metrics</h4><span>Completed run</span></div>
      <div class="detail-metrics">${metricEntries.length ? metricEntries.map(({ name, value, reward }) => `<div class="${reward ? "reward-metric-card" : ""}"><span>${escapeHtml(name.replaceAll("_", " "))}</span><strong>${escapeHtml(name === "success_rate" ? formatSuccessRate(value) : formatMetric(value))}</strong>${reward ? '<small>Interpret with the environment signal above.</small>' : ""}</div>`).join("") : '<p class="muted">Metrics are available after the run completes.</p>'}</div>
    </section>
    <section class="detail-section artifacts-detail-section">
      <div class="detail-section-heading"><h4>Artifacts</h4><span>${escapeHtml(artifacts.length)} files</span></div>
      ${artifacts.length ? `<ul class="artifact-list">${artifacts.map((item) => `<li><span>${escapeHtml(item.name)}</span><span>${escapeHtml(formatBytes(item.size_bytes))}</span></li>`).join("")}</ul>` : '<p class="muted">No artifact files are visible yet.</p>'}
    </section>
    <details class="detail-disclosure"><summary>Resolved configuration</summary><pre>${escapeHtml(JSON.stringify(detail.configuration, null, 2))}</pre></details>
    <details class="detail-disclosure"><summary>Run metadata</summary><pre>${escapeHtml(JSON.stringify(detail.metadata, null, 2))}</pre></details>
    <details class="detail-disclosure"><summary>Process log tail</summary><pre>${escapeHtml(detail.log_tail || "No log output yet.")}</pre></details>`;
}

function rewardChart(points) {
  if (!points?.length) return '<div class="chart-empty">The live curve appears after the first logging interval. Completed runs use the full reward trace.</div>';
  const width = 340;
  const height = 190;
  const margin = { left: 43, right: 12, top: 13, bottom: 29 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const rewards = points.map((item) => Number(item.reward)).filter(Number.isFinite);
  if (!rewards.length) return '<div class="chart-empty">No finite reward values are available.</div>';
  const minimum = Math.min(...rewards);
  const maximum = Math.max(...rewards);
  const padding = maximum === minimum ? Math.max(1, Math.abs(maximum) * .05) : (maximum - minimum) * .08;
  const yMin = minimum - padding;
  const yMax = maximum + padding;
  const x = (index) => margin.left + (points.length === 1 ? plotWidth / 2 : index / (points.length - 1) * plotWidth);
  const y = (value) => margin.top + (yMax - value) / (yMax - yMin) * plotHeight;
  const rawPath = points.map((item, index) => `${index ? "L" : "M"}${x(index).toFixed(1)} ${y(Number(item.reward)).toFixed(1)}`).join(" ");
  const rolling = points.map((item, index) => {
    const window = points.slice(Math.max(0, index - 24), index + 1);
    return window.reduce((sum, point) => sum + Number(point.reward), 0) / window.length;
  });
  const rollingPath = rolling.map((value, index) => `${index ? "L" : "M"}${x(index).toFixed(1)} ${y(value).toFixed(1)}`).join(" ");
  const firstEpisode = points[0].episode;
  const lastEpisode = points[points.length - 1].episode;
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Training reward curve from episode ${escapeHtml(firstEpisode)} to ${escapeHtml(lastEpisode)}">
    <path class="chart-grid" d="M${margin.left} ${margin.top}H${width - margin.right}M${margin.left} ${margin.top + plotHeight / 2}H${width - margin.right}M${margin.left} ${margin.top + plotHeight}H${width - margin.right}"/>
    <path class="chart-axis" d="M${margin.left} ${margin.top}V${height - margin.bottom}H${width - margin.right}"/>
    <path class="chart-line" d="${rawPath}"/><path class="chart-rolling" d="${rollingPath}"/>
    <text class="chart-label" x="${margin.left - 5}" y="${margin.top + 4}" text-anchor="end">${escapeHtml(formatMetric(yMax, 1))}</text>
    <text class="chart-label" x="${margin.left - 5}" y="${height - margin.bottom}" text-anchor="end">${escapeHtml(formatMetric(yMin, 1))}</text>
    <text class="chart-label" x="${margin.left}" y="${height - 9}">${escapeHtml(firstEpisode)}</text>
    <text class="chart-label" x="${width - margin.right}" y="${height - 9}" text-anchor="end">episode ${escapeHtml(lastEpisode)}</text>
  </svg>`;
}

function splRelationSymbol(relation) {
  return {
    root: "ROOT",
    mandatory: "M",
    optional: "O",
    alternative: "XOR",
    or_group: "OR",
  }[relation] || relation.toUpperCase();
}

function splFeatureNodeMarkup(node, selected, hasTrace) {
  const isSelected = node.relation === "root" || selected.has(node.id);
  const selectionClass = !hasTrace ? "" : (isSelected ? "selected" : "unselected");
  const metadata = [
    node.kind && node.kind !== "root" ? node.kind.replaceAll("_", " ") : null,
    node.group ? `${node.group}${node.cardinality ? ` ${node.cardinality}` : ""}` : null,
    node.origin && node.origin !== "builtin" ? "plug-in" : null,
  ].filter(Boolean).map((item) => `<em>${escapeHtml(item)}</em>`).join("");
  const children = (node.children || []).map((child) => splFeatureNodeMarkup(child, selected, hasTrace)).join("");
  return `<div class="spl-tree-node">
    <div class="spl-node-card ${node.relation === "root" ? "root" : ""} ${selectionClass}">
      <span class="spl-relation-symbol">${escapeHtml(splRelationSymbol(node.relation))}</span>
      <div class="spl-node-copy"><strong>${escapeHtml(node.label)}</strong>${node.description ? `<span>${escapeHtml(node.description)}</span>` : ""}${node.detail ? `<small>${escapeHtml(node.detail)}</small>` : ""}</div>
      <div class="spl-node-meta">${metadata}</div>
    </div>
    ${children ? `<div class="spl-tree-children">${children}</div>` : ""}
  </div>`;
}

function renderSplFeatureTree() {
  const model = state.catalog?.spl_model;
  if (!model) return;
  const selected = new Set(state.splTrace?.selected_feature_ids || []);
  $("#spl-feature-tree").innerHTML = splFeatureNodeMarkup(model.tree, selected, Boolean(state.splTrace));
}

function renderSplConstraints() {
  const model = state.catalog?.spl_model;
  if (!model) return;
  const filter = $("#spl-constraint-filter")?.value || "all";
  const statuses = state.splTrace?.constraint_statuses || {};
  const constraints = model.constraints.filter((constraint) => {
    if (filter === "all") return true;
    const status = statuses[constraint.id]?.status || "pending";
    return status === filter || constraint.category === filter;
  });
  const counts = model.constraints.reduce((result, constraint) => {
    const status = statuses[constraint.id]?.status || "pending";
    result[status] = (result[status] || 0) + 1;
    return result;
  }, {});
  $("#spl-constraint-summary").innerHTML = state.splTrace
    ? ["satisfied", "violated", "advisory", "not_applicable"].filter((key) => counts[key]).map((key) => `<span class="${escapeHtml(key)}">${escapeHtml(counts[key])} ${escapeHtml(key.replaceAll("_", " "))}</span>`).join("")
    : '<span>Trace the current Configure selection to evaluate applicability and status.</span>';
  $("#spl-constraint-rows").innerHTML = constraints.length ? constraints.map((constraint) => {
    const projection = statuses[constraint.id] || { status: "pending", issues: [] };
    const codes = (constraint.enforcement_codes || []).map((code) => `<code>${escapeHtml(code)}</code>`).join("");
    const paper = (constraint.paper_rules || []).map((rule) => `<span class="constraint-paper-rule">paper ${escapeHtml(rule)}</span>`).join("");
    const messages = (projection.issues || []).map((issue) => `<div class="constraint-message">${escapeHtml(issue.code)} · ${escapeHtml(issue.message)}</div>`).join("");
    return `<tr>
      <td><span class="constraint-status ${escapeHtml(projection.status)}">${escapeHtml(projection.status.replaceAll("_", " "))}</span></td>
      <td class="constraint-id"><strong>${escapeHtml(constraint.id)}</strong><span>${escapeHtml(constraint.category)} · ${escapeHtml(constraint.relation)}</span></td>
      <td class="constraint-expression">${escapeHtml(constraint.expression)}</td>
      <td class="constraint-meaning">${escapeHtml(constraint.explanation)}<div class="constraint-codes">${codes}${paper}</div>${messages}</td>
    </tr>`;
  }).join("") : '<tr><td colspan="4" class="muted">No constraints match this filter.</td></tr>';
}

function renderSplSelection() {
  const trace = state.splTrace;
  if (!trace) {
    $("#spl-selection-summary").innerHTML = '<p class="muted">Trace the Configure selection to populate this view.</p>';
    $("#spl-derivation-trace").innerHTML = "";
    return;
  }
  const selection = trace.selection;
  const composition = trace.composition || {};
  const roles = [
    ...(composition.architecture_roles || []),
    ...(composition.optimizer_roles || []),
    composition.exploration_role,
    composition.memory_role,
    composition.target_update ? `${composition.target_update} target update` : null,
  ].filter(Boolean);
  $("#spl-selection-summary").innerHTML = `
    <div class="spl-selection-fact"><span>Environment alternative</span><strong>${escapeHtml(selection.environment.name)}</strong></div>
    <div class="spl-selection-fact"><span>Algorithm alternative</span><strong>${escapeHtml(selection.algorithm.name)}</strong></div>
    <div class="spl-selection-fact"><span>Action-behavior alternative</span><strong>${escapeHtml(selection.behavior.name)}</strong></div>
    <div class="spl-selection-fact"><span>Optimizer alternative</span><strong>${escapeHtml(selection.optimizer.name)}</strong></div>
    <div class="spl-selection-fact"><span>Optional search feature</span><strong>${selection.search_enabled ? "Selected" : "Not selected"}</strong></div>
    <div class="spl-selection-fact"><span>Evaluation mode</span><strong>${escapeHtml(selection.evaluation_protocol)}</strong></div>
    <div class="spl-selection-fact"><span>Effective parameter features</span><strong>${escapeHtml(trace.effective_parameters.length)}</strong></div>
    <div class="spl-composition-list">${roles.map((role) => `<span>${escapeHtml(role)}</span>`).join("")}</div>`;
  $("#spl-derivation-trace").innerHTML = trace.derivation.map((step, index) => `
    <div class="spl-derivation-step"><b>${index + 1}</b><strong>${escapeHtml(step.stage)}</strong><span>${escapeHtml(step.result)}</span></div>`).join("");
}

function renderSplPairingMatrix() {
  const model = state.catalog?.spl_model;
  const rows = model?.pairing_matrix || [];
  const container = $("#spl-pairing-matrix");
  if (!container || !rows.length) return;
  const algorithms = rows[0].pairings || [];
  const selectedEnvironment = state.splTrace?.selection?.environment?.id;
  const selectedAlgorithm = state.splTrace?.selection?.algorithm?.id;
  container.innerHTML = `<table class="variant-table spl-pairing-table">
    <thead><tr><th scope="col">Environment / action contract</th>${algorithms.map((algorithm) => `
      <th scope="col" class="spl-pairing-head"><span>${escapeHtml(algorithm.algorithm_name)}</span><code>${escapeHtml(algorithm.algorithm_id)}</code></th>`).join("")}</tr></thead>
    <tbody>${rows.map((row) => `<tr>
      <th scope="row" class="spl-environment-head"><span>${escapeHtml(row.environment_name)}</span><code>${escapeHtml(row.action_kind)} · ${escapeHtml(row.environment_id)}</code></th>
      ${row.pairings.map((pairing) => {
        const selected = row.environment_id === selectedEnvironment && pairing.algorithm_id === selectedAlgorithm;
        const stateClass = pairing.compatible ? "compatible" : "excluded";
        const runtimeNote = pairing.runtime_ready ? "runtime assets installed" : "runtime assets pending";
        const label = `${row.environment_name} with ${pairing.algorithm_name}: ${pairing.compatible ? "compatible" : "excluded"}; ${pairing.reason}; ${runtimeNote}`;
        return `<td class="pairing-cell ${stateClass}${selected ? " selected" : ""}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"><strong aria-hidden="true">${pairing.compatible ? "✓" : "×"}</strong><span>${pairing.compatible ? "valid" : "excluded"}</span>${pairing.runtime_ready ? "" : "<small>runtime pending</small>"}</td>`;
      }).join("")}
    </tr>`).join("")}</tbody>
  </table>`;
}

function renderSplBehaviorMatrix() {
  const rows = state.catalog?.spl_model?.behavior_matrix || [];
  const container = $("#spl-behavior-matrix");
  if (!container || !rows.length) return;
  const behaviors = rows[0].behaviors || [];
  const selectedAlgorithm = state.splTrace?.selection?.algorithm?.id;
  const selectedBehavior = state.splTrace?.selection?.behavior?.id;
  container.innerHTML = `<table class="variant-table spl-pairing-table">
    <thead><tr><th scope="col">Algorithm / policy interface</th>${behaviors.map((behavior) => `
      <th scope="col" class="spl-pairing-head"><span>${escapeHtml(behavior.behavior_name)}</span><code>${escapeHtml(behavior.category)}</code></th>`).join("")}</tr></thead>
    <tbody>${rows.map((row) => `<tr>
      <th scope="row" class="spl-environment-head"><span>${escapeHtml(row.algorithm_name)}</span><code>${escapeHtml(row.policy_interface)}</code></th>
      ${row.behaviors.map((behavior) => {
        const selected = row.algorithm_id === selectedAlgorithm && behavior.behavior_id === selectedBehavior;
        const stateClass = behavior.compatible ? "compatible" : "excluded";
        const label = `${row.algorithm_name} with ${behavior.behavior_name}: ${behavior.compatible ? "compatible" : "excluded"}; ${behavior.reason}`;
        return `<td class="pairing-cell ${stateClass}${selected ? " selected" : ""}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"><strong aria-hidden="true">${behavior.compatible ? "✓" : "×"}</strong><span>${behavior.compatible ? "valid" : "excluded"}</span>${behavior.runtime_ready ? "" : "<small>runtime pending</small>"}</td>`;
      }).join("")}
    </tr>`).join("")}</tbody>
  </table>`;
}

function renderSplOptimizerMatrix() {
  const rows = state.catalog?.spl_model?.optimizer_matrix || [];
  const container = $("#spl-optimizer-matrix");
  if (!container || !rows.length) return;
  const optimizers = rows[0].optimizers || [];
  const selectedAlgorithm = state.splTrace?.selection?.algorithm?.id;
  const selectedOptimizer = state.splTrace?.selection?.optimizer?.id;
  container.innerHTML = `<table class="variant-table spl-pairing-table">
    <thead><tr><th scope="col">Algorithm / update interface</th>${optimizers.map((optimizer) => `
      <th scope="col" class="spl-pairing-head"><span>${escapeHtml(optimizer.optimizer_name)}</span><code>${escapeHtml(optimizer.category)}</code></th>`).join("")}</tr></thead>
    <tbody>${rows.map((row) => `<tr>
      <th scope="row" class="spl-environment-head"><span>${escapeHtml(row.algorithm_name)}</span><code>${escapeHtml(row.optimizer_interface)}</code></th>
      ${row.optimizers.map((optimizer) => {
        const selected = row.algorithm_id === selectedAlgorithm && optimizer.optimizer_id === selectedOptimizer;
        const stateClass = optimizer.compatible ? "compatible" : "excluded";
        const label = `${row.algorithm_name} with ${optimizer.optimizer_name}: ${optimizer.compatible ? "compatible" : "excluded"}; ${optimizer.reason}`;
        return `<td class="pairing-cell ${stateClass}${selected ? " selected" : ""}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"><strong aria-hidden="true">${optimizer.compatible ? "✓" : "×"}</strong><span>${optimizer.compatible ? "valid" : "excluded"}</span>${optimizer.runtime_ready ? "" : "<small>runtime pending</small>"}</td>`;
      }).join("")}
    </tr>`).join("")}</tbody>
  </table>`;
}

function renderSplCatalog() {
  const model = state.catalog?.spl_model;
  if (!model) return;
  const statistics = model.statistics;
  $("#spl-feature-count").textContent = statistics.feature_count;
  $("#spl-constraint-count").textContent = statistics.constraint_count;
  $("#spl-pairing-count").textContent = `${statistics.capability_compatible_products} / ${statistics.theoretical_products}`;
  $("#spl-engineering-flow").innerHTML = model.engineering_flow.map((step) => `
    <div class="spl-flow-step"><span>${escapeHtml(step.phase)}</span><strong>${escapeHtml(step.title)}</strong><p>${escapeHtml(step.detail)}</p></div>`).join("");
  $("#spl-legend").innerHTML = model.legend.map((item) => `
    <div class="spl-legend-item"><b>${escapeHtml(item.symbol)}</b><div><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.meaning)}</span></div></div>`).join("");
  $("#spl-paper-alignment").innerHTML = model.paper_alignment.map((item) => `
    <div class="spl-alignment-row"><strong>${escapeHtml(item.rules)}</strong><em>${escapeHtml(item.status)}</em><span>${escapeHtml(item.detail)}</span></div>`).join("");
  $("#spl-sources").innerHTML = sourceMarkup(model.source_ids || []);
  renderSplFeatureTree();
  renderSplPairingMatrix();
  renderSplBehaviorMatrix();
  renderSplOptimizerMatrix();
  renderSplConstraints();
  renderSplSelection();
}

async function refreshSplTrace() {
  const button = $("#spl-refresh-button");
  button.disabled = true;
  try {
    const { body } = await request("/api/validate", buildConfiguration());
    if (!body.spl_trace) throw new Error((body.issues || []).map((issue) => issue.message).join(" · ") || body.error || "The configuration could not be projected");
    state.splTrace = body.spl_trace;
    renderSplFeatureTree();
    renderSplPairingMatrix();
    renderSplBehaviorMatrix();
    renderSplOptimizerMatrix();
    renderSplConstraints();
    renderSplSelection();
    const status = $("#spl-selected-status");
    status.className = `spl-selection-status ${body.valid ? "valid" : "invalid"}`;
    status.textContent = body.valid ? "Valid derivable product" : "Blocked by active constraints";
    setConnection(body.valid ? "SPL trace valid" : "SPL trace blocked", body.valid ? "valid" : "invalid");
  } catch (error) {
    state.splTrace = null;
    renderSplFeatureTree();
    renderSplPairingMatrix();
    renderSplBehaviorMatrix();
    renderSplOptimizerMatrix();
    renderSplConstraints();
    renderSplSelection();
    const status = $("#spl-selected-status");
    status.className = "spl-selection-status invalid";
    status.textContent = "Configuration shape is incomplete";
    showToast(error.message);
  } finally {
    button.disabled = false;
  }
}

function switchMode(mode) {
  closeCatalogPickers();
  state.mode = mode;
  const product = mode === "product";
  const study = mode === "study";
  const spl = mode === "spl";
  const monitor = mode === "monitor";
  $("#product-workspace").hidden = !product;
  $("#study-workspace").hidden = !study;
  $("#spl-workspace").hidden = !spl;
  $("#monitor-workspace").hidden = !monitor;
  $("#product-actions").hidden = !product;
  $("#study-actions").hidden = !study;
  $("#spl-actions").hidden = !spl;
  $("#monitor-actions").hidden = !monitor;
  $("#product-mode-button").classList.toggle("active", product);
  $("#study-mode-button").classList.toggle("active", study);
  $("#spl-mode-button").classList.toggle("active", spl);
  $("#monitor-mode-button").classList.toggle("active", monitor);
  if (study) updateStudyJsonPreview();
  if (spl) {
    renderSplCatalog();
    refreshSplTrace();
  }
  if (monitor) refreshMonitoring();
}

function catalogChoiceMeta(item, branch) {
  if (branch === "environments") {
    return `${item.capabilities.action_kind} actions · ${item.capabilities.observation_kind} observations · ${item.id}`;
  }
  if (branch === "algorithms") {
    return `${item.requirements.action_kinds.join(" / ")} actions · ${item.composition.policy_interface} policy · ${item.id}`;
  }
  if (branch === "behaviors") {
    return `${item.category} · ${item.requirements.policy_interfaces.join(" / ")} policy · ${item.id}`;
  }
  return `${item.category} · ${item.requirements.interfaces.join(" / ")} update · ${item.id}`;
}

function setCatalogPickerOpen(picker, open) {
  if (!picker) return;
  picker.classList.toggle("open", open);
  picker.querySelector(".catalog-picker-trigger").setAttribute("aria-expanded", String(open));
  picker.querySelector(".catalog-picker-menu").hidden = !open;
}

function closeCatalogPickers(except = null) {
  $$(".catalog-picker.open").forEach((picker) => {
    if (picker !== except) setCatalogPickerOpen(picker, false);
  });
}

function syncCatalogPicker(select) {
  const picker = select.closest(".catalog-field")?.querySelector(".catalog-picker");
  if (!picker) return;
  const selected = select.selectedOptions[0];
  const selectedLabel = selected?.textContent || "Choose a component";
  const trigger = picker.querySelector(".catalog-picker-trigger");
  trigger.querySelector("strong").textContent = selectedLabel;
  trigger.querySelector("small").textContent = selected?.value || "No selection";
  const fieldLabel = select.closest(".catalog-field")?.querySelector("label")?.textContent || "Component";
  trigger.setAttribute("aria-label", `${fieldLabel}: ${selectedLabel}. Open choices.`);
  picker.querySelectorAll(".catalog-picker-choice").forEach((choice) => {
    choice.setAttribute("aria-selected", String(choice.dataset.value === select.value));
  });
}

function syncCatalogPickers() {
  $$(".catalog-select-native").forEach(syncCatalogPicker);
}

function enhanceCatalogSelect(select, items, branch) {
  const field = select.closest(".catalog-field");
  if (!field) return;
  field.querySelector(".catalog-picker")?.remove();
  select.classList.add("catalog-select-native");

  const picker = document.createElement("div");
  picker.className = "catalog-picker";
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.id = `${select.id}-trigger`;
  trigger.className = "catalog-picker-trigger";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-controls", `${select.id}-menu`);
  trigger.innerHTML = '<span><strong></strong><small></small></span><b class="catalog-picker-chevron" aria-hidden="true">⌄</b>';
  const fieldLabel = field.querySelector("label");
  if (fieldLabel) fieldLabel.htmlFor = trigger.id;

  const menu = document.createElement("div");
  menu.id = `${select.id}-menu`;
  menu.className = "catalog-picker-menu";
  menu.setAttribute("role", "listbox");
  menu.setAttribute("aria-label", `${field.querySelector("label")?.textContent || branch} choices`);
  menu.hidden = true;
  for (const item of items) {
    const choice = document.createElement("button");
    choice.type = "button";
    choice.className = "catalog-picker-choice";
    choice.dataset.value = item.id;
    choice.setAttribute("role", "option");
    choice.disabled = !item.runtime_assets;
    const name = document.createElement("strong");
    name.textContent = `${item.display_name}${item.origin === "builtin" ? "" : " · plug-in"}${item.runtime_assets ? "" : " (runtime pending)"}`;
    const meta = document.createElement("small");
    meta.textContent = catalogChoiceMeta(item, branch);
    choice.append(name, meta);
    choice.addEventListener("click", () => {
      select.value = item.id;
      syncCatalogPicker(select);
      setCatalogPickerOpen(picker, false);
      trigger.focus({ preventScroll: true });
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    menu.appendChild(choice);
  }

  trigger.addEventListener("click", () => {
    const open = menu.hidden;
    closeCatalogPickers(picker);
    setCatalogPickerOpen(picker, open);
    if (open) {
      window.requestAnimationFrame(() => {
        const selected = menu.querySelector('[aria-selected="true"]');
        selected?.scrollIntoView({ block: "nearest" });
      });
    }
  });
  picker.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !menu.hidden) {
      event.preventDefault();
      setCatalogPickerOpen(picker, false);
      trigger.focus({ preventScroll: true });
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    if (menu.hidden) setCatalogPickerOpen(picker, true);
    const choices = [...menu.querySelectorAll(".catalog-picker-choice:not(:disabled)")];
    const current = choices.indexOf(document.activeElement);
    let index = current;
    if (event.key === "Home") index = 0;
    else if (event.key === "End") index = choices.length - 1;
    else if (event.key === "ArrowDown") index = Math.min(choices.length - 1, current + 1);
    else index = current <= 0 ? 0 : current - 1;
    choices[index]?.focus({ preventScroll: true });
    choices[index]?.scrollIntoView({ block: "nearest" });
  });
  picker.addEventListener("focusout", () => {
    window.setTimeout(() => {
      if (!picker.contains(document.activeElement)) setCatalogPickerOpen(picker, false);
    }, 0);
  });
  picker.append(trigger, menu);
  field.appendChild(picker);
  syncCatalogPicker(select);
}

function studyDefaultParameterMarkup(definition) {
  const lesson = theorySection("parameters")[definition.id] || {};
  const summary = lesson.summary || definition.description || "Catalog default";
  return `<button type="button" class="study-default-parameter" title="${escapeAttribute(summary)}" data-theory-kind="parameter" data-theory-id="${escapeAttribute(definition.id)}"><span>${escapeHtml(lesson.label || definition.id)}</span><b>${escapeHtml(formatSettingValue(definition.id, definition.default))}</b></button>`;
}

function renderStudyAlgorithmDefaults() {
  const root = $("#study-algorithm-defaults");
  if (!root || !state.catalog) return;
  const selectedIds = new Set(studySelections("study-algorithms"));
  const algorithms = state.catalog.algorithms.filter((item) => selectedIds.has(item.id));
  const sharedDefaults = state.catalog.training_parameters.filter((item) => item.id !== "training.seed");
  const sharedMarkup = sharedDefaults.map((item) => `<span>${escapeHtml((theorySection("parameters")[item.id] || {}).label || item.id)} = ${escapeHtml(formatSettingValue(item.id, item.default))}</span>`).join("");
  const cards = algorithms.map((algorithm) => {
    const parameters = algorithm.parameters || [];
    return `<article class="study-algorithm-default-card">
      <header><div><strong>${escapeHtml(algorithm.display_name)}</strong><span>${parameters.length} algorithm-owned default${parameters.length === 1 ? "" : "s"}</span></div><code>${escapeHtml(algorithm.id)}</code></header>
      ${parameters.length ? `<div class="study-default-parameter-list">${parameters.map(studyDefaultParameterMarkup).join("")}</div>` : '<p class="study-default-empty">This algorithm declares no component-owned hyperparameters.</p>'}
    </article>`;
  }).join("");
  root.innerHTML = `<div class="study-defaults-heading">
      <div><strong>Defaults behind the selected algorithms</strong><span>These fixed values apply unless you add the setting as an axis below. The training seed comes from the replication plan.</span></div>
      <div class="study-shared-defaults">${sharedMarkup}</div>
    </div>
    ${cards ? `<div class="study-algorithm-default-grid">${cards}</div>` : '<p class="study-default-empty">Select an algorithm to inspect its catalog defaults.</p>'}`;
}

function populateStudyEditor() {
  $("#study-environments").innerHTML = state.catalog.environments
    .filter((item) => item.runtime_assets)
    .map((item) => {
      const lesson = theorySection("environments")[item.id] || {};
      const dimensions = item.capabilities.observation_dimensions;
      const contract = `${item.capabilities.action_kind} actions · ${dimensions || "typed"} observations${item.capabilities.success_signal ? " · success signal" : " · return only"}`;
      return `<label title="${escapeHtml(item.id)}"><input type="checkbox" value="${escapeHtml(item.id)}" checked><span><strong>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}</strong><small>${escapeHtml(lesson.summary || item.description || contract)}</small><em>${escapeHtml(contract)}</em></span></label>`;
    })
    .join("");
  $("#study-algorithms").innerHTML = state.catalog.algorithms
    .filter((item) => item.runtime_assets)
    .map((item) => {
      const lesson = theorySection("algorithms")[item.id] || {};
      return `<label title="${escapeHtml(item.id)}"><input type="checkbox" value="${escapeHtml(item.id)}" checked><span><strong>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}</strong><small>${escapeHtml(lesson.summary || item.description || "Installed algorithm component")}</small><em>${escapeHtml(lesson.family || item.requirements.action_kinds.join(" / "))}</em></span></label>`;
    })
    .join("");
  renderStudyAlgorithmDefaults();
  $("#study-behaviors").innerHTML = state.catalog.behaviors
    .filter((item) => item.runtime_assets)
    .map((item) => {
      const lesson = theorySection("behaviors")[item.id] || {};
      return `<label title="${escapeHtml(item.id)}"><input type="checkbox" value="${escapeHtml(item.id)}" checked><span><strong>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}</strong><small>${escapeHtml(lesson.summary || item.description)}</small><em>${escapeHtml(item.category)} · ${escapeHtml(item.requirements.policy_interfaces.join(" / "))}</em></span></label>`;
    })
    .join("");
  $("#study-optimizers").innerHTML = state.catalog.optimizers
    .filter((item) => item.runtime_assets)
    .map((item) => {
      const lesson = theorySection("optimizers")[item.id] || {};
      return `<label title="${escapeHtml(item.id)}"><input type="checkbox" value="${escapeHtml(item.id)}" checked><span><strong>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}</strong><small>${escapeHtml(lesson.summary || item.description)}</small><em>${escapeHtml(item.category)} · ${escapeHtml(item.requirements.interfaces.join(" / "))}</em></span></label>`;
    })
    .join("");
  const defaults = state.catalog.exploration_defaults || {};
  $("#study-evaluation-seeds").value = (defaults.evaluation_seeds || [100, 101, 102]).join(", ");
  $("#study-default-summary").textContent = `Other defaults: ${defaults.training_budget || 500} ${defaults.training_budget_unit || "episodes"} · ${defaults.checkpoint_policy || "best"} checkpoint · ${defaults.evaluation_episodes_per_seed || 10} evaluation episodes per evaluation seed · mean always, uncertainty summaries with 2+ evaluation seeds · success rate only for environments with a success signal · active component parameter defaults.`;
  updateStudyJsonPreview();
}

function populateCatalog() {
  const environmentSelect = $("#environment-select");
  const algorithmSelect = $("#algorithm-select");
  const behaviorSelect = $("#behavior-select");
  const optimizerSelect = $("#optimizer-select");
  environmentSelect.innerHTML = state.catalog.environments.map((item) => `<option value="${escapeAttribute(item.id)}" ${item.runtime_assets ? "" : "disabled"}>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}${item.runtime_assets ? "" : " (runtime pending)"}</option>`).join("");
  algorithmSelect.innerHTML = state.catalog.algorithms.map((item) => `<option value="${escapeAttribute(item.id)}" ${item.runtime_assets ? "" : "disabled"}>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}${item.runtime_assets ? "" : " (runtime pending)"}</option>`).join("");
  behaviorSelect.innerHTML = state.catalog.behaviors.map((item) => `<option value="${escapeAttribute(item.id)}" ${item.runtime_assets ? "" : "disabled"}>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}${item.runtime_assets ? "" : " (runtime pending)"}</option>`).join("");
  optimizerSelect.innerHTML = state.catalog.optimizers.map((item) => `<option value="${escapeAttribute(item.id)}" ${item.runtime_assets ? "" : "disabled"}>${escapeHtml(item.display_name)}${item.origin === "builtin" ? "" : " · plug-in"}${item.runtime_assets ? "" : " (runtime pending)"}</option>`).join("");
  const initialPair = state.catalog.generation_pairings[0];
  const initialAlgorithm = state.catalog.algorithms.find((item) => item.id === initialPair.algorithm_id);
  environmentSelect.value = initialPair.environment_id;
  algorithmSelect.value = initialPair.algorithm_id;
  behaviorSelect.value = initialAlgorithm.composition.default_behavior_id;
  optimizerSelect.value = initialAlgorithm.composition.default_optimizer_id;
  enhanceCatalogSelect(environmentSelect, state.catalog.environments, "environments");
  enhanceCatalogSelect(algorithmSelect, state.catalog.algorithms, "algorithms");
  enhanceCatalogSelect(behaviorSelect, state.catalog.behaviors, "behaviors");
  enhanceCatalogSelect(optimizerSelect, state.catalog.optimizers, "optimizers");
  syncCatalogPickers();
  renderParameters();
  renderMetricTheoryLinks();
  updateCapabilities();
  updatePreview();
  populateStudyEditor();
  renderSplCatalog();
  if (state.catalog.plugin_diagnostics?.length) {
    const diagnostics = state.catalog.plugin_diagnostics;
    $("#plugin-health").hidden = false;
    $("#plugin-issue-count").textContent = `${diagnostics.length} rejected`;
    $("#plugin-issues").innerHTML = issueMarkup(
      diagnostics, "All discovered plug-ins loaded successfully."
    );
    showToast(`${diagnostics.length} plug-in${diagnostics.length === 1 ? "" : "s"} could not be loaded`);
  }
}

function setBusy(busy) {
  $("#validate-button").disabled = busy;
  $("#generate-button").disabled = busy;
  $("#preview-study-button").disabled = busy;
  $("#save-study-button").disabled = busy;
  $("#spl-refresh-button").disabled = busy;
}

function setConnection(text, kind) {
  const chip = $("#connection-status");
  chip.textContent = text;
  chip.className = `status-chip ${kind}`;
}

function pill(value) { return `<span class="capability-pill">${escapeHtml(value)}</span>`; }
function escapeHtml(value) { const node = document.createElement("span"); node.textContent = String(value); return node.innerHTML; }
function escapeAttribute(value) { return escapeHtml(value).replaceAll('"', "&quot;").replaceAll("'", "&#39;"); }
function showToast(message) { const toast = $("#toast"); toast.textContent = message; toast.classList.add("show"); window.setTimeout(() => toast.classList.remove("show"), 4500); }

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const { body } = await request("/api/catalog");
    state.catalog = body;
    populateCatalog();
    setConnection("Catalog ready", "valid");
  } catch (error) {
    setConnection("Catalog unavailable", "invalid");
    showToast(error.message);
  }

  document.body.addEventListener("input", (event) => {
    if (event.target.id === "monitor-run-search") {
      renderMonitorRuns();
      return;
    }
    if (event.target.closest("#study-workspace")) markStudyPlanStale();
    if (event.target.closest("#product-workspace")) state.splTrace = null;
    if (!event.target.closest("#monitor-workspace")) updatePreview();
  });
  document.body.addEventListener("change", (event) => {
    if (["monitor-status-filter", "monitor-algorithm-filter", "monitor-behavior-filter", "monitor-optimizer-filter"].includes(event.target.id)) {
      renderMonitorRuns();
      return;
    }
    if (event.target.id === "spl-constraint-filter") {
      renderSplConstraints();
      return;
    }
    if (event.target.id === "monitor-auto-refresh") return;
    if (event.target.closest("#study-workspace")) markStudyPlanStale();
    if (event.target.closest("#product-workspace")) state.splTrace = null;
    if (event.target.matches(".parameter-mode")) {
      const row = event.target.closest(".parameter-row");
      const definition = parameterDefinitions().find((item) => item.id === row.dataset.parameterId);
      renderParameterValue(row, definition);
    }
    if (event.target.id === "algorithm-select") {
      const algorithm = state.catalog.algorithms.find((item) => item.id === event.target.value);
      if (algorithm?.composition.default_behavior_id) $("#behavior-select").value = algorithm.composition.default_behavior_id;
      if (algorithm?.composition.default_optimizer_id) $("#optimizer-select").value = algorithm.composition.default_optimizer_id;
    }
    if (event.target.matches("#study-algorithms input[type=checkbox]")) renderStudyAlgorithmDefaults();
    if (["algorithm-select", "behavior-select", "optimizer-select"].includes(event.target.id)) renderParameters();
    if (["algorithm-select", "environment-select", "behavior-select", "optimizer-select"].includes(event.target.id)) {
      syncCatalogPickers();
      updateCapabilities();
    }
    if (event.target.id === "search-enabled") $("#search-fields").classList.toggle("disabled-region", !event.target.checked);
    if (event.target.id === "checkpoint-policy") $("#checkpoint-interval-label").hidden = event.target.value !== "periodic";
    if (event.target.matches(".study-axis-target")) {
      const definition = explorationDefinition(event.target.value);
      const row = event.target.closest(".study-axis-row");
      row.querySelector(".study-axis-values").value = defaultAxisValues(definition);
      updateAxisCondition(row, definition);
    }
    updatePreview();
  });
  document.body.addEventListener("click", (event) => {
    if (!event.target.closest(".catalog-picker")) closeCatalogPickers();
    const theoryButton = event.target.closest("[data-theory-kind]");
    if (theoryButton) {
      event.preventDefault();
      openTheory(theoryButton.dataset.theoryKind, theoryButton.dataset.theoryId);
      return;
    }
    const executionButton = event.target.closest("[data-monitor-execution]");
    if (executionButton) {
      loadMonitorExecution(executionButton.dataset.monitorExecution).catch((error) => showToast(error.message));
      return;
    }
    const runRow = event.target.closest("[data-monitor-run]");
    if (runRow) {
      loadMonitorRun(runRow.dataset.monitorRun);
      return;
    }
    if (event.target.matches(".remove-study-axis")) {
      markStudyPlanStale();
      event.target.closest(".study-axis-row").remove();
      $("#empty-study-axes").hidden = Boolean($$(".study-axis-row").length);
      updateStudyJsonPreview();
    }
  });
  $("#validate-button").addEventListener("click", validateConfiguration);
  $("#generate-button").addEventListener("click", generateProduct);
  $("#product-mode-button").addEventListener("click", () => switchMode("product"));
  $("#study-mode-button").addEventListener("click", () => switchMode("study"));
  $("#spl-mode-button").addEventListener("click", () => switchMode("spl"));
  $("#monitor-mode-button").addEventListener("click", () => switchMode("monitor"));
  $("#spl-refresh-button").addEventListener("click", refreshSplTrace);
  $("#refresh-monitor-button").addEventListener("click", refreshMonitoring);
  $("#learning-guide-button").addEventListener("click", openLearningOverview);
  $("#close-learning-dialog").addEventListener("click", closeLearningDialog);
  $("#learning-dialog").addEventListener("click", (event) => {
    if (event.target === $("#learning-dialog")) closeLearningDialog();
  });
  $("#add-study-axis-button").addEventListener("click", () => {
    markStudyPlanStale();
    addStudyAxis();
  });
  $("#preview-study-button").addEventListener("click", () => planStudy(false));
  $("#save-study-button").addEventListener("click", () => planStudy(true));
  $("#copy-button").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("#json-preview").textContent);
    showToast("Configuration copied");
  });
  $("#copy-run-button").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("#run-commands").textContent);
    showToast("Run commands copied");
  });
  $("#copy-study-button").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("#study-json-preview").textContent);
    showToast("Study copied");
  });
  $("#copy-study-run-button").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("#study-run-command").textContent);
    showToast("Study run command copied");
  });
  window.setInterval(() => {
    if (state.mode === "monitor" && $("#monitor-auto-refresh").checked) refreshMonitoring();
  }, 3000);
});
