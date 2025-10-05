import pandas as pd
import numpy as np
import os
import gc
import psutil
from flask import send_file, jsonify
from openpyxl import Workbook
from datetime import datetime

# ========================================================
# PROCESAMIENTO OPTIMIZADO DE ARCHIVOS EXCEL GRANDES
# ========================================================

def process_excel(file1_path, file2_path):
    """
    Optimizado para procesar grandes volúmenes (50.000+ registros)
    sin agotar memoria en Render.
    """

    output_dir = "/tmp"
    os.makedirs(output_dir, exist_ok=True)
    chunksize = 5000

    print("🧩 Iniciando procesamiento optimizado por partes...")

    # ========== Lectura parcial ==========
    def read_large_excel(path):
        chunks = []
        for chunk in pd.read_excel(path, chunksize=chunksize, engine='openpyxl'):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
        del chunks
        gc.collect()
        return df

    df1 = read_large_excel(file1_path)
    df2 = read_large_excel(file2_path)

    # Normalizar columnas
    df1.columns = df1.columns.str.strip().str.lower()
    df2.columns = df2.columns.str.strip().str.lower()

    # Detectar columnas clave
    col_prof = next((c for c in df1.columns if 'profesional' in c), None)
    col_user = next((c for c in df2.columns if 'profesional' in c), None)
    col_serv1 = next((c for c in df1.columns if 'servicio' in c), None)
    col_serv2 = next((c for c in df2.columns if 'servicio' in c), None)

    if not all([col_prof, col_user, col_serv1, col_serv2]):
        return {"error": "❌ No se encontraron columnas esperadas en los archivos Excel."}

    df1.fillna("", inplace=True)
    df2.fillna("", inplace=True)

    professionals = sorted(df1[col_prof].dropna().unique().tolist())
    users = sorted(df2[col_user].dropna().unique().tolist())

    total_services_crystal = len(df1)
    total_services_query = len(df2)

    servicios_por_categoria_crystal = df1[col_serv1].value_counts().to_dict()
    servicios_por_categoria_query = df2[col_serv2].value_counts().to_dict()
    servicios_detallados_crystal = df1.groupby(col_serv1).size().to_dict()
    servicios_detallados_query = df2.groupby(col_serv2).size().to_dict()

    professional_data = {}
    user_data = {}

    # ========== Procesar profesionales ==========
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

    # ========== Procesar usuarios ==========
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

    # Limpiar memoria pesada
    del df1, df2
    gc.collect()

    # Log de uso de memoria (útil para Render)
    mem = psutil.virtual_memory()
    print(f"✅ Proceso finalizado - Memoria usada: {mem.percent}%")

    totals = {
        "total_services_crystal": total_services_crystal,
        "total_services_query": total_services_query,
        "num_professionals": len(professionals),
        "num_users": len(users),
        "servicios_por_categoria_crystal": servicios_por_categoria_crystal,
        "servicios_por_categoria_query": servicios_por_categoria_query,
        "servicios_detallados_crystal": servicios_detallados_crystal,
        "servicios_detallados_query": servicios_detallados_query,
    }

    return {
        "totals": totals,
        "professionals": professionals,
        "users": users,
        "professional_data": professional_data,
        "user_data": user_data,
    }

# ========================================================
# DESCARGA AUTOMÁTICA CON LIMPIEZA POSTERIOR
# ========================================================

from flask import send_file, abort

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join("/tmp", filename)

        if not os.path.exists(file_path):
            print(f"⚠️ Archivo no encontrado: {filename}")
            return jsonify({"error": "Archivo no encontrado"}), 404

        # Registrar memoria antes de enviar
        mem_before = psutil.virtual_memory().percent
        print(f"📤 Enviando archivo {filename} (Memoria antes: {mem_before}%)")

        # Enviar el archivo
        response = send_file(file_path, as_attachment=True)

        # Eliminar archivo temporal tras enviar
        try:
            os.remove(file_path)
            print(f"🧹 Archivo eliminado después de descarga: {filename}")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar {filename}: {e}")

        # Registrar memoria después
        mem_after = psutil.virtual_memory().percent
        print(f"📦 Memoria después: {mem_after}%")

        return response

    except Exception as e:
        print(f"❌ Error en la descarga: {e}")
        return jsonify({"error": str(e)}), 500
