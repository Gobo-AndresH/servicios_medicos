import os
import re
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Logging más limpio
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔒 Carpeta temporal de Render
BASE_DIR = "/tmp"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tamaño máximo
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Config columnas esperadas
CAMPOS_CRYSTAL = ["Profesional", "Servicio"]
CAMPOS_QUERY = ["Nombre Usuario Validación", "Nombre Servicio"]

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', "_", str(name).strip().title())[:50]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        file1 = request.files.get("file1")
        file2 = request.files.get("file2")

        if not file1 or not file2:
            return jsonify({"error": "Debes seleccionar ambos archivos."}), 400

        filename1 = secure_filename(file1.filename)
        filename2 = secure_filename(file2.filename)
        path1 = os.path.join(UPLOAD_FOLDER, filename1)
        path2 = os.path.join(UPLOAD_FOLDER, filename2)
        file1.save(path1)
        file2.save(path2)

        logger.info(f"Procesando archivos: {filename1}, {filename2}")

        df1 = pd.read_excel(path1, engine="openpyxl", usecols=CAMPOS_CRYSTAL)
        df2 = pd.read_excel(path2, engine="openpyxl", usecols=CAMPOS_QUERY)

        # Procesar por profesional
        result_files = []
        for name, group in df1.groupby("Profesional"):
            safe = sanitize_filename(name)
            out_path = os.path.join(UPLOAD_FOLDER, f"{safe}_crystal.xlsx")
            group.to_excel(out_path, index=False)
            result_files.append({"name": name, "url": f"/download/{safe}_crystal.xlsx"})

        # Procesar por usuario validación
        for name, group in df2.groupby("Nombre Usuario Validación"):
            safe = sanitize_filename(name)
            out_path = os.path.join(UPLOAD_FOLDER, f"{safe}_query.xlsx")
            group.to_excel(out_path, index=False)
            result_files.append({"name": name, "url": f"/download/{safe}_query.xlsx"})

        return jsonify({"success": True, "files": result_files}), 200

    except Exception as e:
        logger.error(f"Error procesando: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/download/<path:filename>")
def download(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    return jsonify({"error": "Archivo no encontrado"}), 404

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "short_name": "Servicios Médicos",
        "name": "Control Servicios Médicos",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ],
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#007bff",
        "background_color": "#ffffff"
    })

@app.route("/service-worker.js")
def sw():
    sw_code = """
self.addEventListener('install', e => e.waitUntil(caches.open('v1').then(c => c.addAll(['/','/static/style.css','/static/js/app.js']))));
self.addEventListener('fetch', e => e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))));
"""
    return sw_code, 200, {'Content-Type': 'application/javascript'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

