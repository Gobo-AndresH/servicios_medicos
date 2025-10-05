import os
import re
import logging
import gc
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename

# -------------------------
# Configuración inicial
# -------------------------
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
QUERY_FOLDER = os.path.join(UPLOAD_FOLDER, 'query_filtered')
STATIC_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QUERY_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Columnas
COL_PROF = "Profesional"
COL_USER_VAL = "Nombre Usuario Validación"
COL_SERV = "Servicio"
COL_SERV_NAME = "Nombre Servicio"

# Categorías
CATEGORIES = {
    'ecografia': ['ecografia', 'perfil biofisico'],
    'mamografia': ['mamografia'],
    'cervicometria': ['cervicometria'],
    'rx': ['rx']
}

# -------------------------
# Funciones auxiliares
# -------------------------
def sanitize_filename(name):
    name = str(name).title()
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip()[:50]

def categorize_service(service):
    service = str(service).lower().strip()
    for cat, keywords in CATEGORIES.items():
        if any(k in service for k in keywords):
            return cat
    return 'otros'

def count_categories(df, col):
    counts = {cat: 0 for cat in CATEGORIES.keys()}
    counts['otros'] = 0
    for val in df[col]:
        counts[categorize_service(val)] += 1
    return counts

# -------------------------
# Procesamiento optimizado
# -------------------------
def process_excel_files(file1_path, file2_path):
    professional_data = {}
    user_data = {}
    totals_crystal = {**{k:0 for k in CATEGORIES.keys()}, 'otros':0}
    totals_query = {**{k:0 for k in CATEGORIES.keys()}, 'otros':0}

    # Procesar archivo 1 (profesionales)
    try:
        for df_chunk in pd.read_excel(file1_path, engine='openpyxl', chunksize=1000):
            df_chunk[COL_PROF] = df_chunk[COL_PROF].astype(str).str.strip()
            df_chunk[COL_SERV] = df_chunk[COL_SERV].astype(str).str.strip()
            for prof, df_p in df_chunk.groupby(COL_PROF):
                file_path = os.path.join(UPLOAD_FOLDER, f"{sanitize_filename(prof)}.xlsx")
                if os.path.exists(file_path):
                    df_p.to_excel(file_path, index=False, engine='openpyxl', mode='a', header=False)
                else:
                    df_p.to_excel(file_path, index=False, engine='openpyxl')
                counts = count_categories(df_p, COL_SERV)
                for k, v in counts.items():
                    totals_crystal[k] += v
                professional_data[prof] = professional_data.get(prof, 0) + len(df_p)
            del df_chunk
            gc.collect()
    except Exception as e:
        logger.error(f"Error procesando archivo profesional: {e}")
        return {"error": str(e)}

    # Procesar archivo 2 (usuarios)
    try:
        for df_chunk in pd.read_excel(file2_path, engine='openpyxl', chunksize=1000):
            df_chunk[COL_USER_VAL] = df_chunk[COL_USER_VAL].astype(str).str.strip()
            df_chunk[COL_SERV_NAME] = df_chunk[COL_SERV_NAME].astype(str).str.strip()
            for user, df_u in df_chunk.groupby(COL_USER_VAL):
                file_path = os.path.join(QUERY_FOLDER, f"{sanitize_filename(user)}.xlsx")
                if os.path.exists(file_path):
                    df_u.to_excel(file_path, index=False, engine='openpyxl', mode='a', header=False)
                else:
                    df_u.to_excel(file_path, index=False, engine='openpyxl')
                counts = count_categories(df_u, COL_SERV_NAME)
                for k, v in counts.items():
                    totals_query[k] += v
                user_data[user] = user_data.get(user, 0) + len(df_u)
            del df_chunk
            gc.collect()
    except Exception as e:
        logger.error(f"Error procesando archivo usuario: {e}")
        return {"error": str(e)}

    return {
        "success": True,
        "professional_counts": professional_data,
        "user_counts": user_data,
        "totals_crystal": totals_crystal,
        "totals_query": totals_query
    }

# -------------------------
# Rutas Flask
# -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({"error": "Faltan archivos"}), 400

    f1 = request.files['file1']
    f2 = request.files['file2']

    if f1.filename == '' or f2.filename == '':
        return jsonify({"error": "Archivos vacíos"}), 400

    path1 = os.path.join(UPLOAD_FOLDER, secure_filename(f1.filename))
    path2 = os.path.join(UPLOAD_FOLDER, secure_filename(f2.filename))
    f1.save(path1)
    f2.save(path2)

    result = process_excel_files(path1, path2)
    return jsonify(result)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

# -------------------------
# Main
# -------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
