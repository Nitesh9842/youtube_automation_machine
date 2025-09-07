 
        // Global variables
        let currentTaskId = null;
        let statusCheckInterval = null;
        let uploadHistory = JSON.parse(localStorage.getItem('uploadHistory') || '[]');
        
        // Initialize application
        window.addEventListener('DOMContentLoaded', function() {
            checkAuthenticationStatus();
            loadSettings();
            renderUploadHistory();
        });
        
        // Channel info and authentication
        async function checkAuthenticationStatus() {
            showLoader('Checking authentication...');
            
            try {
                const authResponse = await fetch('/check-auth');
                const authData = await authResponse.json();
                
                if (authData.authenticated) {
                    const channelResponse = await fetch('/get-channel-info');
                    const channelData = await channelResponse.json();
                    
                    if (channelData.authenticated && channelData.channel) {
                        updateChannelInfo(channelData.channel);
                        showDashboard();
                    } else {
                        showLoginPanel();
                    }
                } else {
                    showLoginPanel();
                }
            } catch (error) {
                console.error('Error checking auth status:', error);
                showLoginPanel();
                showAlert('Error checking authentication status. Please try again.', 'error');
            } finally {
                hideLoader();
            }
        }
        
        function updateChannelInfo(channel) {
            document.getElementById('channelName').textContent = channel.title;
            document.getElementById('channelAvatar').src = channel.thumbnail || 'https://via.placeholder.com/56';
            document.getElementById('subscriberCount').textContent = formatNumber(channel.subscriberCount);
            document.getElementById('videoCount').textContent = formatNumber(channel.videoCount);
            document.getElementById('uploadChannelName').textContent = channel.title;
            
            document.getElementById('channelInfo').classList.add('active');
            document.getElementById('logoutBtn').style.display = 'flex';
        }
        
        async function authenticate() {
            showLoader('Connecting to YouTube...');
            
            try {
                const response = await fetch('/authenticate', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const data = await response.json();
                
                if (data.success) {
                    checkAuthenticationStatus();
                    showAlert('Successfully connected to YouTube!', 'success');
                } else {
                    showAlert(data.error || 'Connection failed. Please try again.', 'error');
                    showLoginPanel();
                }
            } catch (error) {
                console.error('Authentication error:', error);
                showAlert('Connection error. Please try again.', 'error');
                showLoginPanel();
            } finally {
                hideLoader();
            }
        }
        
        async function logout() {
            showLoader('Disconnecting...');
            
            try {
                const response = await fetch('/logout', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    showAlert('Successfully disconnected.', 'success');
                    showLoginPanel();
                } else {
                    showAlert(data.error || 'Logout failed. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Logout error:', error);
                showAlert('Logout error. Please try again.', 'error');
            } finally {
                hideLoader();
            }
        }
        
        // Content actions
        async function generatePreview() {
            const url = document.getElementById('reelUrl').value.trim();
            if (!url) {
                showAlert('Please enter a valid Instagram URL', 'error');
                return;
            }

            showLoader('Generating AI preview...');

            try {
                const response = await fetch('/generate-preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();
                hideLoader();

                if (data.success) {
                    showPreviewResult(data);
                } else {
                    showAlert(data.error || 'Failed to generate preview', 'error');
                }
            } catch (error) {
                hideLoader();
                showAlert('Network error: ' + error.message, 'error');
            }
        }

        async function downloadOnly() {
            const url = document.getElementById('reelUrl').value.trim();
            if (!url) {
                showAlert('Please enter a valid Instagram URL', 'error');
                return;
            }

            showLoader('Downloading content...');

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();
                hideLoader();

                if (data.success) {
                    showDownloadResult(data);
                } else {
                    showAlert(data.error || 'Download failed', 'error');
                }
            } catch (error) {
                hideLoader();
                showAlert('Network error: ' + error.message, 'error');
            }
        }

        async function autoUploadBackground() {
            const url = document.getElementById('reelUrl').value.trim();
            if (!url) {
                showAlert('Please enter a valid Instagram URL', 'error');
                return;
            }

            showLoader('Starting upload process...');

            try {
                const response = await fetch('/auto-upload-async', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();
                hideLoader();

                if (data.success) {
                    currentTaskId = data.task_id;
                    showProgressSection();
                    startProgressTracking();
                    clearResultContainer();
                } else {
                    if (response.status === 401) {
                        showAlert('Please connect your YouTube channel first.', 'error');
                    } else {
                        showAlert(data.error || 'Failed to start upload process', 'error');
                    }
                }
            } catch (error) {
                hideLoader();
                showAlert('Network error: ' + error.message, 'error');
            }
        }

        // Progress tracking
        function startProgressTracking() {
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
            }
            
            statusCheckInterval = setInterval(checkTaskStatus, 2000);
        }

        async function checkTaskStatus() {
            if (!currentTaskId) return;
            
            try {
                const response = await fetch(`/task-status/${currentTaskId}`);
                const data = await response.json();
                
                if (data.success) {
                    updateProgress(data.task);
                    
                    if (data.task.status === 'completed' || data.task.status === 'failed') {
                        clearInterval(statusCheckInterval);
                        
                        if (data.task.status === 'completed') {
                            showFinalSuccess(data.task);
                            addToHistory(data.task);
                        } else {
                            showAlert(data.task.error || 'Upload failed', 'error');
                        }
                    }
                }
            } catch (error) {
                console.error('Error checking task status:', error);
            }
        }

        function updateProgress(task) {
            const progressBar = document.getElementById('progressBar');
            const progressPercentage = document.getElementById('progressPercentage');
            
            const statusMap = {
                'started': { progress: 10 },
                'downloading': { progress: 30 },
                'generating_metadata': { progress: 60 },
                'uploading': { progress: 80 },
                'completed': { progress: 100 }
            };
            
            const progress = statusMap[task.status]?.progress || 0;
            
            progressBar.style.width = `${progress}%`;
            progressPercentage.textContent = `${progress}%`;
            
            // Update step states
            const allSteps = ['started', 'downloading', 'generating_metadata', 'uploading', 'completed'];
            const currentIndex = allSteps.indexOf(task.status);
            
            allSteps.forEach((step, index) => {
                const stepElement = document.getElementById(`step-${step}`);
                stepElement.classList.remove('active', 'completed');
                
                if (index < currentIndex) {
                    stepElement.classList.add('completed');
                } else if (index === currentIndex) {
                    stepElement.classList.add('active');
                }
            });
        }
        
        // UI Helpers
        function showLoader(message) {
            document.getElementById('loaderText').textContent = message || 'Processing...';
            document.getElementById('loader').style.display = 'flex';
        }

        function hideLoader() {
            document.getElementById('loader').style.display = 'none';
        }
        
        function showAlert(message, type = 'success') {
            const alertsContainer = document.getElementById('alerts');
            const alert = document.createElement('div');
            
            alert.className = `alert alert-${type}`;
            alert.innerHTML = `
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle'}"></i>
                <span>${message}</span>
            `;
            
            alertsContainer.appendChild(alert);
            
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.style.animation = 'slideInRight 0.5s ease reverse';
                    setTimeout(() => {
                        alertsContainer.removeChild(alert);
                    }, 500);
                }
            }, 5000);
        }
        
        function showProgressSection() {
            document.getElementById('progressSection').style.display = 'block';
        }
        
        function showLoginPanel() {
            hideAllPanels();
            document.getElementById('loginPanel').classList.add('active');
            document.getElementById('channelInfo').classList.remove('active');
            document.getElementById('logoutBtn').style.display = 'none';
        }
        
        function showDashboard() {
            document.getElementById('loginPanel').classList.remove('active');
            showPanel('uploadPanel');
        }
        
        function showPanel(panelId) {
            hideAllPanels();
            document.getElementById(panelId).style.display = 'block';
            
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('onclick')?.includes(panelId)) {
                    link.classList.add('active');
                }
            });
        }
        
        function hideAllPanels() {
            document.querySelectorAll('.content-panel').forEach(panel => {
                panel.style.display = 'none';
            });
        }
        
        function clearResultContainer() {
            document.getElementById('resultContainer').innerHTML = '';
        }
        
        // Result Display Functions
        function showPreviewResult(data) {
            const resultContainer = document.getElementById('resultContainer');
            resultContainer.innerHTML = `
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-icon" style="background: var(--gradient-secondary);">
                            <i class="fas fa-eye"></i>
                        </div>
                        <h3 class="result-title">AI Content Preview</h3>
                    </div>
                    
                    <div class="metadata-grid">
                        <div class="metadata-item">
                            <div class="metadata-label">Generated Title</div>
                            <div class="metadata-value">${data.title}</div>
                        </div>
                        
                        <div class="metadata-item">
                            <div class="metadata-label">Description</div>
                            <div class="metadata-value" style="max-height: 150px; overflow-y: auto;">${data.description}</div>
                        </div>
                        
                        <div class="metadata-item">
                            <div class="metadata-label">Tags</div>
                            <div class="tags-container">
                                ${data.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                            </div>
                        </div>
                        
                        <div class="metadata-item">
                            <div class="metadata-label">Hashtags</div>
                            <div class="tags-container">
                                ${data.hashtags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 24px; text-align: right;">
                        <button class="btn btn-primary" onclick="autoUploadBackground()">
                            <i class="fas fa-rocket"></i>
                            <span>Upload with this content</span>
                        </button>
                    </div>
                </div>
            `;
        }
        
        function showDownloadResult(data) {
            const resultContainer = document.getElementById('resultContainer');
            resultContainer.innerHTML = `
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-icon">
                            <i class="fas fa-download"></i>
                        </div>
                        <h3 class="result-title">Download Complete</h3>
                    </div>
                    
                    <div class="metadata-item">
                        <div class="metadata-label">File Information</div>
                        <div class="metadata-value">
                            <strong>Filename:</strong> ${data.filename}
                        </div>
                        <div style="margin-top: 16px;">
                            <a href="/get-video/${data.filename}" download class="btn btn-primary">
                                <i class="fas fa-download"></i>
                                <span>Download File</span>
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function showFinalSuccess(task) {
            const metadata = task.metadata || {};
            const resultContainer = document.getElementById('resultContainer');
            
            resultContainer.innerHTML = `
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-icon">
                            <i class="fas fa-check"></i>
                        </div>
                        <h3 class="result-title">Upload Successful!</h3>
                    </div>
                    
                    <div class="metadata-grid">
                        <div class="metadata-item">
                            <div class="metadata-label">YouTube Video</div>
                            <div class="metadata-value">
                                <strong>URL:</strong> <a href="${task.youtube_url}" target="_blank" style="color: var(--primary);">${task.youtube_url}</a>
                            </div>
                            <div style="margin-top: 16px;">
                                <a href="${task.youtube_url}" target="_blank" class="btn btn-primary">
                                    <i class="fab fa-youtube"></i>
                                    <span>Watch on YouTube</span>
                                </a>
                            </div>
                        </div>
                        
                        <div class="metadata-item">
                            <div class="metadata-label">AI Generated Title</div>
                            <div class="metadata-value">${metadata.title || 'N/A'}</div>
                        </div>
                        
                        <div class="metadata-item">
                            <div class="metadata-label">Tags</div>
                            <div class="tags-container">
                                ${(metadata.tags || []).map(tag => `<span class="tag">${tag}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // History Management
        function addToHistory(task) {
            const metadata = task.metadata || {};
            
            const historyEntry = {
                id: task.id,
                date: new Date().toISOString(),
                title: metadata.title || 'Untitled Video',
                youtubeUrl: task.youtube_url,
                thumbnail: ''
            };
            
            uploadHistory.unshift(historyEntry);
            
            if (uploadHistory.length > 10) {
                uploadHistory = uploadHistory.slice(0, 10);
            }
            
            localStorage.setItem('uploadHistory', JSON.stringify(uploadHistory));
            
            if (document.getElementById('historyPanel').style.display !== 'none') {
                renderUploadHistory();
            }
        }
        
        function renderUploadHistory() {
            const historyContainer = document.getElementById('historyItems');
            
            if (uploadHistory.length === 0) {
                historyContainer.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                        <i class="fas fa-history" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                        <p>No upload history yet</p>
                    </div>
                `;
                return;
            }
            
            const historyHTML = uploadHistory.map(item => `
                <div class="metadata-item" style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin-bottom: 4px; color: var(--text-primary);">${item.title}</h4>
                        <p style="font-size: 12px; color: var(--text-muted);">${new Date(item.date).toLocaleString()}</p>
                    </div>
                    <a href="${item.youtubeUrl}" target="_blank" class="btn btn-secondary" style="padding: 8px 16px;">
                        <i class="fab fa-youtube"></i>
                        <span>Watch</span>
                    </a>
                </div>
            `).join('');
            
            historyContainer.innerHTML = historyHTML;
        }
        
        // Settings management
        function loadSettings() {
            const settings = JSON.parse(localStorage.getItem('youtubeSettings') || '{}');
            
            if (settings.defaultPrivacy) {
                document.getElementById('defaultPrivacy').value = settings.defaultPrivacy;
            }
            
            if (settings.defaultCategory) {
                document.getElementById('defaultCategory').value = settings.defaultCategory;
            }
            
            if (settings.aiCustomization) {
                document.getElementById('aiCustomization').value = settings.aiCustomization;
            }
        }
        
        function saveSettings() {
            const settings = {
                defaultPrivacy: document.getElementById('defaultPrivacy').value,
                defaultCategory: document.getElementById('defaultCategory').value,
                aiCustomization: document.getElementById('aiCustomization').value
            };
            
            localStorage.setItem('youtubeSettings', JSON.stringify(settings));
            showAlert('Settings saved successfully', 'success');
        }
        
        // Utilities
        function formatNumber(numStr) {  
            const num = parseInt(numStr, 10);
            if (isNaN(num)) return '0';
            
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            } else {
                return num.toString();
            }
        }
    