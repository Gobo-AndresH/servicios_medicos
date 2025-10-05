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
                showGlobalView(data);
                populateFilters(data);
            } else {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = data.message || 'Error procesando los archivos.';
            }
        } catch (err) {
            resultDiv.className = 'result error';
            resultDiv.innerHTML = 'Error de conexión.';
            console.error(err);
        }
    });

    searchButton.addEventListener('click', () => {
        if (!processedData) return;
        const professional = document.getElementById('professional-filter').value;
        const user = document.getElementById('user-filter').value;
        showFilteredView(processedData, professional, user);
    });
});

function showGlobalView(data) {
    document.querySelector('.value-total').textContent = data.totalServices || 0;
    document.querySelector('.value-urgencias').textContent = data.urgencias || 0;
    document.querySelector('.value-general').textContent = data.medicinaGeneral || 0;
    document.querySelector('.value-today').textContent = data.servicesToday || 0;

    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'block';
    resultDiv.className = 'result success';
    resultDiv.innerHTML = 'Archivos procesados correctamente.';
}

function showFilteredView(data, professional, user) {
    let filtered = data.records || [];
    if (professional) filtered = filtered.filter(r => r.professional === professional);
    if (user) filtered = filtered.filter(r => r.user === user);

    const resultDiv = document.getElementById('result');
    if (filtered.length === 0) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = 'No se encontraron registros con esos filtros.';
        return;
    }

    // Generación de tabla responsiva
    let html = `<div class="table-responsive"><table><thead><tr>
        <th>Profesional</th>
        <th>Usuario</th>
        <th>Servicio</th>
        <th>Fecha</th>
        </tr></thead><tbody>`;

    filtered.forEach(r => {
        html += `<tr>
            <td>${r.professional}</td>
            <td>${r.user}</td>
            <td>${r.service}</td>
            <td>${r.date}</td>
        </tr>`;
    });

    html += '</tbody></table></div>';

    resultDiv.className = 'result success';
    resultDiv.innerHTML = html;
}

}

function populateFilters(data) {
    const professionalSelect = document.getElementById('professional-filter');
    const userSelect = document.getElementById('user-filter');

    const professionals = [...new Set((data.records || []).map(r => r.professional))];
    const users = [...new Set((data.records || []).map(r => r.user))];

    professionalSelect.innerHTML = `<option value="">Seleccionar Profesional</option>` + professionals.map(p => `<option value="${p}">${p}</option>`).join('');
    userSelect.innerHTML = `<option value="">Seleccionar Profesional (Query)</option>` + users.map(u => `<option value="${u}">${u}</option>`).join('');
}
