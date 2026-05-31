const API_URL = '/api';

const STAGE_IDS = ['s0', 's1', 's2', 's3'];
const STAGE_NAMES = ['Retailer', 'Wholesaler', 'Distributor', 'Manufacturer'];

// ── Element references ─────────────────────────────────────────────────────

const el = {
    timeVal:     document.getElementById('time-val'),
    demandVal:   document.getElementById('demand-val'),
    scenarioVal: document.getElementById('scenario-val'),
    statusVal:   document.getElementById('status-val'),
    periodNum:   document.getElementById('period-num'),
    periodFill:  document.getElementById('period-fill'),
    resetBtn:    document.getElementById('reset-btn'),
    stepBtn:     document.getElementById('step-btn'),
    workflowSteps: document.getElementById('workflow-steps'),
    stepTag:     document.getElementById('step-tag'),
    resultsPanel:  document.getElementById('results-panel'),
    resultsContent: document.getElementById('results-content'),
};

// ── State ──────────────────────────────────────────────────────────────────

let currentScenario = 'variable';

// ── Scenario selector ──────────────────────────────────────────────────────

document.querySelectorAll('.scenario-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const scenario = btn.dataset.scenario;
        if (scenario === currentScenario) return;

        document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        try {
            const res = await fetch(`${API_URL}/scenario`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario }),
            });
            const data = await res.json();
            if (data.error) { console.error(data.error); return; }
            currentScenario = scenario;
            updateUI(data.state);
            resetReasoning();
            clearResults();
        } catch (e) {
            console.error('Scenario switch failed', e);
        }
    });
});

// ── Reset / New Episode ────────────────────────────────────────────────────

el.resetBtn.addEventListener('click', async () => {
    el.resetBtn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/episode/start`, { method: 'POST' });
        const data = await res.json();
        updateUI(data.state);
        resetReasoning();
        clearResults();
    } catch (e) {
        console.error('Reset failed', e);
    } finally {
        el.resetBtn.disabled = false;
    }
});

// ── Step ───────────────────────────────────────────────────────────────────

el.stepBtn.addEventListener('click', stepEpisode);

async function stepEpisode() {
    el.stepBtn.disabled = true;
    el.stepBtn.textContent = 'Running…';
    try {
        const res = await fetch(`${API_URL}/episode/step`, { method: 'POST' });
        const data = await res.json();

        if (data.status === 'done') {
            el.statusVal.textContent = 'Done';
            el.stepBtn.textContent = 'Step →';
            el.stepBtn.disabled = true;
            return;
        }

        updateUI({ period: data.period, customer_demand: data.customer_demand,
                   is_done: data.is_done, stages: data.stages,
                   scenario: currentScenario });

        // Update agent cards
        data.decisions.forEach(d => {
            const prefix = STAGE_IDS[d.stage];
            typeWriter(document.getElementById(`${prefix}-reasoning`), d.reasoning);
            document.getElementById(`${prefix}-decision`).textContent = `Order ${d.order_quantity}`;
        });

        // Update reward totals from stages
        data.stages.forEach((s, i) => {
            const rEl = document.getElementById(`${STAGE_IDS[i]}-reward`);
            if (rEl) rEl.textContent = s.total_reward.toFixed(1);
        });

        renderWorkflowLog(data.workflow_log, data.period);

        if (data.is_done) {
            el.statusVal.textContent = 'Done';
            el.stepBtn.disabled = true;
            if (data.baseline_rewards) renderResults(data.baseline_rewards);
        }

    } catch (e) {
        console.error('Step failed', e);
        showWorkflowError('Backend error. Check the console.');
    } finally {
        el.stepBtn.textContent = 'Step →';
        if (!el.stepBtn.disabled) el.stepBtn.disabled = false;
    }
}

// ── UI update ──────────────────────────────────────────────────────────────

function updateUI(state) {
    const period = state.period ?? 0;
    const maxP   = state.max_periods ?? 12;

    el.timeVal.textContent    = `${period} / ${maxP}`;
    el.periodNum.textContent  = period;
    el.periodFill.style.width = `${(period / maxP) * 100}%`;
    el.demandVal.textContent  = state.customer_demand != null ? state.customer_demand : '—';
    el.scenarioVal.textContent = capitalize(state.scenario || currentScenario);
    el.statusVal.textContent   = state.is_done ? 'Done' : (period === 0 ? 'Ready' : 'Running');

    if (state.is_done) el.stepBtn.disabled = true;
    else { el.stepBtn.disabled = false; el.stepBtn.textContent = 'Step →'; }

    if (!state.stages) return;
    state.stages.forEach((s, i) => {
        const prefix = STAGE_IDS[i];
        setVal(`${prefix}-inv`,    s.inventory);
        setVal(`${prefix}-back`,   s.backlog);
        setVal(`${prefix}-pipe`,   s.pipeline ? s.pipeline.reduce((a, b) => a + b, 0) : 0);
        setVal(`${prefix}-upback`, s.upstream_backlog ?? 0);
        const rEl = document.getElementById(`${prefix}-reward`);
        if (rEl) rEl.textContent = (s.total_reward ?? 0).toFixed(1);
    });
}

function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function resetReasoning() {
    STAGE_IDS.forEach(prefix => {
        const r = document.getElementById(`${prefix}-reasoning`);
        const d = document.getElementById(`${prefix}-decision`);
        if (r) r.textContent = 'Waiting for simulation step…';
        if (d) d.textContent = 'Order 0';
        const rw = document.getElementById(`${prefix}-reward`);
        if (rw) rw.textContent = '0';
    });
    el.workflowSteps.innerHTML = '<div class="workflow-empty">Press "Step →" to see the execution trace.</div>';
    el.stepTag.textContent = '—';
    el.demandVal.textContent = '—';
    el.statusVal.textContent = 'Ready';
    el.stepBtn.disabled = false;
    el.stepBtn.textContent = 'Step →';
}

function clearResults() {
    el.resultsPanel.style.display = 'none';
    el.resultsContent.innerHTML = '';
}

// ── Results panel ──────────────────────────────────────────────────────────

function renderResults(rewards) {
    el.resultsPanel.style.display = 'block';

    const llm = rewards.llm             || [0, 0, 0, 0];
    const bs  = rewards.base_stock      || [0, 0, 0, 0];
    const td  = rewards.tracking_demand || [0, 0, 0, 0];

    const llmTotal = llm.reduce((a, b) => a + b, 0);
    const bsTotal  = bs.reduce((a, b) => a + b, 0);
    const tdTotal  = td.reduce((a, b) => a + b, 0);

    const allVals = [...llm, ...bs, ...td];
    const maxAbs  = Math.max(1, Math.max(...allVals.map(Math.abs)));

    let rows = STAGE_NAMES.map((name, i) => `
        <tr>
            <td>${name}</td>
            <td class="${colorClass(llm[i])}">${llm[i].toFixed(1)}</td>
            <td class="${colorClass(bs[i])}">${bs[i].toFixed(1)}</td>
            <td class="${colorClass(td[i])}">${td[i].toFixed(1)}</td>
        </tr>
    `).join('');

    el.resultsContent.innerHTML = `
        <p class="results-note">Higher reward = better. Costs are negative contributions.</p>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Stage</th>
                    <th>LLM Agent</th>
                    <th>Base-Stock</th>
                    <th>Tracking-Demand</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
            <tfoot>
                <tr class="totals-row">
                    <td><strong>Total</strong></td>
                    <td class="${colorClass(llmTotal)}"><strong>${llmTotal.toFixed(1)}</strong></td>
                    <td class="${colorClass(bsTotal)}"><strong>${bsTotal.toFixed(1)}</strong></td>
                    <td class="${colorClass(tdTotal)}"><strong>${tdTotal.toFixed(1)}</strong></td>
                </tr>
            </tfoot>
        </table>
        <div class="bar-chart">
            ${barRow('LLM Agent',        llmTotal, maxAbs, 'bar-llm')}
            ${barRow('Base-Stock',        bsTotal,  maxAbs, 'bar-bs')}
            ${barRow('Tracking-Demand',   tdTotal,  maxAbs, 'bar-td')}
        </div>
    `;
}

function colorClass(val) {
    return val > 0 ? 'reward-pos' : val < 0 ? 'reward-neg' : '';
}

function barRow(label, val, maxAbs, cls) {
    const pct = Math.min(100, (Math.abs(val) / maxAbs) * 100);
    const side = val >= 0 ? 'right' : 'left';
    return `
        <div class="bar-row">
            <span class="bar-label">${label}</span>
            <div class="bar-track">
                <div class="bar-fill ${cls}" style="width:${pct}%"></div>
            </div>
            <span class="bar-value ${colorClass(val)}">${val.toFixed(1)}</span>
        </div>
    `;
}

// ── Workflow log ───────────────────────────────────────────────────────────

function renderWorkflowLog(log, period) {
    el.stepTag.textContent = `Period ${period}`;
    el.workflowSteps.innerHTML = '';
    log.forEach((entry, idx) => {
        const item = document.createElement('div');
        item.className = 'workflow-item';
        item.style.animationDelay = `${idx * 40}ms`;
        item.innerHTML = `
            <span class="workflow-index">${idx + 1}</span>
            <span class="workflow-phase">${entry.phase}</span>
            <span class="workflow-detail">${entry.detail}</span>
        `;
        el.workflowSteps.appendChild(item);
    });
}

function showWorkflowError(msg) {
    el.stepTag.textContent = 'Error';
    el.workflowSteps.innerHTML = `<div class="workflow-error">${msg}</div>`;
}

// ── Typewriter ─────────────────────────────────────────────────────────────

function typeWriter(element, text) {
    element.textContent = '';
    let i = 0;
    function tick() {
        if (i < text.length) {
            element.textContent += text.charAt(i++);
            setTimeout(tick, 12);
        }
    }
    tick();
}

// ── Init ───────────────────────────────────────────────────────────────────

async function init() {
    try {
        const res = await fetch(`${API_URL}/episode/state`);
        const data = await res.json();
        updateUI(data.state);
        currentScenario = data.state.scenario || 'variable';
        document.querySelectorAll('.scenario-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.scenario === currentScenario);
        });
    } catch (e) {
        console.error('Init failed', e);
    }
}

init();
