import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import gridfs
import io

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URI'))
db = client.mierda_app
fs = gridfs.GridFS(db)

def procesar_archivo_chat(contenido):
    # Lee el contenido del archivo
    lines = contenido.decode('utf-8').split('\n')
    # ... resto de tu lógica de procesamiento ...
    return df, todos_mensajes

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo')
        return redirect(url_for('index'))
    
    try:
        print("Iniciando procesamiento del archivo...")
        
        # Leer el contenido del archivo
        contenido = file.read()
        print(f"Archivo leído, tamaño: {len(contenido)} bytes")
        
        # Decodificar el contenido
        texto = contenido.decode('utf-8')
        
        # Procesar el archivo
        df, todos_mensajes = procesar_archivo_chat(texto)
        print("Archivo procesado exitosamente")
        
        # Preparar los datos para MongoDB
        stats_data = {
            'fecha_actualizacion': datetime.now(),
            'total_mierdas': int(df['Cantidad'].sum()) if not df.empty else 0,
            'dias': int(df['Cantidad'].count()) if not df.empty else 0,
            'promedio': float(df['Cantidad'].mean()) if not df.empty else 0,
            'datos_df': df.to_dict('records') if not df.empty else [],
            'mensajes': todos_mensajes,
            'contenido_original': texto  # Guardamos el contenido original
        }
        
        # Eliminar documento anterior si existe
        db.estadisticas.delete_one({'_id': 'stats_principales'})
        
        # Insertar nuevos datos
        db.estadisticas.insert_one({
            '_id': 'stats_principales',
            **stats_data
        })
        
        print("Datos guardados en MongoDB")
        flash('Archivo subido y procesado correctamente')
        
    except Exception as e:
        print(f"Error detallado: {e}")
        flash(f'Error al procesar el archivo: {str(e)}')
        
    return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        # Obtener estadísticas de MongoDB
        stats = db.estadisticas.find_one({'_id': 'stats_principales'})
        
        if stats:
            # Convertir datos a DataFrame si hay datos
            df = pd.DataFrame(stats['datos_df']) if stats['datos_df'] else pd.DataFrame()
            todos_mensajes = stats['mensajes']
            
            return render_template('index.html',
                                stats=stats,
                                tabla=df.to_html(classes='data', border=1) if not df.empty else None,
                                todos_mensajes=todos_mensajes,
                                usuarios=df['Usuario'].tolist() if not df.empty else [],
                                cantidades=df['Cantidad'].tolist() if not df.empty else [])
        else:
            return render_template('index.html', 
                                stats=None,
                                tabla=None,
                                todos_mensajes=None,
                                usuarios=[],
                                cantidades=[])
            
    except Exception as e:
        print(f"Error en index: {e}")
        flash(f'Error al cargar los datos: {str(e)}')
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
