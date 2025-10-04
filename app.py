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