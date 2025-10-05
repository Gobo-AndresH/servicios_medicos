<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#007bff">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="icon" href="/static/favicon.ico">
    <title>Control de Servicios Médicos</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">📋 Control de Servicios Médicos</div>
            <div class="subtitle">Sistema de registro para filtrado por profesional</div>
        </header>
        <main>
            <div class="upload-section">
                <label for="file1-input">Archivo Crystal (Profesional):</label>
                <input type="file" id="file1-input" name="file1" accept=".xlsx,.xls" required>
                <label for="file2-input">Archivo Query (Nombre Usuario Validación):</label>
                <input type="file" id="file2-input" name="file2" accept=".xlsx,.xls" required>
                <button id="process-button">Procesar Archivos</button>
            </div>
            <div id="loading" style="display: none; text-align: center; padding: 10px;">
                <i class="fas fa-spinner fa-spin"></i> Procesando archivos...
            </div>
            <div id="result" style="display: none;">
                <div class="filter-section">
                    <label for="professional-filter">Filtrar por Profesional (Crystal):</label>
                    <select id="professional-filter">
                        <option value="">Seleccionar Profesional</option>
                    </select>
                    <label for="user-filter">Filtrar por Profesional (Query):</label>
                    <select id="user-filter">
                        <option value="">Seleccionar Profesional (Query)</option>
                    </select>
                    <button id="search-button">Buscar</button>
                </div>
                <div class="totals-group">
                    <div class="card">
                        <h3>Total Servicios Crystal</h3>
                        <p class="count" id="total-services-crystal">0</p>
                    </div>
                    <div class="card">
                        <h3>Total Servicios Query</h3>
                        <p class="count" id="total-services-query">0</p>
                    </div>
                </div>
                <div class="counts-group">
                    <div class="card">
                        <h3>Cantidad de Profesionales</h3>
                        <p class="count" id="num-professionals">0</p>
                    </div>
                    <div class="card">
                        <h3>Cantidad de Usuarios Validación</h3>
                        <p class="count" id="num-users">0</p>
                    </div>
                </div>
                <div id="global-data"></div>
                <div id="person-data" class="tab-content" style="display: none;"></div>
            </div>
        </main>
        <footer>
            <p>© 2025 Control de Servicios Médicos</p>
        </footer>
    </div>
    <script src="/static/js/app.js"></script>
</body>
</html>
