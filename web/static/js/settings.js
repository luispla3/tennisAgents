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

    // Save settings to localStorage
    function saveSettings() {
        // Automatically determine backend URL based on selected provider
        const backendUrl = BACKEND_URLS[llmProviderSelect.value] || BACKEND_URLS.openai;
        
        const settings = {
            walletBalance: parseFloat(walletBalanceInput.value) || 0,
            analysts: Array.from(document.querySelectorAll('input[name="analysts"]:checked')).map(cb => cb.value),
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
        predictButton.addEventListener('click', function() {
            // Save settings before predicting
            const settings = saveSettings();
            console.log('Predicting with settings:', settings);
            
            // TODO: Implement prediction functionality
            // This will be implemented later
            alert('Funcionalidad de predicción pendiente de implementar');
        });
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

