// ============================================================
// FRONTEND APP.JS - Procesador Virrey Solís
// ============================================================

if (window.location.protocol === 'file:') {
  alert("Por favor, abre esta aplicación desde Render: https://servicios-medicos-n3bl.onrender.com/");
}

let processedData = null;
let abortController = null;
let progressInterval = null;

// ============================================================
// FUNCIONES DE NOTIFICACIÓN (TOASTS)
// ============================================================
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast-message ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 50);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ============================================================
// FUNCIÓN PRINCIPAL: SUBIR ARCHIVOS Y PROCESAR
// ============================================================
function uploadFiles() {
  const file1 = document.getElementById('file1-input')?.files[0];
  const file2 = document.getElementById('file2-input')?.files[0];
  const resultDiv = document.getElementById('result');
  const loadingDiv = document.getElementById('loading');
  const progressContainer = document.getElementById('progress-container');
  const progressBar = document.getElementById('progress-bar');
  const progressText = document.getElementById('progress-text');

  if (!file1 || !file2) {
    showToast("Por favor, selecciona ambos archivos.", "error");
    return;
  }

  const validExtensions = ['xlsx', 'xls'];
  if (!validExtensions.includes(file1.name.split('.').pop().toLowerCase()) ||
      !validExtensions.includes(file2.name.split('.').pop().toLowerCase())) {
    showToast("Solo se permiten archivos Excel (.xlsx o .xls).", "error");
    return;
  }

  loadingDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Procesando archivos...`;
  loadingDiv.style.display = 'block';
  resultDiv.style.display = 'none';

  // Mostrar barra de progreso
  progressContainer.style.display = 'block';
  progressBar.style.width = '0%';
  progressText.textContent = 'Procesando... 0%';
  let progress = 0;
  clearInterval(progressInterval);
  progressInterval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 8, 95);
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `Procesando... ${Math.floor(progress)}%`;
  }, 500);

  // Botón de cancelar
  const cancelButton = document.createElement('button');
  cancelButton.textContent = "Cancelar envío";
  cancelButton.className = "cancel-button";
  cancelButton.onclick = () => {
    if (abortController) {
      abortController.abort();
      loadingDiv.innerHTML = `<div style="color:red;">⛔ Envío cancelado.</div>`;
      clearInterval(progressInterval);
      progressText.textContent = '❌ Cancelado';
      progressBar.style.backgroundColor = '#dc3545';
      showToast("⛔ Envío cancelado por el usuario.", "warning");
    }
  };
  loadingDiv.appendChild(cancelButton);

  const formData = new FormData();
  formData.append('file1', file1);
  formData.append('file2', file2);
  abortController = new AbortController();

  fetch('https://servicios-medicos-n3bl.onrender.com/upload', {
    method: 'POST',
    body: formData,
    signal: abortController.signal
  })
    .then(async response => {
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        if (!response.ok) throw new Error(data.error || `Error HTTP: ${response.status}`);
        return data;
      } catch {
        throw new Error("⚠️ El servidor devolvió una respuesta no válida.");
      }
    })
    .then(data => {
      clearInterval(progressInterval);
      progressBar.style.width = '100%';
      progressText.textContent = '✅ Procesamiento completado';
      setTimeout(() => progressContainer.style.display = 'none', 1500);
      loadingDiv.style.display = 'none';

      if (data.error) {
        showToast(data.error, "error");
        resultDiv.innerHTML = `<div style="color:red;">Error: ${data.error}</div>`;
        resultDiv.style.display = 'block';
      } else {
        showToast("✅ Archivos procesados correctamente.", "success");
        processedData = data;
        mostrarResultados(data);
      }
    })
    .catch(error => {
      if (error.name === 'AbortError') return;
      clearInterval(progressInterval);
      progressText.textContent = '❌ Error en el procesamiento';
      progressBar.style.backgroundColor = '#dc3545';
      showToast(`Error: ${error.message}`, "error");
      loadingDiv.style.display = 'none';
    });
}

// ============================================================
// MOSTRAR RESULTADOS
// ============================================================
function mostrarResultados(data) {
  const totalServicesCrystal = document.getElementById('total-services-crystal');
  const totalServicesQuery = document.getElementById('total-services-query');
  const numProfessionals = document.getElementById('num-professionals');
  const numUsers = document.getElementById('num-users');
  const profSelect = document.getElementById('professional-filter');
  const userSelect = document.getElementById('user-filter');
  const resultDiv = document.getElementById('result');

  showGlobalView(data);
  profSelect.innerHTML = '<option value="">Seleccionar Profesional</option>';
  userSelect.innerHTML = '<option value="">Seleccionar Profesional (Query)</option>';

  data.professionals.sort().forEach(p => {
    if (p && p !== 'nan') {
      const opt = document.createElement('option');
      opt.value = p;
      opt.textContent = toTitleCase(p);
      profSelect.appendChild(opt);
    }
  });

  data.users.sort().forEach(u => {
    if (u && u !== 'nan') {
      const opt = document.createElement('option');
      opt.value = u;
      opt.textContent = toTitleCase(u);
      userSelect.appendChild(opt);
    }
  });

  resultDiv.style.display = 'block';
}

// ============================================================
// MOSTRAR VISTA FILTRADA
// ============================================================
function showFilteredView(type, name) {
  let personData = type === 'prof' ? processedData.professional_data[name] : processedData.user_data[name];
  let fileType = type === 'prof' ? 'Crystal' : 'Query';
  if (!personData) return showToast('No se encontraron datos para el seleccionado.', 'warning');

  const globalData = document.getElementById('global-data');
  const personSection = document.getElementById('person-data');
  globalData.style.display = 'none';
  personSection.innerHTML = '';
  personSection.style.display = 'block';

  const backButton = document.createElement('button');
  backButton.id = 'back-button';
  backButton.textContent = '← Atrás';
  backButton.onclick = () => {
    showGlobalView(processedData);
    document.getElementById('professional-filter').value = '';
    document.getElementById('user-filter').value = '';
  };
  personSection.appendChild(backButton);

  const title = document.createElement('h2');
  title.textContent = `${toTitleCase(name)} (${fileType})`;
  personSection.appendChild(title);

  // Botón de descarga con barra visual
  const downloadButton = document.createElement('a');
  downloadButton.href = personData.download_link;
  downloadButton.className = 'download-button';
  downloadButton.textContent = "⬇️ Descargar Excel filtrado";
  downloadButton.target = "_blank";
  downloadButton.onclick = (e) => {
    e.preventDefault();
    startDownloadProgress();
    fetch(downloadButton.href)
      .then(response => {
        if (!response.ok) throw new Error("Error en la descarga");
        return response.blob();
      })
      .then(blob => {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = downloadButton.href.split('/').pop();
        link.click();
        showToast("📁 Descarga completada", "success");
      })
      .catch(() => showToast("❌ Error al descargar", "error"))
      .finally(() => finishDownloadProgress());
  };
  personSection.appendChild(downloadButton);

  const resumenDiv = document.createElement('div');
  resumenDiv.className = 'servicios-categoria';
  mostrarResumenServicios(toTitleCase(name), personData.servicios_por_categoria, fileType, resumenDiv);
  personSection.appendChild(resumenDiv);

  const detalladosDiv = document.createElement('div');
  detalladosDiv.className = 'detallados-servicios';
  mostrarResumenDetallados(toTitleCase(name), personData.servicios_detallados, fileType, detalladosDiv);
  personSection.appendChild(detalladosDiv);
}

// ============================================================
// UTILIDADES
// ============================================================
function startDownloadProgress() {
  const progressContainer = document.getElementById('progress-container');
  const progressBar = document.getElementById('progress-bar');
  const progressText = document.getElementById('progress-text');
  progressContainer.style.display = 'block';
  progressBar.style.width = '0%';
  progressBar.style.backgroundColor = '#17a2b8';
  progressText.textContent = 'Preparando descarga...';
  let progress = 0;
  clearInterval(progressInterval);
  progressInterval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 12, 100);
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `Descargando... ${Math.floor(progress)}%`;
    if (progress >= 100) clearInterval(progressInterval);
  }, 400);
}

function finishDownloadProgress() {
  clearInterval(progressInterval);
  const progressText = document.getElementById('progress-text');
  const progressContainer = document.getElementById('progress-container');
  progressText.textContent = '✅ Descarga completada';
  setTimeout(() => progressContainer.style.display = 'none', 1500);
}

function toTitleCase(str) {
  return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
}

function showGlobalView(data) {
  const globalData = document.getElementById('global-data');
  const personData = document.getElementById('person-data');
  globalData.innerHTML = '';
  personData.style.display = 'none';
  globalData.style.display = 'block';
}

// ============================================================
// EVENTOS
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('process-button')?.addEventListener('click', uploadFiles);
  document.getElementById('search-button')?.addEventListener('click', () => {
    if (!processedData) return showToast("Primero debes procesar los archivos.", "warning");
    const prof = document.getElementById('professional-filter').value;
    const user = document.getElementById('user-filter').value;
    if (prof && user) return showToast("Selecciona solo uno: Profesional o Usuario.", "warning");
    if (prof) showFilteredView('prof', prof);
    else if (user) showFilteredView('user', user);
    else showGlobalView(processedData);
  });
});
