import os
import re
import logging
import gc
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuración
UPLOAD_FOLDER = 'uploads'
QUERY_FOLDER = os.path.join(UPLOAD_FOLDER, 'query_filtered')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QUERY_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Columnas
col_prof = "Profesional"
col_user_val = "Nombre Usuario Validación"
col_serv = "Servicio"
col_serv_name = "Nombre Servicio"

# Categorías de servicios
CATS = {'ecografia': ['ecografia', 'perfil biofisico'],
        'mamografia': ['mamografia'],
        'cervicometria': ['cervicometria'],
        'rx': ['rx']}

def sanitize(name):
    name = str(name).title()
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip()[:50]

def categorize_service(serv):
    serv = str(serv).lower().strip()
    for cat, keys in CATS.items():
        if any(k in serv for k in keys):
            return cat
    return 'otros'

def count_categories(df, col):
    counts = {cat:0 for cat in CATS.keys()}
    counts['otros'] = 0
    for val in df[col]:
        counts[categorize_service(val)] += 1
    return counts

def count_details(df, col):
    return df[col].value_counts().to_dict()

def process_excel(file1, file2):
    try:
        df1 = pd.read_excel(file1, engine='openpyxl')
        df2 = pd.read_excel(file2, engine='openpyxl')

        # Convertir columnas a tipo categoría cuando sea posible
        for c in df1.select_dtypes(include='object').columns:
            df1[c] = df1[c].astype('category')
        for c in df2.select_dtypes(include='object').columns:
            df2[c] = df2[c].astype('category')

        # Procesar profesionales
        profs = df1[col_prof].dropna().unique()
        prof_data = {}
        for p in profs:
            df_p = df1[df1[col_prof]==p]
            file_path = os.path.join(UPLOAD_FOLDER, f"{sanitize(p)}.xlsx")
            df_p.to_excel(file_path, index=False, engine='openpyxl')
            prof_data[p] = {
                "count": len(df_p),
                "services_by_category": count_categories(df_p, col_serv),
                "details": count_details(df_p, col_serv)
            }
            del df_p
        gc.collect()

        # Procesar usuarios
        users = df2[col_user_val].dropna().unique()
        user_data = {}
        for u in users:
            df_u = df2[df2[col_user_val]==u]
            file_path = os.path.join(QUERY_FOLDER, f"{sanitize(u)}.xlsx")
            df_u.to_excel(file_path, index=False, engine='openpyxl')
            user_data[u] = {
                "count": len(df_u),
                "services_by_category": count_categories(df_u, col_serv_name),
                "details": count_details(df_u, col_serv_name)
            }
            del df_u
        gc.collect()

        return {
            "success": True,
            "professionals": list(profs),
            "users": list(users),
            "professional_data": prof_data,
            "user_data": user_data,
            "totals_crystal": count_categories(df1, col_serv),
            "totals_query": count_categories(df2, col_serv_name),
        }

    except Exception as e:
        logger.exception("Error procesando archivos")
        return {"error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({"error":"Faltan archivos"}), 400
    f1 = request.files['file1']
    f2 = request.files['file2']
    if f1.filename=='' or f2.filename=='':
        return jsonify({"error":"Archivos vacíos"}), 400
    path1 = os.path.join(UPLOAD_FOLDER, secure_filename(f1.filename))
    path2 = os.path.join(UPLOAD_FOLDER, secure_filename(f2.filename))
    f1.save(path1)
    f2.save(path2)
    res = process_excel(path1, path2)
    return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
