const root = document.getElementById('app');
const shell = document.createElement('div');
shell.className = 'shell';
root.appendChild(shell);

const header = window.Components.Header();
shell.appendChild(header.element);

const main = document.createElement('main');
main.className = 'main';
shell.appendChild(main);

const aiView = window.Components.AiSettingsView();
const homeView = window.Components.HomeView();
main.appendChild(aiView.element);
main.appendChild(homeView.element);

const navButtons = header.buttons;
const views = [aiView.element, homeView.element];

let polling = null;
let iconTriedData = false;
const fallbackSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="none"><rect width="96" height="96" rx="18" fill="#0B1B24"/><path d="M18 36h60v36a6 6 0 0 1-6 6H24a6 6 0 0 1-6-6V36Z" fill="#12BFE4"/><path d="M20 20l10 10m6-10 10 10m6-10 10 10m6-10 10 10" stroke="#12BFE4" stroke-width="6" stroke-linecap="round"/></svg>`;
let providerType = 'ytclip';

function waitForApi() {
  return new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api) {
      resolve();
      return;
    }
    let tries = 0;
    const timer = setInterval(() => {
      tries += 1;
      if (window.pywebview && window.pywebview.api) {
        clearInterval(timer);
        resolve();
      } else if (tries > 50) {
        clearInterval(timer);
        resolve();
      }
    }, 100);
  });
}

function toFileUrl(path) {
  if (!path) return '';
  if (path.startsWith('file://')) return path;
  const fixed = path.replace(/\\/g, '/');
  return 'file:///' + fixed;
}

function lockControls(state) {
  homeView.fields.url.disabled = state;
  homeView.fields.clips.disabled = state;
  homeView.fields.subtitle.disabled = state;
  homeView.fields.captions.disabled = state;
  homeView.fields.hook.disabled = state;
  homeView.fields.start.disabled = state;
}

function setActiveView(name) {
  views.forEach((view) => {
    view.classList.toggle('active', view.dataset.view === name);
  });
  navButtons.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.view === name);
  });
}

function setProviderType(type, applyBaseUrl) {
  providerType = type;
  aiView.fields.providerButtons.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.provider === type);
  });
  const showCustom = type === 'custom';
  aiView.fields.hfUrlField.classList.toggle('hidden', !showCustom);
  aiView.fields.cmUrlField.classList.toggle('hidden', !showCustom);
  aiView.fields.hmUrlField.classList.toggle('hidden', !showCustom);
  if (applyBaseUrl && !showCustom) {
    const baseUrl = type === 'ytclip' ? 'https://ai-api.ytclip.org/v1' : 'https://api.openai.com/v1';
    aiView.fields.hfUrl.value = baseUrl;
    aiView.fields.cmUrl.value = baseUrl;
    aiView.fields.hmUrl.value = baseUrl;
  }
}

function setSelectOptions(select, models, preferred) {
  select.innerHTML = '';
  if (!models || models.length === 0) {
    const opt = document.createElement('option');
    opt.value = preferred || '';
    opt.textContent = preferred || 'No models';
    select.appendChild(opt);
    return;
  }
  models.forEach((m) => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  });
  if (preferred && models.includes(preferred)) {
    select.value = preferred;
  }
}

function toggleEye(input, button) {
  const visible = input.type === 'text';
  input.type = visible ? 'password' : 'text';
  button.textContent = visible ? '👁' : '🙈';
}

function getSvgDataUrl() {
  return 'data:image/svg+xml;utf8,' + encodeURIComponent(fallbackSvg);
}

async function setIconFromApi() {
  if (iconTriedData) return;
  iconTriedData = true;
  try {
    const icon = await window.pywebview.api.get_icon_data();
    if (icon && icon.data) {
      header.icon.src = icon.data;
    }
  } catch {}
}

function setIconFallback() {
  header.icon.onerror = () => {
    setIconFromApi();
  };
  header.icon.src = getSvgDataUrl();
}

async function start() {
  const url = homeView.fields.url.value.trim();
  if (!url) return;
  lockControls(true);
  homeView.fields.status.textContent = 'Starting';
  homeView.fields.bar.style.width = '0%';
  try {
    const res = await window.pywebview.api.start_processing(
      url,
      parseInt(homeView.fields.clips.value, 10),
      homeView.fields.captions.checked,
      homeView.fields.hook.checked,
      homeView.fields.subtitle.value
    );
    if (res && res.status === 'started') {
      poll();
      polling = setInterval(poll, 500);
    } else {
      homeView.fields.status.textContent = 'Busy';
      lockControls(false);
    }
  } catch (e) {
    homeView.fields.status.textContent = 'Error';
    lockControls(false);
  }
}

async function poll() {
  try {
    const p = await window.pywebview.api.get_progress();
    const pr = Math.max(0, Math.min(1, p.progress || 0));
    homeView.fields.bar.style.width = (pr * 100).toFixed(1) + '%';
    homeView.fields.status.textContent = p.status || '';
    if (p.status && (p.status.startsWith('error') || p.status === 'complete')) {
      clearInterval(polling);
      polling = null;
      lockControls(false);
    }
  } catch {
    clearInterval(polling);
    polling = null;
    lockControls(false);
  }
}

homeView.fields.start.addEventListener('click', start);

navButtons.forEach((btn) => {
  btn.addEventListener('click', () => setActiveView(btn.dataset.view));
});

aiView.fields.saveBtn.addEventListener('click', async () => {
  const payload = {
    _provider_type: providerType,
    highlight_finder: {
      base_url: aiView.fields.hfUrl.value.trim(),
      api_key: aiView.fields.hfKey.value.trim(),
      model: aiView.fields.hfModel.value.trim()
    },
    caption_maker: {
      base_url: aiView.fields.cmUrl.value.trim(),
      api_key: aiView.fields.cmKey.value.trim(),
      model: aiView.fields.cmModel.value.trim()
    },
    hook_maker: {
      base_url: aiView.fields.hmUrl.value.trim(),
      api_key: aiView.fields.hmKey.value.trim(),
      model: aiView.fields.hmModel.value.trim()
    }
  };
  aiView.fields.status.textContent = 'Saving';
  try {
    const res = await window.pywebview.api.save_ai_settings(payload);
    aiView.fields.status.textContent = res && res.status === 'saved' ? 'Saved' : 'Error';
  } catch {
    aiView.fields.status.textContent = 'Error';
  }
});

async function init() {
  await waitForApi();
  setIconFallback();
  await setIconFromApi();
  if (!header.icon.src) {
    try {
      const paths = await window.pywebview.api.get_asset_paths();
      if (paths && paths.icon) {
        header.icon.src = toFileUrl(paths.icon);
      }
    } catch {}
  }
  try {
    const ai = await window.pywebview.api.get_ai_settings();
    const hf = ai.highlight_finder || {};
    const cm = ai.caption_maker || {};
    const hm = ai.hook_maker || {};
    aiView.fields.hfUrl.value = hf.base_url || '';
    aiView.fields.hfKey.value = hf.api_key || '';
    setSelectOptions(aiView.fields.hfModel, [hf.model].filter(Boolean), hf.model || '');
    aiView.fields.cmUrl.value = cm.base_url || '';
    aiView.fields.cmKey.value = cm.api_key || '';
    setSelectOptions(aiView.fields.cmModel, [cm.model].filter(Boolean), cm.model || '');
    aiView.fields.hmUrl.value = hm.base_url || '';
    aiView.fields.hmKey.value = hm.api_key || '';
    setSelectOptions(aiView.fields.hmModel, [hm.model].filter(Boolean), hm.model || '');
  } catch {}
  try {
    const provider = await window.pywebview.api.get_provider_type();
    providerType = provider.provider_type || 'ytclip';
  } catch {}
  setProviderType(providerType, true);
  setActiveView('home');
}

aiView.fields.providerButtons.forEach((btn) => {
  btn.addEventListener('click', () => setProviderType(btn.dataset.provider, true));
});

aiView.fields.hfEye.addEventListener('click', () => toggleEye(aiView.fields.hfKey, aiView.fields.hfEye));
aiView.fields.cmEye.addEventListener('click', () => toggleEye(aiView.fields.cmKey, aiView.fields.cmEye));
aiView.fields.hmEye.addEventListener('click', () => toggleEye(aiView.fields.hmKey, aiView.fields.hmEye));

async function validateAndLoad(kind) {
  const baseUrl = kind.url.value.trim();
  const apiKey = kind.key.value.trim();
  kind.status.textContent = 'Validating';
  const res = await window.pywebview.api.validate_api_key(baseUrl, apiKey);
  if (!res || res.status !== 'ok') {
    kind.status.textContent = res && res.message ? res.message : 'Invalid';
    return;
  }
  kind.status.textContent = 'Loading models';
  const modelsRes = await window.pywebview.api.get_models(baseUrl, apiKey);
  const models = (modelsRes && modelsRes.models) || [];
  setSelectOptions(kind.model, models, kind.model.value);
  kind.status.textContent = models.length ? 'Valid' : 'Valid, no models';
}

aiView.fields.hfValidateBtn.addEventListener('click', () => validateAndLoad({
  url: aiView.fields.hfUrl,
  key: aiView.fields.hfKey,
  model: aiView.fields.hfModel,
  status: aiView.fields.hfValidateStatus
}));

aiView.fields.cmValidateBtn.addEventListener('click', () => validateAndLoad({
  url: aiView.fields.cmUrl,
  key: aiView.fields.cmKey,
  model: aiView.fields.cmModel,
  status: aiView.fields.cmValidateStatus
}));

aiView.fields.hmValidateBtn.addEventListener('click', () => validateAndLoad({
  url: aiView.fields.hmUrl,
  key: aiView.fields.hmKey,
  model: aiView.fields.hmModel,
  status: aiView.fields.hmValidateStatus
}));

window.addEventListener('pywebviewready', init);
setTimeout(() => init(), 800);
