import { bindTripForm } from './components/trip_form.js';
import { renderItinerary } from './components/itinerary_view.js';
import { renderAgentDashboard } from './components/agent_dashboard.js';
import { bindChatInterface } from './components/chat_interface.js';
import { bindMemoryModal } from './components/memory_modal.js';

const defaultItinerary = {
  destination: 'Munnar',
  overview: 'A balanced three-day escape with scenic viewpoints, tea estates, and local dining.',
  daily_schedule: [
    {
      day_number: 1,
      title: 'Day 1: Arrival and tea garden loop',
      attractions: [{ name: 'Munnar Tea Gardens', description: 'Enjoy scenic walking trails and local tea tastings.', recommended_time: '09:00 AM', duration_hours: 2.5, estimated_cost: 450 }],
      meals: [{ meal_type: 'Lunch', restaurant_name: 'Tea Valley Cafe', cuisine: 'South Indian', estimated_cost: 350 }],
      day_total_cost: 1000,
    },
    {
      day_number: 2,
      title: 'Day 2: Waterfalls and viewpoints',
      attractions: [{ name: 'Attukal Falls', description: 'Gentle trekking and photography stop.', recommended_time: '08:30 AM', duration_hours: 3, estimated_cost: 250 }],
      meals: [{ meal_type: 'Dinner', restaurant_name: 'Hill View Bistro', cuisine: 'Regional', estimated_cost: 420 }],
      day_total_cost: 1200,
    },
  ],
  hotels: [{ name: 'Hillcrest Stay', location: 'Munnar', price_per_night: 1800, rating: 4.6 }],
  budget: {
    total_budget: 8000,
    total_estimated_cost: 6500,
    remaining_budget: 1500,
    is_over_budget: false,
    affordable_alternatives: ['Keep two local restaurants and one scenic stay'],
  },
  weather: [{ date: '2026-12-01', destination: 'Munnar', temperature_celsius: 22, condition: 'Cloudy', rain_probability_pct: 42 }],
  routes: [{ from_location: 'Kochi', to_location: 'Munnar', distance_km: 124, duration_minutes: 180 }],
};

function initialize() {
  bindTripForm();
  bindChatInterface();
  bindMemoryModal();
  renderItinerary(defaultItinerary);
  renderAgentDashboard({
    session_id: 'demo-session',
    status: 'READY',
    steps_taken: 0,
    plan: {
      steps: [
        { number: 1, title: 'Understand travel preferences', status: 'active' },
        { number: 2, title: 'Find attractions and hotels', status: 'pending' },
        { number: 3, title: 'Check weather', status: 'pending' },
        { number: 4, title: 'Plan routes', status: 'pending' },
        { number: 5, title: 'Calculate budget', status: 'pending' },
      ],
    },
  });

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((item) => item.classList.toggle('active', item === tab));
      document.querySelectorAll('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === `${tab.dataset.target}`));
    });
  });

  document.querySelector('#new-plan').addEventListener('click', () => {
    document.querySelector('#trip-form').reset();
    document.querySelector('#form-status').textContent = 'Ready for a new itinerary';
    document.querySelector('#itinerary-output').innerHTML = '<p>No itinerary generated yet. Fill in the form to create one.</p>';
    document.querySelector('#agent-dashboard').innerHTML = '<p>Activity will appear here as the agent thinks, acts, and looks.</p>';
  });
}

initialize();
