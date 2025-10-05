let currentController = null;

function uploadFiles() {
    const file1 = document.getElementById('file1-input').files[0];
    const file2 = document.getElementById('file2-input').files[0];
    const resultDiv = document.getElementById('result');
    const loadingDiv = document.getElementById('loading');

    if (!file1 || !file2) {
        resultDiv.innerHTML = "<p style='color:red;'>Por favor selecciona ambos archivos.</p>";
        resultDiv.style.display = 'block';
        return;
    }

    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);

    // Crear AbortController para cancelar
    currentController = new AbortController();

    loadingDiv.style.display = 'block';
    resultDiv.style.display = 'none';

    fetch('/upload', {
        method: 'POST',
        body: formData,
        signal: currentController.signal
    })
    .then(response => response.json())
    .then(data => {
        loadingDiv.style.display = 'none';
        if (data.error) {
            resultDiv.innerHTML = `<p style='color:red;'>Error: ${data.error}</p>`;
        } else {
            resultDiv.innerHTML = "<h3>Archivos procesados:</h3>";
            data.files.forEach(f => {
                const link = document.createElement('a');
                link.href = f.url;
                link.download = '';
                link.textContent = `Descargar ${f.name}`;
                link.target = '_blank';
                link.click(); // 🔽 Descarga automática
                resultDiv.appendChild(link);
                resultDiv.appendChild(document.createElement('br'));
            });
        }
        resultDiv.style.display = 'block';
    })
    .catch(error => {
        loadingDiv.style.display = 'none';
        if (error.name === 'AbortError') {
            resultDiv.innerHTML = "<p style='color:orange;'>Operación cancelada.</p>";
        } else {
            resultDiv.innerHTML = `<p style='color:red;'>Error: ${error.message}</p>`;
        }
        resultDiv.style.display = 'block';
    });
}

function cancelUpload() {
    if (currentController) {
        currentController.abort();
        currentController = null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('process-button').addEventListener('click', uploadFiles);
    document.getElementById('cancel-button').addEventListener('click', cancelUpload);
});
