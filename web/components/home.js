window.Components = window.Components || {};

window.Components.HomeView = function () {
  const section = document.createElement('section');
  section.className = 'card glass entrance view';
  section.dataset.view = 'home';

  const title = document.createElement('div');
  title.className = 'section-title';
  title.textContent = 'YouTube URL';

  const inputRow = document.createElement('div');
  inputRow.className = 'input-row';

  const url = document.createElement('input');
  url.className = 'input';
  url.placeholder = 'Paste YouTube link here';
  url.id = 'url';

  const start = document.createElement('button');
  start.id = 'start';
  start.className = 'btn primary';
  start.textContent = 'Start';

  inputRow.appendChild(url);
  inputRow.appendChild(start);

  const grid = document.createElement('div');
  grid.className = 'grid';

  function makeField(labelText, inputEl) {
    const field = document.createElement('div');
    field.className = 'field';
    const label = document.createElement('div');
    label.className = 'label';
    label.textContent = labelText;
    field.appendChild(label);
    field.appendChild(inputEl);
    return field;
  }

  const clips = document.createElement('select');
  clips.className = 'select';
  clips.id = 'clips';
  clips.innerHTML = '<option value="3">3 clips</option><option value="5" selected>5 clips</option><option value="8">8 clips</option>';

  const subtitle = document.createElement('select');
  subtitle.className = 'select';
  subtitle.id = 'subtitle';
  subtitle.innerHTML = '<option value="id" selected>Indonesian</option><option value="en">English</option>';

  const capSwitch = makeSwitch('Auto captions', 'captions', true);
  const hookSwitch = makeSwitch('Hook scene', 'hook', false);

  grid.appendChild(makeField('Clips', clips));
  grid.appendChild(makeField('Subtitle', subtitle));
  grid.appendChild(capSwitch);
  grid.appendChild(hookSwitch);

  const progress = document.createElement('div');
  progress.className = 'progress';
  const bar = document.createElement('div');
  bar.id = 'bar';
  bar.className = 'bar';
  progress.appendChild(bar);

  const status = document.createElement('div');
  status.id = 'status';
  status.className = 'status';

  section.appendChild(title);
  section.appendChild(inputRow);
  section.appendChild(grid);
  section.appendChild(progress);
  section.appendChild(status);

  return {
    element: section,
    fields: {
      url,
      start,
      clips,
      subtitle,
      captions: capSwitch.querySelector('input'),
      hook: hookSwitch.querySelector('input'),
      bar,
      status
    }
  };
};

function makeSwitch(text, id, checked) {
  const field = document.createElement('div');
  field.className = 'field';
  const label = document.createElement('label');
  label.className = 'switch';
  const input = document.createElement('input');
  input.type = 'checkbox';
  input.id = id;
  input.checked = checked;
  const slider = document.createElement('span');
  slider.className = 'slider';
  const span = document.createElement('span');
  span.className = 'switch-label';
  span.textContent = text;
  label.appendChild(input);
  label.appendChild(slider);
  label.appendChild(span);
  field.appendChild(label);
  return field;
}
