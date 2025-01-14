import os
from flask import Flask, render_template, request, redirect, url_for, flash
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
        # Debug: ver el contenido del archivo
        print("Contenido del archivo:")
        print(contenido[:500])
        
        # Dividir el contenido en líneas
        lines = contenido.split('\n')
        print(f"Número de líneas: {len(lines)}")
        
        # Inicializar variables
        usuarios_mierdas = {}
        todos_mensajes = []
        
        # Nuevo patrón para el formato [dd/mm/yy, HH:MM:SS]
        patron_fecha = r'\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}:\d{2}\]'
        
        for line in lines:
            if '💩' in line:
                print(f"\nLínea con 💩 encontrada: {line}")
                
                # Extraer fecha y usuario usando el nuevo formato
                match_fecha = re.search(patron_fecha, line)
                if match_fecha:
                    # Separar por '] ' para obtener el resto del mensaje
                    partes = line.split('] ', 1)
                    if len(partes) > 1:
                        mensaje = partes[1]
                        # Separar por ': ' para obtener el usuario
                        if ': ' in mensaje:
                            usuario = mensaje.split(': ', 1)[0].strip()
                            print(f"Usuario encontrado: {usuario}")
                            usuarios_mierdas[usuario] = usuarios_mierdas.get(usuario, 0) + 1
                            todos_mensajes.append(line)
        
        print(f"Usuarios encontrados: {usuarios_mierdas}")
        
        # Crear DataFrame
        if usuarios_mierdas:
            df = pd.DataFrame(list(usuarios_mierdas.items()), columns=['Usuario', 'Cantidad'])
            df = df.sort_values('Cantidad', ascending=False)
            return df, todos_mensajes
        else:
            raise ValueError("No se encontraron mensajes con 💩 en el formato esperado")
        
    except Exception as e:
        print(f"Error detallado en procesar_archivo_chat: {e}")
        raise

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
        contenido = file.read().decode('utf-8')
        print(f"Archivo leído, tamaño: {len(contenido)} caracteres")
        
        # Procesar el archivo
        df, todos_mensajes = procesar_archivo_chat(contenido)
        print("Archivo procesado exitosamente")
        
        if df.empty:
            raise ValueError("No se encontraron datos para procesar")
        
        # Calcular estadísticas
        stats_data = {
            'fecha_actualizacion': datetime.now(),
            'total_mierdas': int(df['Cantidad'].sum()),
            'dias': len(set(re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', contenido))),
            'promedio': round(float(df['Cantidad'].mean()), 2),
            'datos_df': df.to_dict('records'),
            'mensajes': todos_mensajes,
            'contenido_original': contenido
        }
        
        # Actualizar MongoDB
        db.estadisticas.delete_one({'_id': 'stats_principales'})
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
        print("Datos recuperados de MongoDB:", stats is not None)  # Debug
        
        if stats:
            # Convertir datos a DataFrame
            df = pd.DataFrame(stats['datos_df'])
            print("DataFrame creado con éxito")  # Debug
            print("Columnas:", df.columns.tolist())  # Debug
            print("Número de filas:", len(df))  # Debug
            
            # Preparar datos para el template
            datos_stats = {
                'total_mierdas': stats['total_mierdas'],
                'dias': stats['dias'],
                'promedio': stats['promedio'],
                'cagadores_supremos': df.iloc[0]['Usuario'] if not df.empty else "N/A",
                'cantidad_suprema': int(df.iloc[0]['Cantidad']) if not df.empty else 0,
                'estrenidos': df.iloc[-1]['Usuario'] if not df.empty else "N/A",
                'cantidad_minima': int(df.iloc[-1]['Cantidad']) if not df.empty else 0
            }
            
            print("Datos preparados para el template:", datos_stats)  # Debug
            
            return render_template('index.html',
                                stats=datos_stats,
                                tabla=df.to_html(classes='data', border=1) if not df.empty else None,
                                todos_mensajes=stats.get('mensajes', []),
                                usuarios=df['Usuario'].tolist() if not df.empty else [],
                                cantidades=df['Cantidad'].tolist() if not df.empty else [])
        else:
            print("No se encontraron datos en MongoDB")  # Debug
            return render_template('index.html', 
                                stats=None,
                                tabla=None,
                                todos_mensajes=None,
                                usuarios=[],
                                cantidades=[])
            
    except Exception as e:
        print(f"Error en index: {e}")  # Debug
        import traceback
        print(traceback.format_exc())  # Debug detallado
        flash(f'Error al cargar los datos: {str(e)}')
        return render_template('index.html',
                             stats=None,
                             tabla=None,
                             todos_mensajes=None,
                             usuarios=[],
                             cantidades=[])

if __name__ == '__main__':
    app.run(debug=True)
