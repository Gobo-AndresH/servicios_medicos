// Verificar si se accede a través de un servidor válido
if (window.location.protocol === 'file:') {
    alert("Por favor, abre esta aplicación desde el servidor Flask (Render) en https://servicios-medicos-n3bl.onrender.com/");
}

// Registrar Service Worker para PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(reg => console.log('Service Worker registrado con alcance:', reg.scope))
            .catch(err => console.error('Error al registrar Service Worker:', err));
    });
}

let processedData = null;
let abortController = null; // Controlador global para cancelar el envío

function uploadFiles() {
    const file1Input = document.getElementById('file1-input');
    const file2Input = document.getElementById('file2-input');
    const file1 = file1Input?.files[0];
    const file2 = file2Input?.files[0];
    const resultDiv = document.getElementById('result');
    const loadingDiv = document.getElementById('loading');

    // Validaciones básicas
    if (!file1 || !file2) {
        resultDiv.innerHTML = `<div style="color:red;">Por favor, selecciona ambos archivos.</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    const validExtensions = ['xlsx', 'xls'];
    if (!validExtensions.includes(file1.name.split('.').pop().toLowerCase()) ||
        !validExtensions.includes(file2.name.split('.').pop().toLowerCase())) {
        resultDiv.innerHTML = `<div style="color:red;">Solo se permiten archivos Excel (.xlsx o .xls).</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    // Mostrar carga con botón de cancelar
    loadingDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Procesando archivos...`;
    loadingDiv.style.display = 'block';
    resultDiv.style.display = 'none';

    const cancelButton = document.createElement('button');
    cancelButton.textContent = "Cancelar envío";
    cancelButton.className = "cancel-button";
    cancelButton.onclick = () => {
        if (abortController) {
            abortController.abort();
            loadingDiv.innerHTML = `<div style="color:red;">⛔ Envío cancelado por el usuario.</div>`;
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
            throw new Error("⚠️ El servidor devolvió una respuesta no válida. Verifica la consola o el backend.");
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

function mostrarResultados(data) {
    const totalServicesCrystal = document.getElementById('total-services-crystal');
    const totalServicesQuery = document.getElementById('total-services-query');
    const numProfessionals = document.getElementById('num-professionals');
    const numUsers = document.getElementById('num-users');
    const profSelect = document.getElementById('professional-filter');
    const userSelect = document.getElementById('user-filter');
    const resultDiv = document.getElementById('result');

    totalServicesCrystal.textContent = data.totals.total_services_crystal;
    totalServicesQuery.textContent = data.totals.total_services_query;
    numProfessionals.textContent = data.totals.num_professionals;
    numUsers.textContent = data.totals.num_users;

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

function showFilteredView(type, name) {
    let personData = type === 'prof' ? processedData.professional_data[name] : processedData.user_data[name];
    let fileType = type === 'prof' ? 'Crystal' : 'Query';

    if (personData) {
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

        const downloadButton = document.createElement('a');
        downloadButton.href = personData.download_link;
        downloadButton.className = 'download-button';
        downloadButton.textContent = "⬇️ Descargar Excel filtrado";
        downloadButton.target = "_blank";
        personSection.appendChild(downloadButton);

        const resumenDiv = document.createElement('div');
        resumenDiv.className = 'servicios-categoria';
        mostrarResumenServicios(toTitleCase(name), personData.servicios_por_categoria, fileType, resumenDiv);
        personSection.appendChild(resumenDiv);

        const detalladosDiv = document.createElement('div');
        detalladosDiv.className = 'detallados-servicios';
        mostrarResumenDetallados(toTitleCase(name), personData.servicios_detallados, fileType, detalladosDiv);
        personSection.appendChild(detalladosDiv);
    } else {
        alert('No se encontraron datos para el profesional o usuario seleccionado.');
    }
}

function toTitleCase(str) {
    return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
}

function showGlobalView(data) {
    const globalData = document.getElementById('global-data');
    const personData = document.getElementById('person-data');
    globalData.innerHTML = '';
    personData.style.display = 'none';

    globalData.appendChild(createCategoriaContainer('crystal', data.totals.servicios_por_categoria_crystal));
    globalData.appendChild(createDetalladosContainer('crystal', data.totals.servicios_detallados_crystal));
    globalData.appendChild(createCategoriaContainer('query', data.totals.servicios_por_categoria_query));
    globalData.appendChild(createDetalladosContainer('query', data.totals.servicios_detallados_query));

    globalData.style.display = 'block';
}

function createCategoriaContainer(tipo, totales) {
    const container = document.createElement('div');
    container.className = 'servicios-categoria';
    container.innerHTML = `<h3>Total de Servicios por Categoría (${tipo.toUpperCase()})</h3>`;
    const table = document.createElement('table');
    table.innerHTML = `
        <thead><tr><th>Categoría</th><th>Cantidad</th></tr></thead>
        <tbody>${Object.entries(totales).map(([c, v]) => `<tr><td>${c.toUpperCase()}</td><td>${v}</td></tr>`).join('')}</tbody>`;
    container.appendChild(table);
    return container;
}

function createDetalladosContainer(tipo, servicios) {
    const container = document.createElement('div');
    container.className = 'detallados-servicios';
    container.innerHTML = `<h3>Detalles por Nombre de Servicio (${tipo.toUpperCase()})</h3>`;
    const table = document.createElement('table');
    table.innerHTML = `
        <thead><tr><th>Nombre de Servicio</th><th>Cantidad</th></tr></thead>
        <tbody>${Object.entries(servicios).map(([s, v]) => `<tr><td>${s.toUpperCase()}</td><td>${v}</td></tr>`).join('')}</tbody>`;
    container.appendChild(table);
    return container;
}

function mostrarResumenServicios(nombre, servicios, fileType, container) {
    container.innerHTML = `<h3>Resumen de Servicios por Categoría - ${nombre}</h3>
        <table><thead><tr><th>Tipo de Servicio</th><th>Cantidad</th></tr></thead>
        <tbody>${Object.entries(servicios).map(([c, v]) => `<tr><td>${c.toUpperCase()}</td><td>${v}</td></tr>`).join('')}</tbody></table>`;
}

function mostrarResumenDetallados(nombre, servicios, fileType, container) {
    container.innerHTML = `<h3>Resumen Detallado - ${nombre} (${fileType})</h3>
        <table><thead><tr><th>Nombre de Servicio</th><th>Cantidad</th></tr></thead>
        <tbody>${Object.entries(servicios).map(([s, v]) => `<tr><td>${s.toUpperCase()}</td><td>${v}</td></tr>`).join('')}</tbody></table>`;
}

document.addEventListener('DOMContentLoaded', () => {
    const processButton = document.getElementById('process-button');
    const searchButton = document.getElementById('search-button');

    if (processButton) processButton.addEventListener('click', uploadFiles);
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            if (!processedData) {
                alert("Primero debes procesar los archivos.");
                return;
            }
            const prof = document.getElementById('professional-filter').value;
            const user = document.getElementById('user-filter').value;
            if (prof && user) {
                alert("Selecciona solo uno: Profesional o Usuario.");
                return;
            }
            if (prof) showFilteredView('prof', prof);
            else if (user) showFilteredView('user', user);
            else showGlobalView(processedData);
        });
    }
});
