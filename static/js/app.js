// Crear un controlador para abortar la solicitud
let abortController = null;

function uploadFiles() {
    const file1Input = document.getElementById('file1-input');
    const file2Input = document.getElementById('file2-input');
    const file1 = file1Input?.files[0];
    const file2 = file2Input?.files[0];
    const resultDiv = document.getElementById('result');
    const loadingDiv = document.getElementById('loading');

    if (!file1 || !file2) {
        resultDiv.innerHTML = `<div style="color:red;">Por favor, selecciona ambos archivos.</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    // Mostrar carga y botón de cancelar
    loadingDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    const cancelButton = document.createElement('button');
    cancelButton.textContent = "Cancelar envío";
    cancelButton.style = "margin-top:10px; background-color:#dc3545; color:white; padding:8px 12px; border:none; border-radius:5px; cursor:pointer;";
    cancelButton.onclick = () => {
        if (abortController) {
            abortController.abort();
            loadingDiv.innerHTML = `<div style="color:red;">Envío cancelado por el usuario.</div>`;
        }
    };
    loadingDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Procesando archivos...`;
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
        } catch (err) {
            throw new Error("El servidor devolvió una respuesta no válida. Verifica la consola o el backend.");
        }
    })
    .then(data => {
        loadingDiv.style.display = 'none';
        if (data.error) {
            resultDiv.innerHTML = `<div style="color:red;">Error: ${data.error}</div>`;
            resultDiv.style.display = 'block';
        } else {
            processedData = data;
            mostrarResultados(data);
        }
    })
    .catch(error => {
        if (error.name === 'AbortError') {
            console.warn("Solicitud cancelada por el usuario.");
            return;
        }
        loadingDiv.style.display = 'none';
        resultDiv.innerHTML = `<div style="color:red;">Error: ${error.message}</div>`;
        resultDiv.style.display = 'block';
    });
}
