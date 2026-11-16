export function renderItinerary(itinerary) {
  const output = document.querySelector('#itinerary-output');

  if (!itinerary) {
    output.className = 'itinerary-output empty-state';
    output.innerHTML = '<p>No itinerary available.</p>';
    return;
  }

  const dailyCards = (itinerary.daily_schedule || []).map((day) => {
    const attractions = (day.attractions || []).map((attraction) => `
      <div class="attraction">
        <h4>${attraction.name}</h4>
        <p>${attraction.description}</p>
        <div class="badges">
          <span class="badge">${attraction.recommended_time}</span>
          <span class="badge">${attraction.duration_hours} hrs</span>
          <span class="badge">₹${attraction.estimated_cost || 0}</span>
        </div>
      </div>
    `).join('');

    const meals = (day.meals || []).map((meal) => `
      <div class="restaurant">
        <h4>${meal.restaurant_name}</h4>
        <p>${meal.cuisine} • ${meal.meal_type}</p>
        <span>₹${meal.estimated_cost}</span>
      </div>
    `).join('');

    return `
      <div class="day-card">
        <h3>${day.title || `Day ${day.day_number}`}</h3>
        <div class="attraction-list">${attractions || '<p>No attractions planned.</p>'}</div>
        <div class="restaurant-list">${meals || '<p>No meals assigned.</p>'}</div>
        <p><strong>Day cost:</strong> ₹${day.day_total_cost || 0}</p>
      </div>
    `;
  }).join('');

  const hotels = (itinerary.hotels || []).map((hotel) => `
    <div class="hotel">
      <h4>${hotel.name}</h4>
      <p>${hotel.location}</p>
      <span>₹${hotel.price_per_night || 0}/night • ${hotel.rating || 4.5}★</span>
    </div>
  `).join('');

  const routes = (itinerary.routes || []).map((route) => `
    <div class="route">
      <h4>${route.from_location} → ${route.to_location}</h4>
      <p>${route.distance_km || 0} km • ${route.duration_minutes || 0} mins</p>
    </div>
  `).join('');

  const budget = itinerary.budget || {};

  output.className = 'itinerary-output';
  output.innerHTML = `
    <div class="summary-card">
      <div class="metric">
        <div class="metric-label">Destination</div>
        <strong>${itinerary.destination}</strong>
      </div>
      <div class="metric">
        <div class="metric-label">Total budget</div>
        <strong>₹${budget.total_budget || itinerary.budget?.total_budget || 0}</strong>
      </div>
      <div class="metric">
        <div class="metric-label">Remaining</div>
        <strong>₹${budget.remaining_budget || 0}</strong>
      </div>
    </div>

    <div class="budget-card">
      <h3>Budget summary</h3>
      <p>${itinerary.overview || 'Personalized itinerary'}</p>
      <p><strong>Estimated total:</strong> ₹${budget.total_estimated_cost || 0}</p>
      <p><strong>Status:</strong> ${budget.is_over_budget ? 'Over budget' : 'Within budget'}</p>
      <div class="badges">
        ${(budget.affordable_alternatives || []).map((item) => `<span class="badge">${item}</span>`).join('') || '<span class="badge">No alternatives needed</span>'}
      </div>
    </div>

    <div class="day-card">
      <h3>Stay recommendations</h3>
      <div class="hotel-list">${hotels || '<p>No hotels listed.</p>'}</div>
    </div>

    <div class="day-card">
      <h3>Route overview</h3>
      <div class="route-list">${routes || '<p>No route information.</p>'}</div>
    </div>

    <div class="day-card">
      <h3>Day-by-day itinerary</h3>
      ${dailyCards || '<p>No daily plan available.</p>'}
    </div>
  `;
}
