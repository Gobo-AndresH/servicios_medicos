<<<<<<< HEAD
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
=======
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Crear directorios si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        if 'crystal_file' not in request.files or 'query_file' not in request.files:
            return jsonify({'error': 'Faltan archivos en la solicitud'}), 400
        
        crystal_file = request.files['crystal_file']
        query_file = request.files['query_file']
        
        if crystal_file.filename == '' or query_file.filename == '':
            return jsonify({'error': 'No se seleccionaron archivos'}), 400
        
        # Guardar archivos
        crystal_filename = secure_filename(crystal_file.filename)
        query_filename = secure_filename(query_file.filename)
        
        crystal_path = os.path.join(app.config['UPLOAD_FOLDER'], crystal_filename)
        query_path = os.path.join(app.config['UPLOAD_FOLDER'], query_filename)
        
        crystal_file.save(crystal_path)
        query_file.save(query_path)
        
        # Procesar archivos
        result_data = process_files(crystal_path, query_path)
        
        if 'error' in result_data:
            return jsonify(result_data), 400
        
        # Guardar datos para mostrar en pantalla
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], f'reporte_servicios_{timestamp}.xlsx')
        result_data['crystal_data'].to_excel(result_path, index=False)
        
        # Preparar datos para mostrar en frontend
        result_data['download_url'] = f'/download/reporte_servicios_{timestamp}.xlsx'
        
        # Convertir DataFrames a HTML para mostrar en pantalla
        result_data['crystal_html'] = result_data['crystal_data'].head(20).to_html(classes='table table-striped', index=False)
        if result_data['query_data'] is not None:
            result_data['query_html'] = result_data['query_data'].head(20).to_html(classes='table table-striped', index=False)
        
        # Convertir a JSON para enviar al frontend
        result_data['crystal_json'] = result_data['crystal_data'].head(50).to_dict('records')
        if result_data['query_data'] is not None:
            result_data['query_json'] = result_data['query_data'].head(50).to_dict('records')
        
        return jsonify(result_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def find_column(df, possible_names):
    """Encuentra una columna en el DataFrame basado en nombres posibles"""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def process_files(crystal_path, query_path):
    try:
        result_data = {
            'crystal_columns': [],
            'query_columns': [],
            'crystal_mapping': {},
            'query_mapping': {},
            'warnings': [],
            'stats': {},
            'crystal_data': None,
            'query_data': None
        }
        
        # Leer archivo crystal
        try:
            if crystal_path.endswith('.csv'):
                # Probar diferentes encodings
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
                for encoding in encodings:
                    try:
                        crystal_df = pd.read_csv(crystal_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise Exception("No se pudo leer el archivo CSV con los encodings probados")
            else:
                crystal_df = pd.read_excel(crystal_path)
        except Exception as e:
            return {'error': f"Error leyendo archivo crystal: {str(e)}"}
        
        result_data['crystal_columns'] = list(crystal_df.columns)
        print(f"Columnas en crystal: {result_data['crystal_columns']}")
        
        # Mapear columnas para crystal
        crystal_mapping = {
            'fecha': ['fecha', 'Fecha', 'FECHA', 'date', 'Date', 'DATE', 'fecha_servicio', 'FECHA_SERVICIO'],
            'servicio': ['servicio', 'Servicio', 'SERVICIO', 'service', 'Service', 'SERVICE', 'tipo_servicio', 'TIPO_SERVICIO'],
            'nombreIPS': ['nombreIPS', 'NombreIPS', 'NOMBREIPS', 'ips', 'IPS', 'nombre', 'Nombre', 'NOMBRE', 'centro', 'Centro', 'CENTRO'],
            'profesional': ['profesional', 'Profesional', 'PROFESIONAL', 'doctor', 'Doctor', 'DOCTOR', 'medico', 'Medico', 'MEDICO', 'nombre_medico', 'NOMBRE_MEDICO']
        }
        
        # Encontrar las columnas reales
        crystal_columns_found = {}
        for target_col, possible_names in crystal_mapping.items():
            found_col = find_column(crystal_df, possible_names)
            if found_col:
                crystal_columns_found[target_col] = found_col
            else:
                result_data['warnings'].append(f"Columna '{target_col}' no encontrada en archivo crystal")
        
        result_data['crystal_mapping'] = crystal_columns_found
        
        # Crear nuevo DataFrame con las columnas encontradas
        crystal_df_clean = crystal_df.copy()
        for target_col, original_col in crystal_columns_found.items():
            if target_col != original_col:
                crystal_df_clean[target_col] = crystal_df[original_col]
        
        # Seleccionar solo las columnas que necesitamos
        available_columns = [col for col in crystal_mapping.keys() if col in crystal_df_clean.columns]
        crystal_df_clean = crystal_df_clean[available_columns].copy()
        
        # Limpiar fecha si existe
        if 'fecha' in crystal_df_clean.columns:
            try:
                crystal_df_clean['fecha'] = pd.to_datetime(crystal_df_clean['fecha']).dt.date
            except:
                result_data['warnings'].append("No se pudo convertir la columna 'fecha' a formato fecha")
        
        result_data['crystal_data'] = crystal_df_clean
        
        # Leer archivo query
        query_df = None
        try:
            if query_path.endswith('.csv'):
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
                for encoding in encodings:
                    try:
                        query_df = pd.read_csv(query_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    result_data['warnings'].append("No se pudo leer el archivo CSV query")
            else:
                query_df = pd.read_excel(query_path)
        except Exception as e:
            result_data['warnings'].append(f"Error leyendo archivo query: {str(e)}")
        
        if query_df is not None:
            result_data['query_columns'] = list(query_df.columns)
            print(f"Columnas en query: {result_data['query_columns']}")
            
            # Mapear columnas para query
            query_mapping = {
                'fecha_recepcion': ['fecha recepcion', 'Fecha Recepcion', 'FECHA RECEPCION', 'fecha', 'Fecha', 'FECHA', 'fecha_recepcion', 'FECHA_RECEPCION'],
                'nombre_servicio': ['nombre servicio', 'Nombre Servicio', 'NOMBRE SERVICIO', 'servicio', 'Servicio', 'SERVICIO', 'nombre_servicio', 'NOMBRE_SERVICIO'],
                'nombre_sede': ['nombre sede', 'Nombre Sede', 'NOMBRE SEDE', 'sede', 'Sede', 'SEDE', 'nombre_sede', 'NOMBRE_SEDE'],
                'origen': ['origen', 'Origen', 'ORIGEN', 'source', 'Source', 'SOURCE']
            }
            
            # Encontrar las columnas reales para query
            query_columns_found = {}
            for target_col, possible_names in query_mapping.items():
                found_col = find_column(query_df, possible_names)
                if found_col:
                    query_columns_found[target_col] = found_col
            
            result_data['query_mapping'] = query_columns_found
            
            # Crear nuevo DataFrame para query
            query_df_clean = query_df.copy()
            for target_col, original_col in query_columns_found.items():
                if target_col != original_col:
                    query_df_clean[target_col] = query_df[original_col]
            
            # Seleccionar columnas disponibles
            query_available_columns = [col for col in query_mapping.keys() if col in query_df_clean.columns]
            query_df_clean = query_df_clean[query_available_columns].copy()
            
            result_data['query_data'] = query_df_clean
        
        # Calcular estadísticas basadas en crystal file
        stats = {
            'total': len(crystal_df_clean),
            'urgencias': 0,
            'general': 0,
            'hoy': 0
        }
        
        # Contar urgencias si tenemos columna de servicio
        if 'servicio' in crystal_df_clean.columns:
            for servicio in crystal_df_clean['servicio'].astype(str):
                if any(word in servicio.lower() for word in ['urgencia', 'emergencia', 'emergency', 'urgencies']):
                    stats['urgencias'] += 1
        
        # Contar medicina general
        if 'servicio' in crystal_df_clean.columns:
            for servicio in crystal_df_clean['servicio'].astype(str):
                if any(word in servicio.lower() for word in ['general', 'consulta', 'consultation', 'medicina', 'medicina general']):
                    stats['general'] += 1
        
        # Contar servicios de hoy
        if 'fecha' in crystal_df_clean.columns:
            try:
                hoy = pd.Timestamp.today().date()
                for fecha in crystal_df_clean['fecha']:
                    if pd.Timestamp(fecha).date() == hoy:
                        stats['hoy'] += 1
            except:
                result_data['warnings'].append("No se pudo calcular servicios de hoy por error en fechas")
        
        result_data['stats'] = stats
        
        return result_data
        
    except Exception as e:
        return {'error': f"Error procesando archivos: {str(e)}"}

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(
        os.path.join(app.config['UPLOAD_FOLDER'], filename),
        as_attachment=True
    )

@app.route('/static/css/<path:filename>')
def serve_css(filename):
    return send_file(f'static/css/{filename}')

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    return send_file(f'static/js/{filename}')

@app.route('/static/manifest.json')
def serve_manifest():
    return send_file('static/manifest.json')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
>>>>>>> e83d37d9f89f2f2ed280f33a659167a77ab2bc7b
