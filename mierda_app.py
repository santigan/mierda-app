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
        # Agregar print para debugging
        print("Iniciando procesamiento del archivo...")
        
        # Leer el contenido del archivo
        contenido = file.read()
        print(f"Archivo leído, tamaño: {len(contenido)} bytes")
        
        # Procesar el archivo
        df, todos_mensajes = procesar_archivo_chat(contenido)
        print("Archivo procesado exitosamente")
        
        # Guardar en MongoDB
        stats_data = {
            'fecha_actualizacion': datetime.now(),
            'total_mierdas': int(df['Cantidad'].sum()),
            'dias': int(df['Cantidad'].count()),
            'promedio': float(df['Cantidad'].mean()),
            'datos_df': df.to_dict('records'),
            'mensajes': todos_mensajes
        }
        
        # Actualizar o insertar estadísticas
        db.estadisticas.update_one(
            {'_id': 'stats_principales'},
            {'$set': stats_data},
            upsert=True
        )
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
            # Convertir datos a DataFrame
            df = pd.DataFrame(stats['datos_df'])
            todos_mensajes = stats['mensajes']
            
            return render_template('index.html',
                                stats=stats,
                                todos_mensajes=todos_mensajes,
                                usuarios=df['Usuario'].tolist(),
                                cantidades=df['Cantidad'].tolist())
        else:
            flash('No hay datos disponibles. Por favor, sube un archivo.')
            return render_template('index.html')
            
    except Exception as e:
        flash(f'Error al cargar los datos: {str(e)}')
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
