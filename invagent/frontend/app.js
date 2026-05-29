const API_URL = 'http://localhost:8000/api';

const elements = {
    time: document.getElementById('time-val'),
    demand: document.getElementById('demand-val'),
    retCost: document.getElementById('retailer-cost-val'),
    distCost: document.getElementById('distributor-cost-val'),
    
    retInv: document.getElementById('ret-inv'),
    retBack: document.getElementById('ret-back'),
    retTrans: document.getElementById('ret-trans'),
    retReasoning: document.getElementById('ret-reasoning'),
    retDecision: document.getElementById('ret-decision'),
    
    distInv: document.getElementById('dist-inv'),
    distBack: document.getElementById('dist-back'),
    distTrans: document.getElementById('dist-trans'),
    distReasoning: document.getElementById('dist-reasoning'),
    distDecision: document.getElementById('dist-decision'),
    
    resetBtn: document.getElementById('reset-btn'),
    stepBtn: document.getElementById('step-btn')
};

async function fetchState() {
    try {
        const response = await fetch(`${API_URL}/state`);
        const data = await response.json();
        updateUI(data.state);
    } catch (e) {
        console.error("Failed to fetch state. Is the backend running?", e);
    }
}

async function resetSimulation() {
    try {
        elements.resetBtn.disabled = true;
        const response = await fetch(`${API_URL}/reset`, { method: 'POST' });
        const data = await response.json();
        updateUI(data.state);
        
        // Reset reasoning texts
        elements.retReasoning.textContent = "Waiting for simulation step...";
        elements.distReasoning.textContent = "Waiting for simulation step...";
        elements.retDecision.textContent = "Order 0";
        elements.distDecision.textContent = "Order 0";
        elements.demand.textContent = "-";
        
    } catch (e) {
        console.error("Failed to reset.", e);
    } finally {
        elements.resetBtn.disabled = false;
    }
}

async function stepSimulation() {
    try {
        elements.stepBtn.disabled = true;
        elements.stepBtn.textContent = 'Thinking...';
        
        const response = await fetch(`${API_URL}/step`, { method: 'POST' });
        const data = await response.json();
        
        updateUI(data.state);
        
        // Update specific step details
        elements.demand.textContent = data.step_details.customer_demand;
        
        // Update Agent Reasoning
        typeWriterEffect(elements.retReasoning, data.decisions.retailer.reasoning);
        elements.retDecision.textContent = `Order ${data.decisions.retailer.order_quantity}`;
        
        typeWriterEffect(elements.distReasoning, data.decisions.distributor.reasoning);
        elements.distDecision.textContent = `Order ${data.decisions.distributor.order_quantity}`;
        
    } catch (e) {
        console.error("Failed to step simulation.", e);
        alert("Backend not running or error occurred.");
    } finally {
        elements.stepBtn.disabled = false;
        elements.stepBtn.textContent = 'Step Simulation';
    }
}

function updateUI(state) {
    elements.time.textContent = state.time;
    
    elements.retCost.textContent = `$${state.retailer.total_cost.toFixed(2)}`;
    elements.retInv.textContent = state.retailer.inventory;
    elements.retBack.textContent = state.retailer.backlog;
    elements.retTrans.textContent = state.retailer.in_transit;
    
    elements.distCost.textContent = `$${state.distributor.total_cost.toFixed(2)}`;
    elements.distInv.textContent = state.distributor.inventory;
    elements.distBack.textContent = state.distributor.backlog;
    elements.distTrans.textContent = state.distributor.in_transit;
}

function typeWriterEffect(element, text) {
    element.textContent = '';
    let i = 0;
    const speed = 15; // ms per char
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

// Event Listeners
elements.resetBtn.addEventListener('click', resetSimulation);
elements.stepBtn.addEventListener('click', stepSimulation);

// Init
fetchState();
