let paperSteps = [];
let currentPaperStep = 0;
let completedSteps = new Set();

const pfElements = {
    timeline: document.getElementById('pf-timeline'),
    stepNum: document.getElementById('pf-step-num'),
    stepTotal: document.getElementById('pf-step-total'),
    title: document.getElementById('pf-title'),
    subtitle: document.getElementById('pf-subtitle'),
    concept: document.getElementById('pf-concept'),
    insight: document.getElementById('pf-insight'),
    observe: document.getElementById('pf-observe'),
    prevBtn: document.getElementById('pf-prev'),
    nextBtn: document.getElementById('pf-next'),
    panel: document.getElementById('paper-flow-panel')
};

async function initPaperFlow() {
    try {
        const res = await fetch('/api/paper/steps');
        const data = await res.json();
        paperSteps = data.steps;
        pfElements.stepTotal.textContent = paperSteps.length;
        renderTimeline();
        await loadPaperStep(1);
    } catch (e) {
        console.error('Failed to load paper steps', e);
    }
}

function renderTimeline() {
    pfElements.timeline.innerHTML = '';
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
        pfElements.timeline.appendChild(dot);
    });
}

function updateTimelineState() {
    pfElements.timeline.querySelectorAll('.pf-dot').forEach(dot => {
        const id = parseInt(dot.dataset.id);
        dot.classList.toggle('active', id === currentPaperStep);
        dot.classList.toggle('done', completedSteps.has(id) && id !== currentPaperStep);
    });
}

async function loadPaperStep(stepId) {
    pfElements.nextBtn.disabled = true;
    pfElements.prevBtn.disabled = true;
    pfElements.nextBtn.textContent = 'Running…';

    try {
        const res = await fetch(`/api/paper/step/${stepId}`, { method: 'POST' });
        const data = await res.json();
        const step = data.step;

        currentPaperStep = stepId;
        completedSteps.add(stepId);

        // Update content panel
        pfElements.stepNum.textContent = stepId;
        pfElements.title.textContent = step.title;
        pfElements.subtitle.textContent = step.subtitle;
        pfElements.concept.textContent = step.concept;
        pfElements.insight.textContent = step.key_insight;
        pfElements.observe.textContent = step.what_to_observe;

        // Update simulation UI if the step ran a sim action
        if (data.state) {
            updateUI(data.state);
        }
        if (data.sim_result) {
            const sr = data.sim_result;
            if (typeof elements !== 'undefined') {
                elements.demand.textContent = sr.step_details.customer_demand;
                typeWriterEffect(elements.retReasoning, sr.decisions.retailer.reasoning);
                elements.retDecision.textContent = `Order ${sr.decisions.retailer.order_quantity}`;
                typeWriterEffect(elements.distReasoning, sr.decisions.distributor.reasoning);
                elements.distDecision.textContent = `Order ${sr.decisions.distributor.order_quantity}`;
                if (sr.step_details.workflow_log) {
                    renderWorkflowLog(sr.step_details.workflow_log, sr.step_details.time);
                }
            }
        }

        updateTimelineState();
        highlightSection(step.highlight);

    } catch (e) {
        console.error('Failed to run paper step', e);
    } finally {
        pfElements.prevBtn.disabled = currentPaperStep <= 1;
        pfElements.nextBtn.disabled = currentPaperStep >= paperSteps.length;
        pfElements.nextBtn.textContent = currentPaperStep >= paperSteps.length ? 'Complete ✓' : 'Next →';
    }
}

function highlightSection(section) {
    // Remove previous highlights
    document.querySelectorAll('.pf-highlight').forEach(el => el.classList.remove('pf-highlight'));

    const targets = {
        overview:  [document.querySelector('.overview')],
        agents:    [document.querySelector('.agents-container')],
        reasoning: [...document.querySelectorAll('.reasoning-box')],
        transit:   [...document.querySelectorAll('.stat')].filter(s => s.querySelector('.label')?.textContent === 'In Transit'),
        costs:     [document.querySelector('.overview')],
        workflow:  [document.getElementById('workflow-log-panel')],
        all:       [document.querySelector('main')]
    };

    (targets[section] || []).forEach(el => el && el.classList.add('pf-highlight'));
}

pfElements.nextBtn.addEventListener('click', () => {
    if (currentPaperStep < paperSteps.length) loadPaperStep(currentPaperStep + 1);
});
pfElements.prevBtn.addEventListener('click', () => {
    if (currentPaperStep > 1) loadPaperStep(currentPaperStep - 1);
});

// Init after DOM is ready
document.addEventListener('DOMContentLoaded', initPaperFlow);
