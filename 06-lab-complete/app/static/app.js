// App JS - E-commerce Agent Studio

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const providerSelect = document.getElementById("llm-provider");
    const modelSelect = document.getElementById("llm-model");
    const apiKeyInput = document.getElementById("api-key");
    const apiKeyGroup = document.getElementById("api-key-group");
    const toggleKeyBtn = document.getElementById("toggle-key");
    
    const modeChatbot = document.getElementById("mode-chatbot");
    const modeAgent = document.getElementById("mode-agent");
    
    const chatViewport = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const clearChatBtn = document.getElementById("clear-chat");
    const suggestChips = document.querySelectorAll(".suggest-chip");
    
    // Telemetry DOM
    const metricLatency = document.getElementById("metric-latency");
    const metricCost = document.getElementById("metric-cost");
    const metricTokens = document.getElementById("metric-tokens");
    const metricTokenSplit = document.getElementById("metric-token-split");
    
    // Inspector DOM
    const stepCounterBadge = document.getElementById("step-counter-badge");
    const stepsPlaceholder = document.getElementById("steps-placeholder");
    const stepsTimeline = document.getElementById("steps-timeline");
    
    // Toast DOM
    const errorToast = document.getElementById("error-toast");
    const errorToastMessage = document.getElementById("error-toast-message");
    const closeToastBtn = document.getElementById("close-toast");

    // LLM Models Mapping
    const providerModels = {
        openai: [
            { value: "gpt-4o", label: "gpt-4o (Premium)" },
            { value: "gpt-4o-mini", label: "gpt-4o-mini (Fast & Cheap)" },
            { value: "gpt-3.5-turbo", label: "gpt-3.5-turbo (Legacy)" }
        ],
        google: [
            { value: "gemini-2.0-flash", label: "gemini-2.0-flash (Recommended)" },
            { value: "gemini-2.5-flash", label: "gemini-2.5-flash (Fast)" },
            { value: "gemini-flash-latest", label: "gemini-flash-latest" },
            { value: "gemini-pro-latest", label: "gemini-pro-latest" }
        ],
        local: [
            { value: "Phi-3-mini-4k-instruct-q4.gguf", label: "Phi-3 Mini 4K Instruct" }
        ]
    };

    // State parameters for Benchmark comparison
    const benchmarkData = {
        chatbot: { latency: 0, cost: 0, tokens: 0, count: 0 },
        agent: { latency: 0, cost: 0, tokens: 0, count: 0 }
    };

    // Initialize Chart.js
    const ctx = document.getElementById("telemetryChart").getContext("2d");
    
    // Create Neon Gradient colors for the chart
    const cyanGlow = ctx.createLinearGradient(0, 0, 0, 150);
    cyanGlow.addColorStop(0, "rgba(0, 240, 255, 0.8)");
    cyanGlow.addColorStop(1, "rgba(0, 240, 255, 0.1)");
    
    const purpleGlow = ctx.createLinearGradient(0, 0, 0, 150);
    purpleGlow.addColorStop(0, "rgba(157, 78, 221, 0.8)");
    purpleGlow.addColorStop(1, "rgba(157, 78, 221, 0.1)");

    const telemetryChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Latency (ms)", "Tokens Used"],
            datasets: [
                {
                    label: "Baseline Chatbot",
                    data: [0, 0],
                    backgroundColor: purpleGlow,
                    borderColor: "#9d4edd",
                    borderWidth: 1,
                    borderRadius: 6,
                },
                {
                    label: "ReAct Agent",
                    data: [0, 0],
                    backgroundColor: cyanGlow,
                    borderColor: "#00f0ff",
                    borderWidth: 1,
                    borderRadius: 6,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: {
                        color: "rgba(255, 255, 255, 0.05)"
                    },
                    ticks: {
                        color: "#adb5bd",
                        font: { family: "'Inter', sans-serif", size: 10 }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: "#adb5bd",
                        font: { family: "'Outfit', sans-serif", size: 11 }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: "#adb5bd",
                        font: { family: "'Inter', sans-serif", size: 11 },
                        boxWidth: 12
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(13, 17, 30, 0.9)",
                    titleFont: { family: "'Outfit', sans-serif", size: 12 },
                    bodyFont: { family: "'Inter', sans-serif", size: 11 },
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    borderWidth: 1
                }
            }
        }
    });

    // Populate Models based on Provider
    function updateModelsDropdown() {
        const provider = providerSelect.value;
        const models = providerModels[provider] || [];
        
        modelSelect.innerHTML = "";
        models.forEach(model => {
            const option = document.createElement("option");
            option.value = model.value;
            option.textContent = model.label;
            modelSelect.appendChild(option);
        });

        // Hide/Show API key override group
        if (provider === "local") {
            apiKeyGroup.style.display = "none";
        } else {
            apiKeyGroup.style.display = "flex";
            // Retrieve key from localStorage if saved
            const savedKey = localStorage.getItem(`api_key_${provider}`);
            if (savedKey) {
                apiKeyInput.value = savedKey;
            } else {
                apiKeyInput.value = "";
            }
        }
    }

    // Toggle API Key visibility
    toggleKeyBtn.addEventListener("click", () => {
        if (apiKeyInput.type === "password") {
            apiKeyInput.type = "text";
            toggleKeyBtn.classList.replace("fa-eye-slash", "fa-eye");
        } else {
            apiKeyInput.type = "password";
            toggleKeyBtn.classList.replace("fa-eye", "fa-eye-slash");
        }
    });

    // Store API key on change
    apiKeyInput.addEventListener("input", () => {
        const provider = providerSelect.value;
        if (provider !== "local") {
            localStorage.setItem(`api_key_${provider}`, apiKeyInput.value);
        }
    });

    providerSelect.addEventListener("change", updateModelsDropdown);
    
    // Auto grow chat input textarea
    chatInput.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
    });

    // Send Message
    async function sendMessage() {
        const queryText = chatInput.value.trim();
        if (!queryText) return;

        // Reset text input height
        chatInput.value = "";
        chatInput.style.height = "44px";
        
        // Append user bubble
        appendMessageBubble("user", queryText);
        
        // Disable input during request
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Show typing indicator
        const typingIndicator = appendTypingIndicator();

        const provider = providerSelect.value;
        const model = modelSelect.value;
        const mode = modeChatbot.checked ? "chatbot" : "agent";
        const apiKey = apiKeyInput.value.trim();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: queryText,
                    provider: provider,
                    model: model,
                    mode: mode,
                    api_key: apiKey || null
                })
            });

            // Check if status code is not 200
            const data = await response.json();
            
            // Remove typing loader bubble
            typingIndicator.remove();

            if (!response.ok || data.error) {
                showToast(data.message || data.error || "An unknown backend error occurred.");
                return;
            }

            // Append assistant response bubble
            appendMessageBubble("assistant", data.answer, mode === "agent");

            // Process telemetry metrics
            updateTelemetryMetrics(data.metrics);

            // Process step inspector
            updateMindInspector(data.steps, mode === "agent");

            // Update Benchmark graph statistics
            updateBenchmarkChart(mode, data.metrics);

        } catch (error) {
            typingIndicator.remove();
            showToast("Failed to connect to the backend server. Please verify FastAPI is running.");
            console.error("Network Error: ", error);
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
            scrollToBottom();
        }
    }

    // Append Message Bubble to UI
    function appendMessageBubble(role, content, isAgentAnswer = false) {
        const bubble = document.createElement("div");
        bubble.className = `message ${role}-msg`;
        if (isAgentAnswer) {
            bubble.classList.add("agent-answer");
        }

        const avatarIcon = role === "user" 
            ? "fa-user" 
            : (isAgentAnswer ? "fa-robot text-green" : "fa-comment-dots text-cyan");

        // Format code/markdown blocks or lists briefly
        const formattedContent = formatContent(content);

        bubble.innerHTML = `
            <div class="msg-avatar">
                <i class="fa-solid ${avatarIcon}"></i>
            </div>
            <div class="msg-content">
                ${formattedContent}
            </div>
        `;

        chatViewport.appendChild(bubble);
        scrollToBottom();
    }

    // Simple formatting for lists and bold styling in replies
    function formatContent(text) {
        if (!text) return "";
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Simple line break support
        formatted = formatted.replace(/\n/g, "<br>");
        return formatted;
    }

    // Append Typing Indicator
    function appendTypingIndicator() {
        const bubble = document.createElement("div");
        bubble.className = "message assistant-msg typing-msg";
        bubble.innerHTML = `
            <div class="msg-avatar">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <div class="msg-content" style="padding: 12px 20px; color: var(--text-muted);">
                Thinking...
            </div>
        `;
        chatViewport.appendChild(bubble);
        scrollToBottom();
        return bubble;
    }

    // Update Telemetry Panel
    function updateTelemetryMetrics(metrics) {
        if (!metrics) return;
        
        // Latency
        metricLatency.innerHTML = `${metrics.latency_ms}<span class="metric-unit">ms</span>`;
        
        // Cost
        const costStr = metrics.cost_usd !== undefined ? `$${metrics.cost_usd.toFixed(6)}` : "$0.000000";
        metricCost.textContent = costStr;

        // Tokens
        metricTokens.textContent = metrics.total_tokens || 0;
        metricTokenSplit.textContent = `${metrics.prompt_tokens || 0} In / ${metrics.completion_tokens || 0} Out`;
    }

    // Update Mind Inspector (ReAct Steps Accordion)
    function updateMindInspector(steps, isAgentMode) {
        stepsTimeline.innerHTML = "";
        
        if (!isAgentMode || !steps || steps.length === 0) {
            stepCounterBadge.textContent = "0 steps";
            stepsPlaceholder.style.display = "flex";
            stepsTimeline.style.display = "none";
            return;
        }

        // Setup elements
        stepsPlaceholder.style.display = "none";
        stepsTimeline.style.display = "flex";
        stepCounterBadge.textContent = `${steps.length} step${steps.length > 1 ? 's' : ''}`;

        steps.forEach((step, index) => {
            const isLast = index === steps.length - 1;
            const node = document.createElement("div");
            node.className = "step-node";

            // Format thought snippet for header display
            const thoughtPreview = step.thought 
                ? (step.thought.length > 50 ? step.thought.substring(0, 50) + "..." : step.thought)
                : "Reasoning...";

            // Create step accordion card
            const card = document.createElement("div");
            card.className = "step-accordion";
            // Expand first step by default
            if (index === 0) {
                card.classList.add("active");
            }

            card.innerHTML = `
                <div class="accordion-header">
                    <div class="accordion-title">
                        <span class="step-badge">${step.step || (index + 1)}</span>
                        <span class="thought-snippet">${thoughtPreview}</span>
                    </div>
                    <i class="fa-solid fa-chevron-down chevron"></i>
                </div>
                <div class="accordion-content" style="${index === 0 ? 'max-height: 500px;' : ''}">
                    <div class="accordion-inner">
                        <div class="thought-block">
                            <span class="label">Thought</span>
                            <p>${step.thought || 'None'}</p>
                        </div>
                        <div class="action-block">
                            <span class="label">Action Called</span>
                            <div class="code-box">${step.action || 'None'}</div>
                        </div>
                        <div class="observation-block">
                            <span class="label">Observation</span>
                            <div class="obs-box">${step.observation || 'None'}</div>
                        </div>
                    </div>
                </div>
            `;

            // Setup Accordion Toggle Logic
            const header = card.querySelector(".accordion-header");
            const content = card.querySelector(".accordion-content");
            
            header.addEventListener("click", () => {
                const isActive = card.classList.contains("active");
                
                // Toggle active state
                if (isActive) {
                    card.classList.remove("active");
                    content.style.maxHeight = "0px";
                } else {
                    card.classList.add("active");
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            });

            node.appendChild(card);
            stepsTimeline.appendChild(node);
        });
    }

    // Update Benchmark Data & Chart
    function updateBenchmarkChart(mode, metrics) {
        if (!metrics) return;

        const target = benchmarkData[mode];
        target.count += 1;
        // Average rolling calculation
        target.latency = Math.round(((target.latency * (target.count - 1)) + metrics.latency_ms) / target.count);
        target.tokens = Math.round(((target.tokens * (target.count - 1)) + metrics.total_tokens) / target.count);
        target.cost = ((target.cost * (target.count - 1)) + metrics.cost_usd) / target.count;

        // Update datasets (Dataset 0: Chatbot, Dataset 1: Agent)
        telemetryChart.data.datasets[0].data = [
            benchmarkData.chatbot.latency, 
            benchmarkData.chatbot.tokens
        ];
        telemetryChart.data.datasets[1].data = [
            benchmarkData.agent.latency, 
            benchmarkData.agent.tokens
        ];
        
        telemetryChart.update();
    }

    // Helper Scroll Viewport
    function scrollToBottom() {
        chatViewport.scrollTop = chatViewport.scrollHeight;
    }

    // Trigger Notification Toast
    function showToast(message) {
        errorToastMessage.textContent = message;
        errorToast.classList.add("show");

        // Autohide toast after 5s
        setTimeout(() => {
            errorToast.classList.remove("show");
        }, 6000);
    }

    // Event Handlers
    closeToastBtn.addEventListener("click", () => {
        errorToast.classList.remove("show");
    });

    sendBtn.addEventListener("click", sendMessage);

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            // Check for ctrl/meta click or standard
            e.preventDefault();
            sendMessage();
        }
    });

    clearChatBtn.addEventListener("click", () => {
        // Clear chat area
        chatViewport.innerHTML = `
            <div class="message system-msg">
                <div class="msg-avatar"><i class="fa-solid fa-circle-info"></i></div>
                <div class="msg-content">
                    <p><strong>Chat history cleared.</strong></p>
                    <p>Select your mode (Baseline Chatbot vs ReAct Agent) and enter a prompt to begin testing.</p>
                </div>
            </div>
        `;
        
        // Reset telemetry values
        metricLatency.innerHTML = `0<span class="metric-unit">ms</span>`;
        metricCost.textContent = "$0.000000";
        metricTokens.textContent = "0";
        metricTokenSplit.textContent = "0 In / 0 Out";

        // Reset steps
        updateMindInspector([], false);
    });

    // Suggested queries chip click
    suggestChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            chatInput.value = query;
            chatInput.style.height = "auto";
            chatInput.style.height = (chatInput.scrollHeight) + "px";
            chatInput.focus();
        });
    });

    // Initialize values
    updateModelsDropdown();
});
