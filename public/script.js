const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');

function appendMessage(text, isUser=false) {
  const div = document.createElement('div');
  div.textContent = (isUser ? 'You: ' : 'Bot: ') + text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

inputEl.addEventListener('keypress', async (e) => {
  if (e.key === 'Enter' && inputEl.value.trim()) {
    const text = inputEl.value.trim();
    appendMessage(text, true);
    inputEl.value = '';

    try {
      const resp = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await resp.json();
      appendMessage(JSON.stringify(data));
    } catch (err) {
      appendMessage('Error: ' + err.message);
    }
  }
});