const PROVIDER_DEFAULTS = {
    mock:        { needsKey: false, needsUrl: false, modelPlaceholder: '' },
    gemini:      { needsKey: true,  needsUrl: false, modelPlaceholder: 'gemini-1.5-flash' },
    ollama:      { needsKey: false, needsUrl: true,  modelPlaceholder: 'llama3' },
    openrouter:  { needsKey: true,  needsUrl: true,  modelPlaceholder: 'openai/gpt-3.5-turbo' },
};

const cfg = {
    panel:       document.getElementById('llm-config-panel'),
    toggle:      document.getElementById('llm-config-toggle'),
    provider:    document.getElementById('llm-provider'),
    keyRow:      document.getElementById('llm-key-row'),
    apiKey:      document.getElementById('llm-api-key'),
    urlRow:      document.getElementById('llm-url-row'),
    baseUrl:     document.getElementById('llm-base-url'),
    model:       document.getElementById('llm-model'),
    saveBtn:     document.getElementById('llm-save'),
    testBtn:     document.getElementById('llm-test'),
    status:      document.getElementById('llm-status'),
    badge:       document.getElementById('llm-badge'),
};

// ── Toggle collapse ────────────────────────────────────────────────────────
cfg.toggle.addEventListener('click', () => {
    const body = document.getElementById('llm-config-body');
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'flex';
    cfg.toggle.textContent = isOpen ? '▸' : '▾';
});

// ── Show/hide fields based on provider ────────────────────────────────────
cfg.provider.addEventListener('change', () => {
    const meta = PROVIDER_DEFAULTS[cfg.provider.value] || {};
    cfg.keyRow.style.display = meta.needsKey ? 'flex' : 'none';
    cfg.urlRow.style.display = meta.needsUrl ? 'flex' : 'none';
    cfg.model.placeholder = meta.modelPlaceholder || '';
    setStatus('');
});

// ── Save ──────────────────────────────────────────────────────────────────
cfg.saveBtn.addEventListener('click', async () => {
    const body = {
        provider: cfg.provider.value,
        api_key:  cfg.apiKey.value.trim() || null,
        base_url: cfg.baseUrl.value.trim() || null,
        model:    cfg.model.value.trim() || null,
    };
    cfg.saveBtn.disabled = true;
    cfg.saveBtn.textContent = 'Saving…';
    try {
        const res = await fetch('/api/llm/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (res.ok) {
            setStatus('Saved', 'ok');
            updateBadge(cfg.provider.value);
        } else {
            setStatus('Save failed', 'error');
        }
    } catch (e) {
        setStatus('Network error', 'error');
    } finally {
        cfg.saveBtn.disabled = false;
        cfg.saveBtn.textContent = 'Save';
    }
});

// ── Test connection ───────────────────────────────────────────────────────
cfg.testBtn.addEventListener('click', async () => {
    cfg.testBtn.disabled = true;
    cfg.testBtn.textContent = 'Testing…';
    setStatus('Running a test decision…', '');
    try {
        // Save first so the backend uses the current form values
        await fetch('/api/llm/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: cfg.provider.value,
                api_key:  cfg.apiKey.value.trim() || null,
                base_url: cfg.baseUrl.value.trim() || null,
                model:    cfg.model.value.trim() || null,
            }),
        });
        const res = await fetch('/api/llm/test', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            setStatus(`Connected — "${data.reasoning_preview}…"`, 'ok');
            updateBadge(cfg.provider.value);
        } else {
            setStatus(`Error: ${data.reasoning_preview}`, 'error');
        }
    } catch (e) {
        setStatus(`Test failed: ${e}`, 'error');
    } finally {
        cfg.testBtn.disabled = false;
        cfg.testBtn.textContent = 'Test';
    }
});

function setStatus(msg, type) {
    cfg.status.textContent = msg;
    cfg.status.className = 'llm-status' + (type ? ` llm-status-${type}` : '');
}

function updateBadge(provider) {
    const labels = { mock: 'Mock', gemini: 'Gemini', ollama: 'Ollama', openrouter: 'OpenRouter' };
    cfg.badge.textContent = labels[provider] || provider;
    cfg.badge.className = `llm-badge llm-badge-${provider}`;
}

// ── Init — load current config from backend ───────────────────────────────
async function initLLMConfig() {
    try {
        const res = await fetch('/api/llm/config');
        const data = await res.json();
        cfg.provider.value = data.provider;
        cfg.baseUrl.value = data.base_url || '';
        cfg.model.value = data.model || '';
        const meta = PROVIDER_DEFAULTS[data.provider] || {};
        cfg.keyRow.style.display = meta.needsKey ? 'flex' : 'none';
        cfg.urlRow.style.display = meta.needsUrl ? 'flex' : 'none';
        cfg.model.placeholder = meta.modelPlaceholder || '';
        if (data.has_api_key) cfg.apiKey.placeholder = '(key saved)';
        updateBadge(data.provider);
    } catch (e) {
        console.error('Could not load LLM config', e);
    }
}

document.addEventListener('DOMContentLoaded', initLLMConfig);
