import os
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import re
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URI'))
db = client.mierda_app

def procesar_archivo_chat(contenido):
    try:
        print("Iniciando procesamiento del archivo...")
        lines = contenido.split('\n')
        
        # Inicializar variables
        usuarios_mierdas = {}
        todos_mensajes = []
        dias_totales = len(set(re.findall(r'\[\d{1,2}/\d{1,2}/\d{2,4}', contenido)))
        print(f"Días totales encontrados: {dias_totales}")
        
        # Patrón para la fecha
        patron_fecha = r'\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}:\d{2}\]'
        
        for line in lines:
            if '💩' in line:
                match_fecha = re.search(patron_fecha, line)
                if match_fecha:
                    partes = line.split('] ', 1)
                    if len(partes) > 1:
                        mensaje = partes[1]
                        if ': ' in mensaje:
                            usuario = mensaje.split(': ', 1)[0].strip()
                            if usuario != '💩':
                                usuarios_mierdas[usuario] = usuarios_mierdas.get(usuario, 0) + 1
                            todos_mensajes.append(line)
        
        print(f"Usuarios encontrados: {usuarios_mierdas}")
        
        # Crear DataFrame con promedios
        if usuarios_mierdas:
            df = pd.DataFrame(list(usuarios_mierdas.items()), columns=['Usuario', 'Cantidad'])
            num_participantes = len(df)
            
            # Promedio diario individual
            df['Promedio Diario'] = df['Cantidad'].apply(lambda x: round(x / dias_totales, 2))
            
            # Promedio diario general (total de 💩 / (días × participantes))
            promedio_general = round(df['Cantidad'].sum() / (dias_totales * num_participantes), 2)
            
            df = df.sort_values('Cantidad', ascending=False)
            tabla_html = df.to_html(classes='data', border=1, float_format=lambda x: '%.2f' % x)
            
            return df, todos_mensajes, tabla_html, promedio_general
        else:
            raise ValueError("No se encontraron mensajes válidos para procesar")
        
    except Exception as e:
        print(f"Error detallado en procesar_archivo_chat: {e}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('index'))
    
    try:
        print("\n--- INICIO PROCESO DE UPLOAD ---")
        print("Iniciando procesamiento del archivo...")
        
        # Leer el contenido del archivo
        contenido = file.read().decode('utf-8')
        print(f"Archivo leído, tamaño: {len(contenido)} caracteres")
        
        # Procesar el archivo
        df, todos_mensajes, tabla_html, promedio_general = procesar_archivo_chat(contenido)
        print("Archivo procesado exitosamente")
        
        if df.empty:
            raise ValueError("No se encontraron datos para procesar")
        
        # Preparar datos nuevos
        stats_data = {
            'fecha_actualizacion': datetime.now(),
            'total_mierdas': int(df['Cantidad'].sum()),
            'dias': len(set(re.findall(r'\[\d{1,2}/\d{1,2}/\d{2,4}', contenido))),
            'promedio': promedio_general,
            'datos_df': df.to_dict('records'),
            'mensajes': todos_mensajes,
            'tabla_html': tabla_html,
            'contenido_original': contenido
        }
        
        print("Datos preparados para MongoDB")
        
        # Eliminar datos anteriores
        result = db.estadisticas.delete_many({})
        print(f"Registros anteriores eliminados: {result.deleted_count}")
        
        # Insertar nuevos datos
        result = db.estadisticas.insert_one({
            '_id': 'stats_principales',
            **stats_data
        })
        print(f"Nuevos datos insertados con ID: {result.inserted_id}")
        
        print("--- FIN PROCESO DE UPLOAD ---\n")
        flash('¡Archivo subido y procesado correctamente! 🎉', 'success')
        
        # Forzar recarga de la página sin caché
        response = redirect(url_for('index'))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except Exception as e:
        print(f"Error en upload: {e}")
        import traceback
        print(traceback.format_exc())
        flash(f'Error al procesar el archivo: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        stats = db.estadisticas.find_one({'_id': 'stats_principales'})
        
        if stats:
            df = pd.DataFrame(stats['datos_df'])
            
            return render_template('index.html',
                                stats={
                                    'total_mierdas': stats['total_mierdas'],
                                    'dias': stats['dias'],
                                    'promedio': stats['promedio'],
                                    'cagadores_supremos': df.iloc[0]['Usuario'],
                                    'cantidad_suprema': int(df.iloc[0]['Cantidad']),
                                    'estrenidos': df.iloc[-1]['Usuario'],
                                    'cantidad_minima': int(df.iloc[-1]['Cantidad'])
                                },
                                tabla=stats.get('tabla_html', ''),
                                todos_mensajes=stats['mensajes'],
                                usuarios=df['Usuario'].tolist(),
                                cantidades=df['Cantidad'].tolist())
        else:
            return render_template('index.html', 
                                stats=None,
                                tabla=None,
                                todos_mensajes=None,
                                usuarios=[],
                                cantidades=[])
            
    except Exception as e:
        print(f"Error en index: {e}")
        import traceback
        print(traceback.format_exc())
        flash(f'Error al cargar los datos: {str(e)}')
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
