// Verificar si se accede a través de un servidor
if (window.location.protocol === 'file:') {
    alert("Por favor, abre esta aplicación a través del servidor Flask en http://127.0.0.1:5000/, no como archivo local.");
}

// Registrar Service Worker para PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered with scope:', registration.scope);
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    });
}

let processedData = null; // Almacenar los datos procesados para no perderlos

function uploadFiles() {
    const file1Input = document.getElementById('file1-input');
    const file2Input = document.getElementById('file2-input');
    const file1 = file1Input?.files[0];
    const file2 = file2Input?.files[0];
    const resultDiv = document.getElementById('result');
    const loadingDiv = document.getElementById('loading');

    // Validar elementos del DOM
    if (!file1Input || !file2Input || !resultDiv || !loadingDiv) {
        console.error("Error: Uno o más elementos de entrada no se encontraron en el DOM.");
        resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Error: Elementos de la interfaz no encontrados.</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    if (!file1 || !file2) {
        resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Por favor, selecciona ambos archivos.</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    const validExtensions = ['xlsx', 'xls'];
    const file1Ext = file1.name.split('.').pop().toLowerCase();
    const file2Ext = file2.name.split('.').pop().toLowerCase();
    if (!validExtensions.includes(file1Ext) || !validExtensions.includes(file2Ext)) {
        resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Por favor, sube archivos en formato Excel (.xlsx o .xls).</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    if (file1.size > 16 * 1024 * 1024 || file2.size > 16 * 1024 * 1024) {
        resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Uno o ambos archivos exceden el límite de 16 MB.</div>`;
        resultDiv.style.display = 'block';
        return;
    }

    loadingDiv.style.display = 'block';
    resultDiv.style.display = 'none';

    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);
    console.log("Enviando archivo1:", file1.name, "y archivo2:", file2.name);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log("Respuesta recibida:", response);
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        loadingDiv.style.display = 'none';
        if (data.error) {
            resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Error: ${data.error}</div>`;
            resultDiv.style.display = 'block';
        } else {
            processedData = data; // Almacenar los datos procesados

            // Validar elementos antes de actualizar totales
            const totalServicesCrystal = document.getElementById('total-services-crystal');
            const totalServicesQuery = document.getElementById('total-services-query');
            const numProfessionals = document.getElementById('num-professionals');
            const numUsers = document.getElementById('num-users');
            const profSelect = document.getElementById('professional-filter');
            const userSelect = document.getElementById('user-filter');

            if (!totalServicesCrystal || !totalServicesQuery || !numProfessionals || !numUsers || !profSelect || !userSelect) {
                console.error("Error: Uno o más elementos de la interfaz no se encontraron en el DOM.");
                resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Error: Elementos de la interfaz no encontrados.</div>`;
                resultDiv.style.display = 'block';
                return;
            }

            // Actualizar totales
            totalServicesCrystal.textContent = data.totals.total_services_crystal;
            totalServicesQuery.textContent = data.totals.total_services_query;
            numProfessionals.textContent = data.totals.num_professionals;
            numUsers.textContent = data.totals.num_users;

            // Mostrar información global
            showGlobalView(data);

            // Ordenar alfabéticamente los profesionales y usuarios
            const sortedProfessionals = data.professionals.slice().sort((a, b) => a.localeCompare(b));
            const sortedUsers = data.users.slice().sort((a, b) => a.localeCompare(b));

            // Llenar el selector de profesionales
            profSelect.innerHTML = '<option value="">Seleccionar Profesional</option>';
            sortedProfessionals.forEach(prof => {
                if (prof && prof !== 'nan') {
                    const option = document.createElement('option');
                    option.value = prof;
                    option.textContent = toTitleCase(prof);
                    profSelect.appendChild(option);
                }
            });

            // Llenar el selector de usuarios
            userSelect.innerHTML = '<option value="">Seleccionar Profesional (Query)</option>';
            sortedUsers.forEach(user => {
                if (user && user !== 'nan') {
                    const option = document.createElement('option');
                    option.value = user;
                    option.textContent = toTitleCase(user);
                    userSelect.appendChild(option);
                }
            });

            resultDiv.style.display = 'block';
        }
    })
    .catch(error => {
        loadingDiv.style.display = 'none';
        resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Error: ${error.message}</div>`;
        resultDiv.style.display = 'block';
    });
}

function toTitleCase(str) {
    return str.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
}

function showGlobalView(data) {
    const globalData = document.getElementById('global-data');
    const personData = document.getElementById('person-data');

    if (!globalData || !personData) {
        console.error("Error: No se encontraron los elementos 'global-data' o 'person-data' en el DOM.");
        return;
    }

    globalData.innerHTML = '';
    personData.style.display = 'none';

    // Mostrar totales por categoría y detallados para crystal y query
    const crystalCategoria = createCategoriaContainer('crystal', data.totals.servicios_por_categoria_crystal);
    globalData.appendChild(crystalCategoria);

    const crystalDetallados = createDetalladosContainer('crystal', data.totals.servicios_detallados_crystal);
    globalData.appendChild(crystalDetallados);

    const queryCategoria = createCategoriaContainer('query', data.totals.servicios_por_categoria_query);
    globalData.appendChild(queryCategoria);

    const queryDetallados = createDetalladosContainer('query', data.totals.servicios_detallados_query);
    globalData.appendChild(queryDetallados);

    globalData.style.display = 'block';
}

function showFilteredView(type, name) {
    let personData;
    let fileType = type === 'prof' ? 'Crystal' : 'Query';
    if (type === 'prof') {
        personData = processedData.professional_data[name];
    } else if (type === 'user') {
        personData = processedData.user_data[name];
    }

    if (personData) {
        const globalData = document.getElementById('global-data');
        const personSection = document.getElementById('person-data');

        if (!globalData || !personSection) {
            console.error("Error: No se encontraron los elementos 'global-data' o 'person-data' en el DOM.");
            return;
        }

        globalData.style.display = 'none';
        personSection.innerHTML = '';
        personSection.style.display = 'block';

        // Crear botón de atrás
        const backButton = document.createElement('button');
        backButton.id = 'back-button';
        backButton.textContent = 'Atrás';
        backButton.addEventListener('click', () => {
            showGlobalView(processedData);
            document.getElementById('professional-filter').value = '';
            document.getElementById('user-filter').value = '';
        });
        personSection.appendChild(backButton);

        // Resumen por categoría
        const resumenDiv = document.createElement('div');
        resumenDiv.className = 'servicios-categoria';
        mostrarResumenServicios(toTitleCase(name), personData.servicios_por_categoria, fileType, resumenDiv);
        personSection.appendChild(resumenDiv);

        // Resumen detallado
        const detalladosDiv = document.createElement('div');
        detalladosDiv.className = 'detallados-servicios';
        mostrarResumenDetallados(toTitleCase(name), personData.servicios_detallados, fileType, detalladosDiv);
        personSection.appendChild(detalladosDiv);
    } else {
        alert('No se encontró datos para el profesional seleccionado.');
    }
}

function createCategoriaContainer(tipo, totales) {
    const container = document.createElement('div');
    container.className = 'servicios-categoria';
    container.innerHTML = `<h3>Total de Servicios por Categoría (${tipo.toUpperCase()})</h3>`;
    
    const table = document.createElement('table');
    table.innerHTML = `
        <thead>
            <tr>
                <th>Categoría</th>
                <th>Cantidad</th>
            </tr>
        </thead>
        <tbody>
            ${Object.entries(totales).map(([categoria, cantidad]) => `
                <tr>
                    <td>${categoria.toUpperCase()}</td>
                    <td>${cantidad}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    
    container.appendChild(table);
    return container;
}

function createDetalladosContainer(tipo, servicios) {
    const container = document.createElement('div');
    container.className = 'detallados-servicios';
    container.innerHTML = `<h3>Detalles por Nombre de Servicio (${tipo.toUpperCase()})</h3>`;
    
    const table = document.createElement('table');
    table.innerHTML = `
        <thead>
            <tr>
                <th>Nombre de Servicio</th>
                <th>Cantidad</th>
            </tr>
        </thead>
        <tbody>
            ${Object.entries(servicios).map(([servicio, cantidad]) => `
                <tr>
                    <td>${servicio.toUpperCase()}</td>
                    <td>${cantidad}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    
    container.appendChild(table);
    return container;
}

function mostrarResumenServicios(nombre, servicios, fileType, container) {
    container.innerHTML = `<h3>Resumen de Servicios por Categoría - ${nombre}</h3>
        <table>
            <thead>
                <tr>
                    <th>Tipo de Servicio</th>
                    <th>Cantidad</th>
                </tr>
            </thead>
            <tbody>
                ${Object.entries(servicios).map(([categoria, cantidad]) => `
                    <tr>
                        <td>${categoria.toUpperCase()}</td>
                        <td>${cantidad}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
}

function mostrarResumenDetallados(nombre, servicios, fileType, container) {
    container.innerHTML = `<h3>Resumen Detallado por Nombre de Servicio - ${nombre} (${fileType})</h3>
        <table>
            <thead>
                <tr>
                    <th>Nombre de Servicio</th>
                    <th>Cantidad</th>
                </tr>
            </thead>
            <tbody>
                ${Object.entries(servicios).map(([servicio, cantidad]) => `
                    <tr>
                        <td>${servicio.toUpperCase()}</td>
                        <td>${cantidad}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
}

document.addEventListener('DOMContentLoaded', () => {
    const processButton = document.getElementById('process-button');
    const searchButton = document.getElementById('search-button');
    const resultDiv = document.getElementById('result');

    if (processButton) {
        processButton.addEventListener('click', uploadFiles);
    } else {
        console.error("El botón con id 'process-button' no se encontró en el DOM.");
    }

    if (searchButton) {
        searchButton.addEventListener('click', () => {
            if (!processedData) {
                alert("Por favor, procesa los archivos primero antes de buscar.");
                return;
            }

            const profSelect = document.getElementById('professional-filter');
            const userSelect = document.getElementById('user-filter');
            const selectedProf = profSelect.value;
            const selectedUser = userSelect.value;

            if (selectedProf && selectedUser) {
                alert("No es posible filtrar ambos archivos al mismo tiempo. Selecciona solo uno.");
                return;
            }

            if (selectedProf) {
                showFilteredView('prof', selectedProf);
            } else if (selectedUser) {
                showFilteredView('user', selectedUser);
            } else {
                showGlobalView(processedData);
            }
        });
    } else {
        console.error("El botón con id 'search-button' no se encontró en el DOM.");
        resultDiv.innerHTML = `<div style="color: red; text-align: center; padding: 10px; background-color: #f8d7da; border-radius: 5px;">Error: Botón de buscar no encontrado.</div>`;
        resultDiv.style.display = 'block';
    }
});