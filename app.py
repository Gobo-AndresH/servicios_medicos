from flask import Flask, request, jsonify, send_file, render_template
import pandas as pd
import numpy as np
import os
import gc
import psutil
from openpyxl import Workbook

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # Hasta 20MB

# ========================================================
# LECTURA OPTIMIZADA DE ARCHIVOS EXCEL
# ========================================================

def read_large_excel(path):
    """
    Lectura optimizada de Excel sin chunksize.
    Convierte columnas numéricas y libera memoria.
    """
    print(f"📘 Leyendo archivo: {os.path.basename(path)} ...")

    df = pd.read_excel(path, engine='openpyxl')

    # Reducir tipos numéricos
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')

    df.columns = df.columns.str.strip().str.lower()
    gc.collect()
    print(f"✅ Archivo {os.path.basename(path)} leído: {len(df)} filas, {len(df.columns)} columnas.")
    return df


# ========================================================
# PROCESAMIENTO PRINCIPAL
# ========================================================

def process_excel(file1_path, file2_path):
    output_dir = "/tmp"
    os.makedirs(output_dir, exist_ok=True)
    print("🧩 Iniciando procesamiento...")

    df1 = read_large_excel(file1_path)
    df2 = read_large_excel(file2_path)

    # Detección de columnas
    col_prof = next((c for c in df1.columns if 'profesional' in c), None)
    col_user = next((c for c in df2.columns if 'profesional' in c), None)
    col_serv1 = next((c for c in df1.columns if 'servicio' in c), None)
    col_serv2 = next((c for c in df2.columns if 'servicio' in c), None)

    if not all([col_prof, col_user, col_serv1, col_serv2]):
        return {"error": "❌ No se encontraron las columnas esperadas en los archivos."}

    df1.fillna("", inplace=True)
    df2.fillna("", inplace=True)

    professionals = sorted(df1[col_prof].dropna().unique().tolist())
    users = sorted(df2[col_user].dropna().unique().tolist())

    total_services_crystal = len(df1)
    total_services_query = len(df2)

    servicios_por_categoria_crystal = df1[col_serv1].value_counts().to_dict()
    servicios_por_categoria_query = df2[col_serv2].value_counts().to_dict()

    professional_data = {}
    user_data = {}

    # Procesar profesionales
    for prof in professionals:
        df_prof = df1[df1[col_prof] == prof]
        if not df_prof.empty:
            servicios_cat = df_prof[col_serv1].value_counts().to_dict()
            servicios_det = df_prof.groupby(col_serv1).size().to_dict()
            file_name = f"prof_{prof.replace(' ', '_')}.xlsx"
            output_file = os.path.join(output_dir, file_name)
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                df_prof.to_excel(writer, index=False)
            professional_data[prof] = {
                "servicios_por_categoria": servicios_cat,
                "servicios_detallados": servicios_det,
                "download_link": f"/download/{file_name}"
            }
            del df_prof
            gc.collect()

    # Procesar usuarios
    for usr in users:
        df_user = df2[df2[col_user] == usr]
        if not df_user.empty:
            servicios_cat = df_user[col_serv2].value_counts().to_dict()
            servicios_det = df_user.groupby(col_serv2).size().to_dict()
            file_name = f"user_{usr.replace(' ', '_')}.xlsx"
            output_file = os.path.join(output_dir, file_name)
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                df_user.to_excel(writer, index=False)
            user_data[usr] = {
                "servicios_por_categoria": servicios_cat,
                "servicios_detallados": servicios_det,
                "download_link": f"/download/{file_name}"
            }
            del df_user
            gc.collect()

    del df1, df2
    gc.collect()

    mem = psutil.virtual_memory()
    print(f"✅ Procesamiento completo. Uso de memoria: {mem.percent}%")

    return {
        "totals": {
            "total_services_crystal": total_services_crystal,
            "total_services_query": total_services_query,
            "num_professionals": len(professionals),
            "num_users": len(users),
            "servicios_por_categoria_crystal": servicios_por_categoria_crystal,
            "servicios_por_categoria_query": servicios_por_categoria_query,
        },
        "professionals": professionals,
        "users": users,
        "professional_data": professional_data,
        "user_data": user_data
    }


# ========================================================
# ENDPOINTS FLASK
# ========================================================

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file1 = request.files.get('file1')
        file2 = request.files.get('file2')

        if not file1 or not file2:
            return jsonify({"error": "Debes subir ambos archivos."}), 400

        size_limit_mb = 15
        file1_size = len(file1.read()) / (1024 * 1024)
        file2_size = len(file2.read()) / (1024 * 1024)
        file1.seek(0)
        file2.seek(0)

        warning = None
        if file1_size > size_limit_mb or file2_size > size_limit_mb:
            warning = f"⚠️ Archivos grandes detectados ({round(max(file1_size, file2_size),2)} MB). Esto puede tardar varios minutos."

        file1_path = os.path.join("/tmp", file1.filename)
        file2_path = os.path.join("/tmp", file2.filename)
        file1.save(file1_path)
        file2.save(file2_path)

        data = process_excel(file1_path, file2_path)

        if warning:
            data["warning"] = warning

        return jsonify(data)

    except Exception as e:
        print(f"❌ Error en /upload: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join("/tmp", filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "Archivo no encontrado"}), 404

        response = send_file(file_path, as_attachment=True)
        os.remove(file_path)
        print(f"🧹 Archivo eliminado tras descarga: {filename}")
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def home():
    return render_template('index.html')


# ========================================================
# MANEJADOR GLOBAL DE ERRORES
# ========================================================

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    error_trace = traceback.format_exc()
    print("❌ Error global detectado:")
    print(error_trace)
    return jsonify({
        "error": str(e),
        "type": e.__class__.__name__,
        "details": error_trace.splitlines()[-5:]
    }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
