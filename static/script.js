// JavaScript Frontend for Weather Assistant App

class WeatherApp {
    constructor() {
        this.sendMessageApiUrl = '/api/send_message';
        this.modelResponseApiUrl = '/api/model_response';
        this.messageHistoryApiUrl = '/api/message_history';
        this.clearHistoryApiUrl = '/api/clear_history';
        this.statusText = document.getElementById('status-text');
        this.sendBtn = document.getElementById('send-btn');
        this.clearHistoryBtn = document.getElementById('clear-history-btn');
        this.userPrompt = document.getElementById('user-prompt');
        this.chatMessages = document.getElementById('chat-messages');
        
        this.init();
    }

    init() {
        // Load chat history on page load
        this.loadChatHistory();
        
        // Add event listeners
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        
        // Add Enter key support for user prompt
        this.userPrompt.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async sendMessage() {
        const userMessage = this.userPrompt.value.trim();
        
        if (!userMessage) {
            this.setStatus('Please enter a message', 'error');
            return;
        }

        try {
            this.setStatus('Ready', '');
            this.sendBtn.disabled = true;
            this.sendBtn.innerHTML = '<span class="spinner"></span>';
            this.sendBtn.classList.add('loading');
            this.userPrompt.disabled = true;
            
            const response = await fetch(this.sendMessageApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: userMessage
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Clear the input field
            this.userPrompt.value = '';
            
            // Just update status and refresh chat history
            this.setStatus('Message sent successfully!', 'success');
            
            // Refresh chat history after getting response
            setTimeout(() => this.loadChatHistory(), 500);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.displayError('Failed to send message');
            this.setStatus('Error: Could not send message', 'error');
        } finally {
            this.sendBtn.disabled = false;
            this.sendBtn.innerHTML = 'Send';
            this.sendBtn.classList.remove('loading');
            this.userPrompt.disabled = false;
            this.userPrompt.focus();
        }
    }

    setStatus(message, type = '') {
        this.statusText.textContent = message;
        this.statusText.className = type;
    }

    async loadChatHistory() {
        try {
            const response = await fetch(this.messageHistoryApiUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.displayChatHistory(data.messageHistory);
            
        } catch (error) {
            console.error('Error fetching chat history:', error);
        }
    }

    displayChatHistory(messages) {
        this.chatMessages.innerHTML = '';
        
        if (!messages || messages.length === 0) {
            this.chatMessages.innerHTML = '<div class="message system">No conversation history yet.</div>';
            return;
        }

        // Filter out system messages to hide system instructions from UI
        const filteredMessages = messages.filter(message => message.role !== 'system');
        
        if (filteredMessages.length === 0) {
            this.chatMessages.innerHTML = '<div class="message system">No conversation history yet.</div>';
            return;
        }

        filteredMessages.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${message.role}`;
            
            const roleDiv = document.createElement('div');
            roleDiv.className = 'message-role';
            roleDiv.textContent = message.role;
            
            const contentDiv = document.createElement('div');
            
            // Handle different content formats
            if (typeof message.content === 'string') {
                contentDiv.textContent = message.content;
            } else if (Array.isArray(message.content)) {
                // Handle array content (like user messages)
                contentDiv.textContent = message.content.map(item => 
                    item.text || item.content || JSON.stringify(item)
                ).join(' ');
            } else {
                contentDiv.textContent = JSON.stringify(message.content);
            }
            
            messageDiv.appendChild(roleDiv);
            messageDiv.appendChild(contentDiv);
            this.chatMessages.appendChild(messageDiv);
        });

        // Auto-scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    async clearHistory() {
        try {
            this.setStatus('Clearing chat history...', 'loading');
            this.clearHistoryBtn.disabled = true;
            this.clearHistoryBtn.textContent = 'Clearing...';
            
            const response = await fetch(this.clearHistoryApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Refresh displays
            this.loadChatHistory();
            this.setStatus('Chat history cleared!', 'success');
            
        } catch (error) {
            console.error('Error clearing history:', error);
            this.setStatus('Error: Could not clear history', 'error');
        } finally {
            this.clearHistoryBtn.disabled = false;
            this.clearHistoryBtn.textContent = 'Clear History';
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WeatherApp();
});

// Add some visual feedback
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth transitions to all elements
    const style = document.createElement('style');
    style.textContent = `
        #intro-text {
            transition: opacity 0.3s ease;
            white-space: pre-wrap;
            text-align: left;
            font-size: 1.2rem;
            line-height: 1.4;
        }
        
        .refresh-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }
    `;
    document.head.appendChild(style);
});
