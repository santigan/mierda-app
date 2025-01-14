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
            
            # Calcular cantidad de la última semana
            ultima_semana = {}
            ultima_fecha = None
            
            # Encontrar la fecha más reciente
            for mensaje in reversed(todos_mensajes):
                if mensajes_validez.get(mensaje, False):
                    match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2})', mensaje)
                    if match:
                        ultima_fecha = datetime.strptime(match.group(1), '%d/%m/%y')
                        break
            
            if ultima_fecha:
                # Calcular inicio de la última semana
                inicio_ultima_semana = ultima_fecha - timedelta(days=7)
                
                # Contar mensajes de la última semana
                for mensaje in todos_mensajes:
                    if mensajes_validez.get(mensaje, False):
                        match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2}).*?\]\s*(.*?):\s*💩', mensaje)
                        if match:
                            fecha = datetime.strptime(match.group(1), '%d/%m/%y')
                            usuario = match.group(2).strip()
                            
                            if fecha >= inicio_ultima_semana:
                                ultima_semana[usuario] = ultima_semana.get(usuario, 0) + 1
            
            # Agregar columna de última semana al DataFrame
            df['Ultima Semana'] = df['Usuario'].apply(lambda x: f"+{ultima_semana.get(x, 0)}")
            
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
                        <th>Última Semana</th>
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
                        <td class="ultima-semana">{row['Ultima Semana']}</td>
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

def procesar_datos_evolucion(mensajes, mensajes_validez):
    # Crear diccionario para almacenar datos por usuario y fecha
    datos_diarios = {}
    datos_semanales = {}
    
    # Encontrar la primera y última fecha con mensajes
    primera_fecha = None
    ultima_fecha = None
    
    for mensaje in mensajes:
        if mensajes_validez.get(mensaje, False):  # Solo mensajes válidos
            match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2}),\s*\d{1,2}:\d{2}:\d{2}\]\s*(.*?):\s*💩', mensaje)
            if match:
                fecha_str = match.group(1)
                usuario = match.group(2).strip()
                
                # Convertir fecha
                fecha = datetime.strptime(fecha_str, '%d/%m/%y')
                
                # Actualizar primera y última fecha
                if primera_fecha is None or fecha < primera_fecha:
                    primera_fecha = fecha
                if ultima_fecha is None or fecha > ultima_fecha:
                    ultima_fecha = fecha
                
                semana = fecha.strftime('%Y-%V')  # Año-NumeroSemana
                
                # Inicializar estructuras si no existen
                if usuario not in datos_diarios:
                    datos_diarios[usuario] = {}
                if usuario not in datos_semanales:
                    datos_semanales[usuario] = {}
                
                # Incrementar contadores
                datos_diarios[usuario][fecha.strftime('%Y-%m-%d')] = datos_diarios[usuario].get(fecha.strftime('%Y-%m-%d'), 0) + 1
                datos_semanales[usuario][semana] = datos_semanales[usuario].get(semana, 0) + 1
    
    # Asegurarse de que todas las fechas entre la primera y última estén incluidas
    fechas_completas = []
    fecha_actual = primera_fecha
    while fecha_actual <= ultima_fecha:
        fechas_completas.append(fecha_actual.strftime('%Y-%m-%d'))
        fecha_actual += timedelta(days=1)
    
    # Convertir a formato acumulado con todas las fechas
    datos_acumulados_diarios = {}
    datos_acumulados_semanales = {}
    
    for usuario in datos_diarios:
        datos_acumulados_diarios[usuario] = []
        acumulado = 0
        for fecha in fechas_completas:
            acumulado += datos_diarios[usuario].get(fecha, 0)
            datos_acumulados_diarios[usuario].append({
                'fecha': fecha,
                'cantidad': acumulado
            })
    
    # Procesar semanas solo entre la primera y última fecha real
    semanas_completas = []
    semana_actual = primera_fecha
    while semana_actual <= ultima_fecha:
        semanas_completas.append(semana_actual.strftime('%Y-%V'))
        semana_actual += timedelta(days=7)
    
    for usuario in datos_semanales:
        datos_acumulados_semanales[usuario] = []
        acumulado = 0
        for semana in semanas_completas:
            acumulado += datos_semanales[usuario].get(semana, 0)
            datos_acumulados_semanales[usuario].append({
                'semana': semana,
                'cantidad': acumulado
            })
    
    return datos_acumulados_diarios, datos_acumulados_semanales

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
                    match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}:\d{2})\]', mensaje)
                    if match:
                        fecha_str = match.group(1)
                        try:
                            fecha = datetime.strptime(fecha_str, '%d/%m/%y, %H:%M:%S')
                            ultima_fecha = fecha.strftime('%d/%m/%Y %H:%M')
                            break
                        except ValueError:
                            continue

            # Crear el diccionario de stats
            stats_data = {
                'total_mierdas': stats['total_mierdas'],
                'dias': stats['dias'],
                'promedio': stats['promedio'],
                'cagadores_supremos': df.iloc[0]['Usuario'],
                'cantidad_suprema': int(df.iloc[0]['Cantidad']),
                'estrenidos': df.iloc[-1]['Usuario'],
                'cantidad_minima': int(df.iloc[-1]['Cantidad'])
            }

            # Procesar datos para los gráficos de evolución
            datos_diarios, datos_semanales = procesar_datos_evolucion(
                stats['mensajes'], 
                stats.get('mensajes_validez', {})
            )
            
            return render_template('index.html',
                                stats=stats_data,
                                tabla=stats.get('tabla_html', ''),
                                todos_mensajes=stats['mensajes'],
                                mensajes_validez=stats.get('mensajes_validez', {}),
                                usuarios=df['Usuario'].tolist(),
                                cantidades=df['Cantidad'].tolist(),
                                ultima_fecha=ultima_fecha or 'No disponible',
                                datos_evolucion_diaria=datos_diarios,
                                datos_evolucion_semanal=datos_semanales)
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
                             stats=None,
                             tabla=None,
                             todos_mensajes=None,
                             mensajes_validez={},
                             usuarios=[],
                             cantidades=[],
                             ultima_fecha='Error al cargar fecha')

if __name__ == '__main__':
    app.run(debug=True)
