class OpsPilotApp {
    constructor() {
        this.apiBaseUrl = `${window.location.origin}/api`;
        this.storageKeys = {
            token: "opspilot_token",
            mode: "opspilot_mode",
            histories: "opspilot_chat_histories",
            sidebarCollapsed: "opspilot_sidebar_collapsed",
            sidebarWidth: "opspilot_sidebar_width",
        };
        this.rolePresets = {
            viewer: { username: "viewer", password: "viewer123" },
            operator: { username: "operator", password: "operator123" },
            admin: { username: "admin", password: "admin123" },
        };

        this.currentMode = localStorage.getItem(this.storageKeys.mode) || "quick";
        this.authToken = localStorage.getItem(this.storageKeys.token) || "";
        this.currentUser = null;
        this.isAuthenticated = false;
        this.isStreaming = false;
        this.streamController = null;
        this.systemStatusCache = null;
        this.chatRenderLimit = 80;
        this.showFullChatHistory = false;
        this.pendingMessageRenders = new Set();
        this.pendingMessageRenderFrame = null;
        this.pendingScrollToBottom = false;
        this.deletingSessionIds = new Set();

        this.sidebarCollapsed = localStorage.getItem(this.storageKeys.sidebarCollapsed) === "1";
        this.sidebarWidth = this.clampSidebarWidth(this.readStoredNumber(this.storageKeys.sidebarWidth, 348));

        this.chatHistories = this.loadChatHistories();
        this.sessionId = this.generateSessionId();
        this.currentChatHistory = [];
        this.activeTrace = this.createIdleTrace();

        this.initMarkdown();
        this.initializeElements();
        this.applySidebarState();
        this.bindEvents();
        this.updateModeUI();
        this.updateWelcomeState();
        this.updateSendButtonState();
        this.updateAuthUI();
        this.renderChatHistory();
        this.renderChatMessages();
        this.renderTracePanel();
        this.bootstrapAuth();
    }

    initializeElements() {
        this.sidebar = document.getElementById("sidebar");
        this.sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
        this.sidebarResizer = document.getElementById("sidebarResizer");
        this.tracePanelBtn = document.getElementById("tracePanelBtn");
        this.traceSection = document.getElementById("traceSection");
        this.tracePanelTitle = document.getElementById("tracePanelTitle");
        this.tracePanelMeta = document.getElementById("tracePanelMeta");
        this.traceOverview = document.getElementById("traceOverview");
        this.traceEmpty = document.getElementById("traceEmpty");
        this.traceList = document.getElementById("traceList");
        this.clearTraceBtn = document.getElementById("clearTraceBtn");
        this.sidebarScroll = document.getElementById("sidebarScroll");

        this.newChatBtn = document.getElementById("newChatBtn");
        this.chatHistoryList = document.getElementById("chatHistoryList");

        this.accountShell = document.getElementById("accountShell");
        this.accountMenuBtn = document.getElementById("accountMenuBtn");
        this.accountMenu = document.getElementById("accountMenu");
        this.accountAvatar = document.getElementById("accountAvatar");
        this.authStatus = document.getElementById("authStatus");
        this.authFields = document.getElementById("authFields");
        this.authUserPanel = document.getElementById("authUserPanel");
        this.authUserName = document.getElementById("authUserName");
        this.usernameInput = document.getElementById("usernameInput");
        this.passwordInput = document.getElementById("passwordInput");
        this.loginBtn = document.getElementById("loginBtn");
        this.logoutBtn = document.getElementById("logoutBtn");
        this.quickSwitchButtons = Array.from(document.querySelectorAll("[data-login-role]"));
        this.refreshStatusBtn = document.getElementById("refreshStatusBtn");
        this.systemStatusEmpty = document.getElementById("systemStatusEmpty");
        this.systemStatusContent = document.getElementById("systemStatusContent");
        this.systemStatusGrid = document.getElementById("systemStatusGrid");
        this.serviceStatusList = document.getElementById("serviceStatusList");

        this.aiOpsSidebarBtn = document.getElementById("aiOpsSidebarBtn");
        this.chatContainer = document.getElementById("chatContainer");
        this.welcomeGreeting = document.getElementById("welcomeGreeting");
        this.chatMessages = document.getElementById("chatMessages");
        this.messageInput = document.getElementById("messageInput");
        this.sendButton = document.getElementById("sendButton");
        this.toolsBtnWrapper = document.getElementById("toolsBtnWrapper");
        this.toolsBtn = document.getElementById("toolsBtn");
        this.toolsMenu = document.getElementById("toolsMenu");
        this.uploadFileItem = document.getElementById("uploadFileItem");
        this.fileInput = document.getElementById("fileInput");
        this.modeSelectorWrapper = document.getElementById("modeSelectorWrapper");
        this.modeSelectorBtn = document.getElementById("modeSelectorBtn");
        this.modeDropdown = document.getElementById("modeDropdown");
        this.currentModeText = document.getElementById("currentModeText");
        this.modeItems = Array.from(document.querySelectorAll(".dropdown-item[data-mode]"));
        this.loadingOverlay = document.getElementById("loadingOverlay");
    }

    initMarkdown() {
        const applyConfig = () => {
            if (typeof marked === "undefined") {
                return false;
            }

            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false,
            });

            return true;
        };

        if (!applyConfig()) {
            const timer = setInterval(() => {
                if (applyConfig()) {
                    clearInterval(timer);
                }
            }, 120);
        }
    }

    bindEvents() {
        this.newChatBtn.addEventListener("click", () => this.startNewChat());
        this.tracePanelBtn.addEventListener("click", () => this.focusTracePanel());
        this.clearTraceBtn.addEventListener("click", () => {
            this.activeTrace = this.createIdleTrace();
            this.renderTracePanel();
        });

        this.sidebarToggleBtn.addEventListener("click", () => this.toggleSidebar());
        this.sidebarResizer.addEventListener("pointerdown", (event) => this.beginSidebarResize(event));

        this.accountMenuBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            this.toggleAccountMenu();
        });
        this.loginBtn.addEventListener("click", () => this.handleLogin());
        this.logoutBtn.addEventListener("click", () => this.handleLogout(true));
        this.quickSwitchButtons.forEach((button) => {
            button.addEventListener("click", () => this.handleQuickSwitch(button.dataset.loginRole));
        });
        this.refreshStatusBtn.addEventListener("click", () => this.loadSystemStatus(true));

        this.aiOpsSidebarBtn.addEventListener("click", () => this.handleAiOpsRequest());

        this.sendButton.addEventListener("click", () => this.handleSend());
        this.messageInput.addEventListener("input", () => {
            this.autoResizeTextarea();
            this.updateSendButtonState();
        });
        this.messageInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
                event.preventDefault();
                this.handleSend();
            }
        });

        this.toolsBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            this.toggleModeSelector(false);
            this.toggleToolsMenu();
        });
        this.uploadFileItem.addEventListener("click", () => {
            if (!this.ensureOperatorPermission("上传知识文档")) {
                return;
            }
            this.toggleToolsMenu(false);
            this.fileInput.click();
        });
        this.fileInput.addEventListener("change", (event) => this.handleFileSelection(event));

        this.modeSelectorBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            this.toggleToolsMenu(false);
            this.toggleModeSelector();
        });
        this.modeItems.forEach((item) => {
            item.addEventListener("click", () => {
                this.setMode(item.dataset.mode);
                this.toggleModeSelector(false);
            });
        });

        this.chatHistoryList.addEventListener("click", (event) => {
            const deleteButton = event.target.closest(".history-item-delete");
            if (deleteButton) {
                event.stopPropagation();
                if (deleteButton.disabled) {
                    return;
                }
                this.deleteHistorySession(deleteButton.dataset.sessionId);
                return;
            }

            const item = event.target.closest(".history-item");
            if (!item) {
                return;
            }
            if (this.isSessionDeleting(item.dataset.sessionId)) {
                return;
            }

            this.loadHistorySession(item.dataset.sessionId);
        });

        document.addEventListener("click", (event) => this.handleDocumentClick(event));
        document.addEventListener("keydown", (event) => this.handleGlobalKeydown(event));
        window.addEventListener("resize", () => this.handleWindowResize());
    }

    handleDocumentClick(event) {
        if (!this.accountShell.contains(event.target)) {
            this.closeAccountMenu();
        }
        if (!this.toolsBtnWrapper.contains(event.target)) {
            this.toggleToolsMenu(false);
        }
        if (!this.modeSelectorWrapper.contains(event.target)) {
            this.toggleModeSelector(false);
        }
    }

    handleGlobalKeydown(event) {
        if (event.key !== "Escape") {
            return;
        }
        if (this.modeSelectorWrapper.classList.contains("open")) {
            this.toggleModeSelector(false);
            this.modeSelectorBtn.focus();
            return;
        }
        if (this.toolsBtnWrapper.classList.contains("open")) {
            this.toggleToolsMenu(false);
            this.toolsBtn.focus();
            return;
        }
        if (!this.accountMenu.classList.contains("hidden")) {
            this.toggleAccountMenu(false);
            this.accountMenuBtn.focus();
        }
    }

    handleWindowResize() {
        this.sidebarWidth = this.clampSidebarWidth(this.sidebarWidth);
        this.applySidebarState();
    }

    toggleAccountMenu(forceOpen = null) {
        const nextOpen = forceOpen === null ? this.accountMenu.classList.contains("hidden") : forceOpen;
        this.accountShell.classList.toggle("open", nextOpen);
        this.accountMenu.classList.toggle("hidden", !nextOpen);
        this.accountMenuBtn.setAttribute("aria-expanded", String(nextOpen));

        if (nextOpen && this.isAuthenticated) {
            this.loadSystemStatus(false);
        }
    }

    closeAccountMenu() {
        this.toggleAccountMenu(false);
    }

    toggleToolsMenu(forceOpen = null) {
        const nextOpen = forceOpen === null ? !this.toolsBtnWrapper.classList.contains("open") : forceOpen;
        this.toolsBtnWrapper.classList.toggle("open", nextOpen);
        this.toolsBtn.setAttribute("aria-expanded", String(nextOpen));
    }

    toggleModeSelector(forceOpen = null) {
        const nextOpen = forceOpen === null ? !this.modeSelectorWrapper.classList.contains("open") : forceOpen;
        this.modeSelectorWrapper.classList.toggle("open", nextOpen);
        this.modeSelectorBtn.setAttribute("aria-expanded", String(nextOpen));
    }

    toggleSidebar(forceCollapsed = null) {
        const nextCollapsed = forceCollapsed === null ? !this.sidebarCollapsed : forceCollapsed;
        this.sidebarCollapsed = nextCollapsed;
        localStorage.setItem(this.storageKeys.sidebarCollapsed, this.sidebarCollapsed ? "1" : "0");
        if (this.sidebarCollapsed) {
            this.closeAccountMenu();
        }
        this.applySidebarState();
    }

    applySidebarState() {
        document.documentElement.style.setProperty("--sidebar-current-width", `${this.sidebarWidth}px`);
        this.sidebar.classList.toggle("collapsed", this.sidebarCollapsed);
    }

    beginSidebarResize(event) {
        if (this.sidebarCollapsed || window.innerWidth <= 920) {
            return;
        }

        event.preventDefault();
        const startX = event.clientX;
        const startWidth = this.sidebarWidth;
        document.body.classList.add("sidebar-resizing");

        const onPointerMove = (moveEvent) => {
            const delta = moveEvent.clientX - startX;
            this.sidebarWidth = this.clampSidebarWidth(startWidth + delta);
            this.applySidebarState();
        };

        const onPointerUp = () => {
            document.body.classList.remove("sidebar-resizing");
            document.removeEventListener("pointermove", onPointerMove);
            document.removeEventListener("pointerup", onPointerUp);
            localStorage.setItem(this.storageKeys.sidebarWidth, String(this.sidebarWidth));
        };

        document.addEventListener("pointermove", onPointerMove);
        document.addEventListener("pointerup", onPointerUp);
    }

    clampSidebarWidth(value) {
        return Math.min(520, Math.max(280, value || 348));
    }

    readStoredNumber(key, fallback) {
        const value = Number(localStorage.getItem(key));
        return Number.isFinite(value) && value > 0 ? value : fallback;
    }

    async bootstrapAuth() {
        if (!this.authToken) {
            this.renderChatHistory();
            return;
        }

        try {
            const response = await this.apiFetch("/auth/me");
            if (!response.ok) {
                throw new Error("登录态已失效");
            }

            const user = await response.json();
            this.currentUser = user;
            this.isAuthenticated = true;
            await this.syncSessionsFromBackend();
            await this.loadSystemStatus(false);
        } catch (error) {
            this.renderChatHistory();
            console.error("恢复登录态失败:", error);
            this.handleLogout(false);
        } finally {
            this.updateAuthUI();
            this.renderChatHistory();
        }
    }

    apiFetch(path, options = {}) {
        const headers = new Headers(options.headers || {});
        if (this.authToken) {
            headers.set("Authorization", `Bearer ${this.authToken}`);
        }

        return fetch(`${this.apiBaseUrl}${path}`, {
            ...options,
            headers,
        }).then((response) => {
            if (response.status === 401 && this.isAuthenticated) {
                this.handleLogout(false);
                this.showNotification("登录态已过期，请重新登录", "warning");
            }
            return response;
        });
    }

    async handleLogin() {
        const username = this.usernameInput.value.trim();
        const password = this.passwordInput.value.trim();
        if (!username || !password) {
            this.showNotification("请输入用户名和密码", "warning");
            return;
        }
        await this.performLogin(username, password);
    }

    async handleQuickSwitch(role) {
        const preset = this.rolePresets[role];
        if (!preset) {
            return;
        }
        await this.performLogin(preset.username, preset.password);
    }

    async performLogin(username, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }

            const data = await response.json();
            this.authToken = data.access_token;
            this.currentUser = {
                username: data.username,
                role: data.role,
            };
            this.isAuthenticated = true;
            localStorage.setItem(this.storageKeys.token, this.authToken);
            this.passwordInput.value = "";
            this.updateAuthUI();
            await this.syncSessionsFromBackend();
            await this.loadSystemStatus(true);
            this.renderChatHistory();
            this.showNotification(`登录成功，当前角色：${data.role}`, "success");
        } catch (error) {
            console.error("登录失败:", error);
            this.showNotification(error.message || "登录失败", "error");
        }
    }

    handleLogout(showNotice = true) {
        this.authToken = "";
        this.currentUser = null;
        this.isAuthenticated = false;
        this.systemStatusCache = null;
        localStorage.removeItem(this.storageKeys.token);
        this.startNewChat({ keepHistoryPanel: true });
        this.updateAuthUI();
        this.renderChatHistory();
        this.renderSystemStatus(null);
        if (showNotice) {
            this.showNotification("已退出登录", "info");
        }
    }

    updateAuthUI() {
        const loggedIn = this.isAuthenticated && this.currentUser;
        this.authStatus.textContent = loggedIn ? `已登录 · ${this.currentUser.role}` : "未登录";
        this.authFields.classList.toggle("hidden", loggedIn);
        this.authUserPanel.classList.toggle("hidden", !loggedIn);
        this.authUserName.textContent = loggedIn
            ? `${this.currentUser.username} / ${this.currentUser.role}`
            : "未登录";
        this.accountAvatar.textContent = loggedIn
            ? this.currentUser.username.slice(0, 2).toUpperCase()
            : "OP";

        const operatorReady = this.canUseOperatorActions();
        const aiOpsLabel = this.aiOpsSidebarBtn.querySelector("span");
        aiOpsLabel.textContent = operatorReady ? "AI Ops" : "AI Ops 受限";
        this.aiOpsSidebarBtn.classList.toggle("restricted", !operatorReady);
        this.aiOpsSidebarBtn.title = operatorReady
            ? "启动 AIOps 诊断"
            : "当前角色仅支持聊天与知识问答";

        this.uploadFileItem.setAttribute("aria-disabled", String(!operatorReady));
        this.uploadFileItem.style.opacity = operatorReady ? "1" : "0.45";
    }

    canUseOperatorActions() {
        return Boolean(this.currentUser && ["operator", "admin"].includes(this.currentUser.role));
    }

    ensureAuthenticated() {
        if (this.isAuthenticated) {
            return true;
        }
        this.showNotification("请先登录后再发送请求", "warning");
        this.toggleAccountMenu(true);
        return false;
    }

    ensureOperatorPermission(actionName) {
        if (!this.ensureAuthenticated()) {
            return false;
        }
        if (this.canUseOperatorActions()) {
            return true;
        }
        this.showNotification(`当前角色为 viewer，仅支持聊天与知识问答，不支持${actionName}`, "warning");
        return false;
    }

    async syncSessionsFromBackend() {
        if (!this.isAuthenticated) {
            return;
        }

        try {
            const response = await this.apiFetch("/sessions");
            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }

            const payload = await response.json();
            const localById = new Map(this.chatHistories.map((session) => [session.id, session]));
            this.chatHistories = (payload.data || []).map((session) => {
                const cached = localById.get(session.session_id);
                return {
                    id: session.session_id,
                    title: session.title || "新对话",
                    threadId: session.thread_id || session.session_id,
                    lastIntent: session.last_intent || null,
                    createdAt: session.created_at,
                    updatedAt: session.updated_at,
                    messageCount: session.message_count || 0,
                    messages: cached?.messages || [],
                };
            });
            this.pruneDeletingSessionIds();
            this.saveChatHistories();
        } catch (error) {
            console.error("同步会话失败:", error);
        }
    }

    loadChatHistories() {
        try {
            const raw = localStorage.getItem(this.storageKeys.histories);
            if (!raw) {
                return [];
            }
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) {
                return [];
            }
            return parsed.map((session) => ({
                id: session.id,
                title: session.title || "新对话",
                threadId: session.threadId || session.id,
                lastIntent: session.lastIntent || null,
                createdAt: session.createdAt || null,
                updatedAt: session.updatedAt || null,
                messageCount: session.messageCount || 0,
                messages: Array.isArray(session.messages)
                    ? session.messages.map((message) => this.normalizeLocalMessage(message))
                    : [],
            }));
        } catch (error) {
            console.error("读取本地会话缓存失败:", error);
            return [];
        }
    }

    saveChatHistories() {
        const payload = this.chatHistories.map((session) => ({
            id: session.id,
            title: session.title,
            threadId: session.threadId,
            lastIntent: session.lastIntent,
            createdAt: session.createdAt,
            updatedAt: session.updatedAt,
            messageCount: session.messageCount,
            messages: (session.messages || []).map((message) => this.serializeMessage(message)),
        }));
        localStorage.setItem(this.storageKeys.histories, JSON.stringify(payload));
    }

    normalizeLocalMessage(message) {
        return {
            role: message.role,
            content: message.content || "",
            timestamp: message.timestamp || null,
            intent: message.intent || null,
            route: message.route || null,
            timing: message.timing || null,
            traceSummary: message.traceSummary || null,
            requestMeta: message.requestMeta || null,
            requestError: message.requestError || null,
        };
    }

    serializeMessage(message) {
        return {
            role: message.role,
            content: message.content,
            timestamp: message.timestamp || null,
            intent: message.intent || null,
            route: message.route || null,
            timing: message.timing || null,
            traceSummary: message.traceSummary || null,
            requestMeta: message.requestMeta || null,
            requestError: message.requestError || null,
        };
    }

    startNewChat(options = {}) {
        this.sessionId = this.generateSessionId();
        this.currentChatHistory = [];
        this.activeTrace = this.createIdleTrace();
        this.showFullChatHistory = false;
        this.cancelPendingMessageRenders();
        this.updateWelcomeState();
        this.renderChatMessages();
        this.renderTracePanel();
        this.renderChatHistory();
        this.autoResizeTextarea();
        this.updateSendButtonState();
        if (!options.keepHistoryPanel) {
            this.closeAccountMenu();
        }
    }

    async loadHistorySession(sessionId) {
        if (!this.ensureAuthenticated()) {
            return;
        }

        const cached = this.chatHistories.find((session) => session.id === sessionId);
        if (cached?.messages?.length) {
            this.sessionId = sessionId;
            this.currentChatHistory = cached.messages.map((message) => this.normalizeLocalMessage(message));
            this.activeTrace = this.pickLatestTrace(this.currentChatHistory);
            this.showFullChatHistory = false;
            this.updateWelcomeState();
            this.renderChatMessages();
            this.renderTracePanel();
            this.renderChatHistory();
        }

        try {
            const response = await this.apiFetch(`/sessions/${sessionId}`);
            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }

            const payload = await response.json();
            const detail = payload.data || {};
            const localMessages = cached?.messages || [];
            const mergedMessages = this.mergeServerMessages(detail.history || [], localMessages);

            const mergedSession = {
                id: detail.session_id || sessionId,
                title: detail.title || cached?.title || "新对话",
                threadId: detail.thread_id || sessionId,
                lastIntent: detail.last_intent || cached?.lastIntent || null,
                createdAt: detail.created_at || cached?.createdAt || null,
                updatedAt: detail.updated_at || cached?.updatedAt || null,
                messageCount: mergedMessages.length,
                messages: mergedMessages,
            };

            this.upsertSessionRecord(mergedSession);
            this.sessionId = sessionId;
            this.currentChatHistory = mergedMessages.map((message) => this.normalizeLocalMessage(message));
            this.activeTrace = this.pickLatestTrace(this.currentChatHistory);
            this.showFullChatHistory = false;
            this.updateWelcomeState();
            this.renderChatMessages();
            this.renderTracePanel();
            this.renderChatHistory();
        } catch (error) {
            console.error("加载历史会话失败:", error);
            this.showNotification(error.message || "加载历史会话失败", "error");
        }
    }

    mergeServerMessages(serverMessages, localMessages) {
        return serverMessages.map((serverMessage, index) => {
            const localMessage = localMessages[index];
            const normalized = {
                role: serverMessage.role,
                content: serverMessage.content || "",
                timestamp: serverMessage.timestamp || null,
                intent: serverMessage.intent || null,
                route: serverMessage.route || null,
                timing: null,
                traceSummary: null,
            };

            if (
                localMessage &&
                localMessage.role === normalized.role &&
                localMessage.content === normalized.content
            ) {
                normalized.timing = localMessage.timing || null;
                normalized.traceSummary = localMessage.traceSummary || null;
                normalized.timestamp = localMessage.timestamp || normalized.timestamp;
                normalized.requestMeta = localMessage.requestMeta || null;
                normalized.requestError = localMessage.requestError || null;
            }

            return normalized;
        });
    }

    upsertSessionRecord(session) {
        const index = this.chatHistories.findIndex((item) => item.id === session.id);
        if (index >= 0) {
            this.chatHistories.splice(index, 1, session);
        } else {
            this.chatHistories.unshift(session);
        }
        this.chatHistories.sort((left, right) => {
            return new Date(right.updatedAt || 0).getTime() - new Date(left.updatedAt || 0).getTime();
        });
        this.pruneDeletingSessionIds();
        this.saveChatHistories();
    }

    persistCurrentSession(question = "") {
        if (!this.isAuthenticated || !this.sessionId) {
            return;
        }

        const existing = this.chatHistories.find((session) => session.id === this.sessionId);
        const firstUserMessage = this.currentChatHistory.find((message) => message.role === "user");
        const title = existing?.title || this.deriveSessionTitle(firstUserMessage?.content || question || "新对话");
        const latestMessage = [...this.currentChatHistory].reverse().find((message) => message.role === "assistant" || message.role === "user");
        const latestRoute = latestMessage?.route || latestMessage?.intent || existing?.lastIntent || null;
        const now = new Date().toISOString();

        this.upsertSessionRecord({
            id: this.sessionId,
            title,
            threadId: existing?.threadId || this.sessionId,
            lastIntent: latestRoute,
            createdAt: existing?.createdAt || now,
            updatedAt: now,
            messageCount: this.currentChatHistory.length,
            messages: this.currentChatHistory.map((message) => this.serializeMessage(message)),
        });
        this.renderChatHistory();
    }

    deriveSessionTitle(question) {
        return this.truncate(question.trim() || "新对话", 28);
    }

    async deleteHistorySession(sessionId) {
        if (!this.ensureAuthenticated()) {
            return;
        }

        if (this.isSessionDeleting(sessionId)) {
            return;
        }

        this.deletingSessionIds.add(sessionId);
        this.renderChatHistory();

        try {
            const response = await this.apiFetch(`/sessions/${sessionId}`, {
                method: "DELETE",
            });
            if (!response.ok && response.status !== 404) {
                throw new Error(await this.extractErrorMessage(response));
            }

            this.chatHistories = this.chatHistories.filter((session) => session.id !== sessionId);
            this.deletingSessionIds.delete(sessionId);
            this.saveChatHistories();

            if (this.sessionId === sessionId) {
                this.startNewChat({ keepHistoryPanel: true });
            } else {
                this.renderChatHistory();
            }

            this.showNotification("会话已删除", "success");
        } catch (error) {
            this.deletingSessionIds.delete(sessionId);
            this.renderChatHistory();
            console.error("删除会话失败:", error);
            this.showNotification(error.message || "删除会话失败", "error");
        }
    }

    isSessionDeleting(sessionId) {
        return Boolean(sessionId) && this.deletingSessionIds.has(sessionId);
    }

    pruneDeletingSessionIds() {
        const activeSessionIds = new Set(this.chatHistories.map((session) => session.id));
        this.deletingSessionIds.forEach((sessionId) => {
            if (!activeSessionIds.has(sessionId)) {
                this.deletingSessionIds.delete(sessionId);
            }
        });
    }

    renderChatHistory() {
        if (!this.isAuthenticated) {
            this.chatHistoryList.innerHTML = '<div class="trace-empty">登录后可查看并恢复历史会话。</div>';
            return;
        }

        if (!this.chatHistories.length) {
            this.chatHistoryList.innerHTML = '<div class="trace-empty">还没有历史对话，发送第一条消息后会自动沉淀到这里。</div>';
            return;
        }

        this.chatHistoryList.innerHTML = this.chatHistories
            .map((session) => {
                const activeClass = session.id === this.sessionId ? " active" : "";
                const deleting = this.isSessionDeleting(session.id);
                const deletingClass = deleting ? " deleting" : "";
                const deleteTitle = deleting ? "正在删除会话" : "删除会话";
                const updatedAt = session.updatedAt ? this.formatDateTime(session.updatedAt, { withDate: true, withSeconds: false }) : "刚刚";
                const countLabel = session.messageCount ? `${session.messageCount} 条消息` : "待继续";
                return `
                    <div class="history-item${activeClass}${deletingClass}" data-session-id="${this.escapeHtml(session.id)}">
                        <div class="history-item-copy">
                            <div class="history-item-title">${this.escapeHtml(session.title || "新对话")}</div>
                            <div class="history-item-meta">${this.escapeHtml(updatedAt)} · ${this.escapeHtml(countLabel)}</div>
                        </div>
                        <button class="history-item-delete" type="button" title="删除会话" data-session-id="${this.escapeHtml(session.id)}">
                            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                <path d="M4 7H20M9 7V4H15V7M10 11V17M14 11V17M6 7L7 19C7.1 20.1 8 21 9.1 21H14.9C16 21 16.9 20.1 17 19L18 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                    </div>
                `;
            })
            .join("");

        this.chatHistoryList.querySelectorAll(".history-item-delete").forEach((button) => {
            const deleting = this.isSessionDeleting(button.dataset.sessionId);
            const title = deleting ? "正在删除会话" : "删除会话";
            button.disabled = deleting;
            button.setAttribute("aria-disabled", String(deleting));
            button.title = title;
            button.setAttribute("aria-label", title);
        });
    }

    renderChatMessages() {
        this.cancelPendingMessageRenders();
        this.chatMessages.innerHTML = "";
        this.currentChatHistory.forEach((message) => {
            delete message._ui;
            delete message._traceRefs;
            delete message._pendingHighlight;
        });

        const startIndex = this.getChatRenderStartIndex();
        if (startIndex > 0) {
            this.chatMessages.appendChild(this.createMessageHistoryGate(startIndex));
        }

        this.currentChatHistory.slice(startIndex).forEach((message) => {
            const element = this.createMessageElement(message);
            this.chatMessages.appendChild(element);
        });
        this.updateWelcomeState();
        this.scrollChatToBottom(true);
    }

    getChatRenderStartIndex(length = this.currentChatHistory.length) {
        if (this.showFullChatHistory || length <= this.chatRenderLimit) {
            return 0;
        }
        return Math.max(0, length - this.chatRenderLimit);
    }

    canAppendChatMessages(previousLength, nextLength = this.currentChatHistory.length) {
        return this.getChatRenderStartIndex(previousLength) === this.getChatRenderStartIndex(nextLength);
    }

    appendChatMessages(previousLength) {
        if (!this.canAppendChatMessages(previousLength)) {
            this.renderChatMessages();
            return;
        }

        const startIndex = Math.max(previousLength, this.getChatRenderStartIndex());
        const pendingMessages = this.currentChatHistory.slice(startIndex);
        if (!pendingMessages.length) {
            this.renderChatMessages();
            return;
        }

        pendingMessages.forEach((message) => {
            const element = this.createMessageElement(message);
            this.chatMessages.appendChild(element);
        });
        this.updateWelcomeState();
        this.scrollChatToBottom(true);
    }

    createMessageHistoryGate(hiddenCount) {
        const gate = document.createElement("div");
        gate.className = "message-history-gate";

        const button = document.createElement("button");
        button.type = "button";
        button.className = "text-link-btn message-history-gate-btn";
        button.textContent = `展开更早的 ${hiddenCount} 条消息`;
        button.addEventListener("click", () => {
            this.showFullChatHistory = true;
            this.renderChatMessages();
            this.chatMessages.scrollTop = 0;
        });

        gate.appendChild(button);
        return gate;
    }

    createMessageElement(message) {
        const root = document.createElement("div");
        root.className = `message ${message.role}`;

        if (message.role === "assistant") {
            const avatar = document.createElement("div");
            avatar.className = "message-avatar";
            avatar.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 3L14.3 9.7L21 12L14.3 14.3L12 21L9.7 14.3L3 12L9.7 9.7L12 3Z" fill="white"></path>
                </svg>
            `;
            root.appendChild(avatar);
        }

        const wrapper = document.createElement("div");
        wrapper.className = "message-content-wrapper";

        let traceSummary = null;
        if (message.role === "assistant") {
            traceSummary = document.createElement("div");
            traceSummary.className = "message-trace-summary hidden";

            const toggleButton = document.createElement("button");
            toggleButton.type = "button";
            toggleButton.className = "message-trace-toggle";

            const left = document.createElement("div");
            const label = document.createElement("div");
            label.className = "message-trace-label";
            const meta = document.createElement("div");
            meta.className = "message-trace-meta";
            left.appendChild(label);
            left.appendChild(meta);

            const right = document.createElement("div");
            right.className = "message-trace-toggle-right";
            const rightText = document.createElement("span");
            const chevron = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            chevron.setAttribute("viewBox", "0 0 24 24");
            chevron.setAttribute("fill", "none");
            chevron.classList.add("message-trace-chevron");
            chevron.innerHTML = '<path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>';
            right.appendChild(rightText);
            right.appendChild(chevron);

            toggleButton.appendChild(left);
            toggleButton.appendChild(right);

            const body = document.createElement("div");
            body.className = "message-trace-body";

            toggleButton.addEventListener("click", () => {
                if (!message.traceSummary) {
                    return;
                }
                message.traceSummary.expanded = !message.traceSummary.expanded;
                this.setActiveTrace(message.traceSummary);
                this.updateMessageElement(message);
            });

            traceSummary.appendChild(toggleButton);
            traceSummary.appendChild(body);
            wrapper.appendChild(traceSummary);

            message._traceRefs = {
                root: traceSummary,
                label,
                meta,
                rightText,
                body,
            };
        }

        const content = document.createElement("div");
        content.className = "message-content";
        wrapper.appendChild(content);

        const time = document.createElement("div");
        time.className = "message-time";
        wrapper.appendChild(time);

        const timing = document.createElement("div");
        timing.className = "message-timing";
        wrapper.appendChild(timing);

        let actions = null;
        let retryButton = null;
        if (message.role === "assistant") {
            actions = document.createElement("div");
            actions.className = "message-actions hidden";

            retryButton = document.createElement("button");
            retryButton.type = "button";
            retryButton.className = "text-link-btn message-retry-btn";
            retryButton.textContent = "重试";
            retryButton.addEventListener("click", () => this.retryAssistantMessage(message));
            actions.appendChild(retryButton);
            wrapper.appendChild(actions);
        }

        root.appendChild(wrapper);

        message._ui = {
            root,
            wrapper,
            content,
            time,
            timing,
            actions,
            retryButton,
            lastRenderedContent: null,
            needsHighlight: false,
        };

        this.updateMessageElement(message);
        return root;
    }

    updateMessageElement(message, options = {}) {
        if (!message._ui) {
            return;
        }

        const inProgress = message.role === "assistant"
            && this.isStreaming
            && !message.timing?.assistant_completed_at;
        message._ui.root.classList.toggle("streaming", inProgress);

        if (message.role === "assistant") {
            const assistantText = message.content && message.content.trim()
                ? message.content
                : "正在组织回答...";
            if (message._ui.lastRenderedContent !== assistantText) {
                message._ui.content.innerHTML = this.renderMarkdown(assistantText);
                message._ui.lastRenderedContent = assistantText;
                message._ui.needsHighlight = true;
            }
            const shouldHighlight = options.highlight ?? (!inProgress && message._ui.needsHighlight);
            if (shouldHighlight) {
                this.highlightCodeBlocks(message._ui.content);
                message._ui.needsHighlight = false;
            }
        } else {
            message._ui.content.textContent = message.content || "";
        }

        const displayTime = message.timestamp || message.timing?.request_started_at || null;
        if (message.role === "user") {
            message._ui.time.textContent = displayTime
                ? `提问时间 ${this.formatDateTime(displayTime, { withDate: true, withSeconds: false })}`
                : "";
            message._ui.timing.textContent = "";
        } else {
            const startedAt = message.timing?.assistant_started_at || null;
            const completedAt = message.timing?.assistant_completed_at || message.timestamp || null;
            const requestAt = message.timing?.request_started_at || null;

            message._ui.time.textContent = requestAt
                ? `提问时间 ${this.formatDateTime(requestAt, { withDate: true, withSeconds: false })}`
                : "";

            const timingParts = [];
            if (startedAt) {
                timingParts.push(`开始输出 ${this.formatDateTime(startedAt, { withDate: true, withSeconds: false })}`);
            }
            if (completedAt) {
                timingParts.push(`输出完成 ${this.formatDateTime(completedAt, { withDate: true, withSeconds: false })}`);
            }
            if (Number.isFinite(message.timing?.duration_ms)) {
                timingParts.push(`总思考 ${this.formatDuration(message.timing.duration_ms)}`);
            }
            message._ui.timing.textContent = timingParts.join(" · ");
        }

        if (message.role === "assistant" && message._traceRefs) {
            const trace = message.traceSummary;
            if (!trace || (!trace.steps?.length && !trace.intent && !trace.startedAt)) {
                message._traceRefs.root.classList.add("hidden");
            } else {
                message._traceRefs.root.classList.remove("hidden");
                message._traceRefs.root.classList.toggle("expanded", Boolean(trace.expanded));
                message._traceRefs.label.textContent = this.buildTraceHeaderLabel(trace);
                message._traceRefs.meta.textContent = this.buildTraceMetaText(trace);
                message._traceRefs.rightText.textContent = trace.steps?.length
                    ? `${trace.steps.length} 步`
                    : "查看";
                message._traceRefs.body.innerHTML = (trace.steps || [])
                    .map((step) => this.renderTraceEntry(step))
                    .join("");
            }
        }

        if (message._ui.actions && message._ui.retryButton) {
            const showRetry = Boolean(message.requestError && message.requestMeta);
            message._ui.actions.classList.toggle("hidden", !showRetry);
            message._ui.retryButton.disabled = this.isStreaming;
        }
    }

    updateWelcomeState() {
        this.welcomeGreeting.classList.toggle("hidden", this.currentChatHistory.length > 0);
    }

    scrollChatToBottom(force = false) {
        if (!force && !this.isNearChatBottom()) {
            return;
        }
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    isNearChatBottom() {
        const distance = this.chatMessages.scrollHeight - this.chatMessages.scrollTop - this.chatMessages.clientHeight;
        return distance < 120;
    }

    autoResizeTextarea() {
        this.messageInput.style.height = "auto";
        this.messageInput.style.height = `${Math.min(this.messageInput.scrollHeight, 220)}px`;
    }

    updateSendButtonState() {
        const hasText = Boolean(this.messageInput.value.trim());
        this.sendButton.disabled = this.isStreaming || !hasText;
        this.toolsBtn.disabled = this.isStreaming;
        this.chatMessages.querySelectorAll(".message-retry-btn").forEach((button) => {
            button.disabled = this.isStreaming;
        });
    }

    setMode(mode) {
        this.currentMode = mode === "stream" ? "stream" : "quick";
        localStorage.setItem(this.storageKeys.mode, this.currentMode);
        this.updateModeUI();
    }

    updateModeUI() {
        this.currentModeText.textContent = this.currentMode === "stream" ? "流式" : "快速";
        this.modeItems.forEach((item) => {
            const active = item.dataset.mode === this.currentMode;
            item.classList.toggle("active", active);
            item.setAttribute("aria-selected", String(active));
        });
    }

    async handleSend() {
        if (this.isStreaming) {
            return;
        }
        if (!this.ensureAuthenticated()) {
            return;
        }

        const question = this.messageInput.value.trim();
        if (!question) {
            return;
        }

        this.messageInput.value = "";
        this.autoResizeTextarea();
        this.updateSendButtonState();

        const userMessage = this.createUserMessage(question);
        const assistantMessage = this.createAssistantMessage(
            this.currentMode === "stream" ? "流式对话链路" : "问答链路",
            question,
            {
                kind: this.currentMode === "stream" ? "stream-chat" : "quick-chat",
                label: this.currentMode === "stream" ? "流式对话链路" : "问答链路",
                question,
            }
        );

        const previousLength = this.currentChatHistory.length;
        this.currentChatHistory.push(userMessage);
        this.currentChatHistory.push(assistantMessage);
        this.persistCurrentSession(question);
        this.appendChatMessages(previousLength);
        this.setActiveTrace(assistantMessage.traceSummary);

        this.isStreaming = true;
        this.updateSendButtonState();

        try {
            if (this.currentMode === "stream") {
                await this.sendStreamQuestion(question, assistantMessage);
            } else {
                await this.sendQuickQuestion(question, assistantMessage);
            }
            await this.syncSessionsFromBackend();
        } finally {
            this.isStreaming = false;
            this.updateSendButtonState();
            this.persistCurrentSession(question);
            this.renderChatHistory();
        }
    }

    async sendQuickQuestion(question, assistantMessage) {
        const trace = assistantMessage.traceSummary;
        assistantMessage.requestError = null;
        this.addTraceStep(trace, this.createTraceStep("请求已发送", `问题：${question}`, { phase: "request" }));

        try {
            const response = await this.apiFetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    Id: this.sessionId,
                    Question: question,
                }),
            });

            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }

            const payload = await response.json();
            if (!payload?.data?.success) {
                throw new Error(payload?.data?.errorMessage || "快速对话失败");
            }

            const data = payload.data;
            assistantMessage.content = data.answer || "";
            assistantMessage.timing = data.timing || null;
            assistantMessage.timestamp = data.timing?.assistant_completed_at || new Date().toISOString();
            assistantMessage.intent = data.route?.intent || null;
            assistantMessage.route = data.route?.route || null;
            assistantMessage.requestError = null;
            this.applyQuickTrace(trace, data.route || {}, data.timing || null);
            this.markTraceCompleted(trace, data.timing || null);
            this.cancelPendingMessageRender(assistantMessage);
            this.updateMessageElement(assistantMessage, { highlight: true });
            this.setActiveTrace(trace);
        } catch (error) {
            this.handleRequestError(assistantMessage, error, trace);
        }
    }

    applyQuickTrace(trace, route, timing) {
        trace.startedAt = timing?.request_started_at || trace.startedAt;
        trace.intent = route.intent || trace.intent;
        trace.reason = route.reason || trace.reason;
        trace.label = this.traceIntentLabel(route.intent || trace.intent);
        trace.timing = timing ? { ...(trace.timing || {}), ...timing } : trace.timing;
        trace.steps = [];

        this.addTraceStep(
            trace,
            this.createTraceStep(
                "意图分流",
                `命中 ${route.intent || "unknown"}，原因：${route.reason || "未返回原因"}`,
                { phase: "route", timestamp: timing?.request_started_at || trace.startedAt }
            )
        );

        if (route.trace) {
            const retrieval = route.trace;
            const retrievalDurationMs = (retrieval.dense_latency_ms || 0) + (retrieval.sparse_latency_ms || 0) + (retrieval.rerank_latency_ms || 0);
            trace.retrieval = retrieval;
            trace.timing = {
                ...(trace.timing || {}),
                retrieval_duration_ms: retrievalDurationMs,
            };
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    "混合检索",
                    `dense=${retrieval.dense_hits || 0} · sparse=${retrieval.sparse_hits || 0} · fusion=${retrieval.fusion_hits || 0} · rerank=${retrieval.rerank_hits || 0}`,
                    {
                        phase: "retrieval",
                        status: "success",
                        durationMs: retrievalDurationMs,
                    }
                )
            );

            if (Array.isArray(retrieval.final_sources) && retrieval.final_sources.length) {
                this.addTraceStep(
                    trace,
                    this.createTraceStep(
                        "命中文档",
                        retrieval.final_sources.join("\n"),
                        { phase: "retrieval", status: "success" }
                    )
                );
            }
        }

        this.addTraceStep(
            trace,
            this.createTraceStep("答案生成", "快速链路已返回最终答案。", {
                phase: "respond",
                status: "success",
                timestamp: timing?.assistant_completed_at || new Date().toISOString(),
            })
        );
    }

    async sendStreamQuestion(question, assistantMessage) {
        const trace = assistantMessage.traceSummary;
        assistantMessage.requestError = null;
        try {
            const response = await this.apiFetch("/chat_stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "text/event-stream",
                },
                body: JSON.stringify({
                    Id: this.sessionId,
                    Question: question,
                }),
            });

            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }

            await this.consumeSseStream(response, (payload) => this.handleChatStreamPayload(payload, assistantMessage, trace));

            if (!assistantMessage.timing && assistantMessage.content) {
                const fallbackTiming = this.buildFallbackTiming(trace);
                assistantMessage.timing = fallbackTiming;
                assistantMessage.timestamp = fallbackTiming.assistant_completed_at;
                this.markTraceCompleted(trace, fallbackTiming);
                this.cancelPendingMessageRender(assistantMessage);
                this.updateMessageElement(assistantMessage, { highlight: true });
            }
        } catch (error) {
            this.handleRequestError(assistantMessage, error, trace);
        }
    }

    handleChatStreamPayload(payload, assistantMessage, trace) {
        const { type, data } = payload;
        if (!type) {
            return;
        }

        if (type === "route") {
            trace.startedAt = data?.timestamp || trace.startedAt;
            trace.intent = data?.intent || trace.intent;
            trace.reason = data?.reason || trace.reason;
            trace.label = this.traceIntentLabel(data?.intent || trace.intent);
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    "意图分流",
                    `命中 ${data?.intent || "unknown"}，原因：${data?.reason || "未返回原因"}`,
                    { phase: "route", timestamp: data?.timestamp || trace.startedAt }
                )
            );
            return;
        }

        if (type === "search_results") {
            trace.retrieval = data || null;
            trace.timing = {
                ...(trace.timing || {}),
                retrieval_completed_at: data?.timestamp || new Date().toISOString(),
                retrieval_duration_ms: (data?.dense_latency_ms || 0) + (data?.sparse_latency_ms || 0) + (data?.rerank_latency_ms || 0),
            };
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    "检索摘要",
                    `dense=${data?.dense_hits || 0} · sparse=${data?.sparse_hits || 0} · fusion=${data?.fusion_hits || 0} · rerank=${data?.rerank_hits || 0}`,
                    {
                        phase: "retrieval",
                        status: "success",
                        timestamp: data?.timestamp || new Date().toISOString(),
                        durationMs: (data?.dense_latency_ms || 0) + (data?.sparse_latency_ms || 0) + (data?.rerank_latency_ms || 0),
                    }
                )
            );
            if (Array.isArray(data?.final_sources) && data.final_sources.length) {
                this.addTraceStep(
                    trace,
                    this.createTraceStep("命中文档", data.final_sources.join("\n"), {
                        phase: "retrieval",
                        status: "success",
                    })
                );
            }
            return;
        }

        if (type === "status") {
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    "链路状态",
                    data?.message || "状态已更新",
                    {
                        phase: data?.stage || "status",
                        timestamp: data?.timestamp || new Date().toISOString(),
                    }
                )
            );
            return;
        }

        if (type === "tool_call") {
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    "工具调用",
                    typeof data === "string" ? data : JSON.stringify(data, null, 2),
                    {
                        phase: "tool",
                        timestamp: new Date().toISOString(),
                    }
                )
            );
            return;
        }

        if (type === "trace_step") {
            this.addTraceStep(trace, {
                title: data?.title || "执行步骤",
                detail: data?.detail || "",
                status: data?.status || "info",
                phase: data?.phase || "processing",
                timestamp: data?.timestamp || new Date().toISOString(),
                duration_ms: data?.duration_ms,
            });
            return;
        }

        if (type === "content") {
            assistantMessage.content = `${assistantMessage.content || ""}${data || ""}`;
            if (!assistantMessage.timing?.assistant_started_at) {
                assistantMessage.timing = {
                    ...(assistantMessage.timing || {}),
                    request_started_at: trace.startedAt || new Date().toISOString(),
                    assistant_started_at: new Date().toISOString(),
                };
            }
            this.scheduleMessageRender(assistantMessage, { scroll: true });
            return;
        }

        if (type === "done") {
            const timing = {
                request_started_at: data?.request_started_at || trace.startedAt || new Date().toISOString(),
                assistant_started_at: data?.assistant_started_at || assistantMessage.timing?.assistant_started_at || new Date().toISOString(),
                assistant_completed_at: data?.assistant_completed_at || new Date().toISOString(),
                duration_ms: data?.duration_ms || null,
                retrieval_completed_at: data?.retrieval_completed_at || trace.timing?.retrieval_completed_at || null,
                retrieval_duration_ms: data?.retrieval_duration_ms ?? trace.timing?.retrieval_duration_ms ?? null,
                llm_started_at: data?.llm_started_at || null,
                llm_duration_ms: data?.llm_duration_ms ?? null,
                first_chunk_at: data?.first_chunk_at || null,
                time_to_first_chunk_ms: data?.time_to_first_chunk_ms ?? null,
            };
            if (data?.answer && data.answer.length >= (assistantMessage.content || "").length) {
                assistantMessage.content = data.answer;
            }
            assistantMessage.intent = data?.intent || trace.intent || null;
            assistantMessage.route = data?.intent || trace.intent || null;
            assistantMessage.requestError = null;
            trace.label = this.traceIntentLabel(data?.intent || trace.intent);
            assistantMessage.timing = timing;
            assistantMessage.timestamp = timing.assistant_completed_at;
            this.addTraceStep(
                trace,
                this.createTraceStep("流式输出完成", "本轮流式输出已结束。", {
                    phase: "respond",
                    status: "success",
                    timestamp: timing.assistant_completed_at,
                })
            );
            this.markTraceCompleted(trace, timing);
            this.cancelPendingMessageRender(assistantMessage);
            this.updateMessageElement(assistantMessage, { highlight: true });
            this.setActiveTrace(trace);
            return;
        }

        if (type === "error") {
            const errorMessage = typeof data === "string"
                ? data
                : data?.message || "流式对话失败";
            throw new Error(errorMessage);
        }
    }

    async handleAiOpsRequest() {
        if (this.isStreaming) {
            return;
        }
        if (!this.ensureOperatorPermission("AIOps 诊断")) {
            return;
        }

        const prompt = "请执行 AIOps 诊断，检查当前系统告警与异常状态。";
        const userMessage = this.createUserMessage(prompt);
        const assistantMessage = this.createAssistantMessage("AIOps 诊断链路", prompt);

        assistantMessage.requestMeta = {
            kind: "aiops",
            label: "AIOps 诊断链路",
            question: prompt,
        };
        const previousLength = this.currentChatHistory.length;
        this.currentChatHistory.push(userMessage);
        this.currentChatHistory.push(assistantMessage);
        this.persistCurrentSession(prompt);
        this.appendChatMessages(previousLength);
        this.setActiveTrace(assistantMessage.traceSummary);

        this.isStreaming = true;
        this.updateSendButtonState();

        try {
            await this.runAiOpsRequest(assistantMessage);
            await this.syncSessionsFromBackend();
        } catch (error) {
            this.handleRequestError(assistantMessage, error, assistantMessage.traceSummary);
        } finally {
            this.isStreaming = false;
            this.updateSendButtonState();
            this.persistCurrentSession(prompt);
            this.renderChatHistory();
        }
    }

    handleAiOpsPayload(payload, assistantMessage, trace) {
        const type = payload?.type;
        if (!type) {
            return;
        }

        if (!trace.startedAt) {
            trace.startedAt = new Date().toISOString();
        }

        if (type === "status") {
            this.addTraceStep(
                trace,
                this.createTraceStep("链路状态", payload.message || "AIOps 诊断进行中", {
                    phase: payload.stage || "status",
                    timestamp: new Date().toISOString(),
                })
            );
            return;
        }

        if (type === "plan") {
            const plan = Array.isArray(payload.plan) ? payload.plan : [];
            const detail = plan.length
                ? `${payload.message || "诊断计划已生成"}\n${plan.map((step, index) => `${index + 1}. ${step}`).join("\n")}`
                : (payload.message || "诊断计划已生成");
            this.addTraceStep(
                trace,
                this.createTraceStep("执行计划", detail, {
                    phase: "plan",
                    status: "success",
                    timestamp: new Date().toISOString(),
                })
            );
            return;
        }

        if (type === "step_complete") {
            const preview = payload.result_preview ? `\n${payload.result_preview}` : "";
            const remaining = Number.isFinite(payload.remaining_steps) ? `\n剩余步骤：${payload.remaining_steps}` : "";
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    payload.current_step || "执行步骤完成",
                    `${payload.message || "步骤执行完成"}${preview}${remaining}`,
                    {
                        phase: "execute",
                        status: "success",
                        timestamp: new Date().toISOString(),
                    }
                )
            );
            return;
        }

        if (type === "report") {
            if (payload.report) {
                assistantMessage.content = payload.report;
                assistantMessage.requestError = null;
                this.updateMessageElement(assistantMessage, { highlight: true });
                this.scrollChatToBottom();
            }
            this.addTraceStep(
                trace,
                this.createTraceStep("诊断报告", payload.message || "最终报告已生成", {
                    phase: "report",
                    status: "success",
                    timestamp: new Date().toISOString(),
                })
            );
            return;
        }

        if (type === "complete") {
            const report = payload?.diagnosis?.report || assistantMessage.content || "AIOps 诊断已完成。";
            assistantMessage.content = report;
            assistantMessage.requestError = null;
            const timing = this.buildFallbackTiming(trace);
            assistantMessage.timing = timing;
            assistantMessage.timestamp = timing.assistant_completed_at;
            this.markTraceCompleted(trace, timing);
            this.updateMessageElement(assistantMessage, { highlight: true });
            this.setActiveTrace(trace);
            return;
        }

        if (type === "error") {
            throw new Error(payload.message || "AIOps 诊断失败");
        }
    }

    async consumeSseStream(response, onPayload) {
        if (!response.body) {
            throw new Error("当前浏览器不支持流式响应");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            buffer = buffer.replace(/\r/g, "");

            let boundaryIndex = buffer.indexOf("\n\n");
            while (boundaryIndex >= 0) {
                const rawEvent = buffer.slice(0, boundaryIndex).trim();
                buffer = buffer.slice(boundaryIndex + 2);
                if (rawEvent) {
                    const parsed = this.parseSseEvent(rawEvent);
                    if (parsed?.data) {
                        let payload = null;
                        try {
                            payload = JSON.parse(parsed.data);
                        } catch (error) {
                            console.error("SSE 事件解析失败:", error, parsed.data);
                        }
                        if (payload) {
                            onPayload(payload);
                        }
                    }
                }
                boundaryIndex = buffer.indexOf("\n\n");
            }

            if (done) {
                const tail = buffer.trim();
                if (tail) {
                    const parsed = this.parseSseEvent(tail);
                    if (parsed?.data) {
                        const payload = JSON.parse(parsed.data);
                        onPayload(payload);
                    }
                }
                break;
            }
        }
    }

    scheduleMessageRender(message, options = {}) {
        if (!message?._ui) {
            return;
        }
        if (options.highlight) {
            message._pendingHighlight = true;
        }
        this.pendingMessageRenders.add(message);
        this.pendingScrollToBottom = this.pendingScrollToBottom || Boolean(options.scroll);
        if (this.pendingMessageRenderFrame !== null) {
            return;
        }
        this.pendingMessageRenderFrame = window.requestAnimationFrame(() => {
            const queuedMessages = Array.from(this.pendingMessageRenders);
            const shouldScroll = this.pendingScrollToBottom;
            this.pendingMessageRenders.clear();
            this.pendingMessageRenderFrame = null;
            this.pendingScrollToBottom = false;

            queuedMessages.forEach((queuedMessage) => {
                const highlight = Boolean(queuedMessage._pendingHighlight);
                delete queuedMessage._pendingHighlight;
                this.updateMessageElement(queuedMessage, { highlight });
            });

            if (shouldScroll) {
                this.scrollChatToBottom();
            }
        });
    }

    cancelPendingMessageRender(message) {
        if (!message) {
            return;
        }
        this.pendingMessageRenders.delete(message);
        delete message._pendingHighlight;
        if (!this.pendingMessageRenders.size && this.pendingMessageRenderFrame !== null) {
            window.cancelAnimationFrame(this.pendingMessageRenderFrame);
            this.pendingMessageRenderFrame = null;
            this.pendingScrollToBottom = false;
        }
    }

    cancelPendingMessageRenders() {
        this.pendingMessageRenders.forEach((message) => {
            delete message._pendingHighlight;
        });
        this.pendingMessageRenders.clear();
        if (this.pendingMessageRenderFrame !== null) {
            window.cancelAnimationFrame(this.pendingMessageRenderFrame);
            this.pendingMessageRenderFrame = null;
        }
        this.pendingScrollToBottom = false;
    }

    parseSseEvent(rawEvent) {
        const lines = rawEvent.split("\n");
        let event = "message";
        const dataLines = [];

        lines.forEach((line) => {
            if (!line || line.startsWith(":")) {
                return;
            }
            if (line.startsWith("event:")) {
                event = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
                dataLines.push(line.slice(5).trimStart());
            }
        });

        return {
            event,
            data: dataLines.join("\n"),
        };
    }

    handleRequestError(assistantMessage, error, trace) {
        console.error("请求失败:", error);
        const message = error?.message || "请求失败";
        assistantMessage.content = `本次请求未完成：${message}`;
        assistantMessage.requestError = {
            message,
            occurredAt: new Date().toISOString(),
        };
        const fallbackTiming = this.buildFallbackTiming(trace);
        assistantMessage.timing = fallbackTiming;
        assistantMessage.timestamp = fallbackTiming.assistant_completed_at;
        this.addTraceStep(
            trace,
            this.createTraceStep("链路异常", message, {
                phase: "error",
                status: "error",
                timestamp: fallbackTiming.assistant_completed_at,
            })
        );
        this.markTraceCompleted(trace, fallbackTiming);
        this.cancelPendingMessageRender(assistantMessage);
        this.updateMessageElement(assistantMessage, { highlight: false });
        this.setActiveTrace(trace);
        this.showNotification(message, "error");
    }

    async retryAssistantMessage(message) {
        if (this.isStreaming || !message?.requestMeta) {
            return;
        }
        if (!this.ensureAuthenticated()) {
            return;
        }

        const meta = message.requestMeta;
        if (meta.kind === "aiops" && !this.ensureOperatorPermission("AIOps 诊断")) {
            return;
        }
        const startedAt = new Date().toISOString();
        this.cancelPendingMessageRender(message);
        message.content = "";
        message.timestamp = null;
        message.intent = null;
        message.route = null;
        message.timing = null;
        message.requestError = null;
        message.traceSummary = this.createTraceSummary(meta.label || "执行链路", startedAt);
        message.traceSummary.steps.push(
            this.createTraceStep("重试请求", `已再次发起：${meta.question || "当前请求"}`, {
                phase: "request",
                timestamp: startedAt,
            })
        );
        if (message._ui) {
            message._ui.lastRenderedContent = null;
            message._ui.needsHighlight = false;
        }
        this.updateMessageElement(message, { highlight: false });
        this.setActiveTrace(message.traceSummary);

        this.isStreaming = true;
        this.updateSendButtonState();

        try {
            if (meta.kind === "aiops") {
                await this.runAiOpsRequest(message);
            } else if (meta.kind === "stream-chat") {
                await this.sendStreamQuestion(meta.question, message);
            } else {
                await this.sendQuickQuestion(meta.question, message);
            }
            await this.syncSessionsFromBackend();
        } finally {
            this.isStreaming = false;
            this.updateSendButtonState();
            this.persistCurrentSession(meta.question || "");
            this.renderChatHistory();
        }
    }

    createUserMessage(question) {
        return {
            role: "user",
            content: question,
            timestamp: new Date().toISOString(),
            intent: null,
            route: null,
            timing: null,
            traceSummary: null,
        };
    }

    createAssistantMessage(label, question, requestMeta = null) {
        const trace = this.createTraceSummary(label, new Date().toISOString());
        trace.steps.push(this.createTraceStep("请求排队", `已接收问题：${question}`, {
            phase: "request",
            timestamp: trace.startedAt,
        }));

        return {
            role: "assistant",
            content: "",
            timestamp: null,
            intent: null,
            route: null,
            timing: null,
            traceSummary: trace,
            requestMeta: requestMeta
                ? {
                    kind: requestMeta.kind || "quick-chat",
                    label: requestMeta.label || label,
                    question: requestMeta.question || question,
                }
                : null,
            requestError: null,
        };
    }

    createTraceSummary(label, startedAt) {
        return {
            label,
            startedAt,
            completedAt: null,
            totalDurationMs: null,
            timing: null,
            intent: null,
            reason: null,
            retrieval: null,
            steps: [],
            expanded: true,
        };
    }

    createIdleTrace() {
        return {
            label: "等待新请求",
            startedAt: null,
            completedAt: null,
            totalDurationMs: null,
            intent: null,
            reason: null,
            retrieval: null,
            steps: [],
            expanded: false,
        };
    }

    createTraceStep(title, detail, options = {}) {
        return {
            title,
            detail,
            status: options.status || "info",
            phase: options.phase || "processing",
            timestamp: options.timestamp || new Date().toISOString(),
            duration_ms: options.durationMs || null,
        };
    }

    addTraceStep(trace, step) {
        trace.steps = trace.steps || [];
        trace.steps.push(step);
        this.setActiveTrace(trace);
    }

    setActiveTrace(trace) {
        this.activeTrace = trace || this.createIdleTrace();
        this.renderTracePanel();
        if (this.currentChatHistory.length) {
            const latestAssistant = [...this.currentChatHistory].reverse().find((message) => message.role === "assistant");
            if (latestAssistant?.traceSummary === trace) {
                this.updateMessageElement(latestAssistant);
            }
        }
    }

    pickLatestTrace(messages) {
        const latestAssistant = [...messages].reverse().find((message) => message.traceSummary);
        return latestAssistant?.traceSummary || this.createIdleTrace();
    }

    markTraceCompleted(trace, timing) {
        if (!trace) {
            return;
        }
        trace.timing = timing
            ? {
                ...(trace.timing || {}),
                ...timing,
            }
            : (trace.timing || null);
        trace.startedAt = timing?.request_started_at || trace.startedAt;
        trace.completedAt = timing?.assistant_completed_at || trace.completedAt || new Date().toISOString();
        trace.totalDurationMs = Number.isFinite(timing?.duration_ms)
            ? timing.duration_ms
            : Math.max(0, new Date(trace.completedAt).getTime() - new Date(trace.startedAt || trace.completedAt).getTime());
    }

    buildFallbackTiming(trace) {
        const requestStartedAt = trace?.startedAt || new Date().toISOString();
        const assistantStartedAt = trace?.steps?.find((step) => step.phase !== "request")?.timestamp || requestStartedAt;
        const assistantCompletedAt = new Date().toISOString();
        return {
            request_started_at: requestStartedAt,
            assistant_started_at: assistantStartedAt,
            assistant_completed_at: assistantCompletedAt,
            duration_ms: Math.max(0, new Date(assistantCompletedAt).getTime() - new Date(requestStartedAt).getTime()),
        };
    }

    renderTracePanel() {
        const trace = this.activeTrace;
        const hasTrace = Boolean(trace && (trace.steps?.length || trace.startedAt || trace.intent));

        this.tracePanelTitle.textContent = hasTrace ? this.buildTracePanelTitle(trace) : "等待新请求";
        this.tracePanelMeta.textContent = hasTrace
            ? this.buildTracePanelDescription(trace)
            : "发送消息后，这里会显示本轮链路的分步骤时间线、检索摘要和工具调用状态。";

        if (!hasTrace) {
            this.traceOverview.innerHTML = "";
            this.traceList.innerHTML = "";
            this.traceEmpty.classList.remove("hidden");
            return;
        }

        this.traceEmpty.classList.add("hidden");
        this.traceOverview.innerHTML = this.buildTraceOverview(trace);
        this.traceList.innerHTML = (trace.steps || []).map((step) => this.renderTraceEntry(step)).join("");
    }

    buildTracePanelTitle(trace) {
        if (trace.label && trace.label !== "等待新请求") {
            return trace.label;
        }
        return this.traceIntentLabel(trace.intent);
    }

    buildTracePanelDescription(trace) {
        const parts = [];
        if (trace.reason) {
            parts.push(trace.reason);
        }
        if (trace.startedAt) {
            parts.push(`开始于 ${this.formatDateTime(trace.startedAt, { withDate: true, withSeconds: true })}`);
        }
        if (trace.completedAt) {
            parts.push(`结束于 ${this.formatDateTime(trace.completedAt, { withDate: true, withSeconds: true })}`);
        }
        if (Number.isFinite(trace.totalDurationMs)) {
            parts.push(`总耗时 ${this.formatDuration(trace.totalDurationMs)}`);
        }
        return parts.join(" · ");
    }

    buildTraceOverview(trace) {
        const cards = [
            {
                label: "链路",
                value: this.traceIntentLabel(trace.intent),
            },
            {
                label: "开始时间",
                value: trace.startedAt ? this.formatDateTime(trace.startedAt, { withDate: false, withSeconds: true }) : "--",
            },
            {
                label: "结束时间",
                value: trace.completedAt ? this.formatDateTime(trace.completedAt, { withDate: false, withSeconds: true }) : "--",
            },
            {
                label: "总时长",
                value: Number.isFinite(trace.totalDurationMs) ? this.formatDuration(trace.totalDurationMs) : "--",
            },
        ];

        if (trace.retrieval) {
            const retrievalDurationMs = Number.isFinite(trace.timing?.retrieval_duration_ms)
                ? trace.timing.retrieval_duration_ms
                : (trace.retrieval.dense_latency_ms || 0) + (trace.retrieval.sparse_latency_ms || 0) + (trace.retrieval.rerank_latency_ms || 0);
            cards.push({
                label: "检索命中",
                value: `dense ${trace.retrieval.dense_hits || 0} / rerank ${trace.retrieval.rerank_hits || 0}`,
            });
            cards.push({
                label: "命中文档",
                value: Array.isArray(trace.retrieval.final_sources) && trace.retrieval.final_sources.length
                    ? this.truncate(trace.retrieval.final_sources.join(", "), 38)
                    : "--",
            });
            cards.push({
                label: "检索耗时",
                value: Number.isFinite(retrievalDurationMs) ? this.formatDuration(retrievalDurationMs) : "--",
            });
        }

        if (Number.isFinite(trace.timing?.llm_duration_ms)) {
            cards.push({
                label: "模型耗时",
                value: this.formatDuration(trace.timing.llm_duration_ms),
            });
        }

        if (Number.isFinite(trace.timing?.time_to_first_chunk_ms)) {
            cards.push({
                label: "首段可见",
                value: this.formatDuration(trace.timing.time_to_first_chunk_ms),
            });
        }

        return cards
            .map((card) => {
                return `
                    <div class="trace-stat">
                        <div class="trace-stat-label">${this.escapeHtml(card.label)}</div>
                        <div class="trace-stat-value">${this.escapeHtml(card.value)}</div>
                    </div>
                `;
            })
            .join("");
    }

    buildTraceHeaderLabel(trace) {
        const prefix = trace.intent ? this.traceIntentLabel(trace.intent) : trace.label || "执行轨迹";
        return `${prefix} · 分步骤回看`;
    }

    buildTraceMetaText(trace) {
        const parts = [];
        if (trace.startedAt) {
            parts.push(`开始 ${this.formatDateTime(trace.startedAt, { withDate: true, withSeconds: false })}`);
        }
        if (trace.completedAt) {
            parts.push(`完成 ${this.formatDateTime(trace.completedAt, { withDate: true, withSeconds: false })}`);
        }
        if (Number.isFinite(trace.totalDurationMs)) {
            parts.push(`总时长 ${this.formatDuration(trace.totalDurationMs)}`);
        }
        if (!parts.length && trace.reason) {
            parts.push(trace.reason);
        }
        return parts.join(" · ") || "点击展开执行步骤";
    }

    renderTraceEntry(step) {
        const timeParts = [];
        if (step.timestamp) {
            timeParts.push(this.formatDateTime(step.timestamp, { withDate: false, withSeconds: true }));
        }
        if (Number.isFinite(step.duration_ms)) {
            timeParts.push(this.formatDuration(step.duration_ms));
        }
        const time = timeParts.join(" 路 ") || "--";
        const detail = this.escapeHtml(step.detail || "").replace(/\n/g, "<br>");
        return `
            <div class="message-trace-entry ${this.escapeHtml(step.status || "info")}">
                <div class="message-trace-entry-top">
                    <div class="message-trace-entry-title">${this.escapeHtml(step.title || "执行步骤")}</div>
                    <div class="message-trace-entry-time">${this.escapeHtml(time)}</div>
                </div>
                <div class="message-trace-entry-detail">${detail}</div>
            </div>
        `;
    }

    traceIntentLabel(intent) {
        const mapping = {
            smalltalk: "轻量直答链路",
            simple_qa: "简单问答链路",
            knowledge_qa: "知识问答链路",
            aiops_diagnosis: "AIOps 诊断链路",
            unsupported: "边界控制链路",
        };
        return mapping[intent] || "执行链路";
    }

    focusTracePanel() {
        if (this.sidebarCollapsed) {
            this.toggleSidebar(false);
        }
        this.traceSection.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }

    async loadSystemStatus(forceRefresh = false) {
        if (!this.isAuthenticated) {
            this.renderSystemStatus(null);
            return;
        }
        if (!forceRefresh && this.systemStatusCache) {
            this.renderSystemStatus(this.systemStatusCache);
            return;
        }

        try {
            const response = await this.apiFetch("/system/status");
            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }
            const payload = await response.json();
            this.systemStatusCache = payload.data || null;
            this.renderSystemStatus(this.systemStatusCache);
        } catch (error) {
            console.error("读取系统状态失败:", error);
            this.renderSystemStatus(null);
            this.showNotification(error.message || "读取系统状态失败", "error");
        }
    }

    renderSystemStatus(data) {
        if (!data) {
            this.systemStatusEmpty.classList.remove("hidden");
            this.systemStatusContent.classList.add("hidden");
            this.systemStatusGrid.innerHTML = "";
            this.serviceStatusList.innerHTML = "";
            return;
        }

        this.systemStatusEmpty.classList.add("hidden");
        this.systemStatusContent.classList.remove("hidden");

        const cards = [
            { label: "服务版本", value: `${data.service?.name || "OpsPilot"} ${data.service?.version || "--"}` },
            { label: "浏览器访问地址", value: data.network?.access_url || "--" },
            { label: "LLM 模型", value: data.models?.llm || "--" },
            { label: "Embedding 模型", value: data.models?.embedding || "--" },
            { label: "Rerank 模型", value: data.models?.rerank || "--" },
            {
                label: "DashScope Key",
                value: data.providers?.dashscope?.configured
                    ? (data.providers?.dashscope?.masked_key || "已配置")
                    : "未配置",
            },
        ];

        this.systemStatusGrid.innerHTML = cards
            .map((card) => {
                return `
                    <div class="status-item">
                        <div class="trace-stat-label">${this.escapeHtml(card.label)}</div>
                        <div class="trace-stat-value">${this.escapeHtml(card.value)}</div>
                    </div>
                `;
            })
            .join("");

        const serviceEntries = Object.entries(data.services || {});
        this.serviceStatusList.innerHTML = serviceEntries
            .map(([serviceName, service]) => {
                const healthy = Boolean(service?.healthy);
                const extra = service?.url || service?.path || service?.address || "";
                return `
                    <div class="service-status-card ${healthy ? "healthy" : "unhealthy"}">
                        <div class="trace-stat-label">${this.escapeHtml(serviceName)}</div>
                        <div class="trace-stat-value">${this.escapeHtml(service?.message || "--")}</div>
                        <div class="trace-panel-meta">${this.escapeHtml(extra)}</div>
                    </div>
                `;
            })
            .join("");
    }

    async handleFileSelection(event) {
        const [file] = Array.from(event.target.files || []);
        if (!file) {
            return;
        }

        await this.uploadSelectedFile(file);
        this.fileInput.value = "";
    }

    async uploadSelectedFile(file) {
        if (!this.ensureOperatorPermission("上传知识文档")) {
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        this.setLoading(true, "正在上传文档", "OpsPilot 正在写入文件并构建检索索引。");
        try {
            const response = await this.apiFetch("/upload", {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error(await this.extractErrorMessage(response));
            }

            const payload = await response.json();
            const data = payload.data || {};
            const trace = this.buildUploadTrace(file.name, data.index_trace, data.size);
            this.setActiveTrace(trace);
            this.showNotification(`文档上传成功：${file.name}`, "success");
        } catch (error) {
            console.error("上传文档失败:", error);
            this.showNotification(error.message || "上传文档失败", "error");
        } finally {
            this.setLoading(false);
        }
    }

    buildUploadTrace(fileName, indexTrace, size) {
        const trace = this.createTraceSummary("文档索引链路", new Date().toISOString());
        this.addTraceStep(
            trace,
            this.createTraceStep("文件上传", `${fileName} · ${this.formatBytes(size || 0)}`, {
                phase: "upload",
                status: "success",
                timestamp: trace.startedAt,
            })
        );

        if (indexTrace?.stages?.length) {
            indexTrace.stages.forEach((stage) => {
                this.addTraceStep(
                    trace,
                    this.createTraceStep(stage.stage || "索引阶段", stage.message || "", {
                        phase: "index",
                        status: indexTrace.status === "failed" ? "error" : "success",
                    })
                );
            });
        } else if (indexTrace) {
            this.addTraceStep(
                trace,
                this.createTraceStep(
                    "索引结果",
                    `${indexTrace.status || "unknown"} · 分片 ${indexTrace.chunk_count || 0}`,
                    {
                        phase: "index",
                        status: indexTrace.status === "success" ? "success" : "error",
                        durationMs: indexTrace.duration_ms || null,
                    }
                )
            );
        }

        const timing = {
            request_started_at: trace.startedAt,
            assistant_started_at: trace.startedAt,
            assistant_completed_at: new Date().toISOString(),
            duration_ms: indexTrace?.duration_ms || null,
        };
        this.markTraceCompleted(trace, timing);
        return trace;
    }

    setLoading(visible, title = "正在处理请求", subtitle = "请稍候，OpsPilot 正在准备结果。") {
        if (!this.loadingOverlay) {
            return;
        }
        this.loadingOverlay.style.display = visible ? "flex" : "none";
        if (!visible) {
            return;
        }
        const text = this.loadingOverlay.querySelector(".loading-text");
        const subtext = this.loadingOverlay.querySelector(".loading-subtext");
        if (text) {
            text.textContent = title;
        }
        if (subtext) {
            subtext.textContent = subtitle;
        }
    }

    async runAiOpsRequest(assistantMessage) {
        assistantMessage.requestError = null;
        const response = await this.apiFetch("/aiops", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
            },
            body: JSON.stringify({
                session_id: this.sessionId,
            }),
        });

        if (!response.ok) {
            throw new Error(await this.extractErrorMessage(response));
        }

        await this.consumeSseStream(
            response,
            (payload) => this.handleAiOpsPayload(payload, assistantMessage, assistantMessage.traceSummary)
        );

        if (!assistantMessage.timing) {
            const fallbackTiming = this.buildFallbackTiming(assistantMessage.traceSummary);
            assistantMessage.timing = fallbackTiming;
            assistantMessage.timestamp = fallbackTiming.assistant_completed_at;
            this.markTraceCompleted(assistantMessage.traceSummary, fallbackTiming);
            this.updateMessageElement(assistantMessage, { highlight: true });
        }
    }

    showNotification(message, type = "info") {
        const notification = document.createElement("div");
        notification.className = "notification";
        notification.textContent = message;

        const palette = {
            success: "linear-gradient(135deg, #1f9d62 0%, #29b56f 100%)",
            error: "linear-gradient(135deg, #d14343 0%, #f06565 100%)",
            warning: "linear-gradient(135deg, #d97706 0%, #f59e0b 100%)",
            info: "linear-gradient(135deg, #0b57d0 0%, #2f6ce5 100%)",
        };
        notification.style.background = palette[type] || palette.info;

        document.body.appendChild(notification);
        window.setTimeout(() => {
            notification.remove();
        }, 3200);
    }

    renderMarkdown(content) {
        if (!content) {
            return "";
        }
        if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
            return this.escapeHtml(content).replace(/\n/g, "<br>");
        }
        try {
            return DOMPurify.sanitize(marked.parse(content), {
                USE_PROFILES: { html: true },
            });
        } catch (error) {
            console.error("Markdown 渲染失败:", error);
            return this.escapeHtml(content).replace(/\n/g, "<br>");
        }
    }

    highlightCodeBlocks(container) {
        if (typeof hljs === "undefined" || !container) {
            return;
        }
        container.querySelectorAll("pre code").forEach((block) => {
            if (block.dataset.highlighted === "true") {
                return;
            }
            try {
                hljs.highlightElement(block);
                block.dataset.highlighted = "true";
            } catch (error) {
                console.error("代码高亮失败:", error);
            }
        });
    }

    escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    truncate(value, maxLength = 24) {
        const text = String(value || "");
        return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
    }

    formatBytes(size) {
        if (!Number.isFinite(size) || size <= 0) {
            return "0 B";
        }
        const units = ["B", "KB", "MB", "GB"];
        let value = size;
        let index = 0;
        while (value >= 1024 && index < units.length - 1) {
            value /= 1024;
            index += 1;
        }
        return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
    }

    formatDuration(durationMs) {
        if (!Number.isFinite(durationMs) || durationMs < 0) {
            return "--";
        }
        if (durationMs < 1000) {
            return `${durationMs}ms`;
        }
        if (durationMs < 60_000) {
            const seconds = durationMs / 1000;
            return `${seconds >= 10 ? seconds.toFixed(0) : seconds.toFixed(1)}s`;
        }
        const minutes = Math.floor(durationMs / 60_000);
        const seconds = Math.round((durationMs % 60_000) / 1000);
        return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
    }

    formatDateTime(value, options = {}) {
        if (!value) {
            return "--";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        const withDate = options.withDate !== false;
        const withSeconds = Boolean(options.withSeconds);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        const hour = String(date.getHours()).padStart(2, "0");
        const minute = String(date.getMinutes()).padStart(2, "0");
        const second = String(date.getSeconds()).padStart(2, "0");

        const timePart = `${hour}:${minute}${withSeconds ? `:${second}` : ""}`;
        return withDate ? `${year}-${month}-${day} ${timePart}` : timePart;
    }

    generateSessionId() {
        return `session_${this.generateId("s")}`;
    }

    generateId(prefix = "id") {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return `${prefix}_${window.crypto.randomUUID().replace(/-/g, "").slice(0, 12)}_${Date.now()}`;
        }
        return `${prefix}_${Math.random().toString(36).slice(2, 10)}_${Date.now()}`;
    }

    async extractErrorMessage(response) {
        try {
            const payload = await response.clone().json();
            if (typeof payload?.detail === "string") {
                return payload.detail;
            }
            if (typeof payload?.message === "string" && payload.message !== "success") {
                return payload.message;
            }
            if (typeof payload?.data?.errorMessage === "string") {
                return payload.data.errorMessage;
            }
        } catch (error) {
            // ignore parse error
        }
        return `请求失败 (${response.status})`;
    }
}

window.addEventListener("DOMContentLoaded", () => {
    new OpsPilotApp();
});
