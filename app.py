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

# Rutas para las carpetas
UPLOAD_FOLDER = 'Uploads'
QUERY_FILTERED_FOLDER = os.path.join(UPLOAD_FOLDER, 'query_filtered')
STATIC_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QUERY_FILTERED_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Configuración de columnas
columna_profesional = "Profesional"
columna_usuario_validacion = "Nombre Usuario Validación"
columna_servicio = "Servicio"
columna_nombre_servicio = "Nombre Servicio"

# Definir categorías de servicios
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

def process_excel(file1_path, file2_path):
    logger.debug(f"Procesando archivo1: {file1_path} y archivo2: {file2_path}")
    try:
        df1 = pd.read_excel(file1_path, engine='openpyxl')
        df1.columns = [c.strip() for c in df1.columns]
        
        required_cols1 = [columna_profesional, columna_servicio]
        missing_cols1 = [col for col in required_cols1 if col not in df1.columns]
        if missing_cols1:
            logger.error(f"Columnas faltantes en archivo1: {missing_cols1}")
            return {"error": f"Columnas faltantes en archivo1: {', '.join(missing_cols1)}. Disponibles: {', '.join(df1.columns.tolist())}"}
        
        df2 = pd.read_excel(file2_path, engine='openpyxl')
        df2.columns = [c.strip() for c in df2.columns]
        
        required_cols2 = [columna_usuario_validacion, columna_nombre_servicio]
        missing_cols2 = [col for col in required_cols2 if col not in df2.columns]
        if missing_cols2:
            logger.error(f"Columnas faltantes en archivo2: {missing_cols2}")
            return {"error": f"Columnas faltantes en archivo2: {', '.join(missing_cols2)}. Disponibles: {', '.join(df2.columns.tolist())}"}
        
        df1[columna_profesional] = df1[columna_profesional].astype(str).str.strip().str.lower()
        df1[columna_servicio] = df1[columna_servicio].astype(str).str.strip().str.lower()
        df2[columna_usuario_validacion] = df2[columna_usuario_validacion].astype(str).str.strip().str.lower()
        df2[columna_nombre_servicio] = df2[columna_nombre_servicio].astype(str).str.strip().str.lower()
        
        professionals = df1[columna_profesional].unique()
        professional_data = {}
        
        for professional in professionals:
            if pd.notna(professional) and professional != 'nan':
                df_prof = df1[df1[columna_profesional] == professional]
                safe_prof = sanitize_filename(professional)
                output_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{safe_prof}.xlsx")
                df_prof.to_excel(output_file, index=False, engine='openpyxl')
                logger.debug(f"Archivo profesional guardado: {output_file}")
                
                servicios_por_categoria = contar_servicios_por_categoria(df_prof, columna_servicio)
                servicios_detallados = contar_servicios_detallados(df_prof, columna_servicio)
                
                professional_data[professional] = {
                    "count": len(df_prof),
                    "data": df_prof.to_dict('records'),
                    "servicios_por_categoria": servicios_por_categoria,
                    "servicios_detallados": servicios_detallados
                }
        
        users = df2[columna_usuario_validacion].unique()
        user_data = {}
        
        for user in users:
            if pd.notna(user) and user != 'nan':
                df_user = df2[df2[columna_usuario_validacion] == user]
                safe_user = sanitize_filename(user)
                output_file = os.path.join(QUERY_FILTERED_FOLDER, f"{safe_user}.xlsx")
                df_user.to_excel(output_file, index=False, engine='openpyxl')
                logger.debug(f"Archivo usuario guardado: {output_file}")
                
                servicios_por_categoria = contar_servicios_por_categoria(df_user, columna_nombre_servicio)
                servicios_detallados = contar_servicios_detallados(df_user, columna_nombre_servicio)
                
                user_data[user] = {
                    "count": len(df_user),
                    "data": df_user.to_dict('records'),
                    "servicios_por_categoria": servicios_por_categoria,
                    "servicios_detallados": servicios_detallados
                }
        
        total_servicios_crystal = contar_servicios_por_categoria(df1, columna_servicio)
        total_servicios_query = contar_servicios_por_categoria(df2, columna_nombre_servicio)
        detallados_crystal = contar_servicios_detallados(df1, columna_servicio)
        detallados_query = contar_servicios_detallados(df2, columna_nombre_servicio)
        
        total_services_crystal = len(df1)
        num_professionals = len([p for p in professionals if pd.notna(p) and p != 'nan'])
        total_services_query = len(df2)
        num_users = len([u for u in users if pd.notna(u) and u != 'nan'])
        
        logger.debug(f"Total servicios crystal: {total_services_crystal}, Profesionales: {num_professionals}")
        logger.debug(f"Total servicios query: {total_services_query}, Usuarios: {num_users}")
        
        return {
            "success": True,
            "totals": {
                "total_services_crystal": total_services_crystal,
                "num_professionals": num_professionals,
                "total_services_query": total_services_query,
                "num_users": num_users,
                "servicios_por_categoria_crystal": total_servicios_crystal,
                "servicios_por_categoria_query": total_servicios_query,
                "servicios_detallados_crystal": detallados_crystal,
                "servicios_detallados_query": detallados_query
            },
            "professionals": [p for p in professionals if pd.notna(p) and p != 'nan'],
            "users": [u for u in users if pd.notna(u) and u != 'nan'],
            "professional_data": professional_data,
            "user_data": user_data,
            "all_columns": list(df1.columns),
            "all_columns_query": list(df2.columns),
            "categorias_servicios": list(CATEGORIAS_SERVICIOS.keys()) + ['otros']
        }
    except pd.errors.ParserError as e:
        logger.error(f"ParserError: {str(e)}")
        return {"error": "El archivo está corrupto o no es un archivo Excel válido."}
    except PermissionError as e:
        logger.error(f"PermissionError: {str(e)}")
        return {"error": "No se tienen permisos para leer/escribir el archivo."}
    except Exception as e:
        logger.error(f"Excepción general: {str(e)}", exc_info=True)
        return {"error": f"Error procesando los archivos: {str(e)}"}

@app.route('/')
def index():
    logger.debug("Sirviendo index.html")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.debug("Recibida solicitud POST en /upload")
    logger.debug(f"Archivos en request.files: {request.files}")
    if 'file1' not in request.files or 'file2' not in request.files:
        logger.error("Faltan archivos en la solicitud")
        return jsonify({"error": "Por favor, selecciona ambos archivos."}), 400
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    logger.debug(f"Archivo1: {file1.filename}, Archivo2: {file2.filename}")
    if file1.filename == '' or file2.filename == '':
        logger.error("Nombre de archivo vacío")
        return jsonify({"error": "Por favor, selecciona ambos archivos."}), 400
    
    if file1.filename.endswith(('.xlsx', '.xls')) and file2.filename.endswith(('.xlsx', '.xls')):
        file1_path = os.path.join(app.config['UPLOAD_FOLDER'], file1.filename)
        file2_path = os.path.join(app.config['UPLOAD_FOLDER'], file2.filename)
        logger.debug(f"Guardando archivo1 en: {file1_path} y archivo2 en: {file2_path}")
        file1.save(file1_path)
        file2.save(file2_path)
        result = process_excel(file1_path, file2_path)
        logger.debug(f"Resultado de procesamiento: {result}")
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result), 200
    logger.error(f"Formato no válido para los archivos: {file1.filename}, {file2.filename}")
    return jsonify({"error": "Formato de archivo no válido. Sube archivos .xlsx o .xls."}), 400

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "short_name": "Servicios Medicos",
        "name": "Control de Servicios Médicos",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "type": "image/png",
                "sizes": "192x192"
            },
            {
                "src": "/static/icon-512.png",
                "type": "image/png",
                "sizes": "512x512"
            }
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
            return cache.addAll([
                '/',
                '/static/style.css',
                '/static/js/app.js',
                '/static/icon-192.png',
                '/static/icon-512.png'
            ]).catch(error => {
                console.error('Cache addAll failed:', error);
            });
        })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        }).catch(error => {
            console.error('Fetch failed:', error);
        })
    );
});
    """
    return sw_code, 200, {'Content-Type': 'application/javascript'}

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
