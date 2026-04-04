(() => {
  const state = {
    tags: new Set(),
    tagCatalog: [],
    maxTags: 5,
    maxPhotoSizeBytes: 10 * 1024 * 1024,
    submitMessage: '',
  };

  const tagList = document.getElementById('tagList');
  const photoInput = document.getElementById('photos');
  const photoPreview = document.getElementById('photoPreview');
  const previewBox = document.getElementById('preview');
  const statusBox = document.getElementById('status');

  function setStatus(text, isError = false) {
    statusBox.textContent = text;
    statusBox.classList.toggle('error', isError);
  }

  async function loadConfig() {
    const res = await fetch('/api/add-location/form-config');
    const cfg = await res.json();

    state.tagCatalog = cfg.tag_catalog || [];
    state.maxTags = cfg.max_tags || 5;
    state.maxPhotoSizeBytes = (cfg.max_photo_size_mb || 10) * 1024 * 1024;
    state.submitMessage = cfg.submit_message || '';

    renderTags();
    setStatus(state.submitMessage);
  }

  function renderTags() {
    tagList.innerHTML = '';
    state.tagCatalog.forEach((tag) => {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = `tag-chip${state.tags.has(tag.id) ? ' active' : ''}`;
      el.textContent = tag.label;
      el.onclick = () => toggleTag(tag.id);
      tagList.appendChild(el);
    });
  }

  function toggleTag(tagId) {
    if (state.tags.has(tagId)) {
      state.tags.delete(tagId);
      renderTags();
      return;
    }
    if (state.tags.size >= state.maxTags) {
      setStatus(`Можно выбрать максимум ${state.maxTags} тегов`, true);
      return;
    }
    state.tags.add(tagId);
    renderTags();
  }

  function buildPhotoMeta() {
    const files = Array.from(photoInput.files || []);
    return files.map((file, idx) => ({
      temp_id: `local-${Date.now()}-${idx}`,
      filename: file.name,
      mime_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
    }));
  }

  function buildPayload() {
    return {
      name: document.getElementById('name').value,
      description: document.getElementById('description').value,
      coordinates: {
        latitude: Number(document.getElementById('latitude').value),
        longitude: Number(document.getElementById('longitude').value),
      },
      tag_ids: Array.from(state.tags),
      photos: buildPhotoMeta(),
    };
  }

  function validateClient(payload) {
    if (!payload.name?.trim()) return 'Введите название';
    if (!payload.description?.trim()) return 'Введите описание';
    if (payload.tag_ids.length > state.maxTags) return `Можно выбрать максимум ${state.maxTags} тегов`;
    if (!payload.photos.length) return 'Добавьте хотя бы одно фото';
    if (payload.photos.some((p) => p.size_bytes > state.maxPhotoSizeBytes)) return 'Фото превышает допустимый размер';
    if (payload.coordinates.latitude < -90 || payload.coordinates.latitude > 90) return 'Некорректная широта';
    if (payload.coordinates.longitude < -180 || payload.coordinates.longitude > 180) return 'Некорректная долгота';
    return null;
  }

  function renderPreview(normalized) {
    const tags = normalized.tag_ids.length ? normalized.tag_ids.join(', ') : 'Не выбраны';
    const photos = normalized.photos
      .map((photo) => `<li>${photo.filename} (${Math.round(photo.size_bytes / 1024)} KB)</li>`)
      .join('');

    previewBox.innerHTML = `
      <div><strong>Название:</strong> ${normalized.name}</div>
      <div style="margin-top:6px;"><strong>Описание:</strong> ${normalized.description}</div>
      <div style="margin-top:6px;"><strong>Координаты:</strong> ${normalized.coordinates.latitude}, ${normalized.coordinates.longitude}</div>
      <div style="margin-top:6px;"><strong>Теги:</strong> ${tags}</div>
      <div style="margin-top:6px;"><strong>Фото:</strong></div>
      <ul style="margin:6px 0 0 18px;">${photos}</ul>
      <div style="margin-top:8px;"><strong>Статус интеграции:</strong> ${state.submitMessage}</div>
    `;
  }

  async function runPreview() {
    const payload = buildPayload();
    const error = validateClient(payload);
    if (error) {
      setStatus(error, true);
      return;
    }

    const res = await fetch('/api/add-location/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setStatus(data?.detail || 'Ошибка preview', true);
      return;
    }

    renderPreview(data.normalized);
    setStatus('Preview готов. Проверьте данные перед отправкой.');
  }

  async function submit() {
    const payload = buildPayload();
    const error = validateClient(payload);
    if (error) {
      setStatus(error, true);
      return;
    }

    const submitPayload = {
      ...payload,
      idempotency_key: `ui-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    };

    const res = await fetch('/api/add-location/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submitPayload),
    });
    const data = await res.json();
    setStatus(data?.detail || 'Writer-side интеграция пока не подключена', true);
  }

  function onPhotosChanged() {
    const files = Array.from(photoInput.files || []);
    photoPreview.innerHTML = '';
    files.forEach((file) => {
      const el = document.createElement('div');
      el.className = 'photo-pill';
      el.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
      photoPreview.appendChild(el);
    });
  }

  document.getElementById('previewBtn').addEventListener('click', runPreview);
  photoInput.addEventListener('change', onPhotosChanged);
  document.getElementById('addLocationForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    await submit();
  });

  loadConfig().catch(() => setStatus('Не удалось загрузить конфигурацию формы', true));
})();
