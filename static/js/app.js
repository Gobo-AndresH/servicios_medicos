let processedData = null;

// Validación de carga de archivos y envío
document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const searchButton = document.getElementById('search-button');

    uploadForm.addEventListener('submit', async e => {
        e.preventDefault();
        const resultDiv = document.getElementById('result');
        const crystalFile = document.getElementById('crystalFile').files[0];
        const queryFile = document.getElementById('queryFile').files[0];

        if (!crystalFile || !queryFile) {
            alert('Por favor, selecciona ambos archivos.');
            return;
        }

        resultDiv.style.display = 'block';
        resultDiv.className = 'result';
        resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando archivos...';

        const formData = new FormData();
        formData.append('crystal_file', crystalFile);
        formData.append('query_file', queryFile);

        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const data = await response.json();

            if (response.ok) {
                processedData = data;
                show
