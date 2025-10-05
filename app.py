import os
import re
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)

# ✅ Configuración de CORS: solo permite tu dominio Render
CORS(app, resources={r"/*": {"origins": ["https://servicios-medicos-n3bl.onrender.com", "*"]}})

# ✅ Configurar logging para depuración en Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Carpeta temporal compatible con Render (solo /tmp es escribible)
UPLOAD_FOLDER = '/tmp/uploads'
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
    """Sanitiza los nombres de archivo eliminando caracteres peligrosos."""
    name = str(name).title()
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip()[:50]

def categorizar_servicio(servicio):
    """Clasifica el tipo de servicio según palabra clave."""
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
    """Procesa los archivos Excel, valida columnas y genera estadísticas."""
    logger.info(f"Procesando archivo1: {file1_path}, archivo2: {file2_path}")
    try:
        df1 = pd.read_excel(file1_path, engine='openpyxl')
        df2 = pd.read_excel(file2_path, engine='openpyxl')

        df1.columns = [c.strip() for c in df1.columns]
        df2.columns = [c.strip() for c in df2.columns]

        required_cols1 = [columna_profesional, columna_servicio]
        required_cols2 = [columna_usuario_validacion, columna_nombre_servicio]

        missing_cols1 = [col for col in required_cols1 if col not in df1.columns]
        missing_cols2 = [col for col in required_cols2 if col not in df2.columns]

        if missing_cols1:
            return {"error": f"Faltan columnas en archivo 1: {', '.join(missing_cols1)}"}
        if missing_cols2:
            return {"error": f"Faltan columnas en archivo 2: {', '.join(missing_cols2)}"}

        # Normalizar
        for df, cols in [(df1, [columna_profesional, columna_servicio]), (df2, [columna_usuario_validacion, columna_nombre_servicio])]:
            for col in cols:
                df[col] = df[col].astype(str).str.strip().str.lower()

        # Generar datos por profesional (Crystal)
        professionals = df1[columna_profesional].dropna().unique()
        professional_data = {}

        for professional in professionals:
            safe_prof = sanitize_filename(professional)
            df_prof = df1[df1[columna_profesional] == professional]
            output_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{safe_prof}.xlsx")
            df_prof.to_excel(output_file, index=False, engine='openpyxl')

            professional_data[professional] = {
                "count": len(df_prof),
                "servicios_por_categoria": contar_servicios_por_categoria(df_prof, columna_servicio),
                "servicios_detallados": contar_servicios_detallados(df_prof, columna_servicio),
                "download_link": f"/download/{safe_prof}.xlsx"
            }

        # Generar datos por usuario (Query)
        users = df2[columna_usuario_validacion].dropna().unique()
        user_data = {}

        for user in users:
            safe_user = sanitize_filename(user)
            df_user = df2[df2[columna_usuario_validacion] == user]
            output_file = os.path.join(QUERY_FILTERED_FOLDER, f"{safe_user}.xlsx")
            df_user.to_excel(output_file, index=False, engine='openpyxl')

            user_data[user] = {
                "count": len(df_user),
                "servicios_por_categoria": contar_servicios_por_categoria(df_user, columna_nombre_servicio),
                "servicios_detallados": contar_servicios_detallados(df_user, columna_nombre_servicio),
                "download_link": f"/download/{safe_user}.xlsx"
            }

        # Totales globales
        return {
            "success": True,
            "totals": {
                "total_services_crystal": len(df1),
                "total_services_query": len(df2),
                "num_professionals": len(professionals),
                "num_users": len(users),
                "servicios_por_categoria_crystal": contar_servicios_por_categoria(df1, columna_servicio),
                "servicios_por_categoria_query": contar_servicios_por_categoria(df2, columna_nombre_servicio),
                "servicios_detallados_crystal": contar_servicios_detallados(df1, columna_servicio),
                "servicios_detallados_query": contar_servicios_detallados(df2, columna_nombre_servicio)
            },
            "professionals": sorted(professionals.tolist()),
            "users": sorted(users.tolist()),
            "professional_data": professional_data,
            "user_data": user_data,
        }

    except Exception as e:
        logger.error("Error procesando los archivos", exc_info=True)
        return {"error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.info("Solicitud POST en /upload recibida.")
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({"error": "Debes seleccionar ambos archivos."}), 400

    file1 = request.files['file1']
    file2 = request.files['file2']

    if not (file1.filename and file2.filename):
        return jsonify({"error": "Los nombres de los archivos no pueden estar vacíos."}), 400

    if not (file1.filename.endswith(('.xlsx', '.xls')) and file2.filename.endswith(('.xlsx', '.xls'))):
        return jsonify({"error": "Formato no válido. Solo se permiten archivos Excel (.xlsx o .xls)."}), 400

    # Guardar temporalmente
    file1_path = os.path.join(app.config['UPLOAD_FOLDER'], sanitize_filename(file1.filename))
    file2_path = os.path.join(app.config['UPLOAD_FOLDER'], sanitize_filename(file2.filename))
    file1.save(file1_path)
    file2.save(file2_path)

    result = process_excel(file1_path, file2_path)
    status_code = 200 if "success" in result else 400
    return jsonify(result), status_code

@app.route('/download/<path:filename>')
def download_file(filename):
    """Permite descargar los archivos generados."""
    try:
        # Busca tanto en la carpeta principal como en query_filtered
        for folder in [UPLOAD_FOLDER, QUERY_FILTERED_FOLDER]:
            file_path = os.path.join(folder, filename)
            if os.path.exists(file_path):
                return send_from_directory(folder, filename, as_attachment=True)
        return jsonify({"error": "Archivo no encontrado."}), 404
    except Exception as e:
        logger.error("Error en descarga de archivo", exc_info=True)
        return jsonify({"error": f"No se pudo descargar el archivo: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
