import { sendChatMessage } from '../api.js';

export function bindChatInterface() {
  const chatForm = document.querySelector('#chat-form');
  const chatInput = document.querySelector('#chat-input');
  const chatMessages = document.querySelector('#chat-messages');
  const quickActions = document.querySelectorAll('.chip');

  const appendMessage = (role, text) => {
    const message = document.createElement('div');
    message.className = `message ${role}`;
    message.innerHTML = `<p>${text}</p>`;
    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  quickActions.forEach((button) => {
    button.addEventListener('click', async () => {
      const message = button.dataset.message;
      if (!message) return;
      appendMessage('user', message);
      chatInput.value = message;
      await sendChatWithCurrentSession(message);
    });
  });

  async function sendChatWithCurrentSession(message) {
    const sessionId = document.querySelector('#trip-form')?.dataset?.sessionId || 'demo-session';
    try {
      const response = await sendChatMessage(sessionId, message, null);
      appendMessage('bot', response.response || 'I can help with that.');
    } catch (error) {
      appendMessage('bot', error.message || 'The assistant is unavailable right now.');
    }
  }

  chatForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;
    appendMessage('user', message);
    chatInput.value = '';
    await sendChatWithCurrentSession(message);
  });
}
