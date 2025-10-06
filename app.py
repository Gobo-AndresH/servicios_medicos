from flask import Flask, request, jsonify, send_file, render_template
import pandas as pd
import numpy as np
import os
import gc
import psutil
from openpyxl import Workbook
import tempfile
import uuid
import re

app = Flask(__name__, 
           static_folder='static', 
           template_folder='templates',
           static_url_path='/static')

# Configuración para Render
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB para Render

# Variable global para controlar procesos
active_processes = {}

# ========================================================
# FUNCIONES AUXILIARES PARA NOMBRES DE ARCHIVOS
# ========================================================

def format_filename(name):
    """
    Convierte un nombre a formato legible con iniciales en mayúscula
    SIN guiones bajos
    """
    if not name or pd.isna(name):
        return "Sin Nombre"
    
    # Convertir a string y limpiar
    name_str = str(name).strip()
    
    # Reemplazar caracteres especiales con espacios
    name_clean = re.sub(r'[^\w\s]', ' ', name_str)
    
    # Convertir a título (iniciales en mayúscula)
    name_title = name_clean.title()
    
    # Reemplazar múltiples espacios por uno solo
    name_final = re.sub(r'\s+', ' ', name_title).strip()
    
    # Limitar longitud del nombre
    if len(name_final) > 50:
        name_final = name_final[:50]
    
    return name_final

# ========================================================
# FUNCIONES PARA SERIALIZAR DATOS - MÁS ROBUSTA
# ========================================================

def safe_serialize(obj):
    """
    Convierte cualquier objeto a tipos nativos de Python de forma segura
    """
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    elif isinstance(obj, dict):
        return {str(k): safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_serialize(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(safe_serialize(item) for item in obj)
    elif hasattr(obj, 'item'):  # Para numpy scalars
        return obj.item()
    elif pd.isna(obj):
        return None
    else:
        try:
            return str(obj)
        except:
            return None

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
# DETECCIÓN INTELIGENTE DE COLUMNAS
# ========================================================

def detect_columns(df, df_name):
    """
    Detecta automáticamente las columnas relevantes con múltiples variantes
    """
    print(f"🔍 Analizando columnas de {df_name}...")
    print(f"   Columnas disponibles: {list(df.columns)}")
    
    # Buscar columnas con múltiples variantes
    professional_variants = ['profesional', 'profesionales', 'medico', 'médico', 'doctor', 'nombre', 'nombres', 'empleado']
    service_variants = ['servicio', 'servicios', 'procedimiento', 'procedimientos', 'estudio', 'estudios', 'tipo', 'categoria', 'categoría']
    user_variants = ['usuario', 'user', 'paciente', 'nombre', 'nombres', 'identificacion', 'identificación', 'cedula', 'cédula']
    
    col_prof = None
    col_serv = None
    col_user = None
    
    # Buscar columna de profesional
    for variant in professional_variants:
        for col in df.columns:
            if variant in col.lower():
                col_prof = col
                print(f"   ✅ Columna profesional detectada: '{col}' (coincide con '{variant}')")
                break
        if col_prof:
            break
    
    # Buscar columna de servicio
    for variant in service_variants:
        for col in df.columns:
            if variant in col.lower():
                col_serv = col
                print(f"   ✅ Columna servicio detectada: '{col}' (coincide con '{variant}')")
                break
        if col_serv:
            break
    
    # Buscar columna de usuario/paciente
    for variant in user_variants:
        for col in df.columns:
            if variant in col.lower() and col != col_prof:  # Evitar duplicados con profesional
                col_user = col
                print(f"   ✅ Columna usuario detectada: '{col}' (coincide con '{variant}')")
                break
        if col_user:
            break
    
    # Si no encontramos, usar las primeras columnas como fallback
    if not col_prof and len(df.columns) >= 1:
        col_prof = df.columns[0]
        print(f"   ⚠️  Usando primera columna como profesional: '{col_prof}'")
    
    if not col_serv and len(df.columns) >= 2:
        col_serv = df.columns[1]
        print(f"   ⚠️  Usando segunda columna como servicio: '{col_serv}'")
    
    if not col_user and len(df.columns) >= 3:
        col_user = df.columns[2]
        print(f"   ⚠️  Usando tercera columna como usuario: '{col_user}'")
    
    return col_prof, col_serv, col_user

# ========================================================
# PROCESAMIENTO PRINCIPAL SIMPLIFICADO
# ========================================================

def process_excel(file1_path, file2_path, process_id):
    """
    Procesa los archivos y genera Excel por profesional SOLO con datos completos
    """
    try:
        # Verificar si el proceso fue cancelado
        if process_id not in active_processes:
            return {"error": "Proceso cancelado por el usuario"}
        
        # En Render, usar /tmp es más seguro
        output_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
        os.makedirs(output_dir, exist_ok=True)
        print("🧩 Iniciando procesamiento...")
        print(f"📁 Directorio temporal: {output_dir}")

        # Verificar que los archivos existen
        if not os.path.exists(file1_path):
            raise FileNotFoundError(f"Archivo 1 no encontrado: {file1_path}")
        if not os.path.exists(file2_path):
            raise FileNotFoundError(f"Archivo 2 no encontrado: {file2_path}")

        # Actualizar estado del proceso
        active_processes[process_id] = {"status": "reading_files", "progress": 10}
        
        df1 = read_large_excel(file1_path)
        df2 = read_large_excel(file2_path)

        # Verificar cancelación
        if process_id not in active_processes:
            return {"error": "Proceso cancelado por el usuario"}

        # Detección INTELIGENTE de columnas
        print("\n" + "="*50)
        print("🔍 DETECTANDO COLUMNAS EN ARCHIVO CRYSTAL")
        print("="*50)
        col_prof1, col_serv1, col_user1 = detect_columns(df1, "CRYSTAL")
        
        print("\n" + "="*50)
        print("🔍 DETECTANDO COLUMNAS EN ARCHIVO QUERY")
        print("="*50)
        col_prof2, col_serv2, col_user2 = detect_columns(df2, "QUERY")
        
        print("\n" + "="*50)
        print("📊 RESUMEN DE DETECCIÓN DE COLUMNAS")
        print("="*50)
        print(f"CRYSTAL - Profesional: '{col_prof1}', Servicio: '{col_serv1}', Usuario: '{col_user1}'")
        print(f"QUERY   - Profesional: '{col_prof2}', Servicio: '{col_serv2}', Usuario: '{col_user2}'")
        print("="*50 + "\n")

        # Verificar que tenemos las columnas mínimas necesarias
        if not col_prof1:
            error_msg = {
                "error": "❌ No se pudo detectar la columna de profesional en el archivo CRYSTAL",
                "details": {
                    "crystal_columns": list(df1.columns),
                    "query_columns": list(df2.columns)
                }
            }
            return error_msg

        df1.fillna("", inplace=True)
        df2.fillna("", inplace=True)

        # Verificar cancelación
        if process_id not in active_processes:
            return {"error": "Proceso cancelado por el usuario"}

        active_processes[process_id] = {"status": "processing_professionals", "progress": 30}

        # OBTENER DATOS PARA FILTROS - CONVERTIR A LISTAS NATIVAS INMEDIATAMENTE
        professionals = [str(prof) for prof in df1[col_prof1].dropna().unique()] if col_prof1 in df1.columns else []
        professionals.sort()
        
        usuarios_crystal = [str(user) for user in df1[col_user1].dropna().unique()] if col_user1 in df1.columns else []
        usuarios_crystal.sort()
        
        usuarios_query = [str(user) for user in df2[col_user2].dropna().unique()] if col_user2 in df2.columns else []
        usuarios_query.sort()

        total_services_crystal = int(len(df1))
        total_services_query = int(len(df2))

        # Convertir value_counts a dict nativo inmediatamente
        servicios_por_categoria_crystal = {}
        if col_serv1 in df1.columns:
            for k, v in df1[col_serv1].value_counts().items():
                servicios_por_categoria_crystal[str(k)] = int(v)
        
        servicios_por_categoria_query = {}
        if col_serv2 in df2.columns:
            for k, v in df2[col_serv2].value_counts().items():
                servicios_por_categoria_query[str(k)] = int(v)

        professional_data = {}
        user_data = {}

        # Procesar profesionales - GENERAR EXCEL POR PROFESIONAL SOLO CON DATOS COMPLETOS
        total_professionals = len(professionals)
        for index, prof in enumerate(professionals):
            # Verificar cancelación en cada iteración
            if process_id not in active_processes:
                return {"error": "Proceso cancelado por el usuario"}
            
            # Actualizar progreso
            progress = 30 + (index / total_professionals) * 50
            active_processes[process_id] = {"status": f"Procesando {prof}", "progress": progress}
            
            # Filtrar datos del profesional actual
            df_prof = df1[df1[col_prof1] == prof].copy()
            if not df_prof.empty:
                # AGREGAR COLUMNA DE VALIDACIÓN AL DATAFRAME ORIGINAL
                df_prof_copy = df_prof.copy()
                df_prof_copy['Validación Query'] = 'NO'
                
                # Verificar qué usuarios están en Query
                if col_user2 in df2.columns and col_user1 in df_prof_copy.columns:
                    usuarios_en_query = [str(user) for user in df2[col_user2].dropna().unique()]
                    mask = df_prof_copy[col_user1].astype(str).isin(usuarios_en_query)
                    df_prof_copy.loc[mask, 'Validación Query'] = 'SI'
                
                # GENERAR NOMBRE DE ARCHIVO LEGIBLE - SIN GUIONES BAJOS
                nombre_formateado = format_filename(prof)
                file_name = f"{nombre_formateado}.xlsx"
                output_file = os.path.join(output_dir, file_name)
                
                print(f"💾 Generando reporte para {prof}: {output_file}")
                
                # SOLO UNA HOJA CON DATOS COMPLETOS
                with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                    df_prof_copy.to_excel(writer, sheet_name='Datos', index=False)
                
                # Convertir a tipos nativos para serialización - MÁS ROBUSTO
                servicios_cat = {}
                if col_serv1 in df_prof.columns:
                    for k, v in df_prof[col_serv1].value_counts().items():
                        servicios_cat[str(k)] = int(v)
                
                total_usuarios = int(len(df_prof[col_user1].dropna().unique())) if col_user1 in df_prof.columns else 0
                total_servicios = int(len(df_prof))
                
                professional_data[str(prof)] = {
                    "servicios_por_categoria": servicios_cat,
                    "total_usuarios": total_usuarios,
                    "total_servicios": total_servicios,
                    "download_link": f"/download/{file_name}",
                    "nombre_archivo": file_name
                }
                
                del df_prof, df_prof_copy
                gc.collect()

        # PROCESAR ARCHIVO QUERY - Generar archivo con validación de usuarios
        if col_user2 in df2.columns:
            active_processes[process_id] = {"status": "processing_query", "progress": 85}
            
            # Crear archivo de validación de usuarios Query
            df_query_validation = df2.copy()
            df_query_validation['Usuario en Crystal'] = 'NO'
            
            if col_user1 in df1.columns:
                usuarios_crystal_list = [str(user) for user in df1[col_user1].dropna().unique()]
                mask = df_query_validation[col_user2].astype(str).isin(usuarios_crystal_list)
                df_query_validation.loc[mask, 'Usuario en Crystal'] = 'SI'
            
            # Generar archivo Excel para Query con nombre legible - SIN GUIONES BAJOS
            query_file_name = "Validación Usuarios Query.xlsx"
            query_output_file = os.path.join(output_dir, query_file_name)
            
            print(f"💾 Generando reporte de validación Query: {query_output_file}")
            
            # SOLO UNA HOJA CON DATOS COMPLETOS
            with pd.ExcelWriter(query_output_file, engine="openpyxl") as writer:
                df_query_validation.to_excel(writer, sheet_name='Datos', index=False)
            
            usuarios_en_crystal = int(len(df_query_validation[df_query_validation['Usuario en Crystal'] == 'SI']))
            usuarios_solo_query = int(len(df_query_validation[df_query_validation['Usuario en Crystal'] == 'NO']))
            total_usuarios_query = int(len(df_query_validation))
            
            user_data["query_validation"] = {
                "download_link": f"/download/{query_file_name}",
                "nombre_archivo": query_file_name,
                "total_usuarios": total_usuarios_query,
                "usuarios_en_crystal": usuarios_en_crystal,
                "usuarios_solo_query": usuarios_solo_query
            }

        # Limpiar memoria
        del df1, df2
        gc.collect()

        active_processes[process_id] = {"status": "completed", "progress": 100}

        mem = psutil.virtual_memory()
        print(f"✅ Procesamiento completo. Uso de memoria: {mem.percent}%")

        # Construir resultado final con tipos nativos
        result_data = {
            "totals": {
                "total_services_crystal": total_services_crystal,
                "total_services_query": total_services_query,
                "num_professionals": len(professionals),
                "num_users_crystal": len(usuarios_crystal),
                "num_users_query": len(usuarios_query),
                "servicios_por_categoria_crystal": servicios_por_categoria_crystal,
                "servicios_por_categoria_query": servicios_por_categoria_query,
            },
            "professionals": professionals,
            "usuarios_crystal": usuarios_crystal,
            "usuarios_query": usuarios_query,
            "professional_data": professional_data,
            "user_data": user_data,
            "column_mapping": {
                "crystal": {"profesional": str(col_prof1), "servicio": str(col_serv1), "usuario": str(col_user1)},
                "query": {"profesional": str(col_prof2), "servicio": str(col_serv2), "usuario": str(col_user2)}
            },
            "process_id": process_id
        }

        # Aplicar serialización segura a TODO el resultado
        return safe_serialize(result_data)

    except Exception as e:
        print(f"❌ Error en procesamiento: {e}")
        import traceback
        print(traceback.format_exc())
        return {"error": f"Error en procesamiento: {str(e)}"}

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

        # Generar ID único para este proceso
        process_id = str(uuid.uuid4())
        active_processes[process_id] = {"status": "starting", "progress": 0}

        # Guardar archivos temporales - En Render usar /tmp
        temp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
        file1_name = f"crystal_{uuid.uuid4().hex[:8]}.xlsx"
        file2_name = f"query_{uuid.uuid4().hex[:8]}.xlsx"
        
        file1_path = os.path.join(temp_dir, file1_name)
        file2_path = os.path.join(temp_dir, file2_name)
        
        file1.save(file1_path)
        file2.save(file2_path)

        # Procesar archivos
        data = process_excel(file1_path, file2_path, process_id)

        # Limpiar archivos temporales
        try:
            if os.path.exists(file1_path):
                os.remove(file1_path)
            if os.path.exists(file2_path):
                os.remove(file2_path)
        except Exception as e:
            print(f"⚠️ No se pudieron eliminar archivos temporales: {e}")

        # Remover proceso de la lista activa si existe
        if process_id in active_processes:
            del active_processes[process_id]

        return jsonify(data)

    except Exception as e:
        print(f"❌ Error en /upload: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

@app.route('/cancel-process', methods=['POST'])
def cancel_process():
    """Endpoint para cancelar procesos activos"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
            
        process_id = data.get('process_id')
        
        if process_id and process_id in active_processes:
            del active_processes[process_id]
            print(f"✅ Proceso {process_id} cancelado")
            return jsonify({"success": True, "message": "Proceso cancelado correctamente"})
        else:
            return jsonify({"error": "Proceso no encontrado o ya finalizado"}), 404
            
    except Exception as e:
        print(f"❌ Error cancelando proceso: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # En Render usar /tmp
        temp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Archivo no encontrado"}), 404

        # Enviar archivo con nombre personalizado
        response = send_file(file_path, as_attachment=True, download_name=filename)
        
        # Intentar eliminar después de descargar
        try:
            os.remove(file_path)
            print(f"🧹 Archivo eliminado tras descarga: {filename}")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar archivo {filename}: {e}")
            
        return response
        
    except Exception as e:
        return jsonify({"error": f"Error en descarga: {str(e)}"}), 500

@app.route('/')
def home():
    return render_template('index.html')

# Manejo de errores global
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

if __name__ == '__main__':
    # En Render, usar el puerto proporcionado por la variable de entorno
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Iniciando aplicación en puerto: {port}")
    print(f"📁 Directorio de trabajo: {os.getcwd()}")
    print(f"📁 Temp dir: {tempfile.gettempdir()}")
    app.run(host='0.0.0.0', port=port, debug=False)