import { submitPlan } from '../api.js';
import { renderItinerary } from './itinerary_view.js';
import { renderAgentDashboard } from './agent_dashboard.js';

export function bindTripForm() {
  const form = document.querySelector('#trip-form');
  const status = document.querySelector('#form-status');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const payload = {
      origin: data.get('origin')?.toString().trim() || 'Kochi',
      destination: data.get('destination')?.toString().trim() || 'Munnar',
      start_date: data.get('start_date')?.toString() || '2026-12-01',
      days: Number(data.get('days') || 3),
      travellers: Number(data.get('travellers') || 2),
      budget: Number(data.get('budget') || 8000),
      currency: 'INR',
      preferences: {
        travel_style: data.get('travel_style')?.toString() || 'Balanced',
        interests: (data.get('interests')?.toString() || 'Nature,Sightseeing')
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean),
        dietary_preferences: 'Vegetarian',
        preferred_transport: 'Cab',
      },
    };

    status.textContent = 'Planning your trip...';
    status.style.color = '#335cff';

    try {
      const result = await submitPlan(payload);
      form.dataset.sessionId = result.session_id;
      status.textContent = `Session ready: ${result.session_id.slice(0, 8)}`;
      status.style.color = '#17b26a';

      if (result.itinerary) {
        renderItinerary(result.itinerary);
      }

      renderAgentDashboard({
        session_id: result.session_id,
        status: result.status,
        steps_taken: result.steps_taken,
        plan: result.plan,
        error_message: result.error_message,
        pending_approval_prompt: result.pending_approval_prompt,
      });
    } catch (error) {
      status.textContent = error.message;
      status.style.color = '#cf4d3f';
      document.querySelector('#itinerary-output').innerHTML = `<p>${error.message}</p>`;
    }
  });
}
