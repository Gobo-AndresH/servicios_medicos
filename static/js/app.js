// Service Worker PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
        .then(reg => console.log('SW registrado:', reg.scope))
        .catch(err => console.error('SW falló:', err));
    });
}

let processedData = null;

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');
    const profSelect = document.getElementById('filter-prof');
    const userSelect = document.getElementById('filter-user');
    const filterButton = document.getElementById('filter-button');

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        resultDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Procesando archivos...</div>';
        resultDiv.style.display = 'block';

        const formData = new FormData(uploadForm);

        try {
            const res = await fetch('/upload', { method:'POST', body: formData });
            const data = await res.json();

            if (!res.ok) {
                showError(data);
                return;
            }

            processedData = data;
            showResults(data);
            populateFilters(data);

        } catch(err) {
            showError({ error: err.message });
        }
    });

    filterButton.addEventListener('click', () => {
        if (!processedData) return alert("Primero sube los archivos");
        const prof = profSelect.value;
        const user = userSelect.value;
        showFilteredView(processedData, prof, user);
    });
});

// Mostrar resultados
function showResults(data) {
    const resultDiv = document.getElementById('result');
    resultDiv.className = 'result success';
    resultDiv.innerHTML = `
        <h3><i class="fas fa-check-circle"></i> Archivos procesados correctamente</h3>
        <p>Total registros: ${data.stats.total || 0}</p>
    `;
    updateDashboard(data.stats);
}

// Actualizar dashboard
function updateDashboard(stats) {
    document.querySelector('.value-total').textContent = stats.total || 0;
    document.querySelector('.value-urgencias').textContent = stats.urgencias || 0;
    document.querySelector('.value-general').textContent = stats.general || 0;
    document.querySelector('.value-today').textContent = stats.hoy || 0;
}

// Mostrar errores
function showError(data) {
    const resultDiv = document.getElementById('result');
    resultDiv.className = 'result error';
    resultDiv.innerHTML = `<h3><i class="fas fa-exclamation-circle"></i> Error</h3>
    <p>${data.error || "Error desconocido"}</p>`;
}

// Filtrado
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

// Llenar filtros
function populateFilters(data) {
    const profSelect = document.getElementById('filter-prof');
    const userSelect = document.getElementById('filter-user');
    const professionals = [...new Set(data.records.map(r => r.professional))].sort();
    const users = [...new Set(data.records.map(r => r.user))].sort();

    profSelect.innerHTML = '<option value="">--Seleccionar--</option>';
    professionals.forEach(p => { profSelect.innerHTML += `<option value="${p}">${p}</option>` });

    userSelect.innerHTML = '<option value="">--Seleccionar--</option>';
    users.forEach(u => { userSelect.innerHTML += `<option value="${u}">${u}</option>` });
}
