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

  loadingDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Procesando archivos...`;
  loadingDiv.style.display = "block";
  resultDiv.style.display = "none";

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
        return JSON.parse(text);
      } catch (e) {
        console.error("Respuesta no JSON:", text);
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
      if (data.error) {
        const details = data.details ? `<br><small>${data.details.join("<br>")}</small>` : "";
        showToast(`❌ ${data.error}${details}`, "error");
      } else {
        showToast("✅ Archivos procesados correctamente.", "success");
        processedData = data;
        document.getElementById("result").style.display = "block";
      }
    })
    .catch(error => {
      if (error.name === "AbortError") return;
      clearInterval(progressInterval);
      progressBar.style.backgroundColor = "#dc3545";
      progressText.textContent = "❌ Error en el procesamiento";
      showToast(`❌ Error: ${error.message}`, "error");
      loadingDiv.style.display = "none";
    });
}

// ============================================================
// EVENTOS
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("process-button")?.addEventListener("click", uploadFiles);
});
