const messagesEl = document.getElementById('chatbox'); // Matches your HTML ID
const inputEl = document.getElementById('usermsg');   // Matches your HTML ID

/**
 * Appends a message to the UI with basic formatting
 */
function appendMessage(role, text, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'msg';
    msgDiv.style.color = isError ? '#d9534f' : 'inherit';
    
    // Using innerHTML here allows the AI to send <br> or <table> 
    // Note: In production, use a library like 'marked' for secure markdown
    msgDiv.innerHTML = `<b>${role}:</b> ${text.replace(/\n/g, '<br>')}`;
    
    messagesEl.appendChild(msgDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msgDiv;
}

inputEl.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter' && inputEl.value.trim()) {
        const userText = inputEl.value.trim();
        
        // 1. Show User Message
        appendMessage('You', userText);
        inputEl.value = '';

        // 2. Show Loading State
        const loadingDiv = appendMessage('Assistant', '<i>Thinking...</i>');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userText })
            });

            if (!response.ok) throw new Error(`Server returned ${response.status}`);

            const data = await response.json();
            
            // 3. Remove loading text and show real response
            // We use .reply because that's what your FastAPI returns
            loadingDiv.innerHTML = `<b>Assistant:</b> ${data.reply.replace(/\n/g, '<br>')}`;

        } catch (err) {
            console.error('Chat Error:', err);
            loadingDiv.innerHTML = `<b>System:</b> Error - ${err.message}`;
            loadingDiv.style.color = '#d9534f';
        }
    }
});