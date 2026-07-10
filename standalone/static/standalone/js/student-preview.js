function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

const previewRoot = document.querySelector("[data-student-preview]");
const previewDataNode = document.getElementById("student-preview-data");

if (previewRoot && previewDataNode) {
  const actionUrlTemplate = previewRoot.dataset.actionUrlTemplate || "";
  const blockSwitcher = previewRoot.querySelector(".preview-block-switcher");
  const transcript = previewRoot.querySelector(".preview-chat-transcript");
  const form = previewRoot.querySelector(".preview-chat-form");
  const input = previewRoot.querySelector("#preview-chat-input");
  const statusText = previewRoot.querySelector(".preview-chat-status");
  const quizControls = previewRoot.querySelector(".preview-quiz-controls");
  const sidebarToggle = previewRoot.querySelector("[data-preview-sidebar-toggle]");
  const sidebarScrim = previewRoot.querySelector("[data-preview-sidebar-scrim]");
  const previewSidebar = previewRoot.querySelector(".preview-sidebar");
  const courseMetricsPanel = previewRoot.querySelector("[data-preview-course-metrics]");
  const blockSearchInput = previewRoot.querySelector("[data-preview-block-search]");
  const chatBackButton = previewRoot.querySelector("[data-preview-chat-back]");
  const activeBlockAvatar = previewRoot.querySelector("[data-preview-chat-avatar]");
  const activeBlockMeta = previewRoot.querySelector("[data-preview-active-block-meta]");
  const headerCoverage = previewRoot.querySelector("[data-preview-header-coverage]");
  const headerCoverageFill = previewRoot.querySelector("[data-preview-header-coverage-fill]");
  const previewSidebarHead = previewRoot.querySelector(".preview-sidebar-head");
  const previewChatHeader = previewRoot.querySelector(".preview-chat-header");
  const conversationSwitcher = previewRoot.querySelector("[data-preview-conversation-switcher]");
  const conversationSwitcherButtons = Array.from(previewRoot.querySelectorAll("[data-preview-conversation-mode]"));
  const scrollBottomButton = previewRoot.querySelector("[data-preview-scroll-bottom]");
  const sidebarSummary = previewRoot.querySelector("[data-preview-sidebar-summary]");
  const sidebarSummaryText = previewRoot.querySelector("[data-preview-sidebar-summary-text]");
  const sidebarSummaryCopy = previewRoot.querySelector("[data-preview-sidebar-summary-copy]");
  const sidebarSummaryToggle = previewRoot.querySelector("[data-preview-sidebar-summary-toggle]");
  const launchLoader = previewRoot.querySelector("[data-preview-launch-loader]");
  const submitButton = form?.querySelector("button[type='submit']");
  const calculatorTrigger = previewRoot.querySelector("[data-preview-calculator-trigger]");
  const quizMenu = previewRoot.querySelector("[data-quiz-menu]");
  const quizMenuTrigger = previewRoot.querySelector("[data-quiz-menu-trigger]");
  const quizMenuPanel = previewRoot.querySelector("[data-quiz-menu-panel]");
  const headerMenu = previewRoot.querySelector("[data-preview-header-menu]");
  const headerMenuTrigger = previewRoot.querySelector("[data-preview-header-menu-trigger]");
  const headerMenuPanel = previewRoot.querySelector("[data-preview-header-menu-panel]");
  const descriptionResourceButton = previewRoot.querySelector('[data-preview-resource="description"]');
  const objectivesResourceButton = previewRoot.querySelector('[data-preview-resource="objectives"]');
  const collectionObjectivesResourceButton = previewRoot.querySelector('[data-preview-resource="collection_objectives"]');
  const sidebarMenu = previewRoot.querySelector("[data-preview-sidebar-menu]");
  const sidebarMenuTrigger = previewRoot.querySelector("[data-preview-sidebar-menu-trigger]");
  const sidebarMenuPanel = previewRoot.querySelector("[data-preview-sidebar-menu-panel]");
  const waqAlignment = previewRoot.querySelector("[data-waq-alignment]");
  const waqAlignmentLabel = previewRoot.querySelector("[data-waq-alignment-label]");
  const waqAlignmentFill = previewRoot.querySelector("[data-waq-alignment-fill]");
  const waqAlignmentLoader = previewRoot.querySelector("[data-waq-alignment-loader]");
  const activeBlockTitle = previewRoot.querySelector(".preview-active-block-title");
  const projectSwitcher = previewRoot.querySelector("[data-preview-project-switcher]");
  const projectPanel = previewRoot.querySelector("[data-preview-project-panel]");
  const resourceButtons = Array.from(previewRoot.querySelectorAll("[data-preview-resource]"));
  const resetDemoButton = previewRoot.querySelector("[data-preview-reset-demo]");
  const mobileSidebarMedia = window.matchMedia("(max-width: 980px)");
  const mobileChatMedia = window.matchMedia("(max-width: 640px)");
  const messengerMobileMedia = window.matchMedia("(max-width: 980px)");
  const flagSheet = previewRoot.querySelector("[data-preview-flag-sheet]");
  const flagSheetScrim = previewRoot.querySelector("[data-preview-flag-sheet-scrim]");
  const flagSheetCloseButton = previewRoot.querySelector("[data-preview-flag-sheet-close]");
  const flagSheetQuestion = previewRoot.querySelector("[data-preview-flag-sheet-question]");
  const flagObjectiveField = previewRoot.querySelector("[data-preview-flag-objective-field]");
  const flagObjectiveSelect = previewRoot.querySelector("[data-preview-flag-objective-select]");
  const flagInstructionInput = previewRoot.querySelector("[data-preview-flag-instruction]");
  const flagSheetError = previewRoot.querySelector("[data-preview-flag-error]");
  const flagOnlyButton = previewRoot.querySelector("[data-preview-flag-only]");
  const flagSaveButton = previewRoot.querySelector("[data-preview-flag-save]");
  const objectiveSheet = previewRoot.querySelector("[data-preview-objective-sheet]");
  const objectiveSheetScrim = previewRoot.querySelector("[data-preview-objective-sheet-scrim]");
  const objectiveSheetCloseButton = previewRoot.querySelector("[data-preview-objective-sheet-close]");
  const objectiveSheetObjective = previewRoot.querySelector("[data-preview-objective-sheet-objective]");
  const objectiveSheetExistingWrap = previewRoot.querySelector("[data-preview-objective-sheet-existing-wrap]");
  const objectiveSheetExisting = previewRoot.querySelector("[data-preview-objective-sheet-existing]");
  const objectiveGuardrailInput = previewRoot.querySelector("[data-preview-objective-guardrail]");
  const objectiveSheetError = previewRoot.querySelector("[data-preview-objective-sheet-error]");
  const objectiveSheetSaveButton = previewRoot.querySelector("[data-preview-objective-sheet-save]");
  const isTeacherPreview = previewRoot.dataset.previewMode === "student-preview";
  const isMessengerPreview = previewRoot.dataset.previewMode === "student-preview" || previewRoot.dataset.previewMode === "student-demo";
  const isDemoMode = previewRoot.dataset.demoMode === "true";
  const demoEmbedOriginTokenUrl = String(previewRoot.dataset.demoEmbedOriginTokenUrl || "").trim();
  const hideFlagActions = previewRoot.dataset.hideFlagActions === "true";
  const practiceValidationUrl = String(previewRoot.dataset.practiceValidationUrl || "").trim();
  const statsIconUrl = String(previewRoot.dataset.statsIconUrl || "").trim();
  const messageBackgroundUrl = String(previewRoot.dataset.messageBackgroundUrl || "").trim();

  let previewState = JSON.parse(previewDataNode.textContent || "{}");
  let activeBlockId = "";
  let requestInFlight = false;
  let sidebarOpen = true;
  let inlineMessageSequence = 0;
  let sidebarAutoCloseTimer = 0;
  let highlightedSidebarBlockId = "";
  let highlightedSidebarBlockUntil = 0;
  let waqDraftDebounceTimer = 0;
  let waqDraftRequestId = 0;
  let waqAlignmentLoadingRequestId = 0;
  let waqDraftAbortController = null;
  let sidebarSummaryExpanded = false;
  let sidebarSummaryFullText = "";
  let practiceValidationNavigationTimer = 0;
  let demoEmbedOriginTokenPromise = null;
  let flagSheetState = null;
  let guardrailSheetState = null;
  let messengerSearchQuery = "";
  let messengerMobileChatOpen = !isMessengerPreview || !messengerMobileMedia.matches;
  let messengerHeaderHeightSyncFrame = 0;
  let transcriptScrollButtonSyncFrame = 0;
  let conversationListMode = "all";
  const inlineMessagesByBlock = {};
  const loadingMessagesByBlock = {};
  const optimisticUserMessagesByBlock = {};
  const calculatorStatesByMessageId = {};
  const calculatorAnswersByThreadId = {};
  const activeProjectIdsByBlock = {};
  const projectAnswerDraftsById = {};
  const maqSelectionsByQuestionId = {};
  const sidebarSelectionPreviewMs = 2000;
  const previewDateFormatter = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const previewTimeFormatter = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const previewWeekdayFormatter = new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
  });
  const previewSlashDateFormatter = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
  const STATS_THREAD_ID = "__my_stats__";
  const CALCULATOR_FUNCTION_TOKENS = new Set(["sin(", "cos(", "tan(", "asin(", "acos(", "atan(", "log(", "ln(", "sqrt(", "exp("]);
  const CALCULATOR_CONSTANT_TOKENS = new Set(["Ans", "pi", "h", "qe", "c"]);
  const CALCULATOR_OPERATOR_TOKENS = new Set(["+", "-", "*", "/", "^"]);
  const CALCULATOR_SUPERSCRIPT_MAP = {
    0: "⁰",
    1: "¹",
    2: "²",
    3: "³",
    4: "⁴",
    5: "⁵",
    6: "⁶",
    7: "⁷",
    8: "⁸",
    9: "⁹",
    "+": "⁺",
    "-": "⁻",
    "(": "⁽",
    ")": "⁾",
    ".": "˙",
    n: "ⁿ",
    i: "ⁱ",
    p: "ᵖ",
    A: "ᴬ",
    s: "ˢ",
  };
  const CALCULATOR_BUTTON_ROWS = [
    [
      { label: "AC", action: "clear", tone: "action" },
      { label: "DEL", action: "delete", tone: "action" },
      { label: "(", action: "open-paren", tone: "action" },
      { label: ")", action: "close-paren", tone: "action" },
      { label: "Ans", action: "constant", value: "Ans", tone: "accent" },
    ],
    [
      { label: "sin", action: "function", value: "sin", tone: "function" },
      { label: "cos", action: "function", value: "cos", tone: "function" },
      { label: "tan", action: "function", value: "tan", tone: "function" },
      { label: "log", action: "function", value: "log", tone: "function" },
      { label: "ln", action: "function", value: "ln", tone: "function" },
    ],
    [
      { label: "sin⁻¹", action: "function", value: "asin", tone: "function" },
      { label: "cos⁻¹", action: "function", value: "acos", tone: "function" },
      { label: "tan⁻¹", action: "function", value: "atan", tone: "function" },
      { label: "sqrt", action: "function", value: "sqrt", tone: "function" },
      { label: "exp", action: "function", value: "exp", tone: "function" },
    ],
    [
      { label: "x²", action: "square", tone: "function" },
      { label: "xⁿ", action: "power", tone: "function" },
      { label: "×10ⁿ", action: "ten-power", tone: "function" },
      { label: "π", action: "constant", value: "pi", tone: "accent" },
      { label: "Std", action: "standard-form", tone: "accent" },
    ],
    [
      { label: "7", action: "digit", value: "7", tone: "number" },
      { label: "8", action: "digit", value: "8", tone: "number" },
      { label: "9", action: "digit", value: "9", tone: "number" },
      { label: "÷", action: "operator", value: "/", tone: "operator" },
      { label: "×", action: "operator", value: "*", tone: "operator" },
    ],
    [
      { label: "4", action: "digit", value: "4", tone: "number" },
      { label: "5", action: "digit", value: "5", tone: "number" },
      { label: "6", action: "digit", value: "6", tone: "number" },
      { label: "-", action: "operator", value: "-", tone: "operator" },
      { label: "+", action: "operator", value: "+", tone: "operator" },
    ],
    [
      { label: "1", action: "digit", value: "1", tone: "number" },
      { label: "2", action: "digit", value: "2", tone: "number" },
      { label: "3", action: "digit", value: "3", tone: "number" },
      { label: "+/-", action: "toggle-sign", tone: "accent" },
      { label: ".", action: "decimal", tone: "number" },
    ],
    [
      { label: "0", action: "digit", value: "0", tone: "number" },
      { label: "h", action: "constant", value: "h", tone: "accent" },
      { label: "e", action: "constant", value: "qe", tone: "accent" },
      { label: "c", action: "constant", value: "c", tone: "accent" },
      { label: "=", action: "evaluate", tone: "equals" },
    ],
  ];
  const reducedMotionMedia = window.matchMedia("(prefers-reduced-motion: reduce)");
  function stableMessageHash(seedText) {
    let hash = 2166136261;
    const text = String(seedText || "");
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function applySeededMessageBackground(article, message) {
    if (!(article instanceof HTMLElement) || !messageBackgroundUrl) {
      return;
    }
    const seedText = [
      message?.id,
      message?.created_at,
      message?.question_id,
      message?.resource_key,
      message?.kind,
      message?.role,
      message?.text,
    ].filter(Boolean).join("|");
    const hash = stableMessageHash(seedText || "preview-message");
    const positionX = 12 + (hash % 77);
    const positionY = 10 + (Math.floor(hash / 97) % 81);
    const sizePx = 520 + (hash % 140);
    article.style.setProperty("--message-bg-image", `url("${messageBackgroundUrl}")`);
    article.style.setProperty("--message-bg-x", `${positionX}%`);
    article.style.setProperty("--message-bg-y", `${positionY}%`);
    article.style.setProperty("--message-bg-size", `${sizePx}px auto`);
  }

  const richText = window.StandaloneRichText || {
    appendFormattedMessageContent(container, text) {
      if (!container) {
        return;
      }
      const paragraph = document.createElement("p");
      paragraph.textContent = String(text || "");
      container.appendChild(paragraph);
    },
    appendInlineText(target, text) {
      if (target) {
        target.textContent = String(text || "");
      }
    },
    buildTextPanel(headingText, bodyText, extraClass = "") {
      const panel = document.createElement("div");
      panel.className = `preview-written-answer-panel${extraClass ? ` ${extraClass}` : ""}`;
      const heading = document.createElement("span");
      heading.className = "preview-written-answer-heading";
      heading.textContent = headingText;
      const paragraph = document.createElement("p");
      paragraph.textContent = String(bodyText || "");
      panel.append(heading, paragraph);
      return panel;
    },
    renderMath() {},
  };

  function setComposerSubmitButton(button, { label, iconOnly = false } = {}) {
    if (!button) {
      return;
    }
    const safeLabel = String(label || "").trim() || "Submit";
    button.dataset.iconOnly = iconOnly ? "true" : "false";
    button.setAttribute("aria-label", safeLabel);
    button.title = safeLabel;
    if (iconOnly) {
      button.innerHTML = `
        <span class="preview-composer-submit-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
            <path d="M3 20.25 21 12 3 3.75v6.38l12 1.87-12 1.87v6.38Z"></path>
          </svg>
        </span>
        <span class="preview-sr-only">${safeLabel}</span>
      `;
      return;
    }
    button.textContent = safeLabel;
  }

  function activeBlockStorageKey() {
    const courseId = String(previewState?.course?.id || previewRoot.dataset.courseId || "");
    const mode = previewRoot.dataset.previewMode || "preview";
    return courseId ? `quizanchor:${mode}:course:${courseId}:active-block` : "";
  }

  function collectionThreadKey(collectionId) {
    return collectionId ? `collection:${collectionId}` : "";
  }

  function previewThreadKey(state = previewState) {
    const kind = String(state?.active_thread_kind || "");
    const id = String(state?.active_thread_id || "");
    if (kind === "collection" && id) {
      return collectionThreadKey(id);
    }
    if (kind === "block" && id) {
      return id;
    }
    return String(state?.active_block_id || "");
  }

  function persistActiveBlockId(blockId) {
    const storageKey = activeBlockStorageKey();
    if (!storageKey) {
      return;
    }
    try {
      if (blockId) {
        window.localStorage.setItem(storageKey, String(blockId));
      } else {
        window.localStorage.removeItem(storageKey);
      }
    } catch (error) {
      return;
    }
  }

  function restoreActiveBlockId() {
    const storageKey = activeBlockStorageKey();
    if (!storageKey) {
      return;
    }
    try {
      const storedBlockId = window.localStorage.getItem(storageKey);
      if (!storedBlockId) {
        return;
      }
      if (isMessengerPreview && storedBlockId === STATS_THREAD_ID) {
        activeBlockId = STATS_THREAD_ID;
        return;
      }
      const collectionMatch = storedBlockId.match(/^collection:(\d+)$/);
      if (collectionMatch) {
        const matchingCollection = (previewState.collections || []).find(
          (collection) => String(collection.id) === String(collectionMatch[1]),
        );
        if (matchingCollection) {
          activeBlockId = collectionThreadKey(matchingCollection.id);
          return;
        }
      }
      const matchingBlock = (previewState.blocks || []).find((block) => String(block.id) === String(storedBlockId));
      if (matchingBlock) {
        activeBlockId = String(matchingBlock.id);
        return;
      }
      window.localStorage.removeItem(storageKey);
    } catch (error) {
      return;
    }
  }
  activeBlockId = previewThreadKey(previewState);

  function showLaunchLoader() {
    if (launchLoader) {
      launchLoader.hidden = false;
    }
  }

  function demoValidationVisitorStorageKey() {
    const courseKey = String(previewRoot.dataset.demoCourseKey || previewState?.course?.id || "");
    return courseKey ? `quizanchor:demo-validation-visitor:${courseKey}` : "";
  }

  function demoValidationVisitorKey() {
    const storageKey = demoValidationVisitorStorageKey();
    if (!storageKey) {
      return "";
    }
    try {
      let value = window.localStorage.getItem(storageKey) || "";
      if (!value) {
        value = window.crypto?.randomUUID ? window.crypto.randomUUID().replace(/-/g, "") : `${Date.now()}${Math.random().toString(16).slice(2)}`;
        window.localStorage.setItem(storageKey, value);
      }
      return value;
    } catch (_error) {
      return "";
    }
  }

  function normalizeOriginCandidate(value) {
    const rawValue = String(value || "").trim();
    if (!rawValue || rawValue.toLowerCase() === "null") {
      return "";
    }
    try {
      const parsed = rawValue.includes("://") ? new URL(rawValue) : new URL(rawValue, window.location.origin);
      if (!["http:", "https:"].includes(parsed.protocol) || !parsed.host) {
        return "";
      }
      return parsed.origin;
    } catch (_error) {
      return "";
    }
  }

  function demoEmbedParentOriginCandidates() {
    const candidates = [];
    const pushCandidate = (candidate) => {
      const normalized = normalizeOriginCandidate(candidate);
      if (normalized && !candidates.includes(normalized)) {
        candidates.push(normalized);
      }
    };
    if (window.location.ancestorOrigins) {
      Array.from(window.location.ancestorOrigins).forEach(pushCandidate);
    }
    pushCandidate(document.referrer);
    return candidates;
  }

  async function fetchDemoEmbedOriginToken() {
    if (!isDemoMode || !demoEmbedOriginTokenUrl) {
      return "";
    }
    if (demoEmbedOriginTokenPromise) {
      return demoEmbedOriginTokenPromise;
    }
    demoEmbedOriginTokenPromise = (async () => {
      const parentOrigins = demoEmbedParentOriginCandidates();
      for (const parentOrigin of parentOrigins) {
        try {
          const tokenUrl = new URL(demoEmbedOriginTokenUrl, window.location.origin);
          tokenUrl.searchParams.set("parent_origin", parentOrigin);
          const response = await fetch(tokenUrl.toString(), {
            credentials: "same-origin",
            headers: {
              "X-Requested-With": "XMLHttpRequest",
            },
          });
          if (!response.ok) {
            continue;
          }
          const payload = await response.json();
          if (payload && payload.ok && payload.origin_token) {
            return String(payload.origin_token);
          }
        } catch (_error) {
          continue;
        }
      }
      return "";
    })();
    const originToken = await demoEmbedOriginTokenPromise;
    if (!originToken) {
      demoEmbedOriginTokenPromise = null;
    }
    return originToken;
  }

  async function demoValidationUrl(url) {
    if (!isDemoMode || !url) {
      return url;
    }
    try {
      const nextUrl = new URL(url, window.location.origin);
      if (!nextUrl.pathname.includes("/validation-practice/")) {
        return nextUrl.toString();
      }
      if (!nextUrl.searchParams.get("visitor")) {
        const visitorKey = demoValidationVisitorKey();
        if (visitorKey) {
          nextUrl.searchParams.set("visitor", visitorKey);
        }
      }
      if (!nextUrl.searchParams.get("origin_token")) {
        const originToken = await fetchDemoEmbedOriginToken();
        if (originToken) {
          nextUrl.searchParams.set("origin_token", originToken);
        }
      }
      return nextUrl.toString();
    } catch (_error) {
      return url;
    }
  }

  function beginPracticeValidationLaunch(link) {
    if (!link || practiceValidationNavigationTimer) {
      return;
    }
    practiceValidationNavigationTimer = 1;
    void demoValidationUrl(link.href).then((nextUrl) => {
      window.location.assign(nextUrl);
    });
  }

  function isPracticeValidationLaunchLink(link) {
    if (!link || !link.href) {
      return false;
    }
    try {
      const url = new URL(link.href, window.location.origin);
      const path = String(url.pathname || "");
      const isPracticeValidationPath = path.includes("/validation-practice/") || path.includes("/student-preview/validate/practice/");
      return isPracticeValidationPath && !url.searchParams.has("review");
    } catch (_error) {
      return false;
    }
  }

  function actionUrl(blockId, action) {
    return actionUrlTemplate.replace("/0/ACTION/", `/${blockId}/${action}/`);
  }

  function truncateSidebarSummary(text, limit = 100) {
    const normalized = String(text || "").trim();
    if (normalized.length <= limit) {
      return normalized;
    }
    const truncated = normalized.slice(0, limit);
    const lastSpace = truncated.lastIndexOf(" ");
    return (lastSpace > 72 ? truncated.slice(0, lastSpace) : truncated).trimEnd();
  }

  function renderSidebarSummary() {
    if (!sidebarSummaryText || !sidebarSummaryCopy || !sidebarSummaryToggle) {
      return;
    }
    const excerpt = truncateSidebarSummary(sidebarSummaryFullText);
    const isTruncated = excerpt.length < sidebarSummaryFullText.length;
    sidebarSummaryCopy.textContent = sidebarSummaryExpanded || !isTruncated
      ? sidebarSummaryFullText
      : excerpt;
    sidebarSummaryToggle.hidden = !isTruncated;
    sidebarSummaryToggle.textContent = sidebarSummaryExpanded ? "... less" : "... more";
    sidebarSummaryToggle.setAttribute("aria-expanded", sidebarSummaryExpanded ? "true" : "false");
    const isExpanded = sidebarSummaryExpanded && isTruncated;
    sidebarSummary?.classList.toggle("is-expanded", isExpanded);
    previewSidebar?.classList.toggle("has-expanded-summary", isExpanded);
  }

  function isStatsView() {
    return String(activeBlockId || "") === STATS_THREAD_ID;
  }

  function isCollectionView() {
    return /^collection:\d+$/.test(String(activeBlockId || ""));
  }

  function currentCollectionId() {
    const match = String(activeBlockId || "").match(/^collection:(\d+)$/);
    return match ? match[1] : "";
  }

  function currentConversationKey() {
    if (isStatsView()) {
      return STATS_THREAD_ID;
    }
    if (isCollectionView()) {
      return collectionThreadKey(currentCollectionId());
    }
    const block = currentBlock();
    return block ? String(block.id) : "";
  }

  function currentBlock() {
    if (isStatsView() || isCollectionView()) {
      return null;
    }
    return (previewState.blocks || []).find((block) => String(block.id) === String(activeBlockId)) || previewState.blocks?.[0] || null;
  }

  function findCollection(collectionId) {
    return (previewState.collections || []).find((collection) => String(collection.id) === String(collectionId)) || null;
  }

  function currentCollection() {
    return isCollectionView() ? findCollection(currentCollectionId()) : null;
  }

  function collectionBlocks(collection = currentCollection()) {
    if (!collection || !Array.isArray(collection.block_ids)) {
      return [];
    }
    return collection.block_ids
      .map((blockId) => findBlock(blockId))
      .filter(Boolean);
  }

  function currentConversationEntry() {
    if (isStatsView()) {
      return null;
    }
    return currentCollection() || currentBlock();
  }

  function currentActionBlock() {
    if (isStatsView()) {
      return null;
    }
    const collection = currentCollection();
    if (collection) {
      const anchorBlockId = String(collection.anchor_block_id || collection.block_ids?.[0] || "");
      return findBlock(anchorBlockId);
    }
    return currentBlock();
  }

  function findBlock(blockId) {
    return (previewState.blocks || []).find((block) => String(block.id) === String(blockId)) || null;
  }

  function currentProject(block = currentBlock()) {
    if (!block || !Array.isArray(block.projects)) {
      return null;
    }
    const activeProjectId = String(activeProjectIdsByBlock[String(block.id)] || "");
    return block.projects.find((project) => String(project.id) === activeProjectId) || null;
  }

  function setActiveProject(blockId, projectId = "") {
    const key = String(blockId || "");
    if (!key) {
      return;
    }
    if (projectId) {
      activeProjectIdsByBlock[key] = String(projectId);
      return;
    }
    delete activeProjectIdsByBlock[key];
  }

  function currentFlagSheetBlock() {
    return flagSheetState ? findBlock(flagSheetState.blockId) : null;
  }

  function currentGuardrailSheetBlock() {
    return guardrailSheetState ? findBlock(guardrailSheetState.blockId) : null;
  }

  function currentObjectiveForGuardrailSheet() {
    const block = currentGuardrailSheetBlock();
    if (!guardrailSheetState || !block || !Array.isArray(block.learning_objectives)) {
      return null;
    }
    return block.learning_objectives.find(
      (objective) => Number(objective.id || 0) === Number(guardrailSheetState.learningObjectiveId || 0),
    ) || null;
  }

  function setFlagSheetError(message = "") {
    if (!flagSheetError) {
      return;
    }
    flagSheetError.textContent = message;
    flagSheetError.hidden = !message;
  }

  function setGuardrailSheetError(message = "") {
    if (!objectiveSheetError) {
      return;
    }
    objectiveSheetError.textContent = message;
    objectiveSheetError.hidden = !message;
  }

  function closeFlagSheet() {
    flagSheetState = null;
    setFlagSheetError("");
    if (flagInstructionInput) {
      flagInstructionInput.value = "";
    }
    if (flagObjectiveSelect) {
      flagObjectiveSelect.innerHTML = "";
      flagObjectiveSelect.value = "";
    }
    syncFlagSheetState();
  }

  function closeGuardrailSheet() {
    guardrailSheetState = null;
    setGuardrailSheetError("");
    if (objectiveGuardrailInput) {
      objectiveGuardrailInput.value = "";
    }
    if (objectiveSheetExistingWrap) {
      objectiveSheetExistingWrap.hidden = true;
    }
    if (objectiveSheetExisting) {
      objectiveSheetExisting.textContent = "";
    }
    syncGuardrailSheetState();
  }

  function syncFlagSheetState() {
    if (!flagSheet || !isTeacherPreview) {
      return;
    }
    const isOpen = Boolean(flagSheetState);
    flagSheet.hidden = !isOpen;
    flagSheetScrim.hidden = !isOpen;
    flagSheet.classList.toggle("is-open", isOpen);
    if (!isOpen) {
      return;
    }
    if (flagOnlyButton) {
      flagOnlyButton.disabled = requestInFlight;
    }
    if (flagSaveButton) {
      flagSaveButton.disabled = requestInFlight;
    }
    if (flagInstructionInput) {
      flagInstructionInput.disabled = requestInFlight;
    }
    if (flagObjectiveSelect) {
      flagObjectiveSelect.disabled = requestInFlight;
    }
  }

  function syncGuardrailSheetState() {
    if (!objectiveSheet || !isTeacherPreview) {
      return;
    }
    const isOpen = Boolean(guardrailSheetState);
    objectiveSheet.hidden = !isOpen;
    objectiveSheetScrim.hidden = !isOpen;
    objectiveSheet.classList.toggle("is-open", isOpen);
    if (!isOpen) {
      return;
    }
    if (objectiveSheetSaveButton) {
      objectiveSheetSaveButton.disabled = requestInFlight;
    }
    if (objectiveGuardrailInput) {
      objectiveGuardrailInput.disabled = requestInFlight;
    }
  }

  function openFlagSheet(message) {
    if (!isTeacherPreview || !message) {
      return;
    }
    const block = currentBlock();
    if (!block) {
      return;
    }
    flagSheetState = {
      blockId: String(block.id),
      questionId: Number(message.question_id || 0),
      learningObjectiveId: Number(message.learning_objective_id || 0) || null,
    };
    if (flagSheetQuestion) {
      flagSheetQuestion.textContent = questionStemText(message);
    }
    if (flagInstructionInput) {
      flagInstructionInput.value = "";
    }
    setFlagSheetError("");
    if (flagObjectiveSelect) {
      flagObjectiveSelect.innerHTML = "";
      const objectives = Array.isArray(block.learning_objectives) ? block.learning_objectives : [];
      if (flagObjectiveField) {
        flagObjectiveField.hidden = objectives.length === 0;
      }
      if (objectives.length) {
        const placeholderOption = document.createElement("option");
        placeholderOption.value = "";
        placeholderOption.textContent = "Choose a learning objective";
        flagObjectiveSelect.appendChild(placeholderOption);
        objectives.forEach((objective) => {
          const option = document.createElement("option");
          option.value = String(objective.id);
          option.textContent = `${displayObjectiveCode(objective.code)} ${objective.text}`;
          flagObjectiveSelect.appendChild(option);
        });
        flagObjectiveSelect.value = flagSheetState.learningObjectiveId
          ? String(flagSheetState.learningObjectiveId)
          : "";
      }
    }
    syncFlagSheetState();
    flagInstructionInput?.focus();
  }

  function openGuardrailSheet(objective) {
    if (!isTeacherPreview || !objective) {
      return;
    }
    const block = currentBlock();
    if (!block) {
      return;
    }
    guardrailSheetState = {
      blockId: String(block.id),
      learningObjectiveId: Number(objective.id || 0),
    };
    if (objectiveSheetObjective) {
      objectiveSheetObjective.textContent = `${displayObjectiveCode(objective.code)} ${objective.text}`;
    }
    const currentGuidance = String(objective.assistant_guidance || "").trim();
    if (objectiveSheetExistingWrap) {
      objectiveSheetExistingWrap.hidden = !currentGuidance;
    }
    if (objectiveSheetExisting) {
      objectiveSheetExisting.textContent = currentGuidance;
    }
    if (objectiveGuardrailInput) {
      objectiveGuardrailInput.value = "";
    }
    setGuardrailSheetError("");
    syncGuardrailSheetState();
    objectiveGuardrailInput?.focus();
  }

  async function submitFlagSheet({ saveCorrection }) {
    if (!flagSheetState || requestInFlight) {
      return;
    }
    const payload = { question_id: flagSheetState.questionId };
    if (saveCorrection) {
      const instruction = String(flagInstructionInput?.value || "").trim();
      const learningObjectiveId = flagSheetState.learningObjectiveId || Number(flagObjectiveSelect?.value || 0) || null;
      if (!instruction) {
        setFlagSheetError("Add a correction note before saving it.");
        flagInstructionInput?.focus();
        return;
      }
      if (!learningObjectiveId) {
        setFlagSheetError("Choose the learning objective this correction belongs to.");
        flagObjectiveSelect?.focus();
        return;
      }
      payload.instruction = instruction;
      payload.learning_objective_id = learningObjectiveId;
    }
    setFlagSheetError("");
    const succeeded = await postPreviewAction("flag", payload, {
      focusComposer: true,
      scrollMode: "preserve",
      onError: (error) => {
        setFlagSheetError(error?.message || "Unable to save this correction right now.");
      },
    });
    if (succeeded) {
      closeFlagSheet();
    }
  }

  async function submitGuardrailSheet() {
    if (!guardrailSheetState || requestInFlight) {
      return;
    }
    const instruction = String(objectiveGuardrailInput?.value || "").trim();
    if (!instruction) {
      setGuardrailSheetError("Add a guardrail before saving it.");
      objectiveGuardrailInput?.focus();
      return;
    }
    setGuardrailSheetError("");
    const succeeded = await postPreviewAction(
      "guardrail",
      {
        learning_objective_id: guardrailSheetState.learningObjectiveId,
        instruction,
      },
      {
        focusComposer: true,
        scrollMode: "preserve",
        onError: (error) => {
          setGuardrailSheetError(error?.message || "Unable to save this guardrail right now.");
        },
      },
    );
    if (succeeded) {
      closeGuardrailSheet();
    }
  }

  function pendingQuestion(conversation = currentConversationEntry()) {
    if (currentProject(conversation)) {
      return null;
    }
    if (!conversation || !Array.isArray(conversation.transcript)) {
      return null;
    }
    return [...conversation.transcript].reverse().find(
      (message) => message.kind === "question" && !message.answered && !message.flagged,
    ) || null;
  }

  function pendingWrittenQuestion(conversation = currentConversationEntry()) {
    const question = pendingQuestion(conversation);
    return question?.question_type === "waq" ? question : null;
  }

  function syncQuizMenuItems() {
    if (!quizMenuPanel) {
      return;
    }
    const conversation = currentConversationEntry();
    const availableManualQuestionTypes = Array.isArray(conversation?.available_manual_question_types)
      ? conversation.available_manual_question_types
      : ["mcq", "maq", "waq"];
    quizMenuPanel.querySelectorAll("[data-quiz-type]").forEach((button) => {
      const questionType = button.dataset.quizType || "";
      const isVisible = availableManualQuestionTypes.includes(questionType);
      const copy = button.querySelector(".preview-quiz-menu-item-copy");
      if (copy && !copy.dataset.defaultText) {
        copy.dataset.defaultText = copy.textContent || "";
      }
      button.hidden = !isVisible;
      button.toggleAttribute("hidden", !isVisible);
      button.disabled = requestInFlight;
      button.setAttribute("aria-disabled", button.disabled ? "true" : "false");
      if (copy) {
        copy.textContent = copy.dataset.defaultText;
      }
    });
  }

  function updateQuestionMessage(questionId, updater) {
    if (!questionId || typeof updater !== "function") {
      return null;
    }
    let updatedQuestion = null;
    const conversation = currentConversationEntry();
    (conversation?.transcript || []).forEach((message) => {
      if (message.kind === "question" && String(message.question_id) === String(questionId)) {
        updater(message, conversation);
        updatedQuestion = message;
      }
    });
    return updatedQuestion;
  }

  function threadInlineMessages(threadId) {
    const key = String(threadId || "");
    if (!Array.isArray(inlineMessagesByBlock[key])) {
      inlineMessagesByBlock[key] = [];
    }
    return inlineMessagesByBlock[key];
  }

  function blockInlineMessages(blockId) {
    return threadInlineMessages(blockId);
  }

  function createCalculatorState() {
    return {
      tokens: [],
      resultText: "0",
      error: "",
      lastComputedValue: null,
      justEvaluated: false,
      standardFormActive: false,
    };
  }

  function ensureCalculatorState(messageId) {
    const key = String(messageId || "");
    if (!calculatorStatesByMessageId[key]) {
      calculatorStatesByMessageId[key] = createCalculatorState();
    }
    return calculatorStatesByMessageId[key];
  }

  function cleanupCalculatorState(messageId) {
    delete calculatorStatesByMessageId[String(messageId || "")];
  }

  function calculatorThreadAnswer(threadId) {
    const key = String(threadId || "");
    return Number.isFinite(calculatorAnswersByThreadId[key]) ? calculatorAnswersByThreadId[key] : null;
  }

  function setCalculatorThreadAnswer(threadId, value) {
    const key = String(threadId || "");
    if (!key || !Number.isFinite(value)) {
      return;
    }
    calculatorAnswersByThreadId[key] = value;
  }

  function removeCalculatorInlineMessages(threadId) {
    const inlineMessages = threadInlineMessages(threadId);
    if (!inlineMessages.length) {
      return;
    }
    const retainedMessages = inlineMessages.filter((message) => {
      if (message.kind !== "calculator") {
        return true;
      }
      cleanupCalculatorState(message.id);
      return false;
    });
    inlineMessages.length = 0;
    retainedMessages.forEach((message) => inlineMessages.push(message));
  }

  function threadHasCalculatorInlineMessage(threadId) {
    const resolvedThreadId = String(threadId || "");
    if (!resolvedThreadId) {
      return false;
    }
    return threadInlineMessages(resolvedThreadId).some((message) => message.kind === "calculator");
  }

  function currentConversationMessages() {
    if (isStatsView()) {
      return threadInlineMessages(STATS_THREAD_ID)
        .sort((left, right) => left.sequence - right.sequence);
    }
    const conversation = currentConversationEntry();
    return conversation ? combinedTranscript(conversation) : [];
  }

  function currentConversationEndsWithCalculator() {
    const messages = currentConversationMessages();
    const lastMessage = messages[messages.length - 1];
    return !!lastMessage && lastMessage.kind === "calculator";
  }

  function syncCalculatorTriggerVisibility() {
    if (!calculatorTrigger) {
      return;
    }
    const threadId = currentConversationKey();
    calculatorTrigger.hidden = !threadId || currentConversationEndsWithCalculator();
  }

  function calculatorTokenType(token) {
    if (CALCULATOR_FUNCTION_TOKENS.has(token)) {
      return "function";
    }
    if (CALCULATOR_CONSTANT_TOKENS.has(token)) {
      return "constant";
    }
    if (CALCULATOR_OPERATOR_TOKENS.has(token)) {
      return "operator";
    }
    if (token === "(") {
      return "open-paren";
    }
    if (token === ")") {
      return "close-paren";
    }
    if (typeof token === "string" && /^-?(?:\d+\.?\d*|\d*\.?\d+|-?\d+\.?)$/.test(token)) {
      return "number";
    }
    return "unknown";
  }

  function calculatorDisplayToken(token) {
    return {
      "*": "×",
      "/": "÷",
      pi: "π",
      qe: "e",
      "asin(": "sin⁻¹(",
      "acos(": "cos⁻¹(",
      "atan(": "tan⁻¹(",
    }[token] || token;
  }

  function calculatorSuperscriptText(value) {
    return String(value || "").split("").map((character) => CALCULATOR_SUPERSCRIPT_MAP[character] || character).join("");
  }

  function formatCalculatorTokens(tokens) {
    const parts = [];
    let exponentMode = false;
    let exponentDepth = 0;
    (tokens || []).forEach((token) => {
      if (token === "^") {
        exponentMode = true;
        exponentDepth = 0;
        return;
      }
      if (exponentMode) {
        const superscriptToken = calculatorSuperscriptText(calculatorDisplayToken(token));
        if (!parts.length) {
          parts.push(superscriptToken);
        } else {
          parts[parts.length - 1] = `${parts[parts.length - 1]}${superscriptToken}`;
        }
        if (token === "(") {
          exponentDepth += 1;
          return;
        }
        if (token === ")") {
          exponentDepth = Math.max(0, exponentDepth - 1);
          if (exponentDepth === 0) {
            exponentMode = false;
          }
          return;
        }
        if (exponentDepth === 0) {
          exponentMode = false;
        }
        return;
      }
      parts.push(calculatorDisplayToken(token));
    });
    return parts.join(" ");
  }

  function normalizeCalculatorNumberString(value) {
    let text = String(value || "");
    if (!text) {
      return "0";
    }
    if (text.includes(".")) {
      text = text.replace(/(\.\d*?[1-9])0+$/u, "$1").replace(/\.0+$/u, "").replace(/\.$/u, "");
    }
    if (text === "-0") {
      return "0";
    }
    return text || "0";
  }

  function calculatorPlainString(value) {
    if (!Number.isFinite(value)) {
      return "0";
    }
    const raw = String(value);
    if (!/[eE]/.test(raw)) {
      return normalizeCalculatorNumberString(raw);
    }
    const [mantissaPart, exponentPart] = raw.toLowerCase().split("e");
    const exponent = Number(exponentPart || 0);
    let sign = "";
    let mantissa = mantissaPart;
    if (mantissa.startsWith("-")) {
      sign = "-";
      mantissa = mantissa.slice(1);
    }
    const [whole = "0", fraction = ""] = mantissa.split(".");
    const digits = `${whole}${fraction}`.replace(/^0+(?=\d)/u, "") || "0";
    const decimalIndex = whole.length + exponent;
    if (decimalIndex <= 0) {
      return normalizeCalculatorNumberString(`${sign}0.${"0".repeat(Math.abs(decimalIndex))}${digits}`);
    }
    if (decimalIndex >= digits.length) {
      return normalizeCalculatorNumberString(`${sign}${digits}${"0".repeat(decimalIndex - digits.length)}`);
    }
    return normalizeCalculatorNumberString(`${sign}${digits.slice(0, decimalIndex)}.${digits.slice(decimalIndex)}`);
  }

  function roundCalculatorValue(value) {
    return Number(value.toPrecision(12));
  }

  function formatCalculatorValue(value) {
    return normalizeCalculatorNumberString(calculatorPlainString(roundCalculatorValue(value)));
  }

  function formatCalculatorStandardForm(value) {
    if (!Number.isFinite(value)) {
      return "0";
    }
    const rounded = roundCalculatorValue(value);
    if (rounded === 0) {
      return "0";
    }
    const exponent = Math.floor(Math.log10(Math.abs(rounded)));
    const mantissa = roundCalculatorValue(rounded / (10 ** exponent));
    return `${formatCalculatorValue(mantissa)} × 10${calculatorSuperscriptText(exponent)}`;
  }

  function calculatorNeedsImplicitMultiply(tokens, nextType) {
    if (!tokens.length) {
      return false;
    }
    const previousType = calculatorTokenType(tokens[tokens.length - 1]);
    const previousCanMultiply = ["number", "constant", "close-paren"].includes(previousType);
    const nextCanMultiply = ["number", "constant", "function", "open-paren"].includes(nextType);
    return previousCanMultiply && nextCanMultiply;
  }

  function calculatorParenthesisBalance(tokens) {
    return (tokens || []).reduce((balance, token) => {
      if (token === "(" || CALCULATOR_FUNCTION_TOKENS.has(token)) {
        return balance + 1;
      }
      if (token === ")") {
        return balance - 1;
      }
      return balance;
    }, 0);
  }

  function calculatorIsUnaryMinus(tokens, index) {
    if ((tokens[index] || "") !== "-") {
      return false;
    }
    if (index === 0) {
      return true;
    }
    const previousType = calculatorTokenType(tokens[index - 1]);
    return ["operator", "open-paren", "function"].includes(previousType);
  }

  function calculatorSerializeTokens(tokens) {
    return (tokens || []).join("");
  }

  function calculatorResetForInput(state, inputType) {
    if (!state.justEvaluated) {
      state.error = "";
      state.standardFormActive = false;
      return;
    }
    if (inputType === "operator" && Number.isFinite(state.lastComputedValue)) {
      state.tokens = [calculatorPlainString(state.lastComputedValue)];
    } else {
      state.tokens = [];
      state.resultText = "0";
    }
    state.error = "";
    state.justEvaluated = false;
    state.standardFormActive = false;
  }

  function calculatorAppendDigit(state, digit) {
    calculatorResetForInput(state, "number");
    const tokens = state.tokens;
    const lastToken = tokens[tokens.length - 1] || "";
    if (calculatorTokenType(lastToken) === "number") {
      tokens[tokens.length - 1] = `${lastToken}${digit}`;
      return;
    }
    if (calculatorNeedsImplicitMultiply(tokens, "number")) {
      tokens.push("*");
    }
    tokens.push(String(digit));
  }

  function calculatorAppendDecimal(state) {
    calculatorResetForInput(state, "number");
    const tokens = state.tokens;
    const lastToken = tokens[tokens.length - 1] || "";
    if (calculatorTokenType(lastToken) === "number") {
      if (!lastToken.includes(".")) {
        tokens[tokens.length - 1] = `${lastToken}.`;
      }
      return;
    }
    if (calculatorNeedsImplicitMultiply(tokens, "number")) {
      tokens.push("*");
    }
    tokens.push("0.");
  }

  function calculatorAppendConstant(state, token) {
    calculatorResetForInput(state, "constant");
    if (calculatorNeedsImplicitMultiply(state.tokens, "constant")) {
      state.tokens.push("*");
    }
    state.tokens.push(token);
  }

  function calculatorAppendFunction(state, functionName) {
    calculatorResetForInput(state, "function");
    if (calculatorNeedsImplicitMultiply(state.tokens, "function")) {
      state.tokens.push("*");
    }
    state.tokens.push(`${functionName}(`);
  }

  function calculatorAppendOpenParen(state) {
    calculatorResetForInput(state, "open-paren");
    if (calculatorNeedsImplicitMultiply(state.tokens, "open-paren")) {
      state.tokens.push("*");
    }
    state.tokens.push("(");
  }

  function calculatorAppendCloseParen(state) {
    calculatorResetForInput(state, "close-paren");
    const lastType = calculatorTokenType(state.tokens[state.tokens.length - 1] || "");
    if (!state.tokens.length || ["operator", "open-paren", "function"].includes(lastType)) {
      return;
    }
    if (calculatorParenthesisBalance(state.tokens) <= 0) {
      return;
    }
    state.tokens.push(")");
  }

  function calculatorAppendOperator(state, operator) {
    calculatorResetForInput(state, "operator");
    const tokens = state.tokens;
    const lastToken = tokens[tokens.length - 1] || "";
    const lastType = calculatorTokenType(lastToken);
    if (!tokens.length) {
      if (operator === "-") {
        tokens.push("-");
      }
      return;
    }
    if (lastType === "operator") {
      tokens[tokens.length - 1] = operator;
      return;
    }
    if (["open-paren", "function"].includes(lastType)) {
      if (operator === "-") {
        tokens.push("-");
      }
      return;
    }
    tokens.push(operator);
  }

  function calculatorApplySquare(state) {
    calculatorResetForInput(state, "operator");
    const lastType = calculatorTokenType(state.tokens[state.tokens.length - 1] || "");
    if (!state.tokens.length || ["operator", "open-paren", "function"].includes(lastType)) {
      return;
    }
    state.tokens.push("^");
    state.tokens.push("2");
  }

  function calculatorApplyPower(state) {
    calculatorAppendOperator(state, "^");
  }

  function calculatorApplyTenPower(state) {
    calculatorResetForInput(state, "operator");
    const lastType = calculatorTokenType(state.tokens[state.tokens.length - 1] || "");
    if (!state.tokens.length || ["operator", "open-paren", "function"].includes(lastType)) {
      return;
    }
    state.tokens.push("*");
    state.tokens.push("10");
    state.tokens.push("^");
  }

  function calculatorToggleSign(state) {
    calculatorResetForInput(state, "number");
    const tokens = state.tokens;
    const lastIndex = tokens.length - 1;
    const lastToken = tokens[lastIndex] || "";
    if (calculatorTokenType(lastToken) === "number") {
      if (lastToken.startsWith("-")) {
        tokens[lastIndex] = lastToken.slice(1) || "0";
      } else {
        tokens[lastIndex] = `-${lastToken}`;
      }
      return;
    }
    if (lastIndex >= 0 && calculatorIsUnaryMinus(tokens, lastIndex)) {
      tokens.pop();
      return;
    }
    if (!tokens.length || ["operator", "open-paren", "function"].includes(calculatorTokenType(lastToken))) {
      tokens.push("-");
    }
  }

  function calculatorDelete(state) {
    state.error = "";
    state.standardFormActive = false;
    state.justEvaluated = false;
    const tokens = state.tokens;
    const lastToken = tokens[tokens.length - 1] || "";
    if (!tokens.length) {
      state.resultText = "0";
      return;
    }
    if (calculatorTokenType(lastToken) === "number" && lastToken.length > 1) {
      tokens[tokens.length - 1] = lastToken.slice(0, -1);
      if (!tokens[tokens.length - 1]) {
        tokens.pop();
      }
      return;
    }
    tokens.pop();
  }

  function calculatorClear(state) {
    state.tokens = [];
    state.resultText = "0";
    state.error = "";
    state.lastComputedValue = null;
    state.justEvaluated = false;
    state.standardFormActive = false;
  }

  function tokenizeCalculatorExpression(expression) {
    const tokens = [];
    let index = 0;
    const source = String(expression || "");
    while (index < source.length) {
      const character = source[index];
      if (/\s/u.test(character)) {
        index += 1;
        continue;
      }
      if (/[0-9.]/u.test(character)) {
        let nextIndex = index + 1;
        while (nextIndex < source.length && /[0-9.]/u.test(source[nextIndex])) {
          nextIndex += 1;
        }
        tokens.push({ type: "number", value: source.slice(index, nextIndex) });
        index = nextIndex;
        continue;
      }
      if (/[A-Za-z]/u.test(character)) {
        let nextIndex = index + 1;
        while (nextIndex < source.length && /[A-Za-z]/u.test(source[nextIndex])) {
          nextIndex += 1;
        }
        tokens.push({ type: "identifier", value: source.slice(index, nextIndex) });
        index = nextIndex;
        continue;
      }
      if ("+-*/^()".includes(character)) {
        tokens.push({ type: "symbol", value: character });
        index += 1;
        continue;
      }
      throw new Error("Invalid character");
    }
    return tokens;
  }

  function evaluateCalculatorExpression(tokens, ansValue) {
    const expression = calculatorSerializeTokens(tokens);
    if (!expression) {
      throw new Error("Enter an expression");
    }
    const parsedTokens = tokenizeCalculatorExpression(expression);
    let index = 0;

    function currentToken() {
      return parsedTokens[index] || null;
    }

    function consumeSymbol(symbol) {
      const token = currentToken();
      if (token?.type === "symbol" && token.value === symbol) {
        index += 1;
        return true;
      }
      return false;
    }

    function expectSymbol(symbol) {
      if (!consumeSymbol(symbol)) {
        throw new Error("Invalid expression");
      }
    }

    function parseExpression() {
      let value = parseTerm();
      while (true) {
        if (consumeSymbol("+")) {
          value += parseTerm();
          continue;
        }
        if (consumeSymbol("-")) {
          value -= parseTerm();
          continue;
        }
        break;
      }
      return value;
    }

    function parseTerm() {
      let value = parsePower();
      while (true) {
        if (consumeSymbol("*")) {
          value *= parsePower();
          continue;
        }
        if (consumeSymbol("/")) {
          const divisor = parsePower();
          if (Math.abs(divisor) < 1e-12) {
            throw new Error("Cannot divide by zero");
          }
          value /= divisor;
          continue;
        }
        break;
      }
      return value;
    }

    function parsePower() {
      let value = parseUnary();
      if (consumeSymbol("^")) {
        value = value ** parsePower();
      }
      return value;
    }

    function parseUnary() {
      if (consumeSymbol("+")) {
        return parseUnary();
      }
      if (consumeSymbol("-")) {
        return -parseUnary();
      }
      return parsePrimary();
    }

    function applyCalculatorFunction(name, inputValue) {
      if (!Number.isFinite(inputValue)) {
        throw new Error("Invalid expression");
      }
      const radians = (inputValue * Math.PI) / 180;
      switch (name) {
        case "sin":
          return Math.sin(radians);
        case "cos":
          return Math.cos(radians);
        case "tan":
          if (Math.abs(Math.cos(radians)) < 1e-12) {
            throw new Error("tan undefined");
          }
          return Math.tan(radians);
        case "asin":
          if (inputValue < -1 || inputValue > 1) {
            throw new Error("sin⁻¹ domain error");
          }
          return (Math.asin(inputValue) * 180) / Math.PI;
        case "acos":
          if (inputValue < -1 || inputValue > 1) {
            throw new Error("cos⁻¹ domain error");
          }
          return (Math.acos(inputValue) * 180) / Math.PI;
        case "atan":
          return (Math.atan(inputValue) * 180) / Math.PI;
        case "sqrt":
          if (inputValue < 0) {
            throw new Error("sqrt domain error");
          }
          return Math.sqrt(inputValue);
        case "log":
          if (inputValue <= 0) {
            throw new Error("log domain error");
          }
          return Math.log10(inputValue);
        case "ln":
          if (inputValue <= 0) {
            throw new Error("ln domain error");
          }
          return Math.log(inputValue);
        case "exp":
          return Math.exp(inputValue);
        default:
          throw new Error("Invalid function");
      }
    }

    function parsePrimary() {
      const token = currentToken();
      if (!token) {
        throw new Error("Incomplete expression");
      }
      if (token.type === "number") {
        index += 1;
        const numericValue = Number(token.value);
        if (!Number.isFinite(numericValue)) {
          throw new Error("Invalid number");
        }
        return numericValue;
      }
      if (token.type === "identifier") {
        index += 1;
        const identifier = token.value;
        if (identifier === "Ans") {
          if (!Number.isFinite(ansValue)) {
            throw new Error("Ans unavailable");
          }
          return ansValue;
        }
        if (identifier === "pi") {
          return Math.PI;
        }
        if (identifier === "h") {
          return 6.62607015e-34;
        }
        if (identifier === "qe") {
          return 1.602176634e-19;
        }
        if (identifier === "c") {
          return 299792458;
        }
        expectSymbol("(");
        const inputValue = parseExpression();
        expectSymbol(")");
        return applyCalculatorFunction(identifier, inputValue);
      }
      if (consumeSymbol("(")) {
        const value = parseExpression();
        expectSymbol(")");
        return value;
      }
      throw new Error("Invalid expression");
    }

    const value = parseExpression();
    if (index < parsedTokens.length) {
      throw new Error("Invalid expression");
    }
    if (!Number.isFinite(value)) {
      throw new Error("Result out of range");
    }
    return roundCalculatorValue(value);
  }

  function calculatorEvaluate(state, threadId) {
    try {
      const answer = evaluateCalculatorExpression(state.tokens, calculatorThreadAnswer(threadId));
      state.lastComputedValue = answer;
      state.resultText = formatCalculatorStandardForm(answer);
      state.error = "";
      state.justEvaluated = true;
      state.standardFormActive = true;
      state.tokens = [calculatorPlainString(answer)];
      setCalculatorThreadAnswer(threadId, answer);
    } catch (error) {
      state.error = error?.message || "Unable to calculate";
      state.justEvaluated = false;
      state.standardFormActive = false;
    }
  }

  function calculatorShowStandardForm(state) {
    if (!Number.isFinite(state.lastComputedValue)) {
      state.error = "No answer to convert";
      return;
    }
    state.resultText = formatCalculatorStandardForm(state.lastComputedValue);
    state.error = "";
    state.justEvaluated = true;
    state.standardFormActive = true;
  }

  function handleCalculatorButtonPress(message, buttonConfig) {
    if (!message || !buttonConfig) {
      return;
    }
    const threadId = String(message.thread_id || currentConversationKey() || "");
    const state = ensureCalculatorState(message.id);
    switch (buttonConfig.action) {
      case "digit":
        calculatorAppendDigit(state, buttonConfig.value);
        break;
      case "decimal":
        calculatorAppendDecimal(state);
        break;
      case "operator":
        calculatorAppendOperator(state, buttonConfig.value);
        break;
      case "constant":
        calculatorAppendConstant(state, buttonConfig.value);
        break;
      case "function":
        calculatorAppendFunction(state, buttonConfig.value);
        break;
      case "open-paren":
        calculatorAppendOpenParen(state);
        break;
      case "close-paren":
        calculatorAppendCloseParen(state);
        break;
      case "square":
        calculatorApplySquare(state);
        break;
      case "power":
        calculatorApplyPower(state);
        break;
      case "ten-power":
        calculatorApplyTenPower(state);
        break;
      case "toggle-sign":
        calculatorToggleSign(state);
        break;
      case "delete":
        calculatorDelete(state);
        break;
      case "clear":
        calculatorClear(state);
        break;
      case "standard-form":
        calculatorShowStandardForm(state);
        break;
      case "evaluate":
        calculatorEvaluate(state, threadId);
        break;
      default:
        return;
    }
    renderTranscript("preserve");
  }

  function renderCalculatorMessage(article, message) {
    const state = ensureCalculatorState(message.id);
    article.classList.add("preview-message--calculator");
    article.dataset.calculatorMessageId = String(message.id || "");

    const shell = document.createElement("div");
    shell.className = "preview-calculator";

    const screen = document.createElement("div");
    screen.className = `preview-calculator-screen${state.error ? " is-error" : ""}`;
    const expression = document.createElement("div");
    expression.className = "preview-calculator-expression";
    expression.textContent = formatCalculatorTokens(state.tokens) || "0";
    const result = document.createElement("div");
    result.className = "preview-calculator-result";
    result.textContent = state.error || state.resultText || "0";
    screen.append(expression, result);

    const grid = document.createElement("div");
    grid.className = "preview-calculator-grid";
    CALCULATOR_BUTTON_ROWS.flat().forEach((buttonConfig) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `preview-calculator-key is-${buttonConfig.tone || "number"}`;
      button.textContent = buttonConfig.label;
      if (buttonConfig.span) {
        button.style.setProperty("--preview-calc-key-span", String(buttonConfig.span));
      }
      button.addEventListener("click", () => {
        handleCalculatorButtonPress(message, buttonConfig);
      });
      grid.appendChild(button);
    });

    shell.append(screen, grid);
    article.appendChild(shell);
    window.requestAnimationFrame(() => {
      expression.scrollLeft = expression.scrollWidth;
    });
  }

  function setQuizLoading(blockId, isLoading) {
    const key = String(blockId);
    if (isLoading) {
      loadingMessagesByBlock[key] = true;
      return;
    }
    delete loadingMessagesByBlock[key];
  }

  function setOptimisticUserMessage(blockId, text = "") {
    const key = String(blockId);
    if (!text) {
      delete optimisticUserMessagesByBlock[key];
      return;
    }
    optimisticUserMessagesByBlock[key] = {
      id: `optimistic-user-${key}`,
      kind: "text",
      role: "user",
      created_at: new Date().toISOString(),
      text,
    };
  }

  function maqSelection(questionId) {
    return Array.isArray(maqSelectionsByQuestionId[String(questionId)]) ? maqSelectionsByQuestionId[String(questionId)] : [];
  }

  function setMaqSelection(questionId, selections) {
    const key = String(questionId);
    const normalized = [];
    (selections || []).forEach((selection) => {
      const cleaned = String(selection).trim();
      if (cleaned && !normalized.includes(cleaned)) {
        normalized.push(cleaned);
      }
    });
    if (!normalized.length) {
      delete maqSelectionsByQuestionId[key];
      return;
    }
    maqSelectionsByQuestionId[key] = normalized;
  }

  function toggleMaqSelection(questionId, option) {
    const selections = maqSelection(questionId);
    if (selections.includes(option)) {
      setMaqSelection(
        questionId,
        selections.filter((selection) => selection !== option),
      );
      return;
    }
    setMaqSelection(questionId, [...selections, option]);
  }

  function syncRenderedMaqQuestion(questionId) {
    if (!transcript) {
      return;
    }
    const selections = maqSelection(questionId);
    transcript.querySelectorAll("[data-preview-question='true']").forEach((questionCard) => {
      if (String(questionCard.dataset.questionId || "") !== String(questionId)) {
        return;
      }
      questionCard.querySelectorAll("[data-maq-option-button='true']").forEach((optionButton) => {
        const option = optionButton.dataset.optionValue || "";
        const isSelected = selections.includes(option);
        optionButton.classList.toggle("is-selected", isSelected);
        optionButton.setAttribute("aria-pressed", isSelected ? "true" : "false");
        const checkbox = optionButton.querySelector(".preview-answer-chip-checkbox");
        if (checkbox) {
          checkbox.textContent = isSelected ? "✓" : "";
        }
      });
      questionCard.querySelectorAll("[data-maq-submit-button='true']").forEach((submitButton) => {
        submitButton.dataset.hasSelection = selections.length ? "true" : "false";
        submitButton.disabled = requestInFlight || !selections.length;
      });
    });
  }

  function clearAnsweredQuestionSelections() {
    (previewState.blocks || []).forEach((block) => {
      (block.transcript || []).forEach((message) => {
        if (message.kind === "question" && message.answered) {
          delete maqSelectionsByQuestionId[String(message.question_id)];
        }
      });
    });
  }

  function setStatus(message) {
    if (statusText) {
      statusText.textContent = message || "";
    }
  }

  function isMobileSidebar() {
    return mobileSidebarMedia.matches;
  }

  function clearSidebarSelectionPreview() {
    highlightedSidebarBlockId = "";
    highlightedSidebarBlockUntil = 0;
    blockSwitcher?.querySelectorAll(".preview-block-card.is-selection-preview").forEach((card) => {
      card.classList.remove("is-selection-preview");
    });
  }

  function clearSidebarAutoCloseTimer(clearHighlight = false) {
    if (sidebarAutoCloseTimer) {
      window.clearTimeout(sidebarAutoCloseTimer);
      sidebarAutoCloseTimer = 0;
    }
    if (clearHighlight) {
      clearSidebarSelectionPreview();
    }
  }

  function isSidebarSelectionPreview(blockId) {
    return (
      highlightedSidebarBlockId === String(blockId)
      && highlightedSidebarBlockUntil > Date.now()
    );
  }

  function scheduleSidebarAutoClose(blockId) {
    clearSidebarAutoCloseTimer();
    highlightedSidebarBlockId = String(blockId);
    highlightedSidebarBlockUntil = Date.now() + sidebarSelectionPreviewMs;
    sidebarAutoCloseTimer = window.setTimeout(() => {
      clearSidebarAutoCloseTimer(true);
      setSidebarOpen(false);
    }, sidebarSelectionPreviewMs);
  }

  function applySidebarState() {
    if (isMessengerPreview) {
      previewRoot.classList.remove("is-sidebar-collapsed");
      return;
    }
    previewRoot.classList.toggle("is-sidebar-collapsed", !sidebarOpen);
    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-expanded", String(sidebarOpen));
      sidebarToggle.setAttribute("aria-label", sidebarOpen ? "Hide preview sidebar" : "Show preview sidebar");
    }
    if (sidebarScrim) {
      sidebarScrim.hidden = !isMobileSidebar() || !sidebarOpen;
    }
  }

  function setSidebarOpen(nextOpen) {
    if (isMessengerPreview) {
      sidebarOpen = true;
      applySidebarState();
      return;
    }
    if (!nextOpen) {
      clearSidebarAutoCloseTimer(true);
    }
    sidebarOpen = !!nextOpen;
    applySidebarState();
  }

  if (sidebarSummaryCopy) {
    sidebarSummaryFullText = sidebarSummaryCopy.textContent.trim();
    renderSidebarSummary();
  }

  sidebarSummaryToggle?.addEventListener("click", () => {
    sidebarSummaryExpanded = !sidebarSummaryExpanded;
    renderSidebarSummary();
  });

  previewRoot.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a") : null;
    if (!link || !(link instanceof HTMLAnchorElement)) {
      return;
    }
    if (event.defaultPrevented || link.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    if (!isPracticeValidationLaunchLink(link)) {
      return;
    }
    event.preventDefault();
    beginPracticeValidationLaunch(link);
  });

  function toggleSidebar() {
    setSidebarOpen(!sidebarOpen);
  }

  function closeQuizMenu() {
    if (!quizMenu || !quizMenuTrigger || !quizMenuPanel) {
      return;
    }
    quizMenu.dataset.open = "false";
    quizMenuTrigger.setAttribute("aria-expanded", "false");
    quizMenuPanel.setAttribute("hidden", "hidden");
    quizMenuPanel.hidden = true;
  }

  function openQuizMenu() {
    if (!quizMenu || !quizMenuTrigger || !quizMenuPanel || requestInFlight) {
      return;
    }
    syncQuizMenuItems();
    quizMenu.dataset.open = "true";
    quizMenuTrigger.setAttribute("aria-expanded", "true");
    quizMenuPanel.removeAttribute("hidden");
    quizMenuPanel.hidden = false;
  }

  function isQuizMenuOpen() {
    return !!quizMenuPanel && !quizMenuPanel.hidden;
  }

  function closeHeaderMenu() {
    if (!headerMenu || !headerMenuTrigger || !headerMenuPanel) {
      return;
    }
    headerMenu.dataset.open = "false";
    headerMenuTrigger.setAttribute("aria-expanded", "false");
    headerMenuPanel.setAttribute("hidden", "hidden");
    headerMenuPanel.hidden = true;
  }

  function openHeaderMenu() {
    if (!headerMenu || !headerMenuTrigger || !headerMenuPanel) {
      return;
    }
    headerMenu.dataset.open = "true";
    headerMenuTrigger.setAttribute("aria-expanded", "true");
    headerMenuPanel.removeAttribute("hidden");
    headerMenuPanel.hidden = false;
  }

  function isHeaderMenuOpen() {
    return !!headerMenuPanel && !headerMenuPanel.hidden;
  }

  function syncHeaderMenuResourceVisibility(mode = "none") {
    const isCollectionMode = mode === "collection";
    const isBlockMode = mode === "block";
    if (descriptionResourceButton) {
      descriptionResourceButton.hidden = !isBlockMode;
    }
    if (objectivesResourceButton) {
      objectivesResourceButton.hidden = !isBlockMode;
    }
    if (collectionObjectivesResourceButton) {
      collectionObjectivesResourceButton.hidden = !isCollectionMode;
    }
  }

  function closeSidebarMenu() {
    if (!sidebarMenu || !sidebarMenuTrigger || !sidebarMenuPanel) {
      return;
    }
    sidebarMenu.dataset.open = "false";
    sidebarMenuTrigger.setAttribute("aria-expanded", "false");
    sidebarMenuPanel.setAttribute("hidden", "hidden");
    sidebarMenuPanel.hidden = true;
  }

  function openSidebarMenu() {
    if (!sidebarMenu || !sidebarMenuTrigger || !sidebarMenuPanel) {
      return;
    }
    sidebarMenu.dataset.open = "true";
    sidebarMenuTrigger.setAttribute("aria-expanded", "true");
    sidebarMenuPanel.removeAttribute("hidden");
    sidebarMenuPanel.hidden = false;
  }

  function isSidebarMenuOpen() {
    return !!sidebarMenuPanel && !sidebarMenuPanel.hidden;
  }

  function syncMessengerHeaderHeights() {
    messengerHeaderHeightSyncFrame = 0;
    if (!isMessengerPreview || !previewSidebarHead || !previewChatHeader) {
      return;
    }
    previewSidebarHead.style.minHeight = "";
    previewChatHeader.style.minHeight = "";
    const syncedHeight = Math.max(previewSidebarHead.offsetHeight, previewChatHeader.offsetHeight);
    if (!syncedHeight) {
      return;
    }
    const syncedHeightValue = `${syncedHeight}px`;
    previewSidebarHead.style.minHeight = syncedHeightValue;
    previewChatHeader.style.minHeight = syncedHeightValue;
  }

  function scheduleMessengerHeaderHeightSync() {
    if (!isMessengerPreview || !previewSidebarHead || !previewChatHeader) {
      return;
    }
    if (messengerHeaderHeightSyncFrame) {
      window.cancelAnimationFrame(messengerHeaderHeightSyncFrame);
    }
    messengerHeaderHeightSyncFrame = window.requestAnimationFrame(syncMessengerHeaderHeights);
  }

  function closeObjectiveMenus(exceptMenu = null) {
    previewRoot.querySelectorAll("[data-preview-objective-menu]").forEach((menu) => {
      if (exceptMenu && menu === exceptMenu) {
        return;
      }
      const trigger = menu.querySelector("[data-preview-objective-menu-trigger]");
      const panel = menu.querySelector("[data-preview-objective-menu-panel]");
      menu.dataset.open = "false";
      trigger?.setAttribute("aria-expanded", "false");
      if (panel) {
        panel.hidden = true;
        panel.setAttribute("hidden", "hidden");
      }
    });
  }

  function toggleObjectiveMenu(menu) {
    if (!menu || requestInFlight) {
      return;
    }
    const trigger = menu.querySelector("[data-preview-objective-menu-trigger]");
    const panel = menu.querySelector("[data-preview-objective-menu-panel]");
    if (!trigger || !panel) {
      return;
    }
    const willOpen = panel.hidden;
    closeObjectiveMenus(willOpen ? menu : null);
    if (!willOpen) {
      menu.dataset.open = "false";
      trigger.setAttribute("aria-expanded", "false");
      panel.hidden = true;
      panel.setAttribute("hidden", "hidden");
      return;
    }
    menu.dataset.open = "true";
    trigger.setAttribute("aria-expanded", "true");
    panel.hidden = false;
    panel.removeAttribute("hidden");
  }

  function resizeComposerInput() {
    if (!input) {
      return;
    }
    if (input.dataset.mode === "waq") {
      input.style.overflowY = "auto";
      input.style.height = "72px";
      return;
    }
    input.style.overflowY = "hidden";
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 96)}px`;
  }

  function clearWaqDraftTimer() {
    if (waqDraftDebounceTimer) {
      window.clearTimeout(waqDraftDebounceTimer);
      waqDraftDebounceTimer = 0;
    }
  }

  function setWaqAlignmentLoading(requestId) {
    waqAlignmentLoadingRequestId = requestId || 0;
    renderWaqAlignment();
  }

  function clearWaqAlignmentLoading(requestId = 0) {
    if (requestId && requestId !== waqAlignmentLoadingRequestId) {
      return;
    }
    waqAlignmentLoadingRequestId = 0;
    renderWaqAlignment();
  }

  function abortWaqDraftRequest({ clearLoading = true } = {}) {
    if (waqDraftAbortController) {
      waqDraftAbortController.abort();
      waqDraftAbortController = null;
    }
    if (clearLoading) {
      clearWaqAlignmentLoading();
    }
  }

  function setWaqAlignmentFlash(isFlashing) {
    if (!waqAlignment) {
      return;
    }
    waqAlignment.classList.toggle("is-flashing", !!isFlashing);
  }

  function renderWaqAlignment(question = pendingWrittenQuestion(), { flash = false } = {}) {
    if (!waqAlignment || !waqAlignmentLabel || !waqAlignmentFill) {
      return;
    }
    if (!question || question.answered || question.flagged) {
      waqAlignmentLoadingRequestId = 0;
      waqAlignment.hidden = true;
      waqAlignment.dataset.state = "drafting";
      waqAlignment.dataset.loading = "false";
      waqAlignmentFill.style.width = "0%";
      waqAlignmentLabel.textContent = "Start typing";
      if (waqAlignmentLoader) {
        waqAlignmentLoader.hidden = true;
      }
      setWaqAlignmentFlash(false);
      return;
    }

    const score = Number(question.alignment_score || 0);
    const state = question.alignment_state || "drafting";
    const isLoading = !!waqAlignmentLoadingRequestId && !!String(question.draft_answer || "").trim();
    waqAlignment.hidden = false;
    waqAlignment.dataset.state = state;
    waqAlignment.dataset.loading = isLoading ? "true" : "false";
    waqAlignmentFill.style.width = `${Math.max(0, Math.min(score, 100))}%`;
    if (waqAlignmentLoader) {
      waqAlignmentLoader.hidden = !isLoading;
    }
    if (!question.draft_answer && !question.submitted_text) {
      waqAlignmentLabel.textContent = "Start typing";
    } else if (state === "aligned") {
      waqAlignmentLabel.textContent = `Aligned ${formatPercentage(score)}`;
    } else if (state === "close") {
      waqAlignmentLabel.textContent = `${formatPercentage(score)} close`;
    } else {
      waqAlignmentLabel.textContent = `${formatPercentage(score)} building`;
    }
    if (flash) {
      setWaqAlignmentFlash(false);
      window.requestAnimationFrame(() => {
        setWaqAlignmentFlash(true);
        window.setTimeout(() => setWaqAlignmentFlash(false), 700);
      });
      return;
    }
    setWaqAlignmentFlash(false);
  }

  function syncComposerInputFromState() {
    if (!input) {
      return;
    }
    if (isStatsView()) {
      input.value = "";
      input.dataset.mode = "chat";
      resizeComposerInput();
      return;
    }
    if (currentProject()) {
      if (input.dataset.mode === "waq") {
        input.value = "";
      }
      input.dataset.mode = "project-chat";
      resizeComposerInput();
      return;
    }
    const question = pendingWrittenQuestion();
    if (question) {
      const nextValue = question.draft_answer || "";
      if (input.value !== nextValue) {
        input.value = nextValue;
      }
      input.dataset.mode = "waq";
      resizeComposerInput();
      return;
    }

    if (input.dataset.mode === "waq") {
      input.value = "";
    }
    input.dataset.mode = "chat";
    resizeComposerInput();
  }

  function syncComposerState() {
    if (!submitButton || !input) {
      return;
    }
    if (isStatsView()) {
      previewRoot.classList.remove("is-waq-mode", "is-project-mode");
      form?.classList.remove("is-waq-mode");
      form?.classList.add("is-read-only");
      quizControls?.classList.remove("is-answer-mode", "is-submit-mode");
      input.placeholder = "Ask";
      setComposerSubmitButton(submitButton, { label: "Quiz" });
      input.disabled = true;
      submitButton.disabled = true;
      if (quizMenu) {
        quizMenu.hidden = false;
        quizMenu.removeAttribute("hidden");
        quizMenu.setAttribute("aria-hidden", "false");
      }
      if (quizMenuTrigger) {
        quizMenuTrigger.disabled = true;
      }
      closeQuizMenu();
      renderWaqAlignment(null);
      return;
    }
    const activeProject = currentProject();
    const activeWaq = pendingWrittenQuestion();
    const hasText = !!input.value.trim();
    const isWaqMode = !!activeWaq;
    const isProjectMode = !!activeProject;
    const shouldCollapseQuizMenu = hasText || isWaqMode || isProjectMode;

    previewRoot.classList.toggle("is-waq-mode", isWaqMode);
    previewRoot.classList.toggle("is-project-mode", isProjectMode);
    form?.classList.toggle("is-waq-mode", isWaqMode);
    form?.classList.remove("is-read-only");
    input.disabled = requestInFlight;
    quizControls?.classList.toggle("is-answer-mode", isWaqMode);
    quizControls?.classList.toggle("is-submit-mode", shouldCollapseQuizMenu);
    input.placeholder = isWaqMode
      ? "Write your answer..."
      : (isProjectMode ? "Ask for a hint or nudge..." : "Ask");
    setComposerSubmitButton(submitButton, {
      label: isWaqMode ? "Submit answer" : (hasText ? "Send" : (isProjectMode ? "Hint" : "Quiz")),
      iconOnly: isWaqMode,
    });
    submitButton.disabled = requestInFlight || (isWaqMode && !hasText);
    if (quizMenu) {
      quizMenu.hidden = false;
      quizMenu.removeAttribute("hidden");
      quizMenu.setAttribute("aria-hidden", shouldCollapseQuizMenu ? "true" : "false");
    }
    if (shouldCollapseQuizMenu) {
      closeQuizMenu();
    }
    if (quizMenuTrigger) {
      quizMenuTrigger.disabled = requestInFlight || shouldCollapseQuizMenu;
    }
    syncQuizMenuItems();
    renderWaqAlignment(activeWaq);
  }

  function setComposerDisabled(disabled) {
    requestInFlight = disabled;
    if (input) {
      input.disabled = disabled;
    }
    if (submitButton) {
      submitButton.disabled = disabled;
    }
    if (quizMenuTrigger) {
      quizMenuTrigger.disabled = disabled || !!input?.value.trim() || !!pendingWrittenQuestion();
    }
    previewRoot.querySelectorAll(".preview-answer-chip").forEach((button) => {
      button.disabled = disabled;
    });
    previewRoot.querySelectorAll(".preview-question-submit").forEach((button) => {
      button.disabled = disabled || button.dataset.hasSelection !== "true";
    });
    previewRoot.querySelectorAll(".preview-flag-button").forEach((button) => {
      button.disabled = disabled || button.textContent === "Flagged";
    });
    previewRoot.querySelectorAll(".preview-project-answer-input, .preview-project-answer-submit").forEach((field) => {
      field.disabled = disabled || field.dataset.completed === "true";
    });
    previewRoot.querySelectorAll(".preview-further-study-button, .preview-further-study-question").forEach((button) => {
      button.disabled = disabled;
    });
    resourceButtons.forEach((button) => {
      button.disabled = disabled;
    });
    previewRoot.querySelectorAll("[data-preview-metric-button='true']").forEach((button) => {
      button.disabled = disabled;
    });
    if (disabled) {
      closeQuizMenu();
      closeObjectiveMenus();
    }
    syncQuizMenuItems();
    syncFlagSheetState();
    syncGuardrailSheetState();
  }

  function updateComposerClearance() {
    if (!form) {
      return;
    }
    if (form.hidden) {
      previewRoot.style.setProperty("--preview-composer-clearance", "1rem");
      return;
    }
    previewRoot.style.setProperty("--preview-composer-clearance", `${form.offsetHeight + 20}px`);
  }

  function clampPercentage(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return 0;
    }
    return Math.max(0, Math.min(parsed, 100));
  }

  function formatPercentage(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }

  function formatMetricNumber(value) {
    return Number(value || 0).toFixed(1);
  }

  function formatCount(value, singular, plural = `${singular}s`) {
    const count = Number(value || 0);
    return `${count} ${count === 1 ? singular : plural}`;
  }

  function formatHalfLifeDays(days) {
    const count = Number(days || 0);
    if (!count) {
      return "";
    }
    return `${count} day${count === 1 ? "" : "s"}`;
  }

  function formatPreviewDate(isoDate) {
    if (!isoDate) {
      return "";
    }
    const parsed = new Date(`${isoDate}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
      return isoDate;
    }
    return previewDateFormatter.format(parsed);
  }

  function parseMessageDate(value) {
    if (!value) {
      return null;
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function parseCalendarDate(value) {
    const rawValue = String(value || "").trim();
    if (!rawValue) {
      return null;
    }
    const parsed = new Date(`${rawValue}T12:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function isSameCalendarDay(left, right) {
    return left.getFullYear() === right.getFullYear()
      && left.getMonth() === right.getMonth()
      && left.getDate() === right.getDate();
  }

  function calendarDayKey(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return "";
    }
    return [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function daysSince(date) {
    const now = new Date();
    const currentDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const targetDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    return Math.round((currentDay.getTime() - targetDay.getTime()) / 86400000);
  }

  function formatConversationTimestamp(value) {
    const parsed = parseMessageDate(value);
    if (!parsed) {
      return "";
    }
    const now = new Date();
    if (isSameCalendarDay(parsed, now)) {
      return previewTimeFormatter.format(parsed);
    }
    const dayDelta = daysSince(parsed);
    if (dayDelta >= 0 && dayDelta <= 6) {
      return previewWeekdayFormatter.format(parsed);
    }
    return previewSlashDateFormatter.format(parsed);
  }

  function formatTranscriptDayLabel(value) {
    const parsed = value instanceof Date ? value : parseMessageDate(value);
    if (!parsed) {
      return "";
    }
    const now = new Date();
    if (isSameCalendarDay(parsed, now)) {
      return "Today";
    }
    const dayDelta = daysSince(parsed);
    if (dayDelta >= 0 && dayDelta <= 6) {
      return previewWeekdayFormatter.format(parsed);
    }
    return previewDateFormatter.format(parsed);
  }

  function formatStatsTimelineLabel(value) {
    const parsed = value instanceof Date ? value : parseCalendarDate(value);
    if (!parsed) {
      return formatPreviewDate(value) || String(value || "");
    }
    return formatTranscriptDayLabel(parsed);
  }

  function formatMessageClock(value) {
    const parsed = parseMessageDate(value);
    if (!parsed) {
      return "";
    }
    return previewTimeFormatter.format(parsed);
  }

  function appendMessageTimestamp(container, message) {
    const timestampText = formatMessageClock(message?.created_at);
    if (!timestampText) {
      return;
    }
    const timestamp = document.createElement("div");
    timestamp.className = "preview-message-time";
    timestamp.textContent = timestampText;
    container.appendChild(timestamp);
  }

  function renderTranscriptDaySeparator(date) {
    const label = formatTranscriptDayLabel(date);
    if (!label) {
      return null;
    }
    const separator = document.createElement("time");
    separator.className = "preview-chat-day-separator";
    separator.dateTime = calendarDayKey(date);
    separator.textContent = label;
    return separator;
  }

  function messagePreviewText(message) {
    if (!message || message.kind === "loading" || message.kind === "calculator") {
      return "";
    }
    if (message.kind === "question") {
      return questionStemText(message);
    }
    if (message.kind === "resource") {
      return message.text || message.resource_label || "";
    }
    if (message.kind === "feedback" || message.kind === "text" || message.kind === "answer" || message.kind === "validation_reminder") {
      return String(message.text || "").trim();
    }
    return String(message.text || "").trim();
  }

  function humanReadableMessage(message) {
    if (!message || message.kind === "loading") {
      return false;
    }
    return Boolean(messagePreviewText(message));
  }

  function truncateConversationPreview(text, limit = 78) {
    const normalized = String(text || "").replace(/\s+/g, " ").trim();
    if (normalized.length <= limit) {
      return normalized;
    }
    return `${normalized.slice(0, limit - 1).trimEnd()}…`;
  }

  function latestConversationMessage(conversation) {
    const messages = combinedTranscript(conversation);
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (humanReadableMessage(messages[index])) {
        return messages[index];
      }
    }
    return null;
  }

  function latestConversationTimestamp(conversation) {
    const messages = combinedTranscript(conversation);
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (!humanReadableMessage(messages[index])) {
        continue;
      }
      const parsed = parseMessageDate(messages[index]?.created_at);
      if (parsed) {
        return parsed;
      }
    }
    return null;
  }

  function latestConversationAccessTimestamp(conversation) {
    const messages = combinedTranscript(conversation);
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (!humanReadableMessage(message)) {
        continue;
      }
      if (message?.is_block_welcome || message?.is_collection_welcome) {
        continue;
      }
      const parsed = parseMessageDate(message?.created_at);
      if (parsed) {
        return parsed;
      }
    }
    return null;
  }

  function conversationAvatarText(title, fallback = "B") {
    return String(title || "")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || fallback;
  }

  function displayObjectiveCode(code) {
    const normalized = String(code || "").trim();
    if (!normalized.includes(".")) {
      return normalized;
    }
    const parts = normalized.split(".").filter(Boolean);
    return parts.length > 1 ? parts.slice(1).join(".") : normalized;
  }

  function blockConversationRowData(block) {
    const lastMessage = latestConversationMessage(block);
    const lastTimestamp = latestConversationTimestamp(block);
    const lastAccessTimestamp = latestConversationAccessTimestamp(block);
    const createdAt = parseMessageDate(block?.created_at || "");
    return {
      id: String(block?.id || ""),
      threadKind: "block",
      block,
      createdAt,
      lastMessage,
      lastMessageAt: lastAccessTimestamp,
      previewText: truncateConversationPreview(messagePreviewText(lastMessage) || "Tap Quiz to start this conversation."),
      previewTimestamp: formatConversationTimestamp(lastTimestamp ? lastTimestamp.toISOString() : (lastMessage?.created_at || "")),
      avatarUrl: String(block?.avatar_url || "").trim(),
      avatarText: conversationAvatarText(block?.title, "B"),
      title: String(block?.title || ""),
      isSquare: false,
    };
  }

  function collectionConversationRowData(collection) {
    const lastMessage = latestConversationMessage(collection);
    const lastTimestamp = latestConversationTimestamp(collection);
    const lastAccessTimestamp = latestConversationAccessTimestamp(collection);
    const createdAt = parseMessageDate(collection?.created_at || "");
    return {
      id: collectionThreadKey(collection?.id),
      threadKind: "collection",
      collection,
      createdAt,
      lastMessage,
      lastMessageAt: lastAccessTimestamp,
      previewText: truncateConversationPreview(messagePreviewText(lastMessage) || "Tap Quiz to start this conversation."),
      previewTimestamp: formatConversationTimestamp(lastTimestamp ? lastTimestamp.toISOString() : (lastMessage?.created_at || "")),
      avatarUrl: "",
      avatarText: conversationAvatarText(collection?.title, "C"),
      title: String(collection?.title || ""),
      isSquare: true,
    };
  }

  function courseStats() {
    return previewState.course?.stats || {};
  }

  function statsPreviewText(stats = courseStats()) {
    const summary = stats.summary || {};
    return `Mastery ${formatPercentage(summary.mastery)} • Coverage ${formatPercentage(summary.coverage)} • Streak ${Number(summary.longest_streak || 0)}`;
  }

  function statsHeaderMetaText(stats = courseStats()) {
    const updatedLabel = formatConversationTimestamp(stats.latest_answered_at || "");
    return updatedLabel
      ? `Updated ${updatedLabel}`
      : "Mastery, coverage, and longest streak.";
  }

  function statsConversationRowData() {
    const stats = courseStats();
    return {
      id: STATS_THREAD_ID,
      isStats: true,
      title: "My Stats",
      previewText: statsPreviewText(stats),
      previewTimestamp: formatConversationTimestamp(stats.latest_answered_at || ""),
      avatarUrl: statsIconUrl,
      avatarText: "MS",
    };
  }

  function collectionCount() {
    return Array.isArray(previewState.collections) ? previewState.collections.length : 0;
  }

  function normalizeConversationListMode(mode) {
    if (mode === "collections") {
      return "collections";
    }
    if (mode === "blocks") {
      return "blocks";
    }
    return "all";
  }

  function currentConversationListMode() {
    return normalizeConversationListMode(conversationListMode);
  }

  function syncConversationSwitcher() {
    if (!conversationSwitcher) {
      return;
    }
    const hasCollections = collectionCount() > 0;
    conversationSwitcher.hidden = !hasCollections;
    if (!hasCollections) {
      conversationListMode = "all";
      return;
    }
    const activeMode = currentConversationListMode();
    conversationSwitcherButtons.forEach((button) => {
      const isActive = button.dataset.previewConversationMode === activeMode;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function setAvatarContent(container, {
    avatarUrl = "",
    avatarText = "",
    imageClass = "",
    isSquare = false,
  } = {}) {
    if (!container) {
      return;
    }
    const hasImage = Boolean(String(avatarUrl || "").trim());
    container.classList.toggle("is-image", hasImage);
    container.classList.toggle("is-square", Boolean(isSquare));
    container.replaceChildren();
    container.textContent = "";
    if (hasImage) {
      const image = document.createElement("img");
      image.className = imageClass;
      image.src = avatarUrl;
      image.alt = "";
      image.loading = "lazy";
      image.decoding = "async";
      container.appendChild(image);
      return;
    }
    container.textContent = avatarText;
  }

  function sortedConversationBlocks() {
    const activeMode = currentConversationListMode();
    if (activeMode === "collections") {
      return (previewState.collections || []).map((collection) => collectionConversationRowData(collection));
    }
    if (activeMode === "blocks") {
      return (previewState.blocks || []).map((block) => blockConversationRowData(block));
    }
    return [
      ...(previewState.blocks || []).map((block) => blockConversationRowData(block)),
      ...(previewState.collections || []).map((collection) => collectionConversationRowData(collection)),
    ].sort((left, right) => {
      const rightTime = right.lastMessageAt ? right.lastMessageAt.getTime() : 0;
      const leftTime = left.lastMessageAt ? left.lastMessageAt.getTime() : 0;
      if (rightTime !== leftTime) {
        return rightTime - leftTime;
      }
      const leftCreatedAt = left.createdAt ? left.createdAt.getTime() : Number.POSITIVE_INFINITY;
      const rightCreatedAt = right.createdAt ? right.createdAt.getTime() : Number.POSITIVE_INFINITY;
      if (leftCreatedAt !== rightCreatedAt) {
        return leftCreatedAt - rightCreatedAt;
      }
      return 0;
    });
  }

  function filteredConversationBlocks() {
    const query = messengerSearchQuery.trim().toLowerCase();
    const blockEntries = !query
      ? sortedConversationBlocks()
      : sortedConversationBlocks().filter((entry) => {
        const haystack = `${entry.title || ""} ${entry.previewText || ""}`.toLowerCase();
        return haystack.includes(query);
      });
    const statsEntry = statsConversationRowData();
    const statsHaystack = `${statsEntry.title} ${statsEntry.previewText}`.toLowerCase();
    return [
      ...((!query || statsHaystack.includes(query)) ? [statsEntry] : []),
      ...blockEntries,
    ];
  }

  function setMessengerMobileChatOpen(nextOpen) {
    messengerMobileChatOpen = !!nextOpen;
    previewRoot.classList.toggle("is-messenger-chat-open", messengerMobileChatOpen);
    requestTranscriptScrollButtonSync();
  }

  function syncTranscriptScrollButton() {
    if (!transcript || !scrollBottomButton) {
      return;
    }
    if (currentConversationEndsWithCalculator()) {
      scrollBottomButton.hidden = true;
      return;
    }
    const maxScrollTop = Math.max(transcript.scrollHeight - transcript.clientHeight, 0);
    const distanceFromBottom = Math.max(maxScrollTop - transcript.scrollTop, 0);
    const chatIsVisible = !isMessengerPreview || messengerMobileChatOpen || !messengerMobileMedia.matches;
    const shouldShow = chatIsVisible && maxScrollTop > 32 && distanceFromBottom > 72;
    scrollBottomButton.hidden = !shouldShow;
  }

  function requestTranscriptScrollButtonSync() {
    if (!scrollBottomButton) {
      return;
    }
    if (transcriptScrollButtonSyncFrame) {
      return;
    }
    transcriptScrollButtonSyncFrame = window.requestAnimationFrame(() => {
      transcriptScrollButtonSyncFrame = 0;
      syncTranscriptScrollButton();
    });
  }

  function metricLabel(metricKey, scope = "block") {
    return {
      overall: scope === "course" ? "Overall course score" : "Overall score",
      mastery: "Mastery",
      coverage: "Coverage",
    }[metricKey] || "Metric";
  }

  function scrollTranscriptToBottom() {
    transcript?.scrollTo({ top: transcript.scrollHeight, behavior: reducedMotionMedia.matches ? "auto" : "smooth" });
    requestTranscriptScrollButtonSync();
  }

  function transcriptHeaderOffset() {
    if (!transcript || mobileChatMedia.matches) {
      return 0;
    }
    const header = previewRoot.querySelector(".preview-chat-header");
    if (!header || !header.offsetHeight) {
      return 0;
    }
    return header.offsetHeight;
  }

  function scrollTranscriptToMessageTop(messageElement) {
    if (!transcript || !messageElement) {
      return;
    }
    const targetTop = Math.max(messageElement.offsetTop - transcriptHeaderOffset(), 0);
    transcript.scrollTo({ top: targetTop, behavior: reducedMotionMedia.matches ? "auto" : "smooth" });
  }

  function latestTranscriptMessageCard() {
    if (!transcript) {
      return null;
    }
    return transcript.lastElementChild instanceof HTMLElement ? transcript.lastElementChild : null;
  }

  function latestPendingQuestionCard() {
    if (!transcript) {
      return null;
    }
    return Array.from(transcript.querySelectorAll("[data-preview-question='true']")).reverse().find(
      (element) => element.dataset.answered !== "true" && element.dataset.flagged !== "true",
    ) || null;
  }

  function updateMathOverflowState() {
    if (!transcript) {
      return;
    }
    const transcriptStyles = window.getComputedStyle(transcript);
    const transcriptAvailableWidth = transcript.clientWidth
      - Number.parseFloat(transcriptStyles.paddingLeft || "0")
      - Number.parseFloat(transcriptStyles.paddingRight || "0");

    function clearMathOverflowStyles(message) {
      message.classList.remove("preview-message--math-overflow");
      [
        "width",
        "max-width",
      ].forEach((property) => {
        message.style.removeProperty(property);
      });
      const overflowFrame = message.querySelector(":scope > .preview-message-overflow-frame");
      if (overflowFrame instanceof HTMLElement) {
        while (overflowFrame.firstChild) {
          message.insertBefore(overflowFrame.firstChild, overflowFrame);
        }
        overflowFrame.remove();
      }
      message.querySelectorAll(".preview-math-overflow-block").forEach((node) => {
        if (!(node instanceof HTMLElement)) {
          return;
        }
        node.classList.remove("preview-math-overflow-block");
        [
          "min-width",
        ].forEach((property) => {
          node.style.removeProperty(property);
        });
      });
    }

    function ensureMessageOverflowFrame(message) {
      const existingFrame = message.querySelector(":scope > .preview-message-overflow-frame");
      if (existingFrame instanceof HTMLElement) {
        return existingFrame;
      }
      const frame = document.createElement("div");
      frame.className = "preview-message-overflow-frame";
      while (message.firstChild) {
        frame.appendChild(message.firstChild);
      }
      message.appendChild(frame);
      return frame;
    }

    function applyMathOverflowStyles(message, overflowTargets, messageWidth) {
      message.classList.add("preview-message--math-overflow");
      message.style.setProperty("width", `${messageWidth}px`, "important");
      message.style.setProperty("max-width", `${messageWidth}px`, "important");
      ensureMessageOverflowFrame(message);
      overflowTargets.forEach((target) => {
        if (!(target instanceof HTMLElement)) {
          return;
        }
        target.classList.add("preview-math-overflow-block");
        target.style.setProperty("min-width", "max-content", "important");
      });
    }

    transcript.querySelectorAll(".preview-message").forEach((message) => {
      if (!(message instanceof HTMLElement)) {
        return;
      }
      const mathNodes = Array.from(message.querySelectorAll(".katex-display")).filter(
        (node) => node instanceof HTMLElement,
      );
      clearMathOverflowStyles(message);
      if (!mathNodes.length || !mobileChatMedia.matches || transcriptAvailableWidth <= 0) {
        return;
      }
      const messageWidth = Math.min(message.getBoundingClientRect().width, transcriptAvailableWidth);
      const overflowTargets = new Set();
      const hasOverflow = mathNodes.some((node) => {
        const element = node;
        const isOverflowing = element.scrollWidth - messageWidth > 2
          || element.getBoundingClientRect().width - messageWidth > 2;
        if (isOverflowing) {
          overflowTargets.add(element);
        }
        return isOverflowing;
      });
      if (hasOverflow) {
        applyMathOverflowStyles(message, overflowTargets, messageWidth);
      }
    });
  }

  function updateQuestionOverflowState(activeQuestion) {
    if (!transcript || !activeQuestion || !activeQuestion.isConnected) {
      return;
    }
    const hint = activeQuestion.querySelector(".preview-question-overflow-hint");
    if (!hint) {
      return;
    }
    if (!mobileChatMedia.matches) {
      activeQuestion.classList.remove("is-overflowing-question");
      hint.hidden = true;
      return;
    }
    const answerRegion = activeQuestion.querySelector(".preview-message-options") || activeQuestion;
    const transcriptRect = transcript.getBoundingClientRect();
    const answerRect = answerRegion.getBoundingClientRect();
    const visibilityTolerance = 6;
    const isFullyVisible = answerRect.bottom <= transcriptRect.bottom + visibilityTolerance;
    activeQuestion.classList.toggle("is-overflowing-question", !isFullyVisible);
    hint.hidden = isFullyVisible;
  }

  function syncQuestionViewport(scrollMode = "bottom", previousScrollTop = 0) {
    if (!transcript) {
      return;
    }

    const questionCards = Array.from(transcript.querySelectorAll("[data-preview-question='true']"));
    questionCards.forEach((card) => {
      card.classList.remove("is-overflowing-question");
      const hint = card.querySelector(".preview-question-overflow-hint");
      if (hint) {
        hint.hidden = true;
      }
    });

    const activeQuestion = latestPendingQuestionCard();
    if (activeQuestion) {
      if (scrollMode === "question") {
        scrollTranscriptToMessageTop(activeQuestion);
        window.requestAnimationFrame(() => {
          if (latestPendingQuestionCard() === activeQuestion) {
            updateQuestionOverflowState(activeQuestion);
          }
        });
      } else {
        updateQuestionOverflowState(activeQuestion);
        window.requestAnimationFrame(() => {
          if (latestPendingQuestionCard() === activeQuestion) {
            updateQuestionOverflowState(activeQuestion);
          }
        });
      }

      if (scrollMode === "question") {
        return;
      }
    }

    if (scrollMode === "preserve") {
      transcript.scrollTop = Math.min(previousScrollTop, transcript.scrollHeight);
      return;
    }

    const latestMessage = latestTranscriptMessageCard();
    if (latestMessage) {
      scrollTranscriptToMessageTop(latestMessage);
      return;
    }

    scrollTranscriptToBottom();
  }

  function ensureActiveBlockCardVisible() {
    if (!blockSwitcher) {
      return;
    }

    const activeCard = blockSwitcher.querySelector(".preview-block-card.is-active");
    if (!activeCard) {
      return;
    }

    const containerRect = blockSwitcher.getBoundingClientRect();
    const cardRect = activeCard.getBoundingClientRect();
    const padding = 12;
    const visibleHeight = containerRect.height - padding * 2;

    if (cardRect.height > visibleHeight) {
      blockSwitcher.scrollTop = Math.max(activeCard.offsetTop - padding, 0);
      return;
    }

    if (cardRect.top < containerRect.top + padding) {
      blockSwitcher.scrollTop -= containerRect.top + padding - cardRect.top;
      return;
    }

    if (cardRect.bottom > containerRect.bottom - padding) {
      blockSwitcher.scrollTop += cardRect.bottom - (containerRect.bottom - padding);
    }
  }

  function metricButtonMarkup(metricKey, value, { scope = "block", blockId = "", metrics = null } = {}) {
    const blockAttribute = blockId ? ` data-block-id="${blockId}"` : "";
    return `
      <button
        type="button"
        class="preview-block-metric${metricKey === "overall" ? " preview-block-metric--overall" : ""}"
        data-preview-metric-button="true"
        data-metric-key="${metricKey}"
        data-metric-scope="${scope}"${blockAttribute}
      >
        <span>${metricLabel(metricKey, scope)}</span>
        <strong>${formatPercentage(value)}</strong>
      </button>
    `;
  }

  function metricMarkup(metrics, { scope = "block", blockId = "" } = {}) {
    return `
      ${metricButtonMarkup("mastery", metrics.mastery, { scope, blockId, metrics })}
      ${metricButtonMarkup("coverage", metrics.coverage, { scope, blockId, metrics })}
    `;
  }

  function renderCourseMetrics() {
    if (!courseMetricsPanel) {
      return;
    }
    const metrics = previewState.course?.metrics;
    if (!metrics) {
      courseMetricsPanel.hidden = true;
      courseMetricsPanel.innerHTML = "";
      return;
    }
    courseMetricsPanel.hidden = false;
    if (isMessengerPreview) {
      courseMetricsPanel.innerHTML = `
        <div class="preview-messenger-metric-grid">
          <button
            type="button"
            class="preview-messenger-metric-card"
            data-preview-metric-button="true"
            data-metric-key="mastery"
            data-metric-scope="course"
          >
            <span>Mastery</span>
            <strong>${formatPercentage(metrics.mastery)}</strong>
          </button>
          <button
            type="button"
            class="preview-messenger-metric-card"
            data-preview-metric-button="true"
            data-metric-key="coverage"
            data-metric-scope="course"
          >
            <span>Coverage</span>
            <strong>${formatPercentage(metrics.coverage)}</strong>
          </button>
        </div>
      `;
      return;
    }
    courseMetricsPanel.innerHTML = `
      <p class="preview-sidebar-section-label">COURSE METRICS</p>
      <div class="preview-block-metrics preview-block-metrics--course">${metricMarkup(metrics, { scope: "course" })}</div>
    `;
  }

  function optionLabel(index) {
    return String.fromCharCode(65 + index);
  }

  function questionTypeLabel(message) {
    if (message?.question_type_label) {
      return String(message.question_type_label);
    }
    switch (String(message?.question_type || "")) {
      case "num":
        return "Numerical MCQ";
      case "maq":
        return "Multiple-answer MCQ";
      case "waq":
        return "Written answer";
      case "mcq":
      default:
        return "MCQ";
    }
  }

  function formatSelectedAnswers(options, selectedAnswers, flagged = false) {
    const normalizedAnswers = Array.isArray(selectedAnswers) ? selectedAnswers : [];
    const selectedText = normalizedAnswers.map((answer) => {
      const optionIndex = Array.isArray(options) ? options.indexOf(answer) : -1;
      return optionIndex >= 0 ? `${optionLabel(optionIndex)}. ${answer}` : answer;
    });
    if (!selectedText.length) {
      return flagged ? "Selected: flagged" : "";
    }
    return `Selected: ${selectedText.join(", ")}${flagged ? " • flagged" : ""}`;
  }

  function normalizeAnswerList(answers) {
    return Array.isArray(answers) ? answers.filter(Boolean) : [];
  }

  function reviewedOptionState(option, selectedAnswers, correctAnswers) {
    const isSelected = selectedAnswers.includes(option);
    const isCorrect = correctAnswers.includes(option);

    if (isSelected && isCorrect) {
      return { modifier: "is-correct", badge: "Correct", indicator: "✓" };
    }
    if (isSelected && !isCorrect) {
      return { modifier: "is-incorrect", badge: "Your choice", indicator: "×" };
    }
    if (!isSelected && isCorrect) {
      return { modifier: "is-missed", badge: "Missed", indicator: "!" };
    }
    return { modifier: "", badge: "", indicator: "" };
  }

  function renderAnsweredOptions(message) {
    const optionsWrapper = document.createElement("div");
    optionsWrapper.className = "preview-message-options preview-message-options--review";

    const selectedAnswers = normalizeAnswerList(message.selected_answers?.length ? message.selected_answers : [message.selected_answer]);
    const correctAnswers = normalizeAnswerList(message.correct_answers);
    const renderOptions = questionRenderOptions(message);

    message.options.forEach((option, index) => {
      const state = reviewedOptionState(option, selectedAnswers, correctAnswers);
      const optionRow = document.createElement("div");
      optionRow.className = `preview-answer-chip preview-answer-chip--review${state.modifier ? ` ${state.modifier}` : ""}`;
      const indicator = document.createElement("span");
      indicator.className = "preview-answer-chip-indicator";
      indicator.setAttribute("aria-hidden", "true");
      indicator.textContent = state.indicator;
      const label = document.createElement("span");
      label.className = "preview-answer-chip-label";
      label.textContent = optionLabel(index);
      const text = document.createElement("span");
      text.className = "preview-answer-chip-text";
      richText.appendInlineText(text, option, renderOptions);
      optionRow.append(indicator, label, text);
      if (state.badge) {
        const badge = document.createElement("span");
        badge.className = "preview-answer-chip-badge";
        badge.textContent = state.badge;
        optionRow.appendChild(badge);
      }
      optionsWrapper.appendChild(optionRow);
    });

    if (message.flagged) {
      const flaggedNote = document.createElement("p");
      flaggedNote.className = "preview-message-sources";
      flaggedNote.textContent = "Question flagged.";
      optionsWrapper.appendChild(flaggedNote);
    }

    return optionsWrapper;
  }

  function renderWrittenAnswerReview(message) {
    const review = document.createElement("div");
    review.className = "preview-written-answer-review";
    const renderOptions = questionRenderOptions(message);
    review.appendChild(richText.buildTextPanel("Your answer", message.submitted_text || "No answer submitted.", "", renderOptions));

    const meter = document.createElement("div");
    meter.className = `preview-written-answer-alignment is-${message.alignment_state || "drafting"}`;
    meter.innerHTML = `
      <div class="preview-written-answer-alignment-head">
        <span>Alignment</span>
        <strong>${formatPercentage(message.alignment_score)}</strong>
      </div>
      <div class="preview-written-answer-alignment-track" aria-hidden="true">
        <span style="width: ${Math.max(0, Math.min(Number(message.alignment_score || 0), 100))}%;"></span>
      </div>
    `;
    review.appendChild(meter);

    if (message.model_answer_revealed && message.model_answer) {
      review.appendChild(richText.buildTextPanel("Model answer", message.model_answer, "is-model-answer", renderOptions));
    }

    return review;
  }

  function appendFormattedMessageContent(container, text, options = {}) {
    richText.appendFormattedMessageContent(container, text, options);
  }

  function appendMessageTextWithInlineCta(container, message) {
    const text = String(message?.text || "");
    const ctaLabel = String(message?.inline_cta_label || "").trim();
    const ctaUrl = practiceValidationUrl;
    const quotedLabel = ctaLabel ? `"${ctaLabel}"` : "";
    if (!text) {
      return;
    }
    if (!ctaLabel || !ctaUrl || !quotedLabel || !text.includes(quotedLabel)) {
      appendFormattedMessageContent(container, text);
      return;
    }
    const labelIndex = text.indexOf(quotedLabel);
    const beforeText = text.slice(0, labelIndex);
    const afterText = text.slice(labelIndex + quotedLabel.length);
    const paragraph = document.createElement("p");
    paragraph.className = "preview-message-paragraph";
    paragraph.append(document.createTextNode(beforeText));
    paragraph.append(document.createTextNode('"'));
    const link = document.createElement("a");
    link.className = "preview-inline-message-link";
    link.href = ctaUrl;
    link.textContent = ctaLabel;
    paragraph.appendChild(link);
    paragraph.append(document.createTextNode('"'));
    paragraph.append(document.createTextNode(afterText));
    container.appendChild(paragraph);
  }

  function appendQuestionCodeSnippet(container, message) {
    if (!container || !message?.is_coding_question || !message.code_snippet) {
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "preview-question-code-snippet";
    const label = document.createElement("span");
    label.className = "preview-question-code-label";
    const kind = message.coding_question_kind === "debug" ? "Debug" : "Code";
    const language = String(message.coding_language || "").trim();
    label.textContent = language ? `${kind} · ${language}` : kind;
    const pre = document.createElement("pre");
    pre.className = "preview-message-code-block preview-question-code-block";
    if (language) {
      pre.dataset.language = language;
    }
    const code = document.createElement("code");
    code.className = "preview-message-code";
    code.textContent = String(message.code_snippet || "").replace(/^\n+|\n+$/g, "");
    pre.appendChild(code);
    wrapper.appendChild(label);
    wrapper.appendChild(pre);
    container.appendChild(wrapper);
  }

  function questionStemText(message) {
    let stem = String(message?.text || "").trim();
    if (!stem) {
      return "";
    }
    stem = stem
      .replace(/\s*\((?:validation\s+)?variant\s+\d+\)\??\s*$/i, "")
      .replace(/\s+/g, " ")
      .trim();
    if (message?.is_coding_question && message?.code_snippet) {
      const strippedStem = stem.replace(/```[\w+-]*\n?[\s\S]*?```/g, " ").replace(/\s+/g, " ").trim();
      if (strippedStem) {
        stem = strippedStem;
      }
    }
    return stem;
  }

  function isExcelQuestionContext(message) {
    const contextText = [
      questionStemText(message),
      message?.block_label,
      message?.learning_objective,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return /\bexcel\b/.test(contextText);
  }

  function questionRenderOptions(message) {
    return isExcelQuestionContext(message) ? { excelMode: true } : {};
  }

  function appendFurtherStudyAction(actions, message) {
    if (
      !actions
      || !message
      || !Array.isArray(message.further_study_questions)
      || !message.further_study_questions.length
    ) {
      return;
    }
    const furtherStudyButton = document.createElement("button");
    furtherStudyButton.type = "button";
    furtherStudyButton.className = "preview-further-study-button";
    furtherStudyButton.textContent = "Further study";
    furtherStudyButton.disabled = requestInFlight;
    furtherStudyButton.addEventListener("click", () => {
      appendFurtherStudyMessage(message);
    });
    actions.appendChild(furtherStudyButton);
  }

  function renderBlockSwitcher() {
    if (!blockSwitcher) {
      return;
    }
    syncConversationSwitcher();
    if (isMessengerPreview) {
      blockSwitcher.setAttribute(
        "aria-label",
        ({
          all: "Course conversations",
          collections: "Course collections",
          blocks: "Course blocks",
        })[currentConversationListMode()] || "Course conversations",
      );
    }
    const previousScrollTop = blockSwitcher.scrollTop;
    const previousActiveBlockId = blockSwitcher.dataset.activeBlockId || "";
    const activeChanged = previousActiveBlockId !== String(activeBlockId);
    blockSwitcher.innerHTML = "";
    if (isMessengerPreview) {
      const blocks = filteredConversationBlocks();
      if (!blocks.length) {
        const emptyState = document.createElement("div");
        emptyState.className = "preview-messenger-empty-state";
        emptyState.dataset.previewConversationEmpty = "true";
        emptyState.textContent = ({
          all: "No blocks or collections match that search yet.",
          collections: "No collections match that search yet.",
          blocks: "No blocks match that search yet.",
        })[currentConversationListMode()] || "No conversations match that search yet.";
        blockSwitcher.appendChild(emptyState);
      } else {
        blocks.forEach((entry) => {
          const { previewText, previewTimestamp, avatarText, avatarUrl } = entry;
          const rowId = String(entry.id || "");
          const rowTitle = String(entry.title || "");
          const isActive = rowId === String(activeBlockId);
          const isSelectionPreview = !entry.isStats && entry.threadKind !== "collection" && isActive && isSidebarSelectionPreview(rowId);
          const row = document.createElement("button");
          row.type = "button";
          row.className = `preview-conversation-row${isActive ? " is-active" : ""}${isSelectionPreview ? " is-selection-preview" : ""}`;
          row.dataset.blockId = rowId;
          row.innerHTML = `
            <span class="preview-conversation-avatar" aria-hidden="true"></span>
            <span class="preview-conversation-body">
              <span class="preview-conversation-head">
                <strong class="preview-conversation-title"></strong>
                <span class="preview-conversation-time">${previewTimestamp || ""}</span>
              </span>
              <span class="preview-conversation-preview"></span>
            </span>
          `;
          const avatar = row.querySelector(".preview-conversation-avatar");
          setAvatarContent(avatar, {
            avatarUrl,
            avatarText,
            imageClass: "preview-conversation-avatar-image",
            isSquare: entry.isStats || entry.isSquare,
          });
          row.querySelector(".preview-conversation-title").textContent = rowTitle;
          row.querySelector(".preview-conversation-preview").textContent = previewText;
          row.addEventListener("click", () => {
            activeBlockId = rowId;
            if (entry.threadKind === "collection") {
              conversationListMode = "collections";
            } else if (entry.threadKind === "block") {
              conversationListMode = "blocks";
            }
            if (messengerMobileMedia.matches) {
              setMessengerMobileChatOpen(true);
            }
            renderPreview();
          });
          blockSwitcher.appendChild(row);
        });
      }
      blockSwitcher.dataset.activeBlockId = String(activeBlockId);
      window.requestAnimationFrame(() => {
        if (!blockSwitcher) {
          return;
        }
        if (!activeChanged) {
          blockSwitcher.scrollTop = previousScrollTop;
        }
        const activeRow = blockSwitcher.querySelector(`.preview-conversation-row[data-block-id="${activeBlockId}"]`);
        activeRow?.scrollIntoView({ block: "nearest" });
      });
      return;
    }
    (previewState.blocks || []).forEach((block) => {
      const isActive = String(block.id) === String(activeBlockId);
      const isSelectionPreview = isActive && isSidebarSelectionPreview(block.id);
      const article = document.createElement("article");
      article.className = `preview-block-card${isActive ? " is-expanded is-active" : ""}${isSelectionPreview ? " is-selection-preview" : ""}`;

      const controlsId = `preview-block-panel-${block.id}`;
      const header = document.createElement("div");
      header.className = "preview-block-card-header";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "preview-block-card-toggle";
      button.setAttribute("aria-expanded", isActive ? "true" : "false");
      button.setAttribute("aria-controls", controlsId);
      const titleRow = document.createElement("div");
      titleRow.className = "preview-block-title-row";
      const titleText = document.createElement("span");
      titleText.className = "preview-block-title-text";
      titleText.textContent = String(block.title || "");
      const titleIcon = document.createElement("span");
      titleIcon.className = "preview-block-card-icon";
      titleIcon.setAttribute("aria-hidden", "true");
      titleRow.append(titleText, titleIcon);
      button.appendChild(titleRow);
      button.addEventListener("click", () => {
        activeBlockId = String(block.id);
        if (isMobileSidebar()) {
          scheduleSidebarAutoClose(block.id);
        } else {
          clearSidebarAutoCloseTimer(true);
        }
        renderPreview();
      });
      header.appendChild(button);

      const content = document.createElement("div");
      content.id = controlsId;
      content.className = "preview-block-card-content";
      content.hidden = !isActive;
      content.innerHTML = `
        <div class="preview-block-metrics">${metricMarkup(block.metrics, { scope: "block", blockId: block.id })}</div>
      `;

      article.append(header, content);
      blockSwitcher.appendChild(article);
    });
    blockSwitcher.dataset.activeBlockId = String(activeBlockId);
    window.requestAnimationFrame(() => {
      if (!blockSwitcher) {
        return;
      }
      if (!activeChanged) {
        blockSwitcher.scrollTop = previousScrollTop;
      }
      ensureActiveBlockCardVisible();
    });
  }

  function renderMessage(message) {
    const article = document.createElement("article");
    const roleClass = message.role === "user" ? "preview-message--user" : "preview-message--assistant";
    const feedbackClass =
      message.kind === "feedback" ? (message.correct ? " preview-feedback--correct" : " preview-feedback--incorrect") : "";
    article.className = `preview-message ${roleClass}${feedbackClass}`;
    applySeededMessageBackground(article, message);

    if (message.kind === "question") {
      const renderOptions = questionRenderOptions(message);
      article.dataset.previewQuestion = "true";
      article.dataset.questionId = String(message.question_id || "");
      article.dataset.answered = message.answered ? "true" : "false";
      article.dataset.flagged = message.flagged ? "true" : "false";
      if (message.block_label && String(message.thread_kind || "") === "collection") {
        const meta = document.createElement("div");
        meta.className = "preview-message-meta";
        meta.innerHTML = `<span class="preview-message-pill">${message.block_label}</span>`;
        article.appendChild(meta);
      }
      const header = document.createElement("div");
      header.className = "preview-question-header";
      const callout = document.createElement("div");
      callout.className = "preview-question-callout";
      callout.textContent = questionTypeLabel(message);
      header.appendChild(callout);
      const timestampText = formatMessageClock(message.created_at);
      if (timestampText) {
        const timestamp = document.createElement("span");
        timestamp.className = "preview-question-time";
        timestamp.textContent = timestampText;
        header.appendChild(timestamp);
      }
      article.appendChild(header);
      appendFormattedMessageContent(article, questionStemText(message), renderOptions);
      appendQuestionCodeSnippet(article, message);

      if (message.question_type === "waq" && !message.answered && !message.flagged) {
        const helper = document.createElement("p");
        helper.className = "preview-message-sources";
        helper.textContent = "Type your answer in the fixed box below.";
        article.appendChild(helper);
      } else if (Array.isArray(message.options) && message.options.length && !message.answered && !message.flagged) {
        const optionsWrapper = document.createElement("div");
        optionsWrapper.className = "preview-message-options";
        if (message.question_type === "maq") {
          const selections = maqSelection(message.question_id);
          message.options.forEach((option, index) => {
            const optionButton = document.createElement("button");
            optionButton.type = "button";
            optionButton.className = `preview-answer-chip preview-answer-chip--maq${selections.includes(option) ? " is-selected" : ""}`;
            optionButton.dataset.maqOptionButton = "true";
            optionButton.dataset.optionValue = option;
            optionButton.setAttribute("aria-pressed", selections.includes(option) ? "true" : "false");
            optionButton.innerHTML = `
              <span class="preview-answer-chip-checkbox" aria-hidden="true">${selections.includes(option) ? "✓" : ""}</span>
              <span class="preview-answer-chip-label">${optionLabel(index)}</span>
              <span class="preview-answer-chip-text"></span>
            `;
            richText.appendInlineText(optionButton.querySelector(".preview-answer-chip-text"), option, renderOptions);
            optionButton.disabled = requestInFlight;
            optionButton.addEventListener("click", () => {
              toggleMaqSelection(message.question_id, option);
              syncRenderedMaqQuestion(message.question_id);
            });
            optionsWrapper.appendChild(optionButton);
          });

          const submitRow = document.createElement("div");
          submitRow.className = "preview-question-submit-row";
          const submitSelectionButton = document.createElement("button");
          submitSelectionButton.type = "button";
          submitSelectionButton.className = "button secondary preview-question-submit";
          submitSelectionButton.dataset.maqSubmitButton = "true";
          submitSelectionButton.textContent = "Submit";
          submitSelectionButton.dataset.hasSelection = selections.length ? "true" : "false";
          submitSelectionButton.disabled = requestInFlight || !selections.length;
          submitSelectionButton.addEventListener("click", () => {
            const currentSelections = maqSelection(message.question_id);
            void postPreviewAction("answer", {
              question_id: message.question_id,
              answers: currentSelections,
            });
          });
          submitRow.appendChild(submitSelectionButton);
          optionsWrapper.appendChild(submitRow);
        } else {
          message.options.forEach((option, index) => {
            const optionButton = document.createElement("button");
            optionButton.type = "button";
            optionButton.className = "preview-answer-chip";
            optionButton.innerHTML = `
              <span class="preview-answer-chip-label">${optionLabel(index)}</span>
              <span class="preview-answer-chip-text"></span>
            `;
            richText.appendInlineText(optionButton.querySelector(".preview-answer-chip-text"), option, renderOptions);
            optionButton.disabled = requestInFlight;
            optionButton.addEventListener("click", () => {
              void postPreviewAction("answer", {
                question_id: message.question_id,
                answer: option,
              });
            });
            optionsWrapper.appendChild(optionButton);
          });
        }
        article.appendChild(optionsWrapper);
      } else if (message.question_type === "waq" && (message.submitted_text || message.model_answer_revealed)) {
        article.appendChild(renderWrittenAnswerReview(message));
      } else if (
        (Array.isArray(message.selected_answers) && message.selected_answers.length) ||
        message.selected_answer
      ) {
        if (Array.isArray(message.correct_answers) && message.correct_answers.length) {
          article.appendChild(renderAnsweredOptions(message));
        } else {
          const selected = document.createElement("p");
          selected.className = "preview-message-sources";
          selected.textContent = formatSelectedAnswers(
            message.options,
            Array.isArray(message.selected_answers) && message.selected_answers.length
              ? message.selected_answers
              : [message.selected_answer],
            message.flagged,
          );
          article.appendChild(selected);
        }
      }

      const actions = document.createElement("div");
      actions.className = "preview-message-actions";
      if (
        message.answered
        && !message.flagged
        && Array.isArray(message.further_study_questions)
        && message.further_study_questions.length
      ) {
        appendFurtherStudyAction(actions, message);
      }
      if (!hideFlagActions) {
        const flagButton = document.createElement("button");
        flagButton.type = "button";
        flagButton.className = "preview-flag-button";
        flagButton.textContent = message.flagged ? "Flagged" : "Flag question";
        flagButton.disabled = requestInFlight || message.flagged;
        flagButton.addEventListener("click", () => {
          void postPreviewAction("flag", { question_id: message.question_id });
        });
        actions.appendChild(flagButton);
      }
      article.appendChild(actions);
      richText.renderMath(article);
      return article;
    }

    if (message.kind === "calculator") {
      renderCalculatorMessage(article, message);
      return article;
    }

    if (message.kind === "loading") {
      article.classList.add("preview-message--loading");
      article.innerHTML = `
        <div class="preview-loading-dots" aria-label="Generating next quiz question">
          <span></span>
          <span></span>
          <span></span>
        </div>
      `;
      return article;
    }

    if (message.kind === "validation_reminder") {
      article.classList.add("preview-message--validation-reminder");
      appendFormattedMessageContent(article, message.text || "");

      if (message.cta_url) {
        const actions = document.createElement("div");
        actions.className = "preview-message-actions";
        const link = document.createElement("a");
        link.className = "button secondary preview-validation-reminder-link";
        link.href = message.cta_url;
        link.textContent = message.cta_label || "Book validation";
        actions.appendChild(link);
        article.appendChild(actions);
      }

      return article;
    }

    if (message.kind === "resource") {
      article.innerHTML = `
        <div class="preview-message-meta">
          <span class="preview-message-pill">${message.block_label}</span>
          <span class="preview-message-pill">${message.resource_label}</span>
        </div>
      `;
      if (message.resource_key === "metric") {
        if (message.text) {
          const summary = document.createElement("p");
          summary.textContent = message.text;
          article.appendChild(summary);
        }

        const metricRows = Array.isArray(message.metric_rows) ? message.metric_rows : [];
        if (metricRows.length) {
          const list = document.createElement("ul");
          list.className = "preview-metric-detail-list";
          metricRows.forEach((row) => {
            const item = document.createElement("li");
            item.textContent = row;
            list.appendChild(item);
          });
          article.appendChild(list);
        }

        if (message.metric_formula) {
          const formula = document.createElement("p");
          formula.className = "preview-metric-formula";
          formula.textContent = message.metric_formula;
          article.appendChild(formula);
        }

        return article;
      }
      if (message.resource_key === "further_study") {
        if (message.text) {
          const summary = document.createElement("p");
          summary.textContent = message.text;
          article.appendChild(summary);
        }

        const questions = Array.isArray(message.questions) ? message.questions : [];
        if (questions.length) {
          const list = document.createElement("div");
          list.className = "preview-further-study-list";
          questions.forEach((questionText) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "preview-further-study-question";
            button.textContent = questionText;
            button.disabled = requestInFlight;
            button.addEventListener("click", () => {
              void sendCourseChatQuestion(questionText, { focusComposer: true, closeSidebarOnMobile: true });
            });
            list.appendChild(button);
          });
          article.appendChild(list);
        }

        return article;
      }
      if (message.resource_key === "objectives") {
        const list = document.createElement("ul");
        list.className = "preview-objective-list";
        const resourceBlock = findBlock(message.block_id || currentBlock()?.id || 0);
        const objectives = Array.isArray(resourceBlock?.learning_objectives)
          ? resourceBlock.learning_objectives
          : (Array.isArray(message.objectives) ? message.objectives : []);

        if (!objectives.length) {
          const emptyItem = document.createElement("li");
          emptyItem.className = "preview-objective-item";
          emptyItem.textContent = "No learning objectives yet.";
          list.appendChild(emptyItem);
        } else {
          objectives.forEach((objective) => {
            const item = document.createElement("li");
            item.className = `preview-objective-item${objective.covered ? " is-covered" : ""}`;

            const tick = document.createElement("span");
            tick.className = "preview-objective-status";
            tick.setAttribute("aria-hidden", "true");
            tick.textContent = objective.covered ? "✓" : "";

            const code = document.createElement("span");
            code.className = "preview-objective-code";
            code.textContent = displayObjectiveCode(objective.code);

            const text = document.createElement("span");
            text.className = "preview-objective-text";
            text.textContent = objective.text;

            item.append(tick, code, text);

            if (isTeacherPreview) {
              const actions = document.createElement("div");
              actions.className = "preview-objective-actions";
              const menu = document.createElement("div");
              menu.className = "preview-objective-menu";
              menu.dataset.previewObjectiveMenu = "true";
              const trigger = document.createElement("button");
              trigger.type = "button";
              trigger.className = "preview-objective-menu-trigger";
              trigger.setAttribute("aria-label", `Actions for ${displayObjectiveCode(objective.code)}`);
              trigger.setAttribute("aria-haspopup", "menu");
              trigger.setAttribute("aria-expanded", "false");
              trigger.dataset.previewObjectiveMenuTrigger = "true";
              trigger.disabled = requestInFlight;
              trigger.innerHTML = `
                <span class="preview-objective-menu-trigger-dots" aria-hidden="true">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>
              `;
              const panel = document.createElement("div");
              panel.className = "preview-objective-menu-panel";
              panel.setAttribute("role", "menu");
              panel.hidden = true;
              panel.dataset.previewObjectiveMenuPanel = "true";
              panel.innerHTML = `
                <button type="button" role="menuitem" class="preview-objective-menu-item" data-preview-objective-question-type="mcq" data-objective-id="${objective.id}">
                  Re-generate MCQ
                </button>
                <button type="button" role="menuitem" class="preview-objective-menu-item" data-preview-objective-question-type="num" data-objective-id="${objective.id}">
                  Re-generate Numeric
                </button>
                <button type="button" role="menuitem" class="preview-objective-menu-item" data-preview-objective-question-type="maq" data-objective-id="${objective.id}">
                  Re-generate MAQ
                </button>
                <button type="button" role="menuitem" class="preview-objective-menu-item" data-preview-objective-question-type="waq" data-objective-id="${objective.id}">
                  Re-generate WAQ
                </button>
                <button type="button" role="menuitem" class="preview-objective-menu-item is-accent" data-preview-objective-guardrail="true" data-objective-id="${objective.id}">
                  Add guardrail
                </button>
              `;
              menu.append(trigger, panel);
              actions.appendChild(menu);
              item.appendChild(actions);
            }

            list.appendChild(item);
          });
        }

        article.appendChild(list);
        return article;
      }
      if (message.resource_key === "collection_objectives") {
        const groups = Array.isArray(message.objective_groups) ? message.objective_groups : [];
        if (!groups.length) {
          const empty = document.createElement("p");
          empty.textContent = "No learning objectives yet.";
          article.appendChild(empty);
          return article;
        }

        groups.forEach((group) => {
          const section = document.createElement("section");
          section.className = "preview-objective-group";

          const heading = document.createElement("h3");
          heading.className = "preview-objective-group-title";
          heading.textContent = String(group.block_label || "Block");
          section.appendChild(heading);

          const list = document.createElement("ul");
          list.className = "preview-objective-list";
          const objectives = Array.isArray(group.objectives) ? group.objectives : [];

          if (!objectives.length) {
            const emptyItem = document.createElement("li");
            emptyItem.className = "preview-objective-item";
            emptyItem.textContent = "No learning objectives yet.";
            list.appendChild(emptyItem);
          } else {
            objectives.forEach((objective) => {
              const item = document.createElement("li");
              item.className = `preview-objective-item${objective.covered ? " is-covered" : ""}`;

              const tick = document.createElement("span");
              tick.className = "preview-objective-status";
              tick.setAttribute("aria-hidden", "true");
              tick.textContent = objective.covered ? "✓" : "";

              const code = document.createElement("span");
              code.className = "preview-objective-code";
              code.textContent = displayObjectiveCode(objective.code);

              const text = document.createElement("span");
              text.className = "preview-objective-text";
              text.textContent = objective.text;

              item.append(tick, code, text);
              list.appendChild(item);
            });
          }

          section.appendChild(list);
          article.appendChild(section);
        });
        return article;
      }
    }

    if (message.role === "assistant" && message.kind === "text" && message.inline_cta_label) {
      appendMessageTextWithInlineCta(article, message);
    } else {
      appendFormattedMessageContent(article, message.text || "");
    }

    if (message.role === "user" || message.kind === "feedback") {
      appendMessageTimestamp(article, message);
    }

    if (message.role === "assistant" && message.kind === "text") {
      const actions = document.createElement("div");
      actions.className = "preview-message-actions";
      appendFurtherStudyAction(actions, message);
      if (actions.childElementCount) {
        article.appendChild(actions);
      }
    }

    richText.renderMath(article);
    return article;
  }

  function combinedTranscript(conversation) {
    const threadId = conversation
      ? (conversation.block_ids ? collectionThreadKey(conversation.id) : String(conversation.id))
      : "";
    const inlineMessages = threadId ? threadInlineMessages(threadId) : [];
    const project = conversation && !conversation.block_ids ? currentProject(conversation) : null;
    if (project) {
      const baseMessages = Array.isArray(project.transcript) ? project.transcript : [];
      const messages = [];
      inlineMessages
        .filter((message) => message.insert_after_count === 0)
        .sort((left, right) => left.sequence - right.sequence)
        .forEach((message) => messages.push(message));
      baseMessages.forEach((message, index) => {
        messages.push(message);
        inlineMessages
          .filter((inlineMessage) => inlineMessage.insert_after_count === index + 1)
          .sort((left, right) => left.sequence - right.sequence)
          .forEach((inlineMessage) => messages.push(inlineMessage));
      });
      inlineMessages
        .filter((message) => message.insert_after_count > baseMessages.length)
        .sort((left, right) => left.sequence - right.sequence)
        .forEach((message) => messages.push(message));
      if (optimisticUserMessagesByBlock[threadId]) {
        messages.push(optimisticUserMessagesByBlock[threadId]);
      }
      if (loadingMessagesByBlock[threadId]) {
        messages.push({
          id: `loading-project-${threadId}`,
          kind: "loading",
          role: "assistant",
        });
      }
      return messages;
    }
    const baseMessages = Array.isArray(conversation?.transcript) ? conversation.transcript : [];
    const combined = [];

    inlineMessages
      .filter((message) => message.insert_after_count === 0)
      .sort((left, right) => left.sequence - right.sequence)
      .forEach((message) => combined.push(message));

    baseMessages.forEach((message, index) => {
      combined.push(message);
      inlineMessages
        .filter((inlineMessage) => inlineMessage.insert_after_count === index + 1)
        .sort((left, right) => left.sequence - right.sequence)
        .forEach((inlineMessage) => combined.push(inlineMessage));
    });

    inlineMessages
      .filter((message) => message.insert_after_count > baseMessages.length)
      .sort((left, right) => left.sequence - right.sequence)
      .forEach((message) => combined.push(message));

    if (threadId && optimisticUserMessagesByBlock[threadId]) {
      combined.push(optimisticUserMessagesByBlock[threadId]);
    }

    if (threadId && loadingMessagesByBlock[threadId]) {
      combined.push({
        id: `loading-${threadId}`,
        kind: "loading",
        role: "assistant",
      });
    }

    return combined;
  }

  function buildStatsPanel(title, description = "") {
    const panel = document.createElement("section");
    panel.className = "preview-stats-panel";

    const heading = document.createElement("div");
    heading.className = "preview-stats-panel-head";

    const titleElement = document.createElement("h3");
    titleElement.className = "preview-stats-panel-title";
    titleElement.textContent = title;
    heading.appendChild(titleElement);

    if (description) {
      const descriptionElement = document.createElement("p");
      descriptionElement.className = "preview-stats-panel-description";
      descriptionElement.textContent = description;
      heading.appendChild(descriptionElement);
    }

    panel.appendChild(heading);
    return panel;
  }

  function buildStatsSummaryCard(label, value, detail = "") {
    const card = document.createElement("div");
    card.className = "preview-stats-summary-card";

    const labelElement = document.createElement("span");
    labelElement.className = "preview-stats-summary-label";
    labelElement.textContent = label;

    const valueElement = document.createElement("strong");
    valueElement.className = "preview-stats-summary-value";
    valueElement.textContent = value;

    const detailElement = document.createElement("p");
    detailElement.className = "preview-stats-summary-detail";
    detailElement.textContent = detail;

    card.append(labelElement, valueElement, detailElement);
    return card;
  }

  function statsChartPointData(points) {
    const chartLeft = 6;
    const chartRight = 94;
    const chartTop = 8;
    const chartBottom = 58;
    const chartHeight = chartBottom - chartTop;
    const pointCount = Math.max(points.length, 1);
    return points.map((point, index) => {
      const ratio = pointCount === 1 ? 0.5 : index / (pointCount - 1);
      return {
        x: chartLeft + ((chartRight - chartLeft) * ratio),
        masteryY: chartBottom - ((clampPercentage(point.mastery) / 100) * chartHeight),
        coverageY: chartBottom - ((clampPercentage(point.coverage) / 100) * chartHeight),
      };
    });
  }

  function statsChartPath(points, key) {
    return points.map((point, index) => {
      const x = point.x.toFixed(2);
      const y = Number(point[key]).toFixed(2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    }).join(" ");
  }

  function buildStatsTimelineChart(timeline) {
    const chart = document.createElement("div");
    chart.className = "preview-stats-chart";

    if (!timeline.length) {
      const emptyState = document.createElement("p");
      emptyState.className = "preview-stats-empty";
      emptyState.textContent = "Answer a few questions to see mastery and coverage change over time.";
      chart.appendChild(emptyState);
      return chart;
    }

    const SVG_NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 100 64");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Line chart showing mastery and coverage over time");
    svg.classList.add("preview-stats-chart-svg");

    [0, 50, 100].forEach((value) => {
      const y = 58 - ((value / 100) * 50);
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", "6");
      line.setAttribute("y1", y.toFixed(2));
      line.setAttribute("x2", "94");
      line.setAttribute("y2", y.toFixed(2));
      line.setAttribute("class", "preview-stats-chart-grid");
      svg.appendChild(line);
    });

    const points = statsChartPointData(timeline);
    const masteryPath = document.createElementNS(SVG_NS, "path");
    masteryPath.setAttribute("d", statsChartPath(points, "masteryY"));
    masteryPath.setAttribute("class", "preview-stats-chart-line preview-stats-chart-line--mastery");
    svg.appendChild(masteryPath);

    const coveragePath = document.createElementNS(SVG_NS, "path");
    coveragePath.setAttribute("d", statsChartPath(points, "coverageY"));
    coveragePath.setAttribute("class", "preview-stats-chart-line preview-stats-chart-line--coverage");
    svg.appendChild(coveragePath);

    points.forEach((point, index) => {
      const masteryDot = document.createElementNS(SVG_NS, "circle");
      masteryDot.setAttribute("cx", point.x.toFixed(2));
      masteryDot.setAttribute("cy", point.masteryY.toFixed(2));
      masteryDot.setAttribute("r", "1.8");
      masteryDot.setAttribute("class", "preview-stats-chart-dot preview-stats-chart-dot--mastery");
      svg.appendChild(masteryDot);

      const coverageDot = document.createElementNS(SVG_NS, "circle");
      coverageDot.setAttribute("cx", point.x.toFixed(2));
      coverageDot.setAttribute("cy", point.coverageY.toFixed(2));
      coverageDot.setAttribute("r", "1.6");
      coverageDot.setAttribute("class", "preview-stats-chart-dot preview-stats-chart-dot--coverage");
      svg.appendChild(coverageDot);

      if (timeline.length === 1 || index === 0 || index === timeline.length - 1) {
        const label = document.createElementNS(SVG_NS, "text");
        label.setAttribute("x", point.x.toFixed(2));
        label.setAttribute("y", "63");
        label.setAttribute(
          "text-anchor",
          timeline.length === 1 ? "middle" : (index === 0 ? "start" : (index === timeline.length - 1 ? "end" : "middle")),
        );
        label.setAttribute("class", "preview-stats-chart-axis-label");
        label.textContent = formatStatsTimelineLabel(timeline[index]?.date || "");
        svg.appendChild(label);
      }
    });

    chart.appendChild(svg);
    return chart;
  }

  function buildStatsSnapshots(timeline) {
    const snapshots = document.createElement("div");
    snapshots.className = "preview-stats-snapshots";

    timeline.forEach((point) => {
      const card = document.createElement("div");
      card.className = "preview-stats-snapshot";

      const dateLabel = document.createElement("strong");
      dateLabel.textContent = formatStatsTimelineLabel(point.date || "");

      const mastery = document.createElement("span");
      mastery.textContent = `Mastery ${formatPercentage(point.mastery)}`;

      const coverage = document.createElement("span");
      coverage.textContent = `Coverage ${formatPercentage(point.coverage)}`;

      card.append(dateLabel, mastery, coverage);
      snapshots.appendChild(card);
    });

    return snapshots;
  }

  function buildStatsTimelinePanel(stats) {
    const panel = buildStatsPanel(
      "Mastery and coverage timeline",
      "Cumulative progress across every answered chat question.",
    );
    const timeline = Array.isArray(stats.timeline) ? stats.timeline : [];

    if (!timeline.length) {
      const emptyState = document.createElement("p");
      emptyState.className = "preview-stats-empty";
      emptyState.textContent = "Answer a few questions to unlock your timeline.";
      panel.appendChild(emptyState);
      return panel;
    }

    const legend = document.createElement("div");
    legend.className = "preview-stats-legend";
    [
      ["Mastery", "preview-stats-legend-swatch preview-stats-legend-swatch--mastery"],
      ["Coverage", "preview-stats-legend-swatch preview-stats-legend-swatch--coverage"],
    ].forEach(([labelText, className]) => {
      const item = document.createElement("span");
      item.className = "preview-stats-legend-item";
      const swatch = document.createElement("span");
      swatch.className = className;
      const text = document.createElement("span");
      text.textContent = labelText;
      item.append(swatch, text);
      legend.appendChild(item);
    });

    panel.append(legend, buildStatsTimelineChart(timeline), buildStatsSnapshots(timeline));
    return panel;
  }

  function buildStatsBreakdownPanel(stats) {
    const panel = buildStatsPanel(
      "Mastery by question type",
      "Compare how each question format is going so far.",
    );
    const breakdown = Array.isArray(stats.question_type_mastery) ? stats.question_type_mastery : [];
    if (!breakdown.length) {
      const emptyState = document.createElement("p");
      emptyState.className = "preview-stats-empty";
      emptyState.textContent = "Question-type mastery appears once you have answered at least one question.";
      panel.appendChild(emptyState);
      return panel;
    }

    const list = document.createElement("div");
    list.className = "preview-stats-breakdown";

    breakdown.forEach((item) => {
      const row = document.createElement("div");
      row.className = "preview-stats-breakdown-row";

      const head = document.createElement("div");
      head.className = "preview-stats-breakdown-head";

      const title = document.createElement("strong");
      title.textContent = item.label || String(item.question_type || "").toUpperCase();

      const count = document.createElement("span");
      count.textContent = formatCount(item.completed_count || 0, "answer");

      head.append(title, count);

      const track = document.createElement("div");
      track.className = "preview-stats-breakdown-track";
      const fill = document.createElement("span");
      fill.style.width = `${clampPercentage(item.mastery)}%`;
      track.appendChild(fill);

      const foot = document.createElement("div");
      foot.className = "preview-stats-breakdown-foot";
      const mastery = document.createElement("span");
      mastery.textContent = `Mastery ${formatPercentage(item.mastery)}`;
      const detail = document.createElement("span");
      detail.textContent = `${item.correct_count || 0} correct · ${item.incorrect_count || 0} incorrect`;
      foot.append(mastery, detail);

      row.append(head, track, foot);
      list.appendChild(row);
    });

    panel.appendChild(list);
    return panel;
  }

  function syncStatsViewport(scrollMode = "bottom", previousScrollTop = 0) {
    if (!transcript) {
      return;
    }
    if (scrollMode === "preserve") {
      transcript.scrollTop = Math.min(previousScrollTop, transcript.scrollHeight);
      return;
    }
    transcript.scrollTop = 0;
  }

  function renderStatsTranscript(scrollMode = "bottom") {
    if (!transcript) {
      return;
    }
    const previousScrollTop = transcript.scrollTop;
    const stats = courseStats();
    const summary = stats.summary || {};
    const completedCount = Number(summary.completed_count || 0);
    const correctCount = Number(summary.correct_count || 0);
    const coveredObjectiveCount = Number(summary.covered_objective_count || 0);
    const totalObjectiveCount = Number(summary.total_objective_count || 0);
    const longestStreak = Number(summary.longest_streak || 0);

    transcript.innerHTML = "";

    const article = document.createElement("article");
    article.className = "preview-message preview-message--assistant";

    const intro = document.createElement("p");
    intro.className = "preview-message-paragraph";
    intro.textContent = completedCount
      ? "My Stats is calculated from your answered questions across the course:"
      : "You have not answered any questions yet. These metrics will update as you work through the course:";

    const list = document.createElement("ul");
    list.className = "preview-message-list";
    [
      `Mastery % - ${formatPercentage(summary.mastery)} (${correctCount} correct of ${completedCount} attempted).`,
      `Coverage % - ${formatPercentage(summary.coverage)} (${coveredObjectiveCount} of ${totalObjectiveCount} objectives covered).`,
      `Longest streak - ${longestStreak}.`,
    ].forEach((text) => {
      const item = document.createElement("li");
      item.className = "preview-message-list-item";
      item.textContent = text;
      list.appendChild(item);
    });

    article.append(intro, list);
    appendMessageTimestamp(article, { created_at: stats.latest_answered_at || "" });
    transcript.appendChild(article);
    threadInlineMessages(STATS_THREAD_ID)
      .sort((left, right) => left.sequence - right.sequence)
      .forEach((message) => {
        transcript.appendChild(renderMessage(message));
      });

    syncCalculatorTriggerVisibility();
    syncStatsViewport(scrollMode, previousScrollTop);
    requestTranscriptScrollButtonSync();
  }

  function renderTranscript(scrollMode = "bottom") {
    if (!transcript) {
      return;
    }
    if (isStatsView()) {
      renderStatsTranscript(scrollMode);
      return;
    }
    const conversation = currentConversationEntry();
    const previousScrollTop = transcript.scrollTop;
    transcript.innerHTML = "";
    if (!conversation) {
      return;
    }
    let lastRenderedDayKey = "";
    combinedTranscript(conversation).forEach((message) => {
      const createdAt = parseMessageDate(message?.created_at);
      if (createdAt) {
        const currentDayKey = calendarDayKey(createdAt);
        if (currentDayKey && currentDayKey !== lastRenderedDayKey) {
          const separator = renderTranscriptDaySeparator(createdAt);
          if (separator) {
            transcript.appendChild(separator);
          }
        }
        lastRenderedDayKey = currentDayKey || lastRenderedDayKey;
      }
      transcript.appendChild(renderMessage(message));
    });
    updateMathOverflowState();
    syncCalculatorTriggerVisibility();
    syncQuestionViewport(scrollMode, previousScrollTop);
    requestTranscriptScrollButtonSync();
  }

  function resourceMessagePayload(block, resource) {
    if (resource === "description") {
      return {
        block_id: block.id,
        block_label: block.title,
        kind: "resource",
        resource_key: "description",
        resource_label: "Description",
        role: "assistant",
        text: block.summary || "No description yet.",
      };
    }

    const objectives = Array.isArray(block.learning_objectives) ? block.learning_objectives : [];
    return {
      block_id: block.id,
      block_label: block.title,
      kind: "resource",
      resource_key: "objectives",
      resource_label: "Learning objectives",
      role: "assistant",
      text: "",
      objectives,
    };
  }

  function collectionObjectivesMessagePayload(collection = currentCollection()) {
    if (!collection) {
      return null;
    }
    return {
      block_label: collection.title,
      kind: "resource",
      resource_key: "collection_objectives",
      resource_label: "All learning objectives",
      role: "assistant",
      text: "",
      objective_groups: collectionBlocks(collection).map((block) => ({
        block_id: block.id,
        block_label: block.title,
        objectives: Array.isArray(block.learning_objectives) ? block.learning_objectives : [],
      })),
    };
  }

  function furtherStudyMessagePayload(conversation, sourceMessage) {
    const questions = Array.isArray(sourceMessage?.further_study_questions)
      ? sourceMessage.further_study_questions.filter(Boolean)
      : [];
    if (!conversation || !sourceMessage || !questions.length) {
      return null;
    }
    return {
      block_label: conversation.title,
      kind: "resource",
      resource_key: "further_study",
      resource_label: "Further study",
      role: "assistant",
      text: sourceMessage.kind === "question"
        ? "Try one of these follow-up questions."
        : "Take this a step further.",
      questions,
    };
  }

  function metricMessagePayload(metricKey, { scope = "course", block = currentBlock() } = {}) {
    const courseMetrics = previewState.course?.metrics;
    const metrics = scope === "course" ? courseMetrics : block?.metrics;
    if (!metrics) {
      return null;
    }

    if (scope === "block" && metricKey === "coverage" && block) {
      return resourceMessagePayload(block, "objectives");
    }

    const liveBlockCount = Number(courseMetrics?.block_count || 0);
    const liveBlockLabel = formatCount(liveBlockCount, "live block");
    const metricTitle = metricLabel(metricKey);
    const payload = {
      block_label: scope === "course" ? "Course score" : (block?.title || "Practice"),
      kind: "resource",
      resource_key: "metric",
      resource_label: metricTitle,
      role: "assistant",
      text: "",
      metric_rows: [],
      metric_formula: "",
    };

    if (metricKey === "overall") {
      payload.text = scope === "course"
        ? `Overall course score is the average of the mastery and coverage values across ${liveBlockLabel}.`
        : "Overall score is the average of mastery and coverage.";
      payload.metric_rows = [
        `${scope === "course" ? "Average mastery" : "Mastery"}: ${formatPercentage(metrics.mastery)}`,
        `${scope === "course" ? "Average coverage" : "Coverage"}: ${formatPercentage(metrics.coverage)}`,
      ];
      payload.metric_formula = `(${formatMetricNumber(metrics.mastery)} + ${formatMetricNumber(metrics.coverage)}) / 2 = ${formatPercentage(metrics.overall)}`;
      return payload;
    }

    if (metricKey === "mastery") {
      payload.text = scope === "course"
        ? `Average mastery is the mean mastery score across ${liveBlockLabel}.`
        : "Mastery for this block is correct answers divided by completed answers.";
      payload.metric_rows = [
        `Displayed score: ${formatPercentage(metrics.mastery)}`,
        `Correct answers: ${metrics.correct_count || 0}`,
        `Incorrect answers: ${metrics.incorrect_count || 0}`,
        `Completed questions: ${metrics.completed_count || 0}`,
      ];
      return payload;
    }

    if (metricKey === "coverage") {
      payload.text = `Average coverage is the mean block coverage across ${liveBlockLabel}.`;
      payload.metric_rows = [
        `Displayed score: ${formatPercentage(metrics.coverage)}`,
        `Learning objectives covered at least once: ${metrics.covered_objective_count || 0} of ${metrics.total_objective_count || 0} across the whole course`,
      ];
      return payload;
    }

    return null;
  }

  function appendInlineMessage(messagePayload, {
    block = currentBlock(),
    threadId = "",
    dedupeKey = "",
    closeSidebarOnMobile = false,
  } = {}) {
    const resolvedThreadId = String(threadId || (block ? block.id : currentConversationKey()) || "");
    if (!resolvedThreadId || !messagePayload) {
      return;
    }

    const inlineMessages = threadInlineMessages(resolvedThreadId);
    const lastMessage = inlineMessages[inlineMessages.length - 1];
    if (dedupeKey && lastMessage?._dedupe_key === dedupeKey) {
      scrollTranscriptToBottom();
      if (closeSidebarOnMobile && isMobileSidebar()) {
        setSidebarOpen(false);
      }
      return lastMessage;
    }

    if (messagePayload.kind !== "calculator") {
      removeCalculatorInlineMessages(resolvedThreadId);
    }

    const activeConversation = currentConversationEntry();
    const activeProject = block ? currentProject(block) : null;
    let baseCount = 0;
    if (activeProject && Array.isArray(activeProject.transcript)) {
      baseCount = activeProject.transcript.length;
    } else if (block && Array.isArray(block.transcript)) {
      baseCount = block.transcript.length;
    } else if (
      activeConversation
      && resolvedThreadId === currentConversationKey()
      && Array.isArray(activeConversation.transcript)
    ) {
      baseCount = activeConversation.transcript.length;
    } else if (resolvedThreadId === STATS_THREAD_ID) {
      baseCount = 1;
    }
    inlineMessageSequence += 1;
    const message = {
      ...messagePayload,
      thread_id: resolvedThreadId,
      _dedupe_key: dedupeKey,
      id: `inline-message-${resolvedThreadId}-${inlineMessageSequence}`,
      created_at: new Date().toISOString(),
      insert_after_count: baseCount,
      sequence: inlineMessageSequence,
    };
    inlineMessages.push(message);
    renderTranscript();
    if (closeSidebarOnMobile && isMobileSidebar()) {
      setSidebarOpen(false);
    }
    return message;
  }

  function appendResourceMessage(resource) {
    if (resource === "collection_objectives") {
      const collection = currentCollection();
      const payload = collectionObjectivesMessagePayload(collection);
      if (!collection || !payload) {
        return;
      }
      appendInlineMessage(payload, {
        threadId: currentConversationKey(),
        dedupeKey: `resource:collection:${collection.id}:objectives`,
      });
      return;
    }
    const block = currentBlock();
    if (!block || !resource) {
      return;
    }
    appendInlineMessage(resourceMessagePayload(block, resource), {
      block,
      dedupeKey: `resource:${block.id}:${resource}`,
    });
  }

  function appendFurtherStudyMessage(sourceMessage) {
    const conversation = currentConversationEntry();
    const payload = furtherStudyMessagePayload(conversation, sourceMessage);
    if (!conversation || !payload) {
      return;
    }
    const sourceKey = sourceMessage.question_id || sourceMessage.id || payload.questions.join("|");
    appendInlineMessage(payload, {
      block: currentBlock(),
      threadId: currentConversationKey(),
      dedupeKey: `further-study:${currentConversationKey()}:${sourceKey}`,
      closeSidebarOnMobile: true,
    });
  }

  function openCalculatorMessage() {
    const threadId = currentConversationKey();
    if (!threadId) {
      return;
    }
    removeCalculatorInlineMessages(threadId);
    closeQuizMenu();
    closeHeaderMenu();
    appendInlineMessage(
      {
        kind: "calculator",
        role: "assistant",
        text: "",
      },
      {
        block: isStatsView() ? null : currentBlock(),
        threadId,
        closeSidebarOnMobile: true,
      },
    );
  }

  function renderProjectSwitcher() {
    if (!projectSwitcher) {
      return;
    }
    const block = currentBlock();
    projectSwitcher.innerHTML = "";
    if (!block) {
      projectSwitcher.hidden = true;
      return;
    }
    const projects = Array.isArray(block.projects) ? block.projects : [];
    if (!projects.length) {
      projectSwitcher.hidden = true;
      return;
    }
    projectSwitcher.hidden = false;

    const practiceButton = document.createElement("button");
    practiceButton.type = "button";
    practiceButton.className = `preview-header-action${currentProject(block) ? "" : " is-active"}`;
    practiceButton.textContent = "Practice";
    practiceButton.addEventListener("click", () => {
      setActiveProject(block.id, "");
      renderPreview("preserve");
    });
    projectSwitcher.appendChild(practiceButton);

    projects.forEach((project) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `preview-header-action${String(currentProject(block)?.id || "") === String(project.id) ? " is-active" : ""}`;
      button.textContent = project.title;
      button.addEventListener("click", async () => {
        setActiveProject(block.id, project.id);
        if (!project.materialized) {
          await postPreviewAction("project_open", { project_id: project.id }, { scrollMode: "preserve" });
        } else {
          renderPreview("preserve");
        }
      });
      projectSwitcher.appendChild(button);
    });
  }

  function renderProjectPanel() {
    if (!projectPanel) {
      return;
    }
    const block = currentBlock();
    const project = currentProject(block);
    projectPanel.innerHTML = "";
    projectPanel.hidden = !project;
    if (!project) {
      return;
    }

    const statusLabel = project.assignment_status === "complete"
      ? "Complete"
      : (project.assignment_status === "in_progress" ? "In progress" : "Ready");

    const downloads = Array.isArray(project.downloads) ? project.downloads : [];
    const wrapper = document.createElement("div");
    wrapper.className = "preview-written-answer-panel";
    wrapper.innerHTML = `
      <div class="preview-message-meta">
        <span class="preview-message-pill">Project</span>
        <span class="preview-message-pill">${statusLabel}</span>
        ${project.seed ? `<span class="preview-message-pill">Seed ${project.seed}</span>` : ""}
      </div>
    `;

    const instructions = document.createElement("div");
    appendFormattedMessageContent(instructions, project.student_instructions || "Project instructions will appear here once published.");
    wrapper.appendChild(instructions);

    if (downloads.length) {
      const actions = document.createElement("div");
      actions.className = "preview-message-actions";
      downloads.forEach((download) => {
        const link = document.createElement("a");
        link.className = "button secondary";
        link.href = download.url;
        link.textContent = download.label;
        actions.appendChild(link);
      });
      wrapper.appendChild(actions);
    }

    const answerRow = document.createElement("div");
    answerRow.className = "preview-chat-composer";
    const answerInput = document.createElement("input");
    answerInput.type = "text";
    answerInput.className = "preview-project-answer-input";
    answerInput.placeholder = project.answer_unit
      ? `${project.answer_label} (${project.answer_unit})`
      : project.answer_label || "Answer";
    answerInput.value = projectAnswerDraftsById[String(project.id)] || "";
    answerInput.disabled = requestInFlight || project.assignment_status === "complete";
    answerInput.dataset.completed = project.assignment_status === "complete" ? "true" : "false";
    answerInput.addEventListener("input", () => {
      projectAnswerDraftsById[String(project.id)] = answerInput.value;
      submitAnswerButton.disabled = requestInFlight || project.assignment_status === "complete" || !answerInput.value.trim();
    });
    answerInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitAnswerButton.click();
      }
    });
    const submitAnswerButton = document.createElement("button");
    submitAnswerButton.type = "button";
    submitAnswerButton.className = "button preview-project-answer-submit";
    submitAnswerButton.textContent = project.assignment_status === "complete" ? "Completed" : "Submit project answer";
    submitAnswerButton.disabled = requestInFlight || project.assignment_status === "complete" || !answerInput.value.trim();
    submitAnswerButton.dataset.completed = project.assignment_status === "complete" ? "true" : "false";
    submitAnswerButton.addEventListener("click", async () => {
      const answer = String(answerInput.value || "").trim();
      if (!answer) {
        return;
      }
      projectAnswerDraftsById[String(project.id)] = "";
      await postPreviewAction(
        "project_submit",
        { project_id: project.id, answer },
        { focusComposer: true, minDurationMs: 600, scrollMode: "bottom" },
      );
    });
    answerRow.append(answerInput, submitAnswerButton);
    wrapper.appendChild(answerRow);

    const helper = document.createElement("p");
    helper.className = "preview-message-sources";
    helper.textContent = project.assignment_status === "complete"
      ? "This project is complete. You can still revisit the transcript and downloads."
      : (project.hints_remaining > 0
        ? `${project.hints_remaining} guided hint${project.hints_remaining === 1 ? "" : "s"} remaining.`
        : "You can still ask for a nudge in the chat box below.");
    wrapper.appendChild(helper);

    projectPanel.appendChild(wrapper);
  }

  function appendMetricMessage(metricKey, scope, blockId = "") {
    const block = scope === "block" ? findBlock(blockId) : currentBlock();
    if (!block || !metricKey) {
      return;
    }

    const payload = metricMessagePayload(metricKey, { scope, block });
    if (!payload) {
      return;
    }

    const dedupeKey = payload.resource_key === "objectives"
      ? `resource:${block.id}:objectives`
      : `metric:${scope}:${metricKey}:${block.id}`;

    appendInlineMessage(payload, {
      block,
      dedupeKey,
      closeSidebarOnMobile: true,
    });
  }

  function renderPreview(scrollMode = "bottom") {
    const statsView = isStatsView();
    const block = currentBlock();
    const collection = currentCollection();
    if (!statsView && !block && !collection) {
      return;
    }
    closeObjectiveMenus();
    previewRoot.classList.toggle("is-stats-view", statsView);
    if (statsView) {
      closeHeaderMenu();
      closeQuizMenu();
      closeFlagSheet();
      closeGuardrailSheet();
      persistActiveBlockId(activeBlockId);
    } else {
      if (collection) {
        persistActiveBlockId(activeBlockId);
      } else {
        activeBlockId = String(block.id);
        persistActiveBlockId(activeBlockId);
      }
    }
    if (isMessengerPreview && !messengerMobileMedia.matches) {
      setMessengerMobileChatOpen(true);
    }
    if (chatBackButton) {
      chatBackButton.hidden = !isMessengerPreview || !messengerMobileMedia.matches;
    }
    if (statsView) {
      const statsConversation = statsConversationRowData();
      if (activeBlockTitle) {
        activeBlockTitle.textContent = statsConversation.title;
      }
      setAvatarContent(activeBlockAvatar, {
        avatarUrl: statsConversation.avatarUrl,
        avatarText: statsConversation.avatarText,
        imageClass: "preview-chat-header-avatar-image",
        isSquare: true,
      });
      if (activeBlockMeta) {
        activeBlockMeta.hidden = !isMessengerPreview;
        activeBlockMeta.textContent = statsHeaderMetaText();
      }
      if (headerMenu) {
        headerMenu.hidden = true;
      }
      syncHeaderMenuResourceVisibility("none");
      if (headerCoverage && headerCoverageFill) {
        headerCoverage.hidden = true;
        headerCoverageFill.style.width = "0%";
        headerCoverage.setAttribute("aria-valuenow", "0");
        headerCoverage.setAttribute("aria-valuetext", "Coverage unavailable");
        headerCoverage.removeAttribute("title");
      }
      if (form) {
        form.hidden = false;
      }
      renderCourseMetrics();
      renderBlockSwitcher();
      renderProjectSwitcher();
      renderProjectPanel();
      renderTranscript(scrollMode);
      scheduleMessengerHeaderHeightSync();
      syncComposerInputFromState();
      syncComposerState();
      updateComposerClearance();
      return;
    }

    if (collection) {
      closeFlagSheet();
      closeGuardrailSheet();
      const conversation = collectionConversationRowData(collection);
      if (activeBlockTitle) {
        activeBlockTitle.textContent = collection.title;
      }
      setAvatarContent(activeBlockAvatar, {
        avatarUrl: conversation.avatarUrl,
        avatarText: conversation.avatarText,
        imageClass: "preview-chat-header-avatar-image",
        isSquare: true,
      });
      if (activeBlockMeta) {
        activeBlockMeta.hidden = !isMessengerPreview;
        activeBlockMeta.textContent = conversation.previewTimestamp
          ? `Last activity ${conversation.previewTimestamp}`
          : "Tap Quiz to start this conversation.";
      }
      if (headerMenu) {
        headerMenu.hidden = false;
      }
      syncHeaderMenuResourceVisibility("collection");
      if (headerCoverage && headerCoverageFill) {
        const rawCoverage = Number(collection?.metrics?.coverage);
        const hasCoverage = Number.isFinite(rawCoverage);
        const coverage = hasCoverage ? Math.max(0, Math.min(rawCoverage, 100)) : 0;
        headerCoverage.hidden = !hasCoverage;
        if (hasCoverage) {
          const coverageText = formatPercentage(coverage);
          headerCoverageFill.style.width = `${coverage}%`;
          headerCoverage.setAttribute("aria-valuenow", coverage.toFixed(1));
          headerCoverage.setAttribute("aria-valuetext", `Coverage ${coverageText}`);
          headerCoverage.title = `Coverage ${coverageText}`;
        } else {
          headerCoverageFill.style.width = "0%";
          headerCoverage.setAttribute("aria-valuenow", "0");
          headerCoverage.setAttribute("aria-valuetext", "Coverage unavailable");
          headerCoverage.removeAttribute("title");
        }
      }
      if (form) {
        form.hidden = false;
      }
      renderCourseMetrics();
      renderBlockSwitcher();
      renderProjectSwitcher();
      renderProjectPanel();
      renderTranscript(scrollMode);
      scheduleMessengerHeaderHeightSync();
      syncComposerInputFromState();
      syncComposerState();
      updateComposerClearance();
      return;
    }

    const project = currentProject(block);
    const conversation = blockConversationRowData(block);
    if (activeBlockTitle) {
      activeBlockTitle.textContent = project ? `${block.title} · ${project.title}` : block.title;
    }
    setAvatarContent(activeBlockAvatar, {
      avatarUrl: conversation.avatarUrl,
      avatarText: conversation.avatarText,
      imageClass: "preview-chat-header-avatar-image",
      isSquare: false,
    });
    if (activeBlockMeta) {
      activeBlockMeta.hidden = !isMessengerPreview;
      activeBlockMeta.textContent = conversation.previewTimestamp
        ? `Last activity ${conversation.previewTimestamp}`
        : "Tap Quiz to start this conversation.";
    }
    if (headerMenu) {
      headerMenu.hidden = false;
    }
    syncHeaderMenuResourceVisibility("block");
    if (headerCoverage && headerCoverageFill) {
      const rawCoverage = Number(block?.metrics?.coverage);
      const hasCoverage = Number.isFinite(rawCoverage);
      const coverage = hasCoverage ? Math.max(0, Math.min(rawCoverage, 100)) : 0;
      headerCoverage.hidden = !hasCoverage;
      if (hasCoverage) {
        const coverageText = formatPercentage(coverage);
        headerCoverageFill.style.width = `${coverage}%`;
        headerCoverage.setAttribute("aria-valuenow", coverage.toFixed(1));
        headerCoverage.setAttribute("aria-valuetext", `Coverage ${coverageText}`);
        headerCoverage.title = `Coverage ${coverageText}`;
      } else {
        headerCoverageFill.style.width = "0%";
        headerCoverage.setAttribute("aria-valuenow", "0");
        headerCoverage.setAttribute("aria-valuetext", "Coverage unavailable");
        headerCoverage.removeAttribute("title");
      }
    }
    if (form) {
      form.hidden = false;
    }
    renderCourseMetrics();
    renderBlockSwitcher();
    renderProjectSwitcher();
    renderProjectPanel();
    renderTranscript(scrollMode);
    scheduleMessengerHeaderHeightSync();
    if (flagSheetState) {
      const sheetBlock = currentFlagSheetBlock();
      const stillAvailable = Array.isArray(sheetBlock?.transcript)
        && sheetBlock.transcript.some(
          (message) => Number(message.question_id || 0) === Number(flagSheetState.questionId)
            && !message.flagged,
        );
      if (!stillAvailable) {
        closeFlagSheet();
      } else {
        syncFlagSheetState();
      }
    }
    if (guardrailSheetState) {
      const objective = currentObjectiveForGuardrailSheet();
      if (!objective) {
        closeGuardrailSheet();
      } else {
        if (objectiveSheetObjective) {
          objectiveSheetObjective.textContent = `${displayObjectiveCode(objective.code)} ${objective.text}`;
        }
        const currentGuidance = String(objective.assistant_guidance || "").trim();
        if (objectiveSheetExistingWrap) {
          objectiveSheetExistingWrap.hidden = !currentGuidance;
        }
        if (objectiveSheetExisting) {
          objectiveSheetExisting.textContent = currentGuidance;
        }
        syncGuardrailSheetState();
      }
    }
    syncComposerInputFromState();
    syncComposerState();
    updateComposerClearance();
  }

  async function postDraftAnswer(questionId, answerText, requestId) {
    const block = currentActionBlock();
    if (!block) {
      return;
    }

    const controller = new AbortController();
    waqDraftAbortController = controller;
    const response = await fetch(actionUrl(block.id, "draft_answer"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({
        question_id: questionId,
        answer_text: answerText,
        thread_kind: isCollectionView() ? "collection" : "block",
        thread_id: isCollectionView() ? Number(currentCollectionId() || 0) : Number(block.id || 0),
      }),
      credentials: "same-origin",
      signal: controller.signal,
    });
    if (waqDraftAbortController === controller) {
      waqDraftAbortController = null;
    }
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Unable to update alignment right now.");
    }
    if (requestId !== waqDraftRequestId) {
      return;
    }
    let previousState = "drafting";
    const updatedQuestion = updateQuestionMessage(data.alignment.question_id, (message) => {
      previousState = message.alignment_state || "drafting";
      message.draft_answer = data.alignment.answer_text || "";
      message.alignment_score = data.alignment.alignment_score || 0;
      message.alignment_state = data.alignment.alignment_state || "drafting";
    });
    clearWaqAlignmentLoading(requestId);
    const shouldFlash = previousState !== "aligned" && updatedQuestion?.alignment_state === "aligned";
    if (updatedQuestion && String(updatedQuestion.question_id) === String(pendingWrittenQuestion()?.question_id)) {
      renderWaqAlignment(updatedQuestion, { flash: shouldFlash });
    }
  }

  async function postPreviewAction(action, payload = null, options = {}) {
    const block = currentActionBlock();
    if (!block) {
      return false;
    }
    setStatus("");
    clearWaqDraftTimer();
    waqDraftRequestId += 1;
    abortWaqDraftRequest();
    setComposerDisabled(true);
    let succeeded = false;
    try {
      const requestPayload = payload ? { ...payload } : {};
      if (isCollectionView()) {
        requestPayload.thread_kind = "collection";
        requestPayload.thread_id = Number(currentCollectionId() || 0);
      } else {
        requestPayload.thread_kind = "block";
        requestPayload.thread_id = Number(block.id || 0);
      }
      const responsePromise = fetch(actionUrl(block.id, action), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(requestPayload),
        credentials: "same-origin",
      });
      const minimumDelayPromise = options.minDurationMs
        ? new Promise((resolve) => window.setTimeout(resolve, options.minDurationMs))
        : Promise.resolve();
      const [response] = await Promise.all([responsePromise, minimumDelayPromise]);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || "Unable to update right now.");
      }
      removeCalculatorInlineMessages(previewThreadKey(data.preview) || String(block.id || ""));
      previewState = data.preview;
      activeBlockId = previewThreadKey(data.preview) || String(data.preview.active_block_id || block.id);
      clearAnsweredQuestionSelections();
      renderPreview(options.scrollMode || "bottom");
      succeeded = true;
    } catch (error) {
      setStatus(error.message || "Unable to update right now.");
      if (typeof options.onError === "function") {
        options.onError(error);
      }
    } finally {
      setComposerDisabled(false);
      if (options.focusComposer) {
        input?.focus();
      }
      syncComposerState();
    }
    return succeeded;
  }

  async function sendCourseChatQuestion(questionText, { clearComposer = false, focusComposer = true, closeSidebarOnMobile = false } = {}) {
    const trimmed = String(questionText || "").trim();
    if (!trimmed || requestInFlight) {
      return;
    }

    const actionBlock = currentActionBlock();
    if (!actionBlock) {
      return;
    }

    if (clearComposer && input) {
      input.value = "";
      resizeComposerInput();
      syncComposerState();
      updateComposerClearance();
    }

    if (closeSidebarOnMobile && isMobileSidebar()) {
      setSidebarOpen(false);
    }

    const threadId = currentConversationKey();
    setOptimisticUserMessage(threadId, trimmed);
    setQuizLoading(threadId, true);
    renderTranscript();
    try {
      await postPreviewAction("chat", { question: trimmed }, { focusComposer, minDurationMs: 900 });
    } finally {
      setOptimisticUserMessage(threadId, "");
      setQuizLoading(threadId, false);
      renderTranscript();
    }
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!input || requestInFlight) {
      return;
    }
    const trimmed = input.value.trim();
    const activeProject = currentProject();
    if (activeProject) {
      if (trimmed) {
        input.value = "";
        resizeComposerInput();
        syncComposerState();
        updateComposerClearance();
      }
      const block = currentBlock();
      if (block) {
        setOptimisticUserMessage(String(block.id), trimmed || "Hint");
        setQuizLoading(String(block.id), true);
        renderTranscript();
      }
      try {
        await postPreviewAction(
          "project_chat",
          { project_id: activeProject.id, message: trimmed },
          { focusComposer: true, minDurationMs: 600, scrollMode: "bottom" },
        );
      } finally {
        if (block) {
          setOptimisticUserMessage(String(block.id), "");
          setQuizLoading(String(block.id), false);
          renderTranscript();
        }
      }
      return;
    }
    const activeWaq = pendingWrittenQuestion();
    if (activeWaq) {
      if (!trimmed) {
        syncComposerState();
        return;
      }
      clearWaqDraftTimer();
      input.value = "";
      resizeComposerInput();
      syncComposerState();
      updateComposerClearance();
      const threadId = currentConversationKey();
      updateQuestionMessage(activeWaq.question_id, (message) => {
        message.draft_answer = "";
      });
      if (threadId) {
        setOptimisticUserMessage(threadId, trimmed);
        setQuizLoading(threadId, true);
        renderTranscript();
      }
      try {
        await postPreviewAction(
          "answer",
          { question_id: activeWaq.question_id, answer_text: trimmed },
          { focusComposer: true, minDurationMs: 900, scrollMode: "bottom" },
        );
      } finally {
        if (threadId) {
          setOptimisticUserMessage(threadId, "");
          setQuizLoading(threadId, false);
          renderTranscript();
        }
      }
      return;
    }

    if (trimmed) {
      await sendCourseChatQuestion(trimmed, { clearComposer: true, focusComposer: true });
      return;
    }
    input.blur();
    const threadId = currentConversationKey();
    if (threadId) {
      setQuizLoading(threadId, true);
      renderTranscript();
    }
    let quizRequestSucceeded = false;
    try {
        quizRequestSucceeded = await postPreviewAction("quiz", null, { minDurationMs: 2000, scrollMode: "question" });
    } finally {
      if (threadId) {
        setQuizLoading(threadId, false);
        renderTranscript(quizRequestSucceeded ? "question" : "preserve");
      }
    }
  });

  quizMenuTrigger?.addEventListener("click", () => {
    if (requestInFlight || input?.value.trim()) {
      return;
    }
    if (isQuizMenuOpen()) {
      closeQuizMenu();
      return;
    }
    openQuizMenu();
  });

  quizMenuPanel?.querySelectorAll("[data-quiz-type]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (requestInFlight || button.disabled) {
        return;
      }
      const threadId = currentConversationKey();
      const questionType = button.dataset.quizType || "";
      closeQuizMenu();
      renderPreview("preserve");
      input?.blur();
      if (threadId) {
        setQuizLoading(threadId, true);
        renderTranscript();
      }
      let quizRequestSucceeded = false;
      try {
        const requestPayload = questionType === "coding"
          ? { coding_only: true }
          : {
              question_type: questionType,
              ...(questionType === "num" ? { force_new: true } : {}),
            };
        quizRequestSucceeded = await postPreviewAction("quiz", requestPayload, { minDurationMs: 2000, scrollMode: "question" });
      } finally {
        if (threadId) {
          setQuizLoading(threadId, false);
          renderTranscript(quizRequestSucceeded ? "question" : "preserve");
        }
      }
    });
  });

  input?.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form?.requestSubmit();
    }
  });

  input?.addEventListener("input", () => {
    resizeComposerInput();
    syncComposerState();
    updateComposerClearance();
    const activeWaq = pendingWrittenQuestion();
    if (!activeWaq) {
      return;
    }
    updateQuestionMessage(activeWaq.question_id, (message) => {
      message.draft_answer = input.value;
      if (!input.value.trim()) {
        message.alignment_score = 0;
        message.alignment_state = "drafting";
      }
    });
    renderWaqAlignment(activeWaq);
    clearWaqDraftTimer();
    if (!input.value.trim()) {
      waqDraftRequestId += 1;
      abortWaqDraftRequest();
      return;
    }
    abortWaqDraftRequest({ clearLoading: false });
    const requestId = waqDraftRequestId + 1;
    waqDraftRequestId = requestId;
    setWaqAlignmentLoading(requestId);
    waqDraftDebounceTimer = window.setTimeout(() => {
      void postDraftAnswer(activeWaq.question_id, input.value, requestId).catch((error) => {
        if (error?.name === "AbortError") {
          return;
        }
        if (requestId === waqDraftRequestId) {
          clearWaqAlignmentLoading(requestId);
          setStatus("Unable to update alignment right now.");
        }
      });
    }, 120);
  });

  resourceButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeHeaderMenu();
      appendResourceMessage(button.dataset.previewResource || "");
    });
  });

  conversationSwitcherButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextMode = normalizeConversationListMode(button.dataset.previewConversationMode || "blocks");
      if (nextMode === currentConversationListMode()) {
        return;
      }
      conversationListMode = nextMode;
      renderBlockSwitcher();
    });
  });

  resetDemoButton?.addEventListener("click", async () => {
    closeHeaderMenu();
    closeSidebarMenu();
    if (!isDemoMode || requestInFlight) {
      return;
    }
    const confirmed = window.confirm("Reset this demo for everyone using this demo link?");
    if (!confirmed) {
      return;
    }
    persistActiveBlockId("");
    try {
      const visitorStorageKey = demoValidationVisitorStorageKey();
      if (visitorStorageKey) {
        window.localStorage.removeItem(visitorStorageKey);
      }
    } catch (_error) {
      // Ignore storage failures and continue with the shared reset.
    }
    await postPreviewAction("reset", {}, { focusComposer: true, scrollMode: "preserve" });
  });

  calculatorTrigger?.addEventListener("click", () => {
    openCalculatorMessage();
  });

  blockSearchInput?.addEventListener("input", () => {
    messengerSearchQuery = String(blockSearchInput.value || "");
    renderBlockSwitcher();
  });

  headerMenuTrigger?.addEventListener("click", () => {
    if (isHeaderMenuOpen()) {
      closeHeaderMenu();
      return;
    }
    closeQuizMenu();
    closeSidebarMenu();
    closeObjectiveMenus();
    openHeaderMenu();
  });

  sidebarMenuTrigger?.addEventListener("click", () => {
    if (isSidebarMenuOpen()) {
      closeSidebarMenu();
      return;
    }
    closeQuizMenu();
    closeHeaderMenu();
    closeObjectiveMenus();
    openSidebarMenu();
  });

  chatBackButton?.addEventListener("click", () => {
    if (isMessengerPreview && messengerMobileMedia.matches) {
      setMessengerMobileChatOpen(false);
    }
  });

  scrollBottomButton?.addEventListener("click", () => {
    scrollTranscriptToBottom();
  });

  transcript?.addEventListener("scroll", () => {
    requestTranscriptScrollButtonSync();
  }, { passive: true });

  previewRoot.addEventListener("click", (event) => {
    const objectiveMenuTrigger = event.target.closest("[data-preview-objective-menu-trigger='true']");
    if (objectiveMenuTrigger && previewRoot.contains(objectiveMenuTrigger)) {
      event.preventDefault();
      event.stopPropagation();
      toggleObjectiveMenu(objectiveMenuTrigger.closest("[data-preview-objective-menu]"));
      return;
    }

    const objectiveGenerateButton = event.target.closest("[data-preview-objective-question-type]");
    if (objectiveGenerateButton && previewRoot.contains(objectiveGenerateButton)) {
      event.preventDefault();
      event.stopPropagation();
      if (requestInFlight || objectiveGenerateButton.disabled) {
        return;
      }
      const block = currentBlock();
      const objectiveId = Number(objectiveGenerateButton.dataset.objectiveId || 0);
      const questionType = objectiveGenerateButton.dataset.previewObjectiveQuestionType || "";
      closeObjectiveMenus();
      input?.blur();
      if (block) {
        setQuizLoading(String(block.id), true);
        renderTranscript();
      }
      void (async () => {
        let quizRequestSucceeded = false;
        try {
          quizRequestSucceeded = await postPreviewAction(
            "quiz",
            {
              question_type: questionType,
              learning_objective_id: objectiveId,
              force_new: true,
            },
            { minDurationMs: 2000, scrollMode: "question" },
          );
        } finally {
          if (block) {
            setQuizLoading(String(block.id), false);
            renderTranscript(quizRequestSucceeded ? "question" : "preserve");
          }
        }
      })();
      return;
    }

    const objectiveGuardrailButton = event.target.closest("[data-preview-objective-guardrail='true']");
    if (objectiveGuardrailButton && previewRoot.contains(objectiveGuardrailButton)) {
      event.preventDefault();
      event.stopPropagation();
      const block = currentBlock();
      const objectiveId = Number(objectiveGuardrailButton.dataset.objectiveId || 0);
      const objective = Array.isArray(block?.learning_objectives)
        ? block.learning_objectives.find((item) => Number(item.id || 0) === objectiveId)
        : null;
      closeObjectiveMenus();
      if (objective) {
        openGuardrailSheet(objective);
      }
      return;
    }

    const metricButton = event.target.closest("[data-preview-metric-button='true']");
    if (!metricButton || !previewRoot.contains(metricButton) || metricButton.disabled) {
      return;
    }
    event.preventDefault();
    appendMetricMessage(
      metricButton.dataset.metricKey || "",
      metricButton.dataset.metricScope || "block",
      metricButton.dataset.blockId || "",
    );
  });

  flagSheetScrim?.addEventListener("click", () => {
    closeFlagSheet();
  });

  flagSheetCloseButton?.addEventListener("click", () => {
    closeFlagSheet();
  });

  flagOnlyButton?.addEventListener("click", () => {
    void submitFlagSheet({ saveCorrection: false });
  });

  flagSaveButton?.addEventListener("click", () => {
    void submitFlagSheet({ saveCorrection: true });
  });

  flagInstructionInput?.addEventListener("input", () => {
    if (!flagSheetError?.hidden) {
      setFlagSheetError("");
    }
  });

  objectiveSheetScrim?.addEventListener("click", () => {
    closeGuardrailSheet();
  });

  objectiveSheetCloseButton?.addEventListener("click", () => {
    closeGuardrailSheet();
  });

  objectiveSheetSaveButton?.addEventListener("click", () => {
    void submitGuardrailSheet();
  });

  objectiveGuardrailInput?.addEventListener("input", () => {
    if (!objectiveSheetError?.hidden) {
      setGuardrailSheetError("");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && flagSheetState) {
      closeFlagSheet();
    }
    if (event.key === "Escape" && guardrailSheetState) {
      closeGuardrailSheet();
    }
    if (event.key === "Escape") {
      closeObjectiveMenus();
      closeHeaderMenu();
      closeSidebarMenu();
    }
  });

  sidebarToggle?.addEventListener("click", () => {
    toggleSidebar();
  });

  sidebarScrim?.addEventListener("click", () => {
    setSidebarOpen(false);
  });

  document.addEventListener("click", (event) => {
    if (isTeacherPreview) {
      const objectiveMenuTarget = event.target instanceof Element ? event.target.closest("[data-preview-objective-menu]") : null;
      if (!objectiveMenuTarget) {
        closeObjectiveMenus();
      }
    }
    if (headerMenu && isHeaderMenuOpen() && !headerMenu.contains(event.target)) {
      closeHeaderMenu();
    }
    if (sidebarMenu && isSidebarMenuOpen() && !sidebarMenu.contains(event.target)) {
      closeSidebarMenu();
    }
    if (!quizMenu || !isQuizMenuOpen()) {
      return;
    }
    if (!quizMenu.contains(event.target)) {
      closeQuizMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeQuizMenu();
      closeHeaderMenu();
      closeSidebarMenu();
      if (!isMessengerPreview && sidebarOpen) {
        setSidebarOpen(false);
      }
    }
  });

  window.addEventListener("resize", () => {
    updateComposerClearance();
    if (!isMobileSidebar()) {
      clearSidebarAutoCloseTimer(true);
    }
    if (isMessengerPreview && !messengerMobileMedia.matches) {
      setMessengerMobileChatOpen(true);
    }
    applySidebarState();
    scheduleMessengerHeaderHeightSync();
    updateMathOverflowState();
    requestTranscriptScrollButtonSync();
  });
  restoreActiveBlockId();
  if (isCollectionView() && collectionCount()) {
    conversationListMode = "collections";
  } else if (!isCollectionView()) {
    conversationListMode = "all";
  }
  if (isMessengerPreview) {
    setMessengerMobileChatOpen(!messengerMobileMedia.matches);
  }
  applySidebarState();
  renderPreview();
}
