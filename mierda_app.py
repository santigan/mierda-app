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
        mensajes_validez = {}
        dias_totales = len(set(re.findall(r'\[\d{1,2}/\d{1,2}/\d{2,4}', contenido)))
        
        # Patrón para la fecha y formato del mensaje
        patron_fecha = r'\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}:\d{2}\]'
        patron_mensaje = r'\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}:\d{2}\]\s*(.*?):\s*(.*)$'
        
        for line in line_filter(lines):  # Filtrar líneas vacías
            # Procesar cada línea que tenga formato de mensaje
            match = re.match(patron_mensaje, line)
            if match:
                usuario = match.group(1).strip()
                contenido_mensaje = match.group(2).strip()
                
                # Determinar si el mensaje es válido (solo contiene 💩)
                es_valido = contenido_mensaje == '💩' and usuario != '💩'
                
                # Guardar el mensaje
                todos_mensajes.append(line)
                mensajes_validez[line] = es_valido
                
                # Actualizar estadísticas si es válido
                if es_valido:
                    usuarios_mierdas[usuario] = usuarios_mierdas.get(usuario, 0) + 1
        
        # Crear DataFrame con promedios y validez
        if usuarios_mierdas:
            df = pd.DataFrame(list(usuarios_mierdas.items()), columns=['Usuario', 'Cantidad'])
            df['Promedio Diario'] = df['Cantidad'].apply(lambda x: round(x / dias_totales, 2))
            df = df.sort_values('Cantidad', ascending=False)
            
            # Crear tabla HTML personalizada con numeración
            tabla_html = """
            <table class="data">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Participante</th>
                        <th>Cantidad</th>
                        <th>Promedio Diario</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for index, row in df.iterrows():
                posicion = df.index.get_loc(index) + 1
                tabla_html += f"""
                    <tr>
                        <td>{posicion}</td>
                        <td>{row['Usuario']}</td>
                        <td>{int(row['Cantidad'])}</td>
                        <td>{row['Promedio Diario']:.2f}</td>
                    </tr>
                """
            
            tabla_html += "</tbody></table>"
            
            return df, todos_mensajes, tabla_html, mensajes_validez
        else:
            raise ValueError("No se encontraron mensajes válidos para procesar")
        
    except Exception as e:
        print(f"Error detallado en procesar_archivo_chat: {e}")
        raise

def line_filter(lines):
    """Filtra líneas vacías y asegura que sean mensajes válidos."""
    return [line.strip() for line in lines if line.strip() and re.match(r'\[\d{1,2}/\d{1,2}/\d{2,4}', line)]

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
        df, todos_mensajes, tabla_html, mensajes_validez = procesar_archivo_chat(contenido)
        print("Archivo procesado exitosamente")
        
        if df.empty:
            raise ValueError("No se encontraron datos para procesar")
        
        # Calcular el promedio general
        dias_totales = len(set(re.findall(r'\[\d{1,2}/\d{1,2}/\d{2,4}', contenido)))
        num_participantes = len(df)
        promedio_general = round(df['Cantidad'].sum() / (dias_totales * num_participantes), 2)
        
        # Preparar datos nuevos
        stats_data = {
            'fecha_actualizacion': datetime.now(),
            'total_mierdas': int(df['Cantidad'].sum()),
            'dias': dias_totales,
            'promedio': promedio_general,
            'datos_df': df.to_dict('records'),
            'mensajes': todos_mensajes,
            'mensajes_validez': mensajes_validez,
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
        flash('Archivo subido y procesado correctamente', 'success')
        
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
            
            # Encontrar la fecha del último mensaje
            ultima_fecha = None
            if stats.get('mensajes'):
                for mensaje in reversed(stats['mensajes']):
                    # Extraer la fecha del formato [dd/mm/yy, HH:MM:SS]
                    match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}:\d{2})\]', mensaje)
                    if match:
                        fecha_str = match.group(1)
                        # Convertir a formato más amigable
                        try:
                            fecha = datetime.strptime(fecha_str, '%d/%m/%y, %H:%M:%S')
                            ultima_fecha = fecha.strftime('%d/%m/%Y %H:%M')
                            break
                        except ValueError:
                            continue

            return render_template('index.html',
                                stats=stats_data,
                                tabla=stats.get('tabla_html', ''),
                                todos_mensajes=stats['mensajes'],
                                mensajes_validez=stats.get('mensajes_validez', {}),
                                usuarios=df['Usuario'].tolist(),
                                cantidades=df['Cantidad'].tolist(),
                                ultima_fecha=ultima_fecha or 'No disponible')
        else:
            return render_template('index.html', 
                                stats=None,
                                tabla=None,
                                todos_mensajes=None,
                                mensajes_validez={},
                                usuarios=[],
                                cantidades=[],
                                ultima_fecha='No disponible')
            
    except Exception as e:
        print(f"Error en index: {e}")
        import traceback
        print(traceback.format_exc())
        flash(f'Error al cargar los datos: {str(e)}')
        return render_template('index.html',
                             ultima_fecha='Error al cargar fecha')

if __name__ == '__main__':
    app.run(debug=True)
