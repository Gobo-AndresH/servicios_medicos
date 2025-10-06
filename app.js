// ========================================================
// VARIABLES GLOBALES
// ========================================================

let currentProcessId = null;
let isProcessing = false;
let cancelRequested = false;

// ========================================================
// FUNCIONES DE UTILIDAD
// ========================================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 400);
    }, 4000);
}

function showDetailedError(errorData) {
    console.error("Error detallado:", errorData);
    
    let errorMessage = errorData.error || "Error desconocido";
    
    if (errorData.details) {
        errorMessage += "\n\n🔍 Detalles del error:";
        
        if (errorData.details.crystal_columns) {
            errorMessage += `\n\nColumnas en archivo CRYSTAL:\n- ${errorData.details.crystal_columns.join('\n- ')}`;
        }
        
        if (errorData.details.query_columns) {
            errorMessage += `\n\nColumnas en archivo QUERY:\n- ${errorData.details.query_columns.join('\n- ')}`;
        }
    }
    
    alert(`❌ Error:\n\n${errorMessage}`);
}

function updateProgress(percent) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (progressBar && progressText) {
        progressBar.style.width = percent + '%';
        progressText.textContent = `Procesando... ${Math.round(percent)}%`;
    }
}

function toggleProcessingUI(show) {
    const loading = document.getElementById('loading');
    const progressContainer = document.getElementById('progress-container');
    const processButton = document.getElementById('process-button');
    const cancelButton = document.getElementById('cancel-button');
    
    isProcessing = show;
    
    if (loading) {
        loading.style.display = show ? 'block' : 'none';
        loading.innerHTML = show ? 
            '<div class="loading-spinner">⏳ Procesando archivos, por favor espera...</div>' : 
            '';
    }
    
    if (progressContainer) {
        progressContainer.style.display = show ? 'block' : 'none';
    }
    
    if (processButton) {
        processButton.disabled = show;
        processButton.textContent = show ? '⏳ Procesando...' : '⚙️ Procesar archivos';
    }
    
    if (cancelButton) {
        cancelButton.style.display = show ? 'inline-block' : 'none';
        cancelButton.disabled = false;
    }
}

// ========================================================
// FUNCIONES DE CANCELACIÓN
// ========================================================

async function cancelProcess() {
    if (!currentProcessId || !isProcessing) {
        return;
    }
    
    try {
        cancelRequested = true;
        const cancelButton = document.getElementById('cancel-button');
        if (cancelButton) {
            cancelButton.disabled = true;
            cancelButton.textContent = '🛑 Cancelando...';
        }
        
        showToast('🛑 Solicitando cancelación...', 'warning');
        
        const response = await fetch('/cancel-process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ process_id: currentProcessId })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('✅ Proceso cancelado correctamente', 'success');
        } else {
            showToast('⚠️ ' + (result.error || 'No se pudo cancelar el proceso'), 'warning');
        }
        
        resetUI();
        
    } catch (error) {
        console.error('Error cancelando proceso:', error);
        showToast('❌ Error al cancelar el proceso', 'error');
        resetUI();
    }
}

function resetUI() {
    toggleProcessingUI(false);
    updateProgress(0);
    currentProcessId = null;
    isProcessing = false;
    cancelRequested = false;
    
    const cancelButton = document.getElementById('cancel-button');
    if (cancelButton) {
        cancelButton.textContent = '❌ Cancelar Proceso';
        cancelButton.disabled = false;
    }
}

// ========================================================
// FUNCIONES DE PROCESAMIENTO PRINCIPAL
// ========================================================

async function processFiles() {
    if (isProcessing) {
        showToast('⚠️ Ya hay un proceso en ejecución', 'warning');
        return;
    }
    
    const file1Input = document.getElementById('file1-input');
    const file2Input = document.getElementById('file2-input');
    
    const file1 = file1Input.files[0];
    const file2 = file2Input.files[0];
    
    if (!file1 || !file2) {
        showToast('❌ Debes seleccionar ambos archivos', 'error');
        return;
    }
    
    if (!file1.name.match(/\.(xlsx|xls)$/i) || !file2.name.match(/\.(xlsx|xls)$/i)) {
        showToast('❌ Ambos archivos deben ser de Excel (.xlsx o .xls)', 'error');
        return;
    }
    
    console.log('📤 Iniciando procesamiento de archivos...');
    
    cancelRequested = false;
    currentProcessId = Date.now().toString();
    
    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);
    
    toggleProcessingUI(true);
    updateProgress(10);
    
    try {
        updateProgress(20);
        
        console.log('🔄 Enviando archivos al servidor...');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000);
        
        // ✅ URL CORREGIDA para Render - usa ruta relativa
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (cancelRequested) {
            showToast('ℹ️ Proceso interrumpido por el usuario', 'info');
            return;
        }
        
        console.log('✅ Respuesta recibida del servidor. Status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { error: `Error del servidor: ${response.status} - ${errorText}` };
            }
            throw new Error(errorData.error || `Error del servidor: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📊 Datos recibidos del servidor:', data);
        
        if (cancelRequested) {
            showToast('ℹ️ Proceso interrumpido por el usuario', 'info');
            return;
        }
        
        if (data.error) {
            if (data.error.includes('cancelado')) {
                showToast('✅ Proceso cancelado por el usuario', 'info');
                return;
            }
            showDetailedError(data);
            return;
        }
        
        updateProgress(100);
        showToast('✅ Archivos procesados correctamente', 'success');
        
        processData(data);
        
    } catch (error) {
        console.error('Error en processFiles:', error);
        
        if (error.name === 'AbortError') {
            showToast('⏰ Tiempo de espera agotado. El proceso tomó demasiado tiempo.', 'error');
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            showToast('❌ Error de conexión. Verifica que el servidor esté funcionando.', 'error');
        } else if (!cancelRequested) {
            showToast(`❌ Error: ${error.message}`, 'error');
        }
    } finally {
        if (!cancelRequested) {
            setTimeout(() => {
                toggleProcessingUI(false);
                updateProgress(0);
            }, 2000);
        }
    }
}

function processData(data) {
    console.log('Procesando datos recibidos...', data);
    
    const resultSection = document.getElementById('result');
    const personDataSection = document.getElementById('person-data');
    
    if (resultSection) {
        resultSection.style.display = 'block';
        console.log('✅ Sección de resultados mostrada');
    }
    if (personDataSection) {
        personDataSection.style.display = 'none';
    }
    
    updateGlobalData(data.totals);
    populateFilters(data.professionals, data.usuarios_crystal, data.usuarios_query);
    
    window.appData = data;
    
    if (data.column_mapping) {
        console.log('Columnas utilizadas:', data.column_mapping);
        showToast(`✅ Columnas detectadas: ${data.column_mapping.crystal.profesional}, ${data.column_mapping.crystal.servicio}`, 'success');
    }
}

function updateGlobalData(totals) {
    console.log('Actualizando datos globales:', totals);
    
    const elements = {
        'total-services-crystal': totals.total_services_crystal,
        'total-services-query': totals.total_services_query,
        'num-professionals': totals.num_professionals,
        'num-users': totals.num_users_crystal || totals.num_users
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value.toLocaleString();
            console.log(`Actualizado ${id}: ${value}`);
        }
    }
}

function populateFilters(professionals, usuariosCrystal, usuariosQuery) {
    console.log('Llenando filtros. Profesionales:', professionals, 'Usuarios Crystal:', usuariosCrystal, 'Usuarios Query:', usuariosQuery);
    
    const professionalFilter = document.getElementById('professional-filter');
    const userFilter = document.getElementById('user-filter');
    
    if (professionalFilter) {
        professionalFilter.innerHTML = '<option value="">Todos los profesionales (Crystal)</option>';
        if (professionals && professionals.length > 0) {
            professionals.forEach(prof => {
                const option = document.createElement('option');
                option.value = prof;
                option.textContent = prof;
                professionalFilter.appendChild(option);
            });
            console.log(`✅ Filtro de profesionales cargado: ${professionals.length} opciones`);
        }
    }
    
    if (userFilter) {
        userFilter.innerHTML = '<option value="">Todos los usuarios (Query)</option>';
        if (usuariosQuery && usuariosQuery.length > 0) {
            usuariosQuery.forEach(user => {
                const option = document.createElement('option');
                option.value = user;
                option.textContent = user;
                userFilter.appendChild(option);
            });
            console.log(`✅ Filtro de usuarios Query cargado: ${usuariosQuery.length} opciones`);
        }
    }
}

// ========================================================
// FUNCIONES DE BÚSQUEDA Y FILTRADO
// ========================================================

function searchData() {
    const professionalFilter = document.getElementById('professional-filter');
    const userFilter = document.getElementById('user-filter');
    
    const selectedProfessional = professionalFilter ? professionalFilter.value : '';
    const selectedUser = userFilter ? userFilter.value : '';
    
    console.log('Buscando datos para:', { selectedProfessional, selectedUser });
    
    if (!window.appData) {
        showToast('❌ Primero debe procesar los archivos', 'error');
        return;
    }
    
    let resultHTML = '';
    let foundData = false;
    
    // Buscar en profesionales (CRYSTAL)
    if (selectedProfessional && window.appData.professional_data && window.appData.professional_data[selectedProfessional]) {
        const profData = window.appData.professional_data[selectedProfessional];
        resultHTML = createProfessionalHTML(selectedProfessional, profData);
        foundData = true;
        console.log(`✅ Datos encontrados para profesional: ${selectedProfessional}`);
    }
    
    // Buscar en validación de Query (si no se seleccionó nada específico)
    if (!foundData && selectedUser === '' && selectedProfessional === '' && window.appData.user_data && window.appData.user_data.query_validation) {
        const queryData = window.appData.user_data.query_validation;
        resultHTML = createQueryValidationHTML(queryData);
        foundData = true;
        console.log('✅ Mostrando datos de validación Query');
    }
    
    if (!foundData) {
        if (selectedProfessional || selectedUser) {
            showToast('❌ No se encontraron datos para los filtros seleccionados', 'error');
        } else {
            showToast('❌ Seleccione un profesional para buscar', 'error');
        }
        return;
    }
    
    const personDataSection = document.getElementById('person-data');
    const globalDataSection = document.getElementById('global-data');
    
    if (personDataSection) {
        personDataSection.innerHTML = resultHTML;
        personDataSection.style.display = 'block';
    }
    
    if (globalDataSection) {
        globalDataSection.style.display = 'none';
    }
    
    addBackButton();
}

function createProfessionalHTML(professional, data) {
    const totalServicios = data.total_servicios || 0;
    const totalUsuarios = data.total_usuarios || 0;
    
    let html = `
        <h2>👨‍⚕️ Profesional: ${professional}</h2>
        
        <div class="professional-stats">
            <div class="stat-card">
                <h3>Total Servicios</h3>
                <div class="stat-number">${totalServicios.toLocaleString()}</div>
            </div>
            <div class="stat-card">
                <h3>Total Usuarios</h3>
                <div class="stat-number">${totalUsuarios.toLocaleString()}</div>
            </div>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="${data.download_link}" class="download-button" target="_blank" download="${data.nombre_archivo}">
                📥 Descargar: ${data.nombre_archivo}
            </a>
        </div>
    `;
    
    if (data.servicios_por_categoria && Object.keys(data.servicios_por_categoria).length > 0) {
        html += `
            <h3>📊 Servicios por Categoría</h3>
            <table>
                <thead>
                    <tr>
                        <th>Servicio</th>
                        <th>Cantidad</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        for (const [servicio, cantidad] of Object.entries(data.servicios_por_categoria)) {
            html += `
                <tr>
                    <td>${servicio}</td>
                    <td>${cantidad.toLocaleString()}</td>
                </tr>
            `;
        }
        
        html += `
                </tbody>
            </table>
        `;
    }
    
    return html;
}

function createQueryValidationHTML(queryData) {
    let html = `
        <h2>📋 Validación de Usuarios - Archivo Query</h2>
        
        <div class="professional-stats">
            <div class="stat-card">
                <h3>Total Usuarios Query</h3>
                <div class="stat-number">${queryData.total_usuarios.toLocaleString()}</div>
            </div>
            <div class="stat-card">
                <h3>En Crystal</h3>
                <div class="stat-number" style="color: #28a745;">${queryData.usuarios_en_crystal.toLocaleString()}</div>
            </div>
            <div class="stat-card">
                <h3>Solo en Query</h3>
                <div class="stat-number" style="color: #dc3545;">${queryData.usuarios_solo_query.toLocaleString()}</div>
            </div>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="${queryData.download_link}" class="download-button" target="_blank" download="${queryData.nombre_archivo}">
                📥 Descargar: ${queryData.nombre_archivo}
            </a>
        </div>
    `;
    
    return html;
}

function addBackButton() {
    const personDataSection = document.getElementById('person-data');
    if (personDataSection && !document.getElementById('back-button')) {
        const backButton = document.createElement('button');
        backButton.id = 'back-button';
        backButton.textContent = '← Volver al resumen general';
        backButton.onclick = showGlobalData;
        personDataSection.insertBefore(backButton, personDataSection.firstChild);
    }
}

function showGlobalData() {
    const personDataSection = document.getElementById('person-data');
    const globalDataSection = document.getElementById('global-data');
    
    if (personDataSection) {
        personDataSection.style.display = 'none';
        personDataSection.innerHTML = '';
    }
    
    if (globalDataSection) {
        globalDataSection.style.display = 'block';
    }
}

// ========================================================
// EVENT LISTENERS
// ========================================================

function validateFiles() {
    const file1Input = document.getElementById('file1-input');
    const file2Input = document.getElementById('file2-input');
    const processButton = document.getElementById('process-button');
    
    const file1 = file1Input.files[0];
    const file2 = file2Input.files[0];
    
    if (file1 && file2) {
        processButton.disabled = false;
    } else {
        processButton.disabled = true;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando aplicación...');
    
    const processButton = document.getElementById('process-button');
    if (processButton) {
        processButton.addEventListener('click', processFiles);
    }
    
    const cancelButton = document.getElementById('cancel-button');
    if (cancelButton) {
        cancelButton.addEventListener('click', cancelProcess);
    }
    
    const searchButton = document.getElementById('search-button');
    if (searchButton) {
        searchButton.addEventListener('click', searchData);
    }
    
    const professionalFilter = document.getElementById('professional-filter');
    const userFilter = document.getElementById('user-filter');
    
    if (professionalFilter) {
        professionalFilter.addEventListener('change', function() {
            if (userFilter) userFilter.value = '';
        });
    }
    
    if (userFilter) {
        userFilter.addEventListener('change', function() {
            if (professionalFilter) professionalFilter.value = '';
        });
    }
    
    const file1Input = document.getElementById('file1-input');
    const file2Input = document.getElementById('file2-input');
    
    if (file1Input) {
        file1Input.addEventListener('change', validateFiles);
    }
    if (file2Input) {
        file2Input.addEventListener('change', validateFiles);
    }
    
    validateFiles();
    
    console.log('✅ Aplicación inicializada correctamente');
});

window.addEventListener('error', function(e) {
    console.error('Error global:', e.error);
    showToast('❌ Error inesperado en la aplicación', 'error');
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Promesa rechazada:', e.reason);
    showToast('❌ Error en la aplicación', 'error');
    e.preventDefault();
});