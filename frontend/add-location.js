(() => {
  const state = {
    tags: new Set(),
    tagCatalog: [],
    uploadedPhotos: [],
    maxTags: 5,
    maxPhotoSizeBytes: 10 * 1024 * 1024,
    submitMessage: '',
    selectedPoint: null,
  };

  const tagList = document.getElementById('tagList');
  const photoInput = document.getElementById('photos');
  const photoPreview = document.getElementById('photoPreview');
  const previewBox = document.getElementById('preview');
  const statusBox = document.getElementById('status');
  const coordinatesLabel = document.getElementById('coordinatesLabel');
  let pickerMap = null;
  let marker = null;

  function setStatus(text, isError = false) {
    statusBox.textContent = text;
    statusBox.classList.toggle('error', isError);
  }

  function getInitData() {
    return window.Telegram?.WebApp?.initData || '';
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
    const byCategory = {};
    state.tagCatalog.forEach((tag) => {
      const category = tag.category || 'Прочее';
      if (!byCategory[category]) byCategory[category] = [];
      byCategory[category].push(tag);
    });
    Object.entries(byCategory).forEach(([category, tags]) => {
      const title = document.createElement('div');
      title.style.width = '100%';
      title.style.fontWeight = '700';
      title.style.marginTop = '6px';
      title.textContent = category;
      tagList.appendChild(title);
      tags.forEach((tag) => {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = `tag-chip${state.tags.has(tag.id) ? ' active' : ''}`;
        el.textContent = tag.label;
        el.onclick = () => toggleTag(tag.id);
        tagList.appendChild(el);
      });
    });
  }

  function setCoordinates(lat, lng) {
    state.selectedPoint = { lat, lng };
    document.getElementById('latitude').value = lat;
    document.getElementById('longitude').value = lng;
    coordinatesLabel.value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    setStatus('Точка на карте выбрана. Можно продолжать заполнение.');
  }

  function initMapPicker() {
    pickerMap = L.map('pickerMap').setView([55.751244, 37.618423], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(pickerMap);
    pickerMap.on('click', (event) => {
      const { lat, lng } = event.latlng;
      if (!marker) marker = L.marker([lat, lng]).addTo(pickerMap);
      else marker.setLatLng([lat, lng]);
      setCoordinates(lat, lng);
    });
    setStatus('Выберите точку кликом по карте или кнопкой геолокации.');
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setStatus('Геолокация недоступна в этом браузере', true);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        pickerMap.setView([lat, lng], 15);
        if (!marker) marker = L.marker([lat, lng]).addTo(pickerMap);
        else marker.setLatLng([lat, lng]);
        setCoordinates(lat, lng);
      },
      () => setStatus('Не удалось определить геопозицию', true),
    );
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

  function renderUploadedPhotos() {
    photoPreview.innerHTML = '';
    state.uploadedPhotos.forEach((photo) => {
      const el = document.createElement('div');
      el.className = 'photo-pill';
      el.textContent = `${photo.filename} (${Math.round(photo.size_bytes / 1024)} KB)`;
      photoPreview.appendChild(el);
    });
  }

  async function uploadSelectedPhotos() {
    const files = Array.from(photoInput.files || []);
    if (!files.length) {
      state.uploadedPhotos = [];
      renderUploadedPhotos();
      return;
    }

    const toBase64 = (file) => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const value = String(reader.result || '');
        resolve(value.split(',')[1] || '');
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    const encodedFiles = await Promise.all(
      files.map(async (file) => ({
        filename: file.name,
        mime_type: file.type || 'application/octet-stream',
        content_base64: await toBase64(file),
      })),
    );

    const res = await fetch('/api/add-location/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: encodedFiles }),
    });

    const data = await res.json();
    if (!res.ok) {
      setStatus(data?.detail || 'Ошибка загрузки фото', true);
      return;
    }

    state.uploadedPhotos = data;
    renderUploadedPhotos();
    setStatus('Фото загружены и готовы к отправке.');
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
      photos: state.uploadedPhotos,
    };
  }

  function selectedTagLabels() {
    const byId = new Map(state.tagCatalog.map((tag) => [tag.id, tag.label]));
    return Array.from(state.tags).map((id) => byId.get(id) || id);
  }

  function validateClient(payload) {
    if (!payload.name?.trim()) return 'Введите название';
    if (!payload.description?.trim()) return 'Введите описание';
    if (payload.tag_ids.length > state.maxTags) return `Можно выбрать максимум ${state.maxTags} тегов`;
    if (!payload.photos.length) return 'Загрузите хотя бы одно фото';
    if (!Number.isFinite(payload.coordinates.latitude) || !Number.isFinite(payload.coordinates.longitude)) return 'Выберите точку на карте';
    if (payload.coordinates.latitude < -90 || payload.coordinates.latitude > 90) return 'Некорректная широта';
    if (payload.coordinates.longitude < -180 || payload.coordinates.longitude > 180) return 'Некорректная долгота';
    return null;
  }

  function renderPreview(normalized) {
    const tags = selectedTagLabels().length ? selectedTagLabels().join(', ') : 'Не выбраны';
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
      <div style="margin-top:8px;"><strong>Статус:</strong> ${state.submitMessage}</div>
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
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': getInitData(),
      },
      body: JSON.stringify(submitPayload),
    });
    const data = await res.json();

    if (!res.ok) {
      setStatus(data?.detail || 'Не удалось отправить локацию', true);
      return;
    }

    setStatus(`Локация #${data.location_id} отправлена на модерацию.`);
  }

  document.getElementById('previewBtn').addEventListener('click', runPreview);
  document.getElementById('myLocationBtn').addEventListener('click', useMyLocation);
  photoInput.addEventListener('change', uploadSelectedPhotos);
  document.getElementById('addLocationForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    await submit();
  });

  initMapPicker();
  loadConfig().catch(() => setStatus('Не удалось загрузить конфигурацию формы', true));
})();
