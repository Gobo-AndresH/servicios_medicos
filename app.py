import os
import re
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# === 🔧 Configuración de carpetas seguras para Render ===
BASE_DIR = '/tmp'  # Render solo permite escribir aquí
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
QUERY_FILTERED_FOLDER = os.path.join(BASE_DIR, 'query_filtered')
STATIC_FOLDER = 'static'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QUERY_FILTERED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# === Configuración de columnas ===
columna_profesional = "Profesional"
columna_usuario_validacion = "Nombre Usuario Validación"
columna_servicio = "Servicio"
columna_nombre_servicio = "Nombre Servicio"

# === Definir categorías de servicios ===
CATEGORIAS_SERVICIOS = {
    'ecografia': ['ecografia', 'perfil biofisico'],
    'mamografia': ['mamografia'],
    'cervicometria': ['cervicometria'],
    'rx': ['rx']
}

def sanitize_filename(name):
    name = str(name)
    name = name.title()
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip()[:50]

def categorizar_servicio(servicio):
    servicio_str = str(servicio).lower().strip()
    for categoria, palabras_clave in CATEGORIAS_SERVICIOS.items():
        for palabra in palabras_clave:
            if palabra in servicio_str:
                return categoria
    return 'otros'

def contar_servicios_por_categoria(df, columna_servicio):
    conteo = {categoria: 0 for categoria in CATEGORIAS_SERVICIOS.keys()}
    conteo['otros'] = 0
    for servicio in df[columna_servicio]:
        categoria = categorizar_servicio(servicio)
        conteo[categoria] += 1
    return conteo

def contar_servicios_detallados(df, columna_servicio):
    return df[columna_servicio].value_counts().to_dict()

# === Procesar archivos Excel ===
def process_excel(file1_path, file2_path):
    logger.debug(f"Procesando archivo1: {file1_path} y archivo2: {file2_path}")
    try:
        df1 = pd.read_excel(file1_path, engine='openpyxl')
        df1.columns = [c.strip() for c in df1.columns]

        required_cols1 = [columna_profesional, columna_servicio]
        missing_cols1 = [col for col in required_cols1 if col not in df1.columns]
        if missing_cols1:
            return {"error": f"Columnas faltantes en archivo1: {', '.join(missing_cols1)}"}

        df2 = pd.read_excel(file2_path, engine='openpyxl')
        df2.columns = [c.strip() for c in df2.columns]

        required_cols2 = [columna_usuario_validacion, columna_nombre_servicio]
        missing_cols2 = [col for col in required_cols2 if col not in df2.columns]
        if missing_cols2:
            return {"error": f"Columnas faltantes en archivo2: {', '.join(missing_cols2)}"}

        df1[columna_profesional] = df1[columna_profesional].astype(str).str.strip().str.lower()
        df1[columna_servicio] = df1[columna_servicio].astype(str).str.strip().str.lower()
        df2[columna_usuario_validacion] = df2[columna_usuario_validacion].astype(str).str.strip().str.lower()
        df2[columna_nombre_servicio] = df2[columna_nombre_servicio].astype(str).str.strip().str.lower()

        professionals = df1[columna_profesional].unique()
        users = df2[columna_usuario_validacion].unique()

        professional_data = {}
        user_data = {}

        # Guardar archivos individuales de profesionales
        for professional in professionals:
            if pd.notna(professional) and professional != 'nan':
                df_prof = df1[df1[columna_profesional] == professional]
                safe_prof = sanitize_filename(professional)
                output_file = os.path.join(UPLOAD_FOLDER, f"{safe_prof}.xlsx")
                df_prof.to_excel(output_file, index=False, engine='openpyxl')
                professional_data[professional] = {
                    "count": len(df_prof),
                    "servicios_por_categoria": contar_servicios_por_categoria(df_prof, columna_servicio),
                    "servicios_detallados": contar_servicios_detallados(df_prof, columna_servicio),
                    "download_url": f"/download/{safe_prof}.xlsx"
                }

        # Guardar archivos individuales de usuarios
        for user in users:
            if pd.notna(user) and user != 'nan':
                df_user = df2[df2[columna_usuario_validacion] == user]
                safe_user = sanitize_filename(user)
                output_file = os.path.join(QUERY_FILTERED_FOLDER, f"{safe_user}.xlsx")
                df_user.to_excel(output_file, index=False, engine='openpyxl')
                user_data[user] = {
                    "count": len(df_user),
                    "servicios_por_categoria": contar_servicios_por_categoria(df_user, columna_nombre_servicio),
                    "servicios_detallados": contar_servicios_detallados(df_user, columna_nombre_servicio),
                    "download_url": f"/download/query/{safe_user}.xlsx"
                }

        return {
            "success": True,
            "totals": {
                "total_services_crystal": len(df1),
                "num_professionals": len(professionals),
                "total_services_query": len(df2),
                "num_users": len(users),
                "servicios_por_categoria_crystal": contar_servicios_por_categoria(df1, columna_servicio),
                "servicios_por_categoria_query": contar_servicios_por_categoria(df2, columna_nombre_servicio),
                "servicios_detallados_crystal": contar_servicios_detallados(df1, columna_servicio),
                "servicios_detallados_query": contar_servicios_detallados(df2, columna_nombre_servicio)
            },
            "professionals": list(professionals),
            "users": list(users),
            "professional_data": professional_data,
            "user_data": user_data
        }

    except Exception as e:
        logger.error(f"Error procesando archivos: {e}", exc_info=True)
        return {"error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({"error": "Por favor, selecciona ambos archivos."}), 400
    file1 = request.files['file1']
    file2 = request.files['file2']
    if not file1.filename or not file2.filename:
        return jsonify({"error": "Por favor, selecciona ambos archivos."}), 400

    file1_path = os.path.join(UPLOAD_FOLDER, file1.filename)
    file2_path = os.path.join(UPLOAD_FOLDER, file2.filename)
    file1.save(file1_path)
    file2.save(file2_path)

    result = process_excel(file1_path, file2_path)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200

# === 🧾 Rutas de descarga ===
@app.route('/download/<path:filename>')
def download_file(filename):
    if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    return jsonify({"error": "Archivo no encontrado"}), 404

@app.route('/download/query/<path:filename>')
def download_query_file(filename):
    if os.path.exists(os.path.join(QUERY_FILTERED_FOLDER, filename)):
        return send_from_directory(QUERY_FILTERED_FOLDER, filename, as_attachment=True)
    return jsonify({"error": "Archivo no encontrado"}), 404

# === PWA Files ===
@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "short_name": "Servicios Medicos",
        "name": "Control de Servicios Médicos",
        "icons": [
            {"src": "/static/icon-192.png", "type": "image/png", "sizes": "192x192"},
            {"src": "/static/icon-512.png", "type": "image/png", "sizes": "512x512"}
        ],
        "start_url": "/",
        "background_color": "#ffffff",
        "display": "standalone",
        "scope": "/",
        "theme_color": "#007bff"
    }
    return jsonify(manifest_data)

@app.route('/service-worker.js')
def service_worker():
    sw_code = """
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open('v1').then(cache => {
            return cache.addAll(['/','/static/style.css','/static/js/app.js','/static/icon-192.png','/static/icon-512.png']);
        })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)));
});
    """
    return sw_code, 200, {'Content-Type': 'application/javascript'}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
