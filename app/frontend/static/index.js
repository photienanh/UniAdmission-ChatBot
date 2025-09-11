import { stream_text } from "/static/stream.js";

let currentSessionId = null;
let chatHistory = [];

document.addEventListener('DOMContentLoaded', function() {
    // Prevent unwanted focus behavior
    document.addEventListener('mousedown', function(e) {
        // Only allow focus on inputs, textareas, and buttons
        if (!e.target.matches('input, textarea, button, a, select')) {
            e.preventDefault();
        }
    });

    // Configure marked.js for better markdown parsing
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true, // Convert \n to <br>
            gfm: true,    // GitHub flavored markdown
            sanitize: false // Allow HTML (be careful with user input)
        });
    }
    
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const newChatBtn = document.getElementById('new-chat-btn');
    const modelSelect = document.getElementById('model-select');
    const retrieveDataButton = document.getElementById('retrieve-data-button');
    const searchResultsCount = document.getElementById('search-results-count');
    const searchDocsCount = document.getElementById('search-docs-count');
    const priorityDomains = document.getElementById('priority-domains');
    const sendButton = document.getElementById('send-button');
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsPopup = document.getElementById('settings-popup');
    const settingsCloseBtn = document.getElementById('settings-close-btn');
    const advancedSettingsItem = document.getElementById('advanced-settings-item');
    const advancedSettingsSidebar = document.getElementById('advanced-settings-sidebar');
    const advancedSettingsCloseBtn = document.getElementById('advanced-settings-close-btn');
    const advancedSettingsOverlay = document.getElementById('advanced-settings-overlay');
    const temperatureSlider = document.getElementById('temperature-slider');
    const temperatureValue = document.getElementById('temperature-value');
    const topPSlider = document.getElementById('top-p-slider');
    const topPValue = document.getElementById('top-p-value');
    const topKSlider = document.getElementById('top-k-slider');
    const topKValue = document.getElementById('top-k-value');
    const maxTokensInput = document.getElementById('max-tokens-input');
    const maxHistoryInput = document.getElementById('max-history');
    
    // Advanced search parameters
    const websearchCheckbox = document.getElementById('websearch-checkbox');
    const localdbCheckbox = document.getElementById('localdb-checkbox');
    const maxQueryInput = document.getElementById('max-query');
    const queryScoreThreshold = document.getElementById('query-score-threshold');
    const queryScoreValue = document.getElementById('query-score-value');
    const engineTypeSelect = document.getElementById('engine-type');
    const schoolDomainCheckbox = document.getElementById('school-domain');
    const timeMetricSelect = document.getElementById('time-metric');
    const timeRangeInput = document.getElementById('time-range');
    const pageRerankCheckbox = document.getElementById('page-rerank');
    const chunkRerankCheckbox = document.getElementById('chunk-rerank');
    const pageScoreThreshold = document.getElementById('page-score-threshold');
    const pageScoreValue = document.getElementById('page-score-value');
    const chunkScoreThreshold = document.getElementById('chunk-score-threshold');
    const chunkScoreValue = document.getElementById('chunk-score-value');
    const includePdfCheckbox = document.getElementById('include-pdf');
    const includeImageCheckbox = document.getElementById('include-image');
    const mergeTableCheckbox = document.getElementById('merge-table');
    const mergeNeighborCheckbox = document.getElementById('merge-neighbor');
    const llmRerankCheckbox = document.getElementById('llm-rerank-checkbox');
    const simpleTimeLimit = document.getElementById('simple-time-limit');
    const simpleRetrieveMode = document.getElementById('simple-retrieve-mode');

    // Handle slider switch clicks
    document.querySelectorAll('.slider-switch').forEach(switchElement => {
        switchElement.addEventListener('click', function(e) {
            e.preventDefault();
            const checkbox = this.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));
        });
    });
    
    // Add click handlers for initial model items
    document.querySelectorAll('.model-item').forEach(item => {
        item.addEventListener('click', function() {
            // Remove active class from all models
            document.querySelectorAll('.model-item').forEach(i => i.classList.remove('active'));
            
            // Add active class to clicked model
            this.classList.add('active');
            
            // Update hidden select for compatibility
            const hiddenSelect = document.getElementById('model-select');
            if (hiddenSelect) {
                hiddenSelect.value = this.dataset.model;
            }
        });
    });

    // Load available models
    async function loadModels() {
        try {
            const response = await fetch('/models');
            const models = await response.json();
            
            // Get models list container
            const modelsList = document.getElementById('models-list');
            if (!modelsList) return;
            
            // Clear existing models but keep at least default ones
            const hasModels = models && models.length > 0;
            if (hasModels) {
                modelsList.innerHTML = '';
                
                // Add models to list
                models.forEach((model, index) => {
                    const modelItem = document.createElement('div');
                    modelItem.className = 'model-item';
                    modelItem.dataset.model = model.id;
                    
                    // Set first model as default if available
                    if (index === 0) {
                        modelItem.classList.add('active');
                    }
                    
                    modelItem.innerHTML = `
                        <span>${model.name}</span>
                    `;
                    
                    // Add click handler
                    modelItem.addEventListener('click', function() {
                        // Remove active class from all models
                        document.querySelectorAll('.model-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        
                        // Add active class to clicked model
                        this.classList.add('active');
                        
                        // Update hidden select for compatibility
                        const hiddenSelect = document.getElementById('model-select');
                        if (hiddenSelect) {
                            hiddenSelect.value = model.id;
                        }
                    });
                    
                    modelsList.appendChild(modelItem);
                });
                
                // Update hidden select options
                const hiddenSelect = document.getElementById('model-select');
                if (hiddenSelect) {
                    hiddenSelect.innerHTML = '';
                    models.forEach((model, index) => {
                        const option = document.createElement('option');
                        option.value = model.id;
                        option.textContent = model.name;
                        if (index === 0) option.selected = true;
                        hiddenSelect.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('Error loading models:', error);
            // Keep default models if API fails - they're already in HTML
        }
    }
    
    // Advanced settings item click handler
    advancedSettingsItem.addEventListener('click', function(e) {
        e.stopPropagation();
        showAdvancedSettingsSidebar();
    });
    
    // Close advanced settings sidebar
    advancedSettingsCloseBtn.addEventListener('click', function() {
        hideAdvancedSettingsSidebar();
    });
    
    // Handle ESC key for advanced sidebar
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (advancedSettingsSidebar.classList.contains('show')) {
                hideAdvancedSettingsSidebar();
            }
        }
    });
    
    // Close advanced sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (!advancedSettingsSidebar.contains(e.target) && !advancedSettingsItem.contains(e.target)) {
            hideAdvancedSettingsSidebar();
        }
    });
    
    // Close advanced sidebar when clicking overlay
    advancedSettingsOverlay.addEventListener('click', function() {
        hideAdvancedSettingsSidebar();
    });
    
    function showAdvancedSettingsSidebar() {
        advancedSettingsSidebar.classList.add('show');
        advancedSettingsOverlay.classList.add('show');
        // Close basic settings popup
        hideSettingsPopup();
    }
    
    function hideAdvancedSettingsSidebar() {
        advancedSettingsSidebar.classList.remove('show');
        advancedSettingsOverlay.classList.remove('show');
    }
    
    // Toggle settings popup
    settingsToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        const isVisible = settingsPopup.classList.contains('show');
        if (isVisible) {
            hideSettingsPopup();
        } else {
            showSettingsPopup();
        }
    });
    
    // Close settings popup
    settingsCloseBtn.addEventListener('click', function() {
        hideSettingsPopup();
    });
    
    // Close popup when clicking outside
    document.addEventListener('click', function(e) {
        if (!settingsPopup.contains(e.target) && !settingsToggle.contains(e.target)) {
            hideSettingsPopup();
        }
    });
    
    function showSettingsPopup() {
        settingsPopup.classList.add('show');
        settingsToggle.classList.add('active');
        // Close advanced settings if open
        hideAdvancedSettingsSidebar();
    }
    
    function hideSettingsPopup() {
        settingsPopup.classList.remove('show');
        settingsToggle.classList.remove('active');
    }
    
    // Handle slider value updates
    temperatureSlider.addEventListener('input', function() {
        temperatureValue.textContent = this.value;
    });
    
    topPSlider.addEventListener('input', function() {
        topPValue.textContent = this.value;
    });
    
    topKSlider.addEventListener('input', function() {
        topKValue.textContent = this.value;
    });
    
    // Advanced settings sliders
    queryScoreThreshold.addEventListener('input', function() {
        queryScoreValue.textContent = this.value;
    });
    
    pageScoreThreshold.addEventListener('input', function() {
        pageScoreValue.textContent = this.value;
    });
    
    chunkScoreThreshold.addEventListener('input', function() {
        chunkScoreValue.textContent = this.value;
    });
    
    // Enable/disable send button based on input
    userInput.addEventListener('input', function() {
        sendButton.disabled = this.value.trim().length === 0;
        // Auto-resize textarea
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
    
    // Validate search docs count input (0-30 range) - visual feedback for invalid values
    searchDocsCount.addEventListener('input', function() {
        let value = parseInt(this.value);
        
        // Check if value is invalid and add/remove visual feedback
        if (this.value !== '' && (!isNaN(value) && (value < 0 || value > 30))) {
            this.classList.add('invalid');
        } else {
            this.classList.remove('invalid');
        }
    });
    
    // Validate search docs count input (0-30 range) - only on blur to allow free typing
    searchDocsCount.addEventListener('blur', function() {
        let value = parseInt(this.value);
        if (this.value === '' || isNaN(value) || value < 0) {
            this.value = 0;
        } else if (value > 30) {
            this.value = 30;
        }
        // Remove invalid class after correction
        this.classList.remove('invalid');
    });
    
    // Validate max tokens input (128-8192 range) - visual feedback for invalid values
    maxTokensInput.addEventListener('input', function() {
        let value = parseInt(this.value);
        
        // Check if value is invalid and add/remove visual feedback
        if (this.value !== '' && (!isNaN(value) && (value < 128 || value > 8192))) {
            this.classList.add('invalid');
        } else {
            this.classList.remove('invalid');
        }
    });
    
    // Validate max tokens input (128-8192 range) - only on blur to allow free typing
    maxTokensInput.addEventListener('blur', function() {
        let value = parseInt(this.value);
        
        // Reset to valid range if value is invalid
        if (isNaN(value) || value < 128) {
            this.value = 128;
        } else if (value > 8192) {
            this.value = 8192;
        }
        
        // Remove invalid class after correction
        this.classList.remove('invalid');
    });
    
    // Validate max query input (1-4 range) - visual feedback for invalid values
    maxQueryInput.addEventListener('input', function() {
        let value = parseInt(this.value);
        
        // Check if value is invalid and add/remove visual feedback
        if (this.value !== '' && (!isNaN(value) && (value < 1 || value > 4))) {
            this.classList.add('invalid');
        } else {
            this.classList.remove('invalid');
        }
    });
    
    // Validate max query input (1-4 range) - only on blur to allow free typing
    maxQueryInput.addEventListener('blur', function() {
        let value = parseInt(this.value);
        if (this.value === '' || isNaN(value) || value < 1) {
            this.value = 1;
        } else if (value > 4) {
            this.value = 4;
        }
        // Remove invalid class after correction
        this.classList.remove('invalid');
    });
    
    // Validate max history input (1-20 range) - visual feedback for invalid values
    maxHistoryInput.addEventListener('input', function() {
        let value = parseInt(this.value);
        
        // Check if value is invalid and add/remove visual feedback
        if (this.value !== '' && (!isNaN(value) && (value < 1 || value > 20))) {
            this.classList.add('invalid');
        } else {
            this.classList.remove('invalid');
        }
    });
    
    // Validate max history input (1-20 range) - only on blur to allow free typing
    maxHistoryInput.addEventListener('blur', function() {
        let value = parseInt(this.value);
        if (this.value === '' || isNaN(value) || value < 1) {
            this.value = 1;
        } else if (value > 20) {
            this.value = 20;
        }
        // Remove invalid class after correction
        this.classList.remove('invalid');
    });
    
    // Toggle sidebar functions
    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        // Update bot message spacing when sidebar toggles on desktop
        updateBotMessageSpacing();
    }
    
    // Update bot message padding based on sidebar state
    function updateBotMessageSpacing() {
        const botMessages = document.querySelectorAll('.message.bot-message .message-content');
        const isSidebarCollapsed = sidebar.classList.contains('collapsed');
        
        botMessages.forEach(messageContent => {
            if (isSidebarCollapsed) {
                messageContent.style.paddingLeft = '24px';
            } else {
                messageContent.style.paddingLeft = '40px'; // Gần lề sidebar hơn nữa
            }
        });
    }
    
    function closeSidebar() {
        sidebar.classList.add('collapsed');
    }
    
    // Toggle sidebar
    sidebarToggle.addEventListener('click', toggleSidebar);
    
    // Fill prompt from example cards
    window.fillPrompt = function(text) {
        userInput.value = text;
        sendButton.disabled = false;
        userInput.focus();
    };
    
    // New chat
    newChatBtn.addEventListener('click', function() {
        startNewChat();
    });
    
    function startNewChat() {
        currentSessionId = null;
        clearChatMessages();
        showWelcomeScreen();
        document.getElementById('chat-title').textContent = 'UniAdmission ChatBot';
        
        // Remove active class from all sessions
        document.querySelectorAll('.chat-session').forEach(s => s.classList.remove('active'));
    }
    
    function clearChatMessages() {
        chatMessages.innerHTML = '';
    }
    
    function showWelcomeScreen() {
        chatMessages.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-content">
                    <h2>UniAdmission ChatBot</h2>
                    <p>Xin chào! Tôi là UniAdmission Bot. Bạn có thể hỏi tôi bất kỳ thông tin gì về tuyển sinh đại học.</p>
                    <div class="example-prompts">
                        <div class="prompt-card" onclick="fillPrompt('Điểm chuẩn Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội')">
                            <i class="fas fa-graduation-cap"></i>
                            <span>Điểm chuẩn Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội</span>
                        </div>
                        <div class="prompt-card" onclick="fillPrompt('Các trường đào tạo ngành Trí tuệ nhân tạo')">
                            <i class="fas fa-brain"></i>
                            <span>Các trường đào tạo ngành Trí tuệ nhân tạo</span>
                        </div>
                        <div class="prompt-card" onclick="fillPrompt('Ngành CNTT có tốt không?')">
                            <i class="fas fa-laptop-code"></i>
                            <span>Ngành CNTT có tốt không?</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = userInput.value.trim();
        if (message === '') return;
        
        // Get settings - check active model item first, then fallback to select
        const activeModelItem = document.querySelector('.model-item.active');
        const selectedModelType = activeModelItem ? activeModelItem.dataset.model : modelSelect.value;
        const useGemini = selectedModelType.includes('gemini');
        const retrieveData = retrieveDataButton.checked;
        const temperature = parseFloat(temperatureSlider.value);
        const topP = parseFloat(topPSlider.value);
        const topK = parseInt(topKSlider.value);
        const maxTokens = parseInt(maxTokensInput.value);
        const maxHistory = parseInt(maxHistoryInput.value);
        
        // Advanced search parameters
        let maxQuery = parseInt(maxQueryInput.value);
        const queryScore = parseFloat(queryScoreThreshold.value);
        let engineType = engineTypeSelect.value;
        let schoolDomain = schoolDomainCheckbox.checked;
        let timeMetric = timeMetricSelect.value;
        let timeRange = parseInt(timeRangeInput.value);
        const pageRerank = pageRerankCheckbox.checked;
        const chunkRerank = chunkRerankCheckbox.checked;
        const pageScore = parseFloat(pageScoreThreshold.value);
        const chunkScore = parseFloat(chunkScoreThreshold.value);
        let includePdf = includePdfCheckbox.checked;
        const includeImage = includeImageCheckbox.checked;
        let mergeTable = mergeTableCheckbox.checked;
        let mergeNeighbor = mergeNeighborCheckbox.checked;
        let llmrerank = llmRerankCheckbox.checked;
        const simpleTimeLimitValue = simpleTimeLimit.value;
        const simpleRetrieveModeValue = simpleRetrieveMode.value;
        let usewebsearch = retrieveData && websearchCheckbox.checked;
        let uselocaldb = retrieveData && localdbCheckbox.checked;

        // Validate k_docs value before sending
        let kDocsValue = parseInt(searchDocsCount.value);
        if (isNaN(kDocsValue) || kDocsValue < 0) kDocsValue = 0;
        if (kDocsValue > 50) kDocsValue = 50;
        let kPagesValue = parseInt(searchResultsCount.value);
        // Send to backend
        if (!retrieveData) {
            kDocsValue = 0;
            kPagesValue = 0;
        }

        if (simpleTimeLimitValue === "") {
        }
        else {
            // Match number + metric (like "7d", "1m", "1y")
            const match = simpleTimeLimitValue.match(/^(\d+)([a-zA-Z])$/);
            timeRange = parseInt(match[1], 10); // numeric value
            timeMetric = match[2]; 
        }
        if (retrieveData) {
            if (simpleRetrieveModeValue === "option") {

            }
            else if (simpleRetrieveModeValue === "basic") {
                usewebsearch = true;
                uselocaldb = true;
                maxQuery = 1;
                kPagesValue = 1;
                kDocsValue = 3;
                includePdf = false;
                mergeTable = false;
                mergeNeighbor = false;
                llmrerank = false;
            }
            else if (simpleRetrieveModeValue == "mid") {
                usewebsearch = true;
                uselocaldb = true;
                maxQuery = 2;
                kPagesValue = 3;
                kDocsValue = 5;
                includePdf = false;
                mergeTable = true;
                mergeNeighbor = false;
                llmrerank = false;
            }
            else if (simpleRetrieveModeValue == "advanced") {
                usewebsearch = true;
                uselocaldb = true;
                maxQuery = 3;
                kPagesValue = 5;
                kDocsValue = 5;
                includePdf = true;
                mergeTable = true;
                mergeNeighbor = true;
                llmrerank = true;
            }
        }
        
        console.log('Model selected:', selectedModelType, 'Use Gemini:', useGemini);
        console.log('Web Search enabled:', retrieveData);
        
        // Add user message
        addMessage(message, 'user');
        
        // Clear input
        userInput.value = '';
        userInput.style.height = 'auto';
        sendButton.disabled = true;
        
        // Hide welcome screen if showing
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }
        
        // Show typing indicator
        showTypingIndicator();

        
        // Build comprehensive params object
        const params = {
            model_id: selectedModelType,
            // Sampling parameters
            temperature: temperature,
            top_p: topP,
            top_k: topK,
            max_tokens: maxTokens,
            max_history: maxHistory,
            
            // Basic web search
            domain_restrict: priorityDomains.checked,
            k_pages: kPagesValue,
            k_docs: kDocsValue,
            
            // Advanced search parameters
            use_websearch: usewebsearch,
            use_localdb: uselocaldb,
            max_query: maxQuery,
            query_score_threshold: queryScore,
            engine_type: engineType,
            school_domain: schoolDomain,
            page_rerank: pageRerank,
            chunk_rerank: chunkRerank,
            page_score_threshold: pageScore,
            chunk_score_threshold: chunkScore,
            include_pdf: includePdf,
            include_image: includeImage,
            merge_table: mergeTable,
            merge_neighbor: mergeNeighbor,
            llm_rerank: llmrerank,
        };
        
        // Add time parameters if specified
        if (timeMetric && timeRange) {
            params.time_metric = timeMetric;
            params.time_range = timeRange;
        }
        
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: message,
                session_id: currentSessionId,
                params: params
            })
        })
.then(response => {
    if (response.status === 401) {
        window.location.href = '/login';
        return;
    }
    return response.json();
})
.then(async data => {
    hideTypingIndicator();
    if (data.error) {
        addMessage('Xin lỗi, có lỗi xảy ra: ' + data.error, 'bot');
    } else {
        console.log(data.result_url);
        console.log('Server response datax:', data);
        currentSessionId = data.session_id;
        // Tạo message rỗng để append dần text stream
        // const botMessageDiv = document.createElement('div');
        // botMessageDiv.className = 'message bot-message';
        // botMessageDiv.innerHTML = `<div class="message-content markdown-content"></div>`;
        // chatMessages.appendChild(botMessageDiv);

        // Generate a timestamp string
        const timestampId = 'element-' + Date.now();

        addMessage_with_id("", 'bot', timestampId, data.web_sources || null);
        const contentDiv = document.getElementById(timestampId);
        // Gọi API stream với stream_id
        let speed = 1; // 1/(1) s to flush buffer
        let max_speed = 300; // 300 char/s
        await stream_text(data.result_url, contentDiv, chatMessages, speed, max_speed);

        // Reload chat history nếu là session mới
        if (!document.querySelector(`[data-session-id="${data.session_id}"]`)) {
            loadChatHistory();
        }
    }
})
.catch(error => {
    hideTypingIndicator();
    addMessage('Xin lỗi, có lỗi kết nối xảy ra.', 'bot');
    console.error('Error:', error);
});
    });
    
    // Enter key handling
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.disabled) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });
    
    function addMessage(content, role, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        // Parse markdown cho bot messages, plain text cho user messages
        let processedContent;
        let contentClass = '';
        
        if (role === 'bot') {
            // Parse markdown và clean up
            processedContent = marked.parse(content);
            contentClass = 'markdown-content';
        } else {
            // User messages - just replace newlines with <br>
            processedContent = `<p>${content.replace(/\n/g, '<br>')}</p>`;
        }
        
        // Tạo nút nguồn nếu có sources
        let sourcesButton = '';
        console.log('Creating sources button for role:', role, 'sources:', sources); // Debug log
        if (role === 'bot' && sources && sources.length > 0) {
            console.log('Creating sources button with', sources.length, 'sources'); // Debug log
            try {
                const sourcesJson = JSON.stringify(sources);
                console.log('Sources JSON:', sourcesJson); // Debug log
                sourcesButton = `
                    <div class="sources-button-container">
                        <button class="sources-button" onclick="showSources(this)" data-sources='${sourcesJson.replace(/'/g, '&#39;')}'>
                            <i class="fas fa-link"></i>
                            <span>Nguồn (${sources.length})</span>
                        </button>
                    </div>
                `;
            } catch (error) {
                console.error('Error creating sources JSON:', error);
            }
        }
        
        messageDiv.innerHTML = `
            <div class="message-content ${contentClass}">
                ${processedContent}
                ${sourcesButton}
                <div class="message-actions">
                    <button class="copy-button" onclick="copyMessageContent(this)" title="Copy message">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        
        // Apply correct padding for bot messages based on sidebar state
        if (role === 'bot') {
            const messageContent = messageDiv.querySelector('.message-content');
            const isSidebarCollapsed = sidebar.classList.contains('collapsed');
            
            if (isSidebarCollapsed) {
                messageContent.style.paddingLeft = '24px';
            } else {
                messageContent.style.paddingLeft = '40px'; // Gần lề sidebar hơn nữa
            }
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    function addMessage_with_id(content, role, id, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        // Parse markdown cho bot messages, plain text cho user messages
        let processedContent;
        let contentClass = '';
        
        if (role === 'bot') {
            // Parse markdown và clean up
            processedContent = marked.parse(content);
            contentClass = 'markdown-content';
        } else {
            // User messages - just replace newlines with <br>
            processedContent = `<p>${content.replace(/\n/g, '<br>')}</p>`;
        }
        
        // Tạo nút nguồn nếu có sources
        let sourcesButton = '';
        console.log('Creating sources button for role:', role, 'sources:', sources); // Debug log
        if (role === 'bot' && sources && sources.length > 0) {
            console.log('Creating sources button with', sources.length, 'sources'); // Debug log
            try {
                const sourcesJson = JSON.stringify(sources);
                console.log('Sources JSON:', sourcesJson); // Debug log
                sourcesButton = `
                    <div class="sources-button-container">
                        <button class="sources-button" onclick="showSources(this)" data-sources='${sourcesJson.replace(/'/g, '&#39;')}'>
                            <i class="fas fa-link"></i>
                            <span>Nguồn (${sources.length})</span>
                        </button>
                    </div>
                `;
            } catch (error) {
                console.error('Error creating sources JSON:', error);
            }
        }
        
        messageDiv.innerHTML = `
            <div class="message-content ${contentClass}">
                <div id=${id}>
                    ${processedContent}
                </div>
                ${sourcesButton}
                <div class="message-actions">
                    <button class="copy-button" onclick="copyMessageContent(this)" title="Copy message">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        
        // Apply correct padding for bot messages based on sidebar state
        if (role === 'bot') {
            const messageContent = messageDiv.querySelector('.message-content');
            const isSidebarCollapsed = sidebar.classList.contains('collapsed');
            
            if (isSidebarCollapsed) {
                messageContent.style.paddingLeft = '24px';
            } else {
                messageContent.style.paddingLeft = '40px'; // Gần lề sidebar hơn nữa
            }
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        
        // Apply correct padding for typing indicator based on sidebar state
        const messageContent = typingDiv.querySelector('.message-content');
        const isSidebarCollapsed = sidebar.classList.contains('collapsed');
        
        if (isSidebarCollapsed) {
            messageContent.style.paddingLeft = '24px';
        } else {
            messageContent.style.paddingLeft = '40px'; // Gần lề sidebar hơn nữa
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function hideTypingIndicator() {
        const typing = document.querySelector('.typing');
        if (typing) typing.remove();
    }
    
    // Logout function
    window.logout = function() {
        fetch('/logout', {
            method: 'GET',
            cache: 'no-cache'
        })
        .then(() => {
            // Clear browser cache và history
            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, null, '/login');
            }
            // Force reload để đảm bảo không cache
            window.location.replace('/login');
        })
        .catch(() => {
            // Nếu có lỗi, vẫn redirect về login
            window.location.replace('/login');
        });
    };
    
    // Toggle user dropdown
    window.toggleUserDropdown = function() {
        const dropdown = document.getElementById('user-dropdown');
        const icon = document.getElementById('dropdown-icon');
        
        dropdown.classList.toggle('show');
        icon.classList.toggle('rotated');
    };
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        const userMenu = document.getElementById('user-menu');
        const dropdown = document.getElementById('user-dropdown');
        const icon = document.getElementById('dropdown-icon');
        
        if (!userMenu.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('show');
            icon.classList.remove('rotated');
        }
    });
    
    // Chat history event handling
    document.getElementById('chat-history').addEventListener('click', function(e) {
        const sessionElement = e.target.closest('.chat-session');
        const deleteButton = e.target.closest('.delete-session');
        
        if (deleteButton) {
            e.stopPropagation();
            const sessionId = deleteButton.dataset.sessionId;
            if (confirm('Bạn có chắc muốn xóa cuộc trò chuyện này?')) {
                deleteSession(sessionId);
            }
        } else if (sessionElement) {
            const sessionId = sessionElement.dataset.sessionId;
            loadSession(sessionId);
        }
    });
    
    function loadChatHistory() {
        fetch('/sessions')
        .then(response => response.json())
        .then(sessions => {
            const historyDiv = document.getElementById('chat-history');
            historyDiv.innerHTML = '';
            
            sessions.forEach(session => {
                const sessionDiv = document.createElement('div');
                sessionDiv.className = 'chat-session';
                sessionDiv.dataset.sessionId = session.id;
                sessionDiv.innerHTML = `
                    <span class="session-title">${session.title}</span>
                    <button class="delete-session" data-session-id="${session.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
                historyDiv.appendChild(sessionDiv);
            });
        })
        .catch(error => console.error('Error loading chat history:', error));
    }
    
    function loadSession(sessionId) {
        fetch(`/session/${sessionId}/messages`)
        .then(response => response.json())
        .then(data => {
            currentSessionId = sessionId;
            clearChatMessages();
            
            document.getElementById('chat-title').textContent = data.session.title;
            
            data.messages.forEach(message => {
                // Lấy web_sources từ trường web_sources hoặc extra_data
                const sources = message.web_sources || message.extra_data?.web_sources || null;
                addMessage(message.text, message.role, sources);
            });
            
            // Mark session as active
            document.querySelectorAll('.chat-session').forEach(s => s.classList.remove('active'));
            document.querySelector(`[data-session-id="${sessionId}"]`).classList.add('active');
        })
        .catch(error => console.error('Error loading session:', error));
    }
    
    function deleteSession(sessionId) {
        fetch(`/session/${sessionId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadChatHistory();
                if (currentSessionId === sessionId) {
                    startNewChat();
                }
            }
        })
        .catch(error => console.error('Error deleting session:', error));
    }
    
    // Check authentication periodically (but not too frequently to avoid false alerts)
    function checkAuthStatus() {
        fetch('/check', {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                // User is not authenticated, redirect to login
                window.location.href = '/login';
            }
        })
        .catch(error => {
            console.warn('Auth check failed:', error);
            // Don't redirect on network errors to avoid false alerts
        });
    }
    
    // Check auth every 15 minutes (reduced frequency to avoid false alerts)
    setInterval(checkAuthStatus, 15 * 60 * 1000);
    
    // Function to show sources modal
    window.showSources = function(button) {
        console.log('showSources called with button:', button); // Debug log
        console.log('Button dataset:', button.dataset); // Debug log
        
        try {
            const sourcesData = button.dataset.sources;
            console.log('Raw sources data:', sourcesData); // Debug log
            
            if (!sourcesData) {
                console.warn('No sources data found in button dataset');
                return;
            }
            
            const sources = JSON.parse(sourcesData);
            console.log('Parsed sources:', sources); // Debug log
            
            // Check if sources is valid and not empty
            if (!sources || !Array.isArray(sources) || sources.length === 0) {
                console.warn('No valid sources found');
                return;
            }
            
            // Create modal
            const modal = document.createElement('div');
            modal.className = 'sources-modal';
            modal.innerHTML = `
                <div class="sources-modal-content">
                    <div class="sources-modal-header">
                        <h3>Nguồn tham khảo</h3>
                        <button class="sources-modal-close">&times;</button>
                    </div>
                    <div class="sources-modal-body">
                        ${sources.map((source, index) => `
                            <div class="source-item">
                                <div class="source-header">
                                    <span class="source-number">${index + 1}</span>
                                    <div class="source-info">
                                        <a href="${source.url || '#'}" target="_blank" class="source-title">
                                            ${source.title || source.url || 'Không có tiêu đề'}
                                        </a>
                                        <div class="source-url">${source.url || 'Không có URL'}</div>
                                    </div>
                                </div>
                                <div class="source-content">
                                    ${source.description && source.description.trim() !== '' && source.description !== 'We cannot provide a description for this page right now' ? source.description : 'Không có mô tả'}
                                </div>
                                <div class="source-context" id="source-context-${index}" style="display: none;">
                                    <div class="context-header">
                                        <strong>Nội dung đầy đủ:</strong>
                                    </div>
                                    <div class="context-content">
                                        ${source.text && source.text.trim() !== '' && source.text !== 'We cannot provide a description for this page right now' ? source.text : 'Không có nội dung'}
                                    </div>
                                </div>
                                <div class="source-footer">
                                    <button class="show-context-btn" onclick="showSourceContext(${index}, this)" title="Xem nội dung đầy đủ">
                                        <i class="fas fa-eye"></i>
                                        <span>Show context</span>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Animate source items
            setTimeout(() => {
                const sourceItems = modal.querySelectorAll('.source-item');
                sourceItems.forEach((item, index) => {
                    setTimeout(() => {
                        item.style.opacity = '0';
                        item.style.transform = 'translateY(20px)';
                        item.style.transition = 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                        
                        setTimeout(() => {
                            item.style.opacity = '1';
                            item.style.transform = 'translateY(0)';
                        }, 50);
                    }, index * 100);
                });
            }, 100);
            
            // Close modal handlers
            const closeBtn = modal.querySelector('.sources-modal-close');
            const closeModal = () => {
                modal.style.animation = 'modalFadeOut 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                modal.querySelector('.sources-modal-content').style.animation = 'modalSlideOut 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                setTimeout(() => {
                    modal.remove();
                }, 300);
            };
            
            closeBtn.addEventListener('click', closeModal);
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeModal();
                }
            });
            
            // Close on ESC key
            const handleEsc = (e) => {
                if (e.key === 'Escape') {
                    closeModal();
                    document.removeEventListener('keydown', handleEsc);
                }
            };
            document.addEventListener('keydown', handleEsc);
            
        } catch (error) {
            console.error('Error in showSources:', error);
            alert('Có lỗi khi hiển thị nguồn tham khảo');
        }
    };
    
    // Function to show/hide source context
    window.showSourceContext = function(sourceIndex, buttonElement) {
        const contextDiv = document.getElementById(`source-context-${sourceIndex}`);
        const icon = buttonElement.querySelector('i');
        const text = buttonElement.querySelector('span');
        
        if (contextDiv.style.display === 'none') {
            contextDiv.style.display = 'block';
            icon.className = 'fas fa-eye-slash';
            text.textContent = 'Hide context';
            buttonElement.title = 'Ẩn nội dung đầy đủ';
        } else {
            contextDiv.style.display = 'none';
            icon.className = 'fas fa-eye';
            text.textContent = 'Show context';
            buttonElement.title = 'Xem nội dung đầy đủ';
        }
    };
    
    // Function to copy message content
    window.copyMessageContent = function(buttonElement) {
        try {
            // Find the message content div
            const messageContent = buttonElement.closest('.message-content');
            let textToCopy = '';
            
            // Get all text content from the message, excluding the copy button and sources button
            const contentElements = messageContent.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, pre, blockquote');
            if (contentElements.length > 0) {
                // Extract text from structured content
                contentElements.forEach((element, index) => {
                    if (index > 0) textToCopy += '\n';
                    textToCopy += element.textContent.trim();
                });
            } else {
                // Fallback: get all text content and clean it
                const clonedContent = messageContent.cloneNode(true);
                // Remove the copy button and sources button from the clone
                const actionsDiv = clonedContent.querySelector('.message-actions');
                const sourcesDiv = clonedContent.querySelector('.sources-button-container');
                if (actionsDiv) actionsDiv.remove();
                if (sourcesDiv) sourcesDiv.remove();
                textToCopy = clonedContent.textContent.trim();
            }
            
            // Visual feedback function
            const showFeedback = (success = true) => {
                const icon = buttonElement.querySelector('i');
                const originalClass = icon.className;
                
                if (success) {
                    icon.className = 'fas fa-check';
                    buttonElement.style.color = '#22c55e';
                } else {
                    icon.className = 'fas fa-times';
                    buttonElement.style.color = '#ef4444';
                }
                
                // Reset after 2 seconds
                setTimeout(() => {
                    icon.className = originalClass;
                    buttonElement.style.color = '';
                }, 2000);
            };
            
            // Try modern clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    showFeedback(true);
                }).catch(err => {
                    console.warn('Modern clipboard failed, trying fallback:', err);
                    // Try fallback method
                    fallbackCopy(textToCopy, showFeedback);
                });
            } else {
                // Use fallback method directly
                fallbackCopy(textToCopy, showFeedback);
            }
            
        } catch (error) {
            console.error('Error copying message:', error);
            // Show error feedback
            const icon = buttonElement.querySelector('i');
            const originalClass = icon.className;
            icon.className = 'fas fa-times';
            buttonElement.style.color = '#ef4444';
            setTimeout(() => {
                icon.className = originalClass;
                buttonElement.style.color = '';
            }, 2000);
        }
    };
    
    // Fallback copy function for older browsers or when modern clipboard fails
    function fallbackCopy(text, callback) {
        try {
            // Create a temporary textarea element
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '-9999px';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            
            // Focus and select the text
            textArea.focus();
            textArea.select();
            textArea.setSelectionRange(0, 99999); // For mobile devices
            
            // Try to copy using execCommand
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);
            
            if (callback) {
                callback(successful);
            }
            
            if (!successful) {
                console.error('Fallback copy failed');
            }
        } catch (err) {
            console.error('Fallback copy error:', err);
            if (callback) {
                callback(false);
            }
        }
    }
    
    // Initialize
    loadModels();
    loadChatHistory();
    
    // Update bot message spacing after loading history
    setTimeout(() => {
        updateBotMessageSpacing();
    }, 100);
    
    // Focus input
    setTimeout(() => {
        userInput.focus();
    }, 100);
});
