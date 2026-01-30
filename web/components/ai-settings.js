window.Components = window.Components || {};

window.Components.AiSettingsView = function () {
  const section = document.createElement('section');
  section.className = 'card glass entrance view';
  section.dataset.view = 'ai-settings';

  const title = document.createElement('div');
  title.className = 'section-title';
  title.textContent = 'AI Settings';

  const providerTitle = document.createElement('div');
  providerTitle.className = 'label';
  providerTitle.textContent = 'Provider';

  const providerGrid = document.createElement('div');
  providerGrid.className = 'provider-grid';

  function makeProvider(label, value) {
    const btn = document.createElement('button');
    btn.className = 'provider-card';
    btn.dataset.provider = value;
    btn.textContent = label;
    return btn;
  }

  const providerYt = makeProvider('🎬 YT CLIP AI', 'ytclip');
  const providerOpenai = makeProvider('🤖 OPENAI', 'openai');
  const providerCustom = makeProvider('⚙️ CUSTOM', 'custom');

  providerGrid.appendChild(providerYt);
  providerGrid.appendChild(providerOpenai);
  providerGrid.appendChild(providerCustom);

  const grid = document.createElement('div');
  grid.className = 'ai-grid';

  function makeCard(label) {
    const card = document.createElement('div');
    card.className = 'ai-card';
    const t = document.createElement('div');
    t.className = 'ai-title';
    t.textContent = label;
    const url = document.createElement('input');
    url.className = 'input';
    url.placeholder = 'https://api.openai.com/v1';
    const keyWrap = document.createElement('div');
    keyWrap.className = 'input-group';
    const key = document.createElement('input');
    key.className = 'input';
    key.placeholder = 'sk-...';
    key.type = 'password';
    const eye = document.createElement('button');
    eye.className = 'icon-btn';
    eye.type = 'button';
    eye.textContent = '👁';
    keyWrap.appendChild(key);
    keyWrap.appendChild(eye);
    const model = document.createElement('select');
    model.className = 'select';
    model.innerHTML = '<option value="">Select model</option>';
    const urlField = makeField('Base URL', url);
    urlField.classList.add('url-field');
    const keyField = makeField('API Key', keyWrap);
    const modelField = makeField('Model', model);
    const actions = document.createElement('div');
    actions.className = 'validate-row';
    const validateBtn = document.createElement('button');
    validateBtn.className = 'btn ghost';
    validateBtn.textContent = 'Validate';
    const validateStatus = document.createElement('div');
    validateStatus.className = 'status-inline';
    actions.appendChild(validateBtn);
    actions.appendChild(validateStatus);
    card.appendChild(t);
    card.appendChild(urlField);
    card.appendChild(keyField);
    card.appendChild(modelField);
    card.appendChild(actions);
    return { card, url, key, eye, model, urlField, validateBtn, validateStatus };
  }

  function makeField(text, inputEl) {
    const field = document.createElement('div');
    field.className = 'field';
    const label = document.createElement('div');
    label.className = 'label';
    label.textContent = text;
    field.appendChild(label);
    field.appendChild(inputEl);
    return field;
  }

  const hf = makeCard('Highlight Finder');
  const cm = makeCard('Caption Maker (Whisper)');
  const hm = makeCard('Hook Maker (TTS)');
  hm.model.innerHTML = '<option value="tts-1">tts-1</option><option value="tts-1-hd">tts-1-hd</option>';
  cm.model.innerHTML = '<option value="whisper-1">whisper-1</option>';

  grid.appendChild(hf.card);
  grid.appendChild(cm.card);
  grid.appendChild(hm.card);

  const actions = document.createElement('div');
  actions.className = 'ai-actions';

  const save = document.createElement('button');
  save.id = 'save_ai';
  save.className = 'btn primary';
  save.textContent = 'Save AI Settings';

  const status = document.createElement('div');
  status.id = 'ai_status';
  status.className = 'status';

  actions.appendChild(save);
  actions.appendChild(status);

  section.appendChild(title);
  section.appendChild(providerTitle);
  section.appendChild(providerGrid);
  section.appendChild(grid);
  section.appendChild(actions);

  return {
    element: section,
    fields: {
      providerButtons: [providerYt, providerOpenai, providerCustom],
      hfUrl: hf.url,
      hfUrlField: hf.urlField,
      hfKey: hf.key,
      hfEye: hf.eye,
      hfModel: hf.model,
      hfValidateBtn: hf.validateBtn,
      hfValidateStatus: hf.validateStatus,
      cmUrl: cm.url,
      cmUrlField: cm.urlField,
      cmKey: cm.key,
      cmEye: cm.eye,
      cmModel: cm.model,
      cmValidateBtn: cm.validateBtn,
      cmValidateStatus: cm.validateStatus,
      hmUrl: hm.url,
      hmUrlField: hm.urlField,
      hmKey: hm.key,
      hmEye: hm.eye,
      hmModel: hm.model,
      hmValidateBtn: hm.validateBtn,
      hmValidateStatus: hm.validateStatus,
      saveBtn: save,
      status
    }
  };
};
