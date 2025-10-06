// ============================================================
// FRONTEND APP.JS - Virrey Solís IPS
// ============================================================

let processedData = null;
let abortController = null;
let progressInterval = null;

// ============================================================
// FUNCIONES DE NOTIFICACIÓN (TOASTS)
// ============================================================
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast-message ${type}`;
  toast.innerHTML = message.replace(/\n/g, "<br>");
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 50);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}

// ============================================================
// FUNCIÓN PRINCIPAL: SUBIR ARCHIVOS Y PROCESAR
// ============================================================
function uploadFiles() {
  const file1 = document.getElementById("file1-input")?.files[0];
  const file2 = document.getElementById("file2-input")?.files[0];
  const loadingDiv = document.getElementById("loading");
  const resultDiv = document.getElementById("result");
  const progressContainer = document.getElementById("progress-container");
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");

  if (!file1 || !file2) {
    showToast("❌ Por favor selecciona ambos archivos.", "error");
    return;
  }

  // Reiniciar UI
  loadingDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Procesando archivos...`;
  loadingDiv.style.display = "block";
  resultDiv.style.display = "none";
  document.getElementById("person-data").style.display = "none";
  document.getElementById("person-data").innerHTML = "";
  progressBar.style.backgroundColor = '#007bff'; // Reset progress bar color on new upload

  progressContainer.style.display = "block";
  progressBar.style.width = "0%";
  progressText.textContent = "Procesando... 0%";
  let progress = 0;
  clearInterval(progressInterval);
  progressInterval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 10, 95);
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `Procesando... ${Math.floor(progress)}%`;
  }, 600);

  abortController = new AbortController();
  const formData = new FormData();
  formData.append("file1", file1);
  formData.append("file2", file2);

  fetch("/upload", { method: "POST", body: formData, signal: abortController.signal })
    .then(async response => {
      const text = await response.text();
      try {
        // Si la respuesta es exitosa, parsea el JSON
        if (response.ok) {
          return JSON.parse(text);
        }
        // Si hay un error, intenta parsear el JSON de error
        const errorData = JSON.parse(text);
        throw new Error(errorData.error || "Ocurrió un error en el servidor.");
      } catch (e) {
        console.error("Respuesta no JSON o error de parseo:", text);
        throw new Error("El servidor devolvió una respuesta no válida.");
      }
    })
    .then(data => {
      clearInterval(progressInterval);
      progressBar.style.width = "100%";
      progressText.textContent = "✅ Procesamiento completado";
      setTimeout(() => progressContainer.style.display = "none", 1500);
      loadingDiv.style.display = "none";

      if (data.warning) showToast(data.warning, "warning");
      
      showToast("✅ Archivos procesados correctamente.", "success");
      processedData = data; // Guardamos los datos
      displayResults(data); // ✅ ¡LLAMAMOS A LA FUNCIÓN PARA MOSTRAR LOS DATOS!
      
    })
    .catch(error => {
      if (error.name === "AbortError") {
          showToast("Proceso cancelado por el usuario.", "warning");
          return;
      }
      clearInterval(progressInterval);
      progressBar.style.backgroundColor = "#dc3545";
      progressText.textContent = "❌ Error en el procesamiento";
      showToast(`❌ Error: ${error.message}`, "error");
      loadingDiv.style.display = "none";
    });
}

// ============================================================
// ✅ NUEVAS FUNCIONES PARA RENDERIZAR DATOS
// ============================================================

/**
 * Función principal que orquesta la visualización de resultados.
 */
function displayResults(data) {
  if (!data || !data.totals) {
    showToast("❌ No se recibieron datos válidos para mostrar.", "error");
    return;
  }
  updateGlobalData(data.totals);
  populateFilters(data.professionals, data.users);
  document.getElementById("result").style.display = "block";
}

/**
 * Actualiza las tarjetas de resumen con los totales.
 */
function updateGlobalData(totals) {
  document.getElementById("total-services-crystal").textContent = totals.total_services_crystal || 0;
  document.getElementById("total-services-query").textContent = totals.total_services_query || 0;
  document.getElementById("num-professionals").textContent = totals.num_professionals || 0;
  document.getElementById("num-users").textContent = totals.num_users || 0;
}

/**
 * Llena los menús desplegables con los profesionales y usuarios.
 */
function populateFilters(professionals, users) {
  const profFilter = document.getElementById("professional-filter");
  const userFilter = document.getElementById("user-filter");

  profFilter.innerHTML = '<option value="">Selecciona un profesional</option>';
  userFilter.innerHTML = '<option value="">Selecciona un usuario</option>';

  professionals.forEach(prof => {
    const option = document.createElement("option");
    option.value = prof;
    option.textContent = prof;
    profFilter.appendChild(option);
  });

  users.forEach(user => {
    const option = document.createElement("option");
    option.value = user;
    option.textContent = user;
    userFilter.appendChild(option);
  });
}

/**
 * Busca y muestra los datos de una persona específica (profesional o usuario).
 */
function searchData() {
  const profName = document.getElementById("professional-filter").value;
  const userName = document.getElementById("user-filter").value;
  const personDataContainer = document.getElementById("person-data");

  // Prioriza la búsqueda de profesionales si ambos están seleccionados
  const personName = profName || userName;
  const personType = profName ? 'professional' : 'user';

  if (!personName) {
    showToast("Selecciona un profesional o un usuario para buscar.", "warning");
    personDataContainer.style.display = "none";
    return;
  }

  const dataToShow = processedData[`${personType}_data`][personName];
  if (!dataToShow) {
    showToast("No se encontraron datos para la selección.", "error");
    return;
  }
  
  // Generar la tabla de resultados
  let tableHtml = `
    <hr>
    <h3>Resultados para: ${personName}</h3>
    <a href="${dataToShow.download_link}" class="download-button" download>📥 Descargar Excel</a>
    <table>
      <thead>
        <tr>
          <th>Servicio</th>
          <th>Cantidad</th>
        </tr>
      </thead>
      <tbody>
  `;
  
  for (const [service, count] of Object.entries(dataToShow.servicios_por_categoria)) {
    tableHtml += `
      <tr>
        <td>${service}</td>
        <td>${count}</td>
      </tr>
    `;
  }
  
  tableHtml += `</tbody></table>`;
  
  personDataContainer.innerHTML = tableHtml;
  personDataContainer.style.display = "block";
}


// ============================================================
// EVENTOS
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("process-button")?.addEventListener("click", uploadFiles);
  // ✅ AÑADIR EVENTO PARA EL BOTÓN DE BÚSQUEDA
  document.getElementById("search-button")?.addEventListener("click", searchData);
});
