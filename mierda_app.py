from flask import Flask, render_template, request
from datetime import datetime
import pandas as pd
import re

app = Flask(__name__)

def obtener_ultima_fecha():
    try:
        with open('mierda_chat.txt', 'r', encoding='utf-8') as file:
            mensajes = [m for m in file.readlines() if m.strip()]
            
        ultima_fecha = None
        for mensaje in reversed(mensajes):
            fecha_match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2})', mensaje)
            if fecha_match:
                fecha_str = fecha_match.group(1)
                partes_fecha = fecha_str.split('/')
                partes_fecha[2] = '20' + partes_fecha[2]
                ultima_fecha = '/'.join(partes_fecha)
                break
                
        return ultima_fecha if ultima_fecha else "13/1/2025"
    except Exception as e:
        print(f"Error al leer el archivo: {str(e)}")
        return "13/1/2025"

def procesar_mensajes(fecha_inicio, fecha_fin):
    try:
        with open('mierda_chat.txt', 'r', encoding='utf-8') as file:
            mensajes = [m for m in file.readlines() if m.strip()]
    except Exception as e:
        print(f"Error al leer el archivo: {str(e)}")
        return pd.DataFrame(), []
    
    conteo = {}
    todos_mensajes = []
    formato_fecha = "%d/%m/%y"
    fecha_inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y")
    fecha_fin = datetime.strptime(fecha_fin, "%d/%m/%Y")
    
    for mensaje in mensajes:
        try:
            partes = mensaje.split('] ')
            if len(partes) != 2:
                continue
                
            fecha_match = re.search(r'\[(\d{1,2}/\d{1,2}/\d{2})', mensaje)
            if not fecha_match:
                continue
                
            fecha_str = fecha_match.group(1)
            fecha_mensaje = datetime.strptime(fecha_str, formato_fecha)
            
            if fecha_inicio <= fecha_mensaje <= fecha_fin:
                info = partes[1].split(': ', 1)
                if len(info) != 2:
                    continue
                    
                usuario, contenido = info
                contenido = contenido.strip()
                
                if usuario == "💩":
                    continue
                    
                if contenido == "💩":
                    if usuario in conteo:
                        conteo[usuario] += 1
                    else:
                        conteo[usuario] = 1
                    todos_mensajes.append({
                        'fecha': fecha_str,
                        'usuario': usuario,
                        'mensaje': contenido,
                        'valido': True
                    })
                else:
                    todos_mensajes.append({
                        'fecha': fecha_str,
                        'usuario': usuario,
                        'mensaje': contenido,
                        'valido': False
                    })
                        
        except Exception as e:
            continue
    
    if conteo:
        df = pd.DataFrame(list(conteo.items()), columns=['Usuario', 'Cantidad'])
        df = df.sort_values(by='Cantidad', ascending=False)
        df = df[df['Usuario'].notna()]
        df.index = range(1, len(df) + 1)
        df.index.name = '#'
    else:
        df = pd.DataFrame(columns=['Usuario', 'Cantidad'])
    
    return df, todos_mensajes

@app.route('/', methods=['GET', 'POST'])
def index():
    fecha_inicio = "24/12/2024"
    fecha_fin = obtener_ultima_fecha()
    
    # Procesar datos automáticamente
    df, todos_mensajes = procesar_mensajes(fecha_inicio, fecha_fin)
    
    # Calcular días
    fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
    fecha_fin_dt = datetime.strptime(fecha_fin, "%d/%m/%Y")
    dias = (fecha_fin_dt - fecha_inicio_dt).days + 1
    
    # Agregar columna de promedio
    if not df.empty:
        df['Promedio Diario'] = round(df['Cantidad'] / dias, 2)
    
    # Renombrar columna Usuario a Participante
    if not df.empty:
        df = df.rename(columns={'Usuario': 'Participante'})
    
    total_mierdas = int(df['Cantidad'].sum()) if not df.empty else 0
    num_participantes = len(df) if not df.empty else 1
    promedio = round(total_mierdas / (dias * num_participantes), 2)
    
    # Obtener los cagadores supremos (máximos)
    max_cantidad = df['Cantidad'].max() if not df.empty else 0
    cagadores_supremos = df[df['Cantidad'] == max_cantidad]['Participante'].tolist() if not df.empty else ["N/A"]
    
    # Obtener los estreñidos (mínimos)
    min_cantidad = df['Cantidad'].min() if not df.empty else 0
    estrenidos = df[df['Cantidad'] == min_cantidad]['Participante'].tolist() if not df.empty else ["N/A"]
    
    stats = {
        'total_mierdas': total_mierdas,
        'dias': dias,
        'promedio': promedio,
        'cagadores_supremos': cagadores_supremos,
        'cantidad_suprema': int(max_cantidad),
        'estrenidos': estrenidos,
        'cantidad_minima': int(min_cantidad)
    }
    
    return render_template('index.html', 
                        tabla=df.to_html(classes='data', 
                                       border=1,
                                       justify='center',
                                       index=True,
                                       index_names=False),
                        stats=stats,
                        todos_mensajes=todos_mensajes,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin,
                        usuarios=df['Participante'].tolist() if not df.empty else [],
                        cantidades=df['Cantidad'].tolist() if not df.empty else [])

if __name__ == '__main__':
    app.run(debug=True)
