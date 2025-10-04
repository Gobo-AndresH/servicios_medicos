document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');
    
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        formData.append('crystal_file', document.getElementById('crystalFile').files[0]);
        formData.append('query_file', document.getElementById('queryFile').files[0]);
        
        resultDiv.style.display = 'block';
        resultDiv.className = 'result';
        resultDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Procesando archivos...</div>';
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showResults(data);
            } else {
                showError(data);
            }
            
        } catch (error) {
            showError({ error: error.message });
        }
    });
    
    function showResults(data) {
        resultDiv.className = 'result success';
        
        let html = `
            <div class="results-container">
                <h3><i class="fas fa-check-circle"></i> Archivos procesados correctamente</h3>
                
                <!-- Estadísticas -->
                <div class="stats-section">
                    <h4><i class="fas fa-chart-bar"></i> Estadísticas</h4>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <span class="stat-value">${data.stats.total || 0}</span>
                            <span class="stat-label">Total Servicios</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value">${data.stats.urgencias || 0}</span>
                            <span class="stat-label">Urgencias</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value">${data.stats.general || 0}</span>
                            <span class="stat-label">Medicina General</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-value">${data.stats.hoy || 0}</span>
                            <span class="stat-label">Servicios Hoy</span>
                        </div>
                    </div>
                </div>
                
                <!-- Tabs para navegar entre la información -->
                <div class="tabs">
                    <button class="tab-button active" onclick="showTab('info-tab')">
                        <i class="fas fa-info-circle"></i> Información
                    </button>
                    <button class="tab-button" onclick="showTab('crystal-tab')">
                        <i class="fas fa-file-medical"></i> Datos Crystal
                    </button>
        `;
        
        if (data.query_data) {
            html += `
                <button class="tab-button" onclick="showTab('query-tab')">
                    <i class="fas fa-file-alt"></i> Datos Query
                </button>
            `;
        }
        
        html += `
                </div>
                
                <!-- Contenido de los tabs -->
                <div class="tab-content">
                    <!-- Tab de Información -->
                    <div id="info-tab" class="tab-pane active">
                        <h4><i class="fas fa-database"></i> Información de Columnas</h4>
                        
                        <div class="info-section">
                            <h5>Archivo Crystal:</h5>
                            <p><strong>Columnas encontradas:</strong> ${data.crystal_columns.join(', ')}</p>
                            ${Object.keys(data.crystal_mapping).length > 0 ? `
                                <p><strong>Columnas mapeadas:</strong></p>
                                <ul>
                                    ${Object.entries(data.crystal_mapping).map(([target, original]) => 
                                        `<li><strong>${target}</strong> ← ${original}</li>`
                                    ).join('')}
                                </ul>
                            ` : '<p>No se encontraron columnas para mapear</p>'}
                        </div>
        `;
        
        if (data.query_data) {
            html += `
                        <div class="info-section">
                            <h5>Archivo Query:</h5>
                            <p><strong>Columnas encontradas:</strong> ${data.query_columns.join(', ')}</p>
                            ${Object.keys(data.query_mapping).length > 0 ? `
                                <p><strong>Columnas mapeadas:</strong></p>
                                <ul>
                                    ${Object.entries(data.query_mapping).map(([target, original]) => 
                                        `<li><strong>${target}</strong> ← ${original}</li>`
                                    ).join('')}
                                </ul>
                            ` : '<p>No se encontraron columnas para mapear</p>'}
                        </div>
            `;
        }
        
        if (data.warnings && data.warnings.length > 0) {
            html += `
                        <div class="warning-section">
                            <h5><i class="fas fa-exclamation-triangle"></i> Advertencias:</h5>
                            <ul>
                                ${data.warnings.map(warning => `<li>${warning}</li>`).join('')}
                            </ul>
                        </div>
            `;
        }
        
        html += `
                        <div class="download-section">
                            <a class="download-link" href="${data.download_url}">
                                <i class="fas fa-download"></i> Descargar Reporte Completo
                            </a>
                        </div>
                    </div>
                    
                    <!-- Tab de Datos Crystal -->
                    <div id="crystal-tab" class="tab-pane">
                        <h4><i class="fas fa-file-medical"></i> Datos del Archivo Crystal (primeras 20 filas)</h4>
                        <div class="table-container">
                            ${data.crystal_html || '<p>No hay datos para mostrar</p>'}
                        </div>
                    </div>
        `;
        
        if (data.query_data) {
            html += `
                    <!-- Tab de Datos Query -->
                    <div id="query-tab" class="tab-pane">
                        <h4><i class="fas fa-file-alt"></i> Datos del Archivo Query (primeras 20 filas)</h4>
                        <div class="table-container">
                            ${data.query_html || '<p>No hay datos para mostrar</p>'}
                        </div>
                    </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
        
        resultDiv.innerHTML = html;
        updateDashboard(data.stats);
    }
    
    function showError(data) {
        resultDiv.className = 'result error';
        let html = `<h3><i class="fas fa-exclamation-circle"></i> Error</h3>`;
        
        if (data.error) {
            html += `<p>${data.error}</p>`;
        }
        
        if (data.crystal_columns) {
            html += `
                <div class="info-section">
                    <h4>Columnas encontradas en Crystal:</h4>
                    <p>${data.crystal_columns.join(', ')}</p>
                </div>
            `;
        }
        
        if (data.query_columns) {
            html += `
                <div class="info-section">
                    <h4>Columnas encontradas en Query:</h4>
                    <p>${data.query_columns.join(', ')}</p>
                </div>
            `;
        }
        
        if (data.warnings && data.warnings.length > 0) {
            html += `
                <div class="warning-section">
                    <h4>Advertencias:</h4>
                    <ul>
                        ${data.warnings.map(warning => `<li>${warning}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        resultDiv.innerHTML = html;
    }
    
    function updateDashboard(stats) {
        document.querySelector('.value-total').textContent = stats.total || 0;
        document.querySelector('.value-urgencias').textContent = stats.urgencias || 0;
        document.querySelector('.value-general').textContent = stats.general || 0;
        document.querySelector('.value-today').textContent = stats.hoy || 0;
    }
});

// Función global para cambiar tabs
function showTab(tabId) {
    // Ocultar todos los tabs
    document.querySelectorAll('.tab-pane').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Mostrar el tab seleccionado
    document.getElementById(tabId).classList.add('active');
    
    // Actualizar botones activos
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Encontrar el botón que corresponde al tab y activarlo
    const activeButton = Array.from(document.querySelectorAll('.tab-button')).find(button => 
        button.onclick.toString().includes(tabId)
    );
    
    if (activeButton) {
        activeButton.classList.add('active');
    }
}