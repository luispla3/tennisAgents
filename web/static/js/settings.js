// Settings modal functionality
document.addEventListener('DOMContentLoaded', function() {
    const settingsButton = document.getElementById('settingsButton');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsModal = document.getElementById('closeSettingsModal');
    const cancelSettings = document.getElementById('cancelSettings');
    const settingsForm = document.getElementById('settingsForm');
    const walletBalanceInput = document.getElementById('walletBalanceInput');
    const walletBalanceDisplay = document.getElementById('walletBalance');
    const llmProviderSelect = document.getElementById('llmProvider');
    const shallowThinkerSelect = document.getElementById('shallowThinker');
    const deepThinkerSelect = document.getElementById('deepThinker');
    const predictButton = document.getElementById('predictButton');

    // Analysis Modal Elements
    const analysisModal = document.getElementById('analysisModal');
    const closeAnalysisModal = document.getElementById('closeAnalysisModal');
    const analysisStatus = document.getElementById('analysisStatus');
    const activeAgents = document.getElementById('activeAgents');
    const analysisLogs = document.getElementById('analysisLogs');
    const analysisReports = document.getElementById('analysisReports');
    const analysisTitle = document.getElementById('analysisTitle');
    
    function closeAnalysis() {
        if (analysisModal) {
            analysisModal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
    
    if(closeAnalysisModal) {
        closeAnalysisModal.addEventListener('click', closeAnalysis);
        if (analysisModal) {
            analysisModal.querySelector('.settings-modal-backdrop').addEventListener('click', closeAnalysis);
        }
    }

    // LLM Model options by provider
    const SHALLOW_AGENT_OPTIONS = {
        openai: [
            { display: "GPT-4o-mini - Fast and efficient for quick tasks", value: "gpt-4o-mini" },
            { display: "GPT-4.1-nano - Ultra-lightweight model for basic operations", value: "gpt-4.1-nano" },
            { display: "GPT-4.1-mini - Compact model with good performance", value: "gpt-4.1-mini" },
            { display: "GPT-4o - Standard model with solid capabilities", value: "gpt-4o" },
            { display: "GPT-5-mini - Next generation model with enhanced capabilities", value: "gpt-5-mini" },
            { display: "GPT-5-nano - Ultra-lightweight model for basic operations", value: "gpt-5-nano" }
        ],
        anthropic: [
            { display: "Claude Haiku 3.5 - Fast inference and standard capabilities", value: "claude-3-5-haiku-latest" },
            { display: "Claude Sonnet 3.5 - Highly capable standard model", value: "claude-3-5-sonnet-latest" },
            { display: "Claude Sonnet 3.7 - Exceptional hybrid reasoning and agentic capabilities", value: "claude-3-7-sonnet-latest" },
            { display: "Claude Sonnet 4 - High performance and excellent reasoning", value: "claude-sonnet-4-0" }
        ],
        google: [
            { display: "Gemini 2.0 Flash-Lite - Cost efficiency and low latency (RECOMMENDED)", value: "gemini-2.0-flash-lite" },
            { display: "Gemini 2.0 Flash - Next generation features, speed, and thinking", value: "gemini-2.0-flash" },
            { display: "Gemini 2.5 Flash - Adaptive thinking, cost efficiency", value: "gemini-2.5-flash-preview-05-20" }
        ],
        openrouter: [
            { display: "Meta: Llama 4 Scout", value: "meta-llama/llama-4-scout:free" },
            { display: "Meta: Llama 3.3 8B Instruct - A lightweight and ultra-fast variant of Llama 3.3 70B", value: "meta-llama/llama-3.3-8b-instruct:free" },
            { display: "google/gemini-2.0-flash-exp:free - Gemini Flash 2.0 offers a significantly faster time to first token", value: "google/gemini-2.0-flash-exp:free" }
        ],
        ollama: [
            { display: "llama3.1 local", value: "llama3.1" },
            { display: "llama3.2 local", value: "llama3.2" },
            { display: "gpt oss 20b", value: "gpt-oss:20b" }
        ]
    };

    const DEEP_AGENT_OPTIONS = {
        openai: [
            { display: "GPT-4.1-nano - Ultra-lightweight model for basic operations", value: "gpt-4.1-nano" },
            { display: "GPT-4.1-mini - Compact model with good performance", value: "gpt-4.1-mini" },
            { display: "GPT-4o - Standard model with solid capabilities", value: "gpt-4o" },
            { display: "o4-mini - Specialized reasoning model (compact)", value: "o4-mini" },
            { display: "o3-mini - Advanced reasoning model (lightweight)", value: "o3-mini" },
            { display: "o3 - Full advanced reasoning model", value: "o3" },
            { display: "o1 - Premier reasoning and problem-solving model", value: "o1" },
            { display: "GPT-5 - Next generation model with enhanced capabilities", value: "gpt-5" }
        ],
        anthropic: [
            { display: "Claude Haiku 3.5 - Fast inference and standard capabilities", value: "claude-3-5-haiku-latest" },
            { display: "Claude Sonnet 3.5 - Highly capable standard model", value: "claude-3-5-sonnet-latest" },
            { display: "Claude Sonnet 3.7 - Exceptional hybrid reasoning and agentic capabilities", value: "claude-3-7-sonnet-latest" },
            { display: "Claude Sonnet 4 - High performance and excellent reasoning", value: "claude-sonnet-4-0" },
            { display: "Claude Opus 4 - Most powerful Anthropic model", value: "claude-opus-4-0" }
        ],
        google: [
            { display: "Gemini 2.0 Flash-Lite - Cost efficiency and low latency (RECOMMENDED)", value: "gemini-2.0-flash-lite" },
            { display: "Gemini 2.0 Flash - Next generation features, speed, and thinking", value: "gemini-2.0-flash" },
            { display: "Gemini 2.5 Flash - Adaptive thinking, cost efficiency", value: "gemini-2.5-flash-preview-05-20" },
            { display: "Gemini 2.5 Pro", value: "gemini-2.5-pro-preview-06-05" }
        ],
        openrouter: [
            { display: "DeepSeek V3 - a 685B-parameter, mixture-of-experts model", value: "deepseek/deepseek-chat-v3-0324:free" },
            { display: "Deepseek - latest iteration of the flagship chat model family from the DeepSeek team.", value: "deepseek/deepseek-chat-v3-0324:free" }
        ],
        ollama: [
            { display: "llama3.1 local", value: "llama3.1" },
            { display: "qwen3", value: "qwen3" },
            { display: "gpt oss 20b", value: "gpt-oss:20b" }
        ]
    };

    // URL mapping for backend
    const BACKEND_URLS = {
        openai: "https://api.openai.com/v1",
        anthropic: "https://api.anthropic.com/",
        google: "https://generativelanguage.googleapis.com/v1",
        openrouter: "https://openrouter.ai/api/v1",
        ollama: "http://localhost:11434/v1"
    };

    // Load saved settings from localStorage
    function loadSettings() {
        const savedSettings = localStorage.getItem('tennisAgentsSettings');
        if (savedSettings) {
            try {
                const settings = JSON.parse(savedSettings);
                
                // Load wallet balance
                if (settings.walletBalance !== undefined && walletBalanceInput) {
                    walletBalanceInput.value = settings.walletBalance;
                    updateWalletDisplay(settings.walletBalance);
                }
                
                // Load analysts
                if (settings.analysts && Array.isArray(settings.analysts)) {
                    document.querySelectorAll('input[name="analysts"]').forEach(checkbox => {
                        checkbox.checked = settings.analysts.includes(checkbox.value);
                    });
                }
                
                // Load research depth
                if (settings.researchDepth) {
                    const researchDepthEl = document.getElementById('researchDepth');
                    if (researchDepthEl) {
                        researchDepthEl.value = settings.researchDepth;
                    }
                }
                
                // Load LLM provider
                if (settings.llmProvider && llmProviderSelect) {
                    llmProviderSelect.value = settings.llmProvider;
                    updateModelOptions(settings.llmProvider);
                }
                
                // Load thinking agents
                if (settings.shallowThinker && shallowThinkerSelect) {
                    shallowThinkerSelect.value = settings.shallowThinker;
                }
                if (settings.deepThinker && deepThinkerSelect) {
                    deepThinkerSelect.value = settings.deepThinker;
                }
                
                // Load match info if available
                if (settings.player1) {
                    const player1El = document.getElementById('player1');
                    if (player1El) player1El.value = settings.player1;
                }
                if (settings.player2) {
                    const player2El = document.getElementById('player2');
                    if (player2El) player2El.value = settings.player2;
                }
                if (settings.tournament) {
                    const tournamentEl = document.getElementById('tournament');
                    if (tournamentEl) tournamentEl.value = settings.tournament;
                }
                if (settings.analysisDate) {
                    const analysisDateEl = document.getElementById('analysisDate');
                    if (analysisDateEl) analysisDateEl.value = settings.analysisDate;
                }
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
    }

    // Helper function to order analysts correctly
    function orderAnalysts(selectedAnalysts) {
        const correctOrder = ['news', 'players', 'social', 'tournament', 'weather', 'match_live', 'odds'];
        return correctOrder.filter(analyst => selectedAnalysts.includes(analyst));
    }

    // Save settings to localStorage
    function saveSettings() {
        // Automatically determine backend URL based on selected provider
        const backendUrl = BACKEND_URLS[llmProviderSelect.value] || BACKEND_URLS.openai;
        
            const settings = {
            walletBalance: parseFloat(walletBalanceInput.value) || 0,
            // Ensure analysts are in the correct execution order
            analysts: orderAnalysts(Array.from(document.querySelectorAll('input[name="analysts"]:checked')).map(cb => cb.value)),
            researchDepth: parseInt(document.getElementById('researchDepth').value),
            llmProvider: llmProviderSelect.value,
            backendUrl: backendUrl, // Automatically set based on provider
            shallowThinker: shallowThinkerSelect.value,
            deepThinker: deepThinkerSelect.value,
            player1: document.getElementById('player1').value,
            player2: document.getElementById('player2').value,
            tournament: document.getElementById('tournament').value,
            analysisDate: document.getElementById('analysisDate').value
        };
        
        localStorage.setItem('tennisAgentsSettings', JSON.stringify(settings));
        return settings;
    }

    // Update wallet display
    function updateWalletDisplay(balance) {
        const balanceElement = document.getElementById('walletAmountDisplay');
        if (balanceElement) {
            balanceElement.textContent = `${parseFloat(balance || 0).toFixed(2)} €`;
        }
    }

    // Update model options based on provider
    function updateModelOptions(provider) {
        const shallowOptions = SHALLOW_AGENT_OPTIONS[provider] || [];
        const deepOptions = DEEP_AGENT_OPTIONS[provider] || [];
        
        // Clear existing options
        shallowThinkerSelect.innerHTML = '';
        deepThinkerSelect.innerHTML = '';
        
        // Add shallow options
        shallowOptions.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.value;
            optionElement.textContent = option.display;
            shallowThinkerSelect.appendChild(optionElement);
        });
        
        // Add deep options
        deepOptions.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.value;
            optionElement.textContent = option.display;
            deepThinkerSelect.appendChild(optionElement);
        });
        
        // Select first option if available
        if (shallowOptions.length > 0) {
            shallowThinkerSelect.value = shallowOptions[0].value;
        }
        if (deepOptions.length > 0) {
            deepThinkerSelect.value = deepOptions[0].value;
        }
    }

    // Open settings modal
    function openSettingsModal() {
        settingsModal.classList.add('active');
        document.body.style.overflow = 'hidden';
        loadSettings();
    }

    // Close settings modal
    function closeModal() {
        settingsModal.classList.remove('active');
        document.body.style.overflow = '';
    }

    // Event listeners
    settingsButton.addEventListener('click', openSettingsModal);
    closeSettingsModal.addEventListener('click', closeModal);
    cancelSettings.addEventListener('click', closeModal);
    
    // Close on backdrop click
    settingsModal.querySelector('.settings-modal-backdrop').addEventListener('click', closeModal);
    
    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && settingsModal.classList.contains('active')) {
            closeModal();
        }
    });

    // Handle form submission
    settingsForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const settings = saveSettings();
        updateWalletDisplay(settings.walletBalance);
        closeModal();
        
        // Show success message (optional)
        console.log('Settings saved:', settings);
    });

    // Handle LLM provider change
    llmProviderSelect.addEventListener('change', function() {
        const provider = this.value;
        updateModelOptions(provider);
    });

    // Handle wallet balance input change
    walletBalanceInput.addEventListener('input', function() {
        updateWalletDisplay(this.value);
    });

    // Handle predict button click
    if (predictButton) {
        predictButton.addEventListener('click', async function() {
            // Save settings before predicting
            const settings = saveSettings();
            console.log('Predicting with settings:', settings);
            
            closeModal(); // Close settings modal
            
            // Open Analysis Modal
            if (analysisModal) {
                analysisModal.classList.add('active');
                document.body.style.overflow = 'hidden';
                
                // Reset UI
                analysisStatus.innerHTML = `
                    <div class="loading-spinner" style="width: 20px; height: 20px; border-width: 2px;"></div>
                    <span>Initializing system...</span>
                `;
                analysisStatus.style.background = 'rgba(34, 197, 94, 0.1)';
                analysisStatus.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                analysisStatus.style.color = '#22c55e';
                
                activeAgents.innerHTML = '';
                analysisLogs.innerHTML = '';
                analysisReports.innerHTML = `
                    <div style="text-align: center; color: var(--text-secondary); padding-top: 50px;">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="opacity: 0.5; margin-bottom: 10px;">
                            <path d="M14 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V8L14 2Z"/>
                            <path d="M14 2V8H20"/>
                            <path d="M16 13H8"/>
                            <path d="M16 17H8"/>
                            <path d="M10 9H8"/>
                        </svg>
                        <p>Reports will appear here as they are generated...</p>
                    </div>
                `;
                
                // Initialize agents badges
                const allAgents = [
                    "News Analyst", "Odds Analyst", "Players Analyst", "Social Analyst", 
                    "Tournament Analyst", "Weather Analyst", "Match Live Analyst",
                    "Aggressive Analyst", "Safe Analyst", "Neutral Analyst", "Expected Analyst"
                ];
                
                // Filter allAgents to show relevant ones (selected + risk managers)
                // First, determine which analysts are selected
                const selectedAnalysts = settings.analysts.map(a => {
                    // Convert "news" to "News Analyst"
                    return a.charAt(0).toUpperCase() + a.slice(1).replace('_', ' ') + " Analyst";
                });
                
                const agentsToShow = allAgents.filter(a => {
                    if (a.includes("Risk") || ["Aggressive Analyst", "Safe Analyst", "Neutral Analyst", "Expected Analyst"].includes(a)) return true;
                    return selectedAnalysts.includes(a);
                });

                agentsToShow.forEach(agent => {
                    const badge = document.createElement('div');
                    badge.id = `badge-${agent.replace(/\s+/g, '-')}`;
                    badge.className = 'agent-badge';
                    badge.style.cssText = `
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 500;
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border-color);
                        color: var(--text-secondary);
                        transition: all 0.3s ease;
                        opacity: 0.5;
                    `;
                    badge.textContent = agent;
                    activeAgents.appendChild(badge);
                });

                try {
                    const response = await fetch('/api/run-analysis', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            player1: settings.player1,
                            player2: settings.player2,
                            tournament: settings.tournament,
                            analysis_date: settings.analysisDate,
                            wallet_balance: settings.walletBalance,
                            analysts: settings.analysts,
                            research_depth: settings.researchDepth,
                            llm_provider: settings.llmProvider,
                            shallow_thinker: settings.shallowThinker,
                            deep_thinker: settings.deepThinker,
                            backend_url: settings.backendUrl
                        })
                    });

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        // Handle the last line which might be incomplete
                        // If we are done, processing the buffer is fine, but in loop we might split mid-json
                        // Actually buffer logic:
                        // If line ends with \n it's a full line. If not, it's partial.
                        // Simple split logic:
                        // keep the last part in buffer if it doesn't end with newline?
                        // The split removes newlines.
                        
                        // Better logic:
                        // lines = (previous_buffer + new_chunk).split('\n')
                        // process all except last one, set buffer = last one
                        
                        // Re-implement buffer logic correctly:
                        // We appended to buffer before split, so lines contains everything
                        buffer = lines.pop(); 
                        
                        for (const line of lines) {
                            if (!line.trim()) continue;
                            try {
                                const event = JSON.parse(line);
                                handleAnalysisEvent(event);
                            } catch (e) {
                                console.error('Error parsing event:', e, line);
                            }
                        }
                    }
                    
                    // Process any remaining buffer if valid json
                    if (buffer && buffer.trim()) {
                         try {
                            const event = JSON.parse(buffer);
                            handleAnalysisEvent(event);
                        } catch (e) {
                            console.error('Error parsing final buffer:', e, buffer);
                        }
                    }

                } catch (error) {
                    console.error('Analysis error:', error);
                    analysisStatus.innerHTML = `
                        <span style="color: #ef4444;">Error: ${error.message}</span>
                    `;
                    analysisStatus.style.borderColor = '#ef4444';
                    analysisStatus.style.background = 'rgba(239, 68, 68, 0.1)';
                }
            } else {
                alert('Error: Analysis modal not found');
            }
        });
    }

    function handleAnalysisEvent(event) {
        const timestamp = new Date().toLocaleTimeString();
        
        if (event.type === 'status') {
            const message = event.data.message;
            const step = event.data.step;
            
            if (step === 'completed') {
                analysisStatus.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 6L9 17L4 12"/>
                    </svg>
                    <span>${message}</span>
                `;
            } else {
                analysisStatus.innerHTML = `
                    <div class="loading-spinner" style="width: 20px; height: 20px; border-width: 2px;"></div>
                    <span>${message}</span>
                `;
            }
        }
        else if (event.type === 'log') {
            const { type, content } = event.data;
            const logEntry = document.createElement('div');
            logEntry.style.marginBottom = '5px';
            logEntry.style.borderBottom = '1px solid #222';
            logEntry.style.paddingBottom = '5px';
            
            let color = '#a0a0a0';
            if (type === 'Reasoning') color = '#60a5fa'; // Blue
            if (type === 'System') color = '#4ade80'; // Green
            if (type === 'Tool Call') color = '#f472b6'; // Pink
            
            logEntry.innerHTML = `
                <span style="color: #666;">[${timestamp}]</span>
                <span style="color: ${color}; font-weight: bold;">[${type}]</span>
                <span style="color: #ddd;">${content}</span>
            `;
            
            analysisLogs.appendChild(logEntry);
            analysisLogs.scrollTop = analysisLogs.scrollHeight;
        }
        else if (event.type === 'tool_call') {
            const { name, args } = event.data;
             const logEntry = document.createElement('div');
            logEntry.style.marginBottom = '5px';
            logEntry.style.borderBottom = '1px solid #222';
            logEntry.style.paddingBottom = '5px';
            
            logEntry.innerHTML = `
                <span style="color: #666;">[${timestamp}]</span>
                <span style="color: #f472b6; font-weight: bold;">[Tool Call]</span>
                <span style="color: #ddd;">${name}(${args.substring(0, 100)}${args.length > 100 ? '...' : ''})</span>
            `;
            analysisLogs.appendChild(logEntry);
            analysisLogs.scrollTop = analysisLogs.scrollHeight;
        }
        else if (event.type === 'agent_status') {
            const { agent, status } = event.data;
            const badgeId = `badge-${agent.replace(/\s+/g, '-')}`;
            const badge = document.getElementById(badgeId);
            
            if (badge) {
                if (status === 'completed') {
                    badge.style.opacity = '1';
                    badge.style.background = 'rgba(34, 197, 94, 0.2)';
                    badge.style.borderColor = '#22c55e';
                    badge.style.color = '#22c55e';
                } else if (status === 'in_progress') {
                    badge.style.opacity = '1';
                    badge.style.background = 'rgba(59, 130, 246, 0.2)';
                    badge.style.borderColor = '#3b82f6';
                    badge.style.color = '#3b82f6';
                    badge.classList.add('pulse-animation'); // Assuming CSS class exists or add inline
                    badge.style.animation = 'pulse 2s infinite';
                }
            }
            
            // Log status change
            const logEntry = document.createElement('div');
            logEntry.style.color = '#fbbf24';
            logEntry.textContent = `[${timestamp}] Agent Status: ${agent} -> ${status}`;
            analysisLogs.appendChild(logEntry);
            analysisLogs.scrollTop = analysisLogs.scrollHeight;
        }
        else if (event.type === 'report') {
            const { section, content } = event.data;
            
            // Create or update report section
            let reportContainer = document.getElementById(`report-${section}`);
            if (!reportContainer) {
                // Clear placeholder if first report
                if (analysisReports.querySelector('svg')) {
                    analysisReports.innerHTML = '';
                }
                
                reportContainer = document.createElement('div');
                reportContainer.id = `report-${section}`;
                reportContainer.className = 'report-card';
                reportContainer.style.cssText = `
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                `;
                
                const title = section.replace(/_/g, ' ').replace('report', '').toUpperCase();
                const titleEl = document.createElement('h3');
                titleEl.textContent = title;
                titleEl.style.cssText = `
                    color: var(--accent-primary);
                    border-bottom: 1px solid var(--border-color);
                    padding-bottom: 10px;
                    margin-bottom: 10px;
                    font-size: 16px;
                `;
                
                const contentEl = document.createElement('div');
                contentEl.className = 'markdown-content';
                contentEl.style.cssText = 'color: var(--text-secondary); font-size: 14px; line-height: 1.6;';
                
                reportContainer.appendChild(titleEl);
                reportContainer.appendChild(contentEl);
                analysisReports.appendChild(reportContainer);
            }
            
            // Update content
            const contentEl = reportContainer.querySelector('.markdown-content');
            if (window.marked) {
                contentEl.innerHTML = window.marked.parse(content);
            } else {
                contentEl.textContent = content;
            }
            
            // Scroll to bottom of reports to show latest
            analysisReports.scrollTop = analysisReports.scrollHeight;
        }
        else if (event.type === 'risk_update') {
            const { analyst, content } = event.data;
             // Log risk update
            const logEntry = document.createElement('div');
            logEntry.style.color = '#f87171'; // Reddish
            logEntry.textContent = `[${timestamp}] Risk Debate: ${analyst} spoke.`;
            analysisLogs.appendChild(logEntry);
            analysisLogs.scrollTop = analysisLogs.scrollHeight;
            
            // Also update risk report section if needed, but 'report' event handles the full section update usually.
            // However, for incremental updates we might want to show it.
            // For now, let's rely on the 'report' event for the full text, 
            // or maybe create a 'Risk Debate' live feed?
            // The backend sends 'risk_analysis_report' updates too via 'report' event?
            // No, the backend logic in web/app.py sends 'risk_update' for each analyst message
            // AND I need to verify if it sends the full report.
            // In web/app.py, I didn't implement 'risk_analysis_report' stream explicitly in the loop?
            // Let's check web/app.py logic.
            // It streams 'risk_update' for each analyst.
            // It does NOT stream 'risk_analysis_report' explicitly unless I added it.
            // Wait, I added logic for 'risk_update'.
            
            // So I should append these to a Risk Analysis section.
            let reportContainer = document.getElementById(`report-risk_analysis`);
            if (!reportContainer) {
                 if (analysisReports.querySelector('svg')) {
                    analysisReports.innerHTML = '';
                }
                reportContainer = document.createElement('div');
                reportContainer.id = `report-risk_analysis`;
                reportContainer.className = 'report-card';
                reportContainer.style.cssText = `
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-left: 3px solid #ef4444;
                `;
                 const titleEl = document.createElement('h3');
                titleEl.textContent = "RISK MANAGEMENT DEBATE";
                titleEl.style.cssText = `
                    color: #ef4444;
                    border-bottom: 1px solid var(--border-color);
                    padding-bottom: 10px;
                    margin-bottom: 10px;
                    font-size: 16px;
                `;
                 const contentEl = document.createElement('div');
                contentEl.className = 'risk-content';
                contentEl.style.cssText = 'display: flex; flex-direction: column; gap: 10px;';
                
                reportContainer.appendChild(titleEl);
                reportContainer.appendChild(contentEl);
                analysisReports.appendChild(reportContainer);
            }
            
            const contentEl = reportContainer.querySelector('.risk-content');
            const entry = document.createElement('div');
            entry.style.cssText = `
                padding: 10px;
                background: var(--bg-tertiary);
                border-radius: 6px;
            `;
            entry.innerHTML = `
                <strong style="color: #f87171;">${analyst}:</strong>
                <div class="markdown-content" style="margin-top: 5px; color: var(--text-secondary); font-size: 14px;">
                    ${window.marked ? window.marked.parse(content) : content}
                </div>
            `;
            contentEl.appendChild(entry);
             analysisReports.scrollTop = analysisReports.scrollHeight;
        }
        else if (event.type === 'individual_decisions') {
            const decisions = event.data;
            
            let reportContainer = document.getElementById(`report-individual_decisions`);
            if (!reportContainer) {
                reportContainer = document.createElement('div');
                reportContainer.id = `report-individual_decisions`;
                reportContainer.className = 'report-card';
                reportContainer.style.cssText = `
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-left: 3px solid #8b5cf6;
                `;
                
                const titleEl = document.createElement('h3');
                titleEl.textContent = "INDIVIDUAL RISK MANAGER DECISIONS";
                titleEl.style.cssText = `
                    color: #8b5cf6;
                    border-bottom: 1px solid var(--border-color);
                    padding-bottom: 10px;
                    margin-bottom: 10px;
                    font-size: 16px;
                `;
                
                reportContainer.appendChild(titleEl);
                analysisReports.appendChild(reportContainer);
            }
            
            for (const [model, decision] of Object.entries(decisions)) {
                const decisionEl = document.createElement('div');
                decisionEl.style.cssText = `
                    margin-bottom: 15px;
                    padding: 10px;
                    background: var(--bg-tertiary);
                    border-radius: 6px;
                `;
                
                decisionEl.innerHTML = `
                    <strong style="color: #a78bfa;">${model}:</strong>
                    <div class="markdown-content" style="margin-top: 5px; color: var(--text-secondary); font-size: 14px;">
                        ${window.marked ? window.marked.parse(decision) : decision}
                    </div>
                `;
                reportContainer.appendChild(decisionEl);
            }
            analysisReports.scrollTop = analysisReports.scrollHeight;
        }
    }

    // Initialize
    updateModelOptions(llmProviderSelect.value);
    loadSettings();
    
    // Initialize wallet balance to 0 if not set
    if (!walletBalanceInput.value || walletBalanceInput.value === '' || parseFloat(walletBalanceInput.value) === 0) {
        walletBalanceInput.value = '0.00';
    }
    updateWalletDisplay(walletBalanceInput.value || 0);
    
    // Expose function to update match info from predict.js
    window.updateMatchInfo = function(player1, player2, tournament, date) {
        if (player1) document.getElementById('player1').value = player1;
        if (player2) document.getElementById('player2').value = player2;
        if (tournament) document.getElementById('tournament').value = tournament;
        if (date) document.getElementById('analysisDate').value = date;
        
        // Save updated match info
        saveSettings();
    };
    
    // Expose function to get settings
    window.getSettings = function() {
        return saveSettings();
    };
    
    // Expose function to open settings modal
    window.openSettingsModal = function() {
        openSettingsModal();
    };
});

