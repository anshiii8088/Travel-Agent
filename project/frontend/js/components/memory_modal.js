import { deletePreference, getPreferences, upsertPreference } from '../api.js';

export function bindMemoryModal() {
  const modal = document.querySelector('#memory-modal');
  const openButton = document.querySelector('#open-memory');
  const closeButton = document.querySelector('#close-memory');
  const content = document.querySelector('#memory-content');

  async function refreshPreferences() {
    try {
      const prefs = await getPreferences();
      const entries = Object.entries(prefs || {});
      if (!entries.length) {
        content.innerHTML = '<p>No saved preferences yet.</p>';
        return;
      }

      content.innerHTML = entries.map(([key, value]) => `
        <div class="preference-item">
          <div>
            <strong>${key}</strong>
            <div>${JSON.stringify(value.value ?? value)}</div>
          </div>
          <button data-key="${key}">Delete</button>
        </div>
      `).join('');

      content.querySelectorAll('button[data-key]').forEach((button) => {
        button.addEventListener('click', async () => {
          await deletePreference(button.dataset.key);
          await refreshPreferences();
        });
      });
    } catch (error) {
      content.innerHTML = `<p>${error.message}</p>`;
    }
  }

  openButton.addEventListener('click', async () => {
    modal.classList.remove('hidden');
    await refreshPreferences();
  });

  closeButton.addEventListener('click', () => {
    modal.classList.add('hidden');
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      modal.classList.add('hidden');
    }
  });

  const seedButton = document.createElement('button');
  seedButton.className = 'secondary-btn';
  seedButton.textContent = 'Save sample preference';
  seedButton.addEventListener('click', async () => {
    await upsertPreference({ key: 'favorite_activities', value: ['Nature', 'Tea tasting'] });
    await refreshPreferences();
  });

  content.appendChild(seedButton);
}
