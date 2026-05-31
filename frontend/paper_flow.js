let paperSteps = [];
let currentPaperStep = 0;
let completedSteps = new Set();

const pfEl = {
    timeline:  document.getElementById('pf-timeline'),
    stepNum:   document.getElementById('pf-step-num'),
    stepTotal: document.getElementById('pf-step-total'),
    title:     document.getElementById('pf-title'),
    subtitle:  document.getElementById('pf-subtitle'),
    concept:   document.getElementById('pf-concept'),
    insight:   document.getElementById('pf-insight'),
    observe:   document.getElementById('pf-observe'),
    prevBtn:   document.getElementById('pf-prev'),
    nextBtn:   document.getElementById('pf-next'),
};

async function initPaperFlow() {
    try {
        const res = await fetch('/api/paper/steps');
        const data = await res.json();
        paperSteps = data.steps;
        pfEl.stepTotal.textContent = paperSteps.length;
        renderTimeline();
        await loadPaperStep(1);
    } catch (e) {
        console.error('Failed to load paper steps', e);
    }
}

function renderTimeline() {
    pfEl.timeline.innerHTML = '';
    paperSteps.forEach(s => {
        const dot = document.createElement('button');
        dot.className = 'pf-dot';
        dot.dataset.id = s.id;
        dot.setAttribute('aria-label', s.title);
        dot.innerHTML = `
            <span class="pf-dot-num">${s.id}</span>
            <span class="pf-dot-label">${s.title}</span>
        `;
        dot.addEventListener('click', () => loadPaperStep(s.id));
        pfEl.timeline.appendChild(dot);
    });
}

function updateTimelineState() {
    pfEl.timeline.querySelectorAll('.pf-dot').forEach(dot => {
        const id = parseInt(dot.dataset.id);
        dot.classList.toggle('active', id === currentPaperStep);
        dot.classList.toggle('done', completedSteps.has(id) && id !== currentPaperStep);
    });
}

async function loadPaperStep(stepId) {
    pfEl.nextBtn.disabled = true;
    pfEl.prevBtn.disabled = true;
    pfEl.nextBtn.textContent = 'Running…';

    try {
        const res = await fetch(`/api/paper/step/${stepId}`, { method: 'POST' });
        const data = await res.json();
        const step = data.step;

        currentPaperStep = stepId;
        completedSteps.add(stepId);

        pfEl.stepNum.textContent  = stepId;
        pfEl.title.textContent    = step.title;
        pfEl.subtitle.textContent = step.subtitle;
        pfEl.concept.textContent  = step.concept;
        pfEl.insight.textContent  = step.key_insight;
        pfEl.observe.textContent  = step.what_to_observe;

        // Update the main simulation UI from returned state
        if (data.state && typeof updateUI === 'function') {
            updateUI(data.state);
        }

        // If the step ran a simulation step, update agent cards
        if (data.sim_result) {
            const sr = data.sim_result;
            const decisions = sr.decisions || [];

            decisions.forEach(d => {
                const prefix = ['s0', 's1', 's2', 's3'][d.stage];
                if (!prefix) return;
                const rEl = document.getElementById(`${prefix}-reasoning`);
                const dEl = document.getElementById(`${prefix}-decision`);
                if (rEl && typeof typeWriter === 'function') typeWriter(rEl, d.reasoning);
                if (dEl) dEl.textContent = `Order ${d.order_quantity}`;
            });

            const sd = sr.step_details;
            if (sd) {
                if (typeof renderWorkflowLog === 'function' && sd.workflow_log) {
                    renderWorkflowLog(sd.workflow_log, sd.period);
                }
                if (typeof el !== 'undefined' && el.demandVal) {
                    el.demandVal.textContent = sd.customer_demand ?? '—';
                }
            }
        }

        updateTimelineState();
        highlightSection(step.highlight);

    } catch (e) {
        console.error('Failed to run paper step', e);
    } finally {
        pfEl.prevBtn.disabled = currentPaperStep <= 1;
        pfEl.nextBtn.disabled = currentPaperStep >= paperSteps.length;
        pfEl.nextBtn.textContent = currentPaperStep >= paperSteps.length ? 'Complete ✓' : 'Next →';
    }
}

function highlightSection(section) {
    document.querySelectorAll('.pf-highlight').forEach(e => e.classList.remove('pf-highlight'));
    const targets = {
        overview:  [document.querySelector('.overview')],
        agents:    [document.querySelector('.agents-grid')],
        scenario:  [document.querySelector('.scenario-bar')],
        reasoning: [...document.querySelectorAll('.reasoning-box')],
        transit:   [...document.querySelectorAll('.stat')].filter(
                       s => s.querySelector('.label')?.textContent === 'Pipeline'),
        costs:     [document.querySelector('.overview')],
        workflow:  [document.getElementById('workflow-log-panel')],
        results:   [document.getElementById('results-panel')],
        all:       [document.querySelector('main')],
    };
    (targets[section] || []).forEach(e => e && e.classList.add('pf-highlight'));
}

pfEl.nextBtn.addEventListener('click', () => {
    if (currentPaperStep < paperSteps.length) loadPaperStep(currentPaperStep + 1);
});
pfEl.prevBtn.addEventListener('click', () => {
    if (currentPaperStep > 1) loadPaperStep(currentPaperStep - 1);
});

document.addEventListener('DOMContentLoaded', initPaperFlow);
