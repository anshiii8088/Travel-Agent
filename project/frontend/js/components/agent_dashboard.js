export function renderAgentDashboard(data) {
  const dashboard = document.querySelector('#agent-dashboard');
  const badge = document.querySelector('#step-status');

  if (!data) {
    dashboard.className = 'agent-dashboard empty-state';
    dashboard.innerHTML = '<p>Activity will appear here as the agent thinks, acts, and looks.</p>';
    badge.textContent = 'Idle';
    return;
  }

  const planSteps = (data.plan && data.plan.steps) || [
    { number: 1, title: 'Understand travel preferences', status: 'active' },
    { number: 2, title: 'Find attractions and hotels', status: 'pending' },
    { number: 3, title: 'Check weather', status: 'pending' },
    { number: 4, title: 'Plan routes', status: 'pending' },
    { number: 5, title: 'Calculate budget', status: 'pending' },
  ];

  badge.textContent = data.status || 'READY';
  dashboard.className = 'agent-dashboard';
  dashboard.innerHTML = `
    <div class="summary-card">
      <div class="metric">
        <div class="metric-label">Session</div>
        <strong>${data.session_id || 'demo-session'}</strong>
      </div>
      <div class="metric">
        <div class="metric-label">Current phase</div>
        <strong>${data.status || 'READY'}</strong>
      </div>
      <div class="metric">
        <div class="metric-label">Step count</div>
        <strong>${data.steps_taken || 0} / 10</strong>
      </div>
    </div>

    <div class="budget-card">
      <h3>Execution plan</h3>
      <div class="plan-list">
        ${planSteps.map((step) => `
          <div class="plan-step ${step.status === 'active' ? 'active' : ''}">
            <strong>Step ${step.number}</strong>
            <span>${step.title}</span>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="budget-card">
      <h3>Safety notes</h3>
      <p>${data.pending_approval_prompt || 'No approval required right now.'}</p>
      <p>${data.error_message || 'No recovery issues reported.'}</p>
    </div>
  `;
}
