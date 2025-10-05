import pandas as pd
import numpy as np
import os
import gc
from openpyxl import Workbook

def process_excel(file1_path, file2_path):
    """
    Optimizado para procesar grandes volúmenes (50.000+ registros)
    sin agotar memoria en Render.
    """

    # Configurar rutas
    output_dir = "/tmp"
    os.makedirs(output_dir, exist_ok=True)

    # Leer en chunks (por partes)
    chunksize = 5000  # procesa 5000 filas por bloque
    print("Iniciando lectura de archivos por partes...")

    # Leer archivo 1 (Crystal)
    df1_chunks = []
    for chunk in pd.read_excel(file1_path, chunksize=chunksize, engine='openpyxl'):
        df1_chunks.append(chunk)
    df1 = pd.concat(df1_chunks, ignore_index=True)
    del df1_chunks
    gc.collect()

    # Leer archivo 2 (Query)
    df2_chunks = []
    for chunk in pd.read_excel(file2_path, chunksize=chunksize, engine='openpyxl'):
        df2_chunks.append(chunk)
    df2 = pd.concat(df2_chunks, ignore_index=True)
    del df2_chunks
    gc.collect()

    # Normalizar nombres de columnas (evitar errores por mayúsculas/minúsculas)
    df1.columns = df1.columns.str.strip().str.lower()
    df2.columns = df2.columns.str.strip().str.lower()

    # Detectar nombres clave
    col_prof = next((c for c in df1.columns if 'profesional' in c), None)
    col_user = next((c for c in df2.columns if 'profesional' in c), None)
    col_serv1 = next((c for c in df1.columns if 'servicio' in c), None)
    col_serv2 = next((c for c in df2.columns if 'servicio' in c), None)

    if not all([col_prof, col_user, col_serv1, col_serv2]):
        return {"error": "No se encontraron columnas esperadas en los archivos Excel."}

    # Reemplazar NaN por texto vacío
    df1.fillna("", inplace=True)
    df2.fillna("", inplace=True)

    # Agrupar datos globales
    total_services_crystal = len(df1)
    total_services_query = len(df2)

    professionals = sorted(df1[col_prof].dropna().unique().tolist())
    users = sorted(df2[col_user].dropna().unique().tolist())

    # Contadores globales
    servicios_por_categoria_crystal = df1[col_serv1].value_counts().to_dict()
    servicios_por_categoria_query = df2[col_serv2].value_counts().to_dict()

    # Totales por servicio
    servicios_detallados_crystal = df1.groupby(col_serv1).size().to_dict()
    servicios_detallados_query = df2.groupby(col_serv2).size().to_dict()

    # Diccionarios para almacenar resultados individuales
    professional_data = {}
    user_data = {}

    # --- Procesar profesionales individualmente ---
    for prof in professionals:
        df_prof = df1[df1[col_prof] == prof]

        if not df_prof.empty:
            servicios_cat = df_prof[col_serv1].value_counts().to_dict()
            servicios_det = df_prof.groupby(col_serv1).size().to_dict()

            file_name = f"prof_{prof.replace(' ', '_')}.xlsx"
            output_file = os.path.join(output_dir, file_name)

            # Escribir Excel directamente sin mantener en memoria
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                df_prof.to_excel(writer, index=False)

            professional_data[prof] = {
                "servicios_por_categoria": servicios_cat,
                "servicios_detallados": servicios_det,
                "download_link": f"/download/{file_name}"
            }

            # Liberar memoria
            del df_prof
            gc.collect()

    # --- Procesar usuarios individualmente ---
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

    # --- Totales globales ---
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

    gc.collect()

    return {
        "totals": totals,
        "professionals": professionals,
        "users": users,
        "professional_data": professional_data,
        "user_data": user_data,
    }
