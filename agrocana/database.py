"""
============================================================
 MODULO DE BASE DE DATOS - SQLite local
============================================================

Este archivo se encarga UNICAMENTE de hablar con la base de datos.
Lo separamos de main.py (que maneja la interfaz visual) para que
el codigo quede organizado: cada archivo tiene una sola responsabilidad.

SQLite guarda todo en un solo archivo (datos_campo.db) que vive
dentro de la carpeta del proyecto. No necesita instalar ningun
servidor de base de datos, ya viene incluido en Python.
"""

import sqlite3
from datetime import datetime

# Nombre del archivo donde se guardara la base de datos.
# Se creara automaticamente la primera vez que se ejecute la app.
NOMBRE_BASE_DATOS = "datos_campo.db"


def crear_base_datos():
    """
    Crea la tabla 'parcelas' si todavia no existe.
    Esta funcion se debe llamar UNA VEZ al iniciar la app (la llamamos
    en main.py antes de abrir la ventana), asi nos aseguramos de que
    la tabla siempre este lista antes de intentar guardar algo.
    """
    # sqlite3.connect() abre el archivo de base de datos (o lo crea si no existe)
    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)
    cursor = conexion.cursor()

    # "CREATE TABLE IF NOT EXISTS" evita error si la tabla ya existia
    # de una ejecucion anterior de la app.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parcelas (
            fid INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            operador TEXT,
            parcela TEXT,
            variedad TEXT,
            area_ha REAL,
            tipo_corte TEXT,
            geometria TEXT,
            sincronizado INTEGER DEFAULT 0
        )
    """)
    # Explicacion de cada columna:
    # fid            -> identificador unico, se genera solo (AUTOINCREMENT)
    # fecha          -> fecha y hora de captura, como texto (ej: "2026-07-14 10:32")
    # operador       -> nombre del operador que capturo el dato
    # parcela        -> codigo de la parcela (ej: C01P1Z27)
    # variedad       -> variedad de cana sembrada
    # area_ha        -> area en hectareas (por ahora puede quedar en None/NULL,
    #                   en la Fase 3 se llenara automatico al dibujar el poligono)
    # geometria      -> coordenadas del poligono en formato texto (GeoJSON),
    #                   la llenaremos en la Fase 3. Por ahora queda vacia.
    # sincronizado   -> 0 = todavia no se ha subido al servidor, 1 = ya se subio.
    #                   Esto lo usaremos en la Fase de sincronizacion con el portal web.

    conexion.commit()  # guarda los cambios en el archivo
    conexion.close()   # cierra la conexion (buena practica, libera el archivo)


def obtener_fecha_actual():
    """
    Devuelve la fecha y hora ACTUAL como texto, con el formato
    "YYYY-MM-DD HH:MM:SS" (facil de ordenar y de leer despues en el portal web).

    Esta funcion la usa main.py para PRELLENAR el campo de fecha en el
    formulario, apenas se abre. El operador luego puede editar ese texto
    si necesita corregir la fecha/hora antes de guardar.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def guardar_parcela(fecha, operador, parcela, variedad, tipo_corte, area_ha=None, geometria=None):
    """
    Guarda un nuevo registro de parcela en la base de datos.

    Parametros:
        fecha (str): fecha/hora del registro. Se prellena automatico en el
                     formulario (ver obtener_fecha_actual), pero el operador
                     puede editarla antes de guardar, por eso llega aqui
                     como parametro en vez de generarse dentro de esta funcion.
        operador (str): nombre del operador seleccionado en el formulario
        parcela (str): codigo de la parcela seleccionado en el formulario
        variedad (str): variedad de cana seleccionada
        tipo_corte (str): "Manual" o "Mecanizada"
        area_ha (float, opcional): area en hectareas. None por ahora (Fase 2),
                                    se llenara en la Fase 3.
        geometria (str, opcional): coordenadas del poligono en texto (GeoJSON).
                                    None por ahora, se llenara en la Fase 3.

    Retorna:
        El fid (numero de identificador) del registro recien creado.
    """
    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)
    cursor = conexion.cursor()

    # Usamos "?" como marcadores de posicion (en vez de meter las variables
    # directo en el texto del SQL) para evitar errores y problemas de seguridad
    # (esto se llama "consulta parametrizada", es la forma correcta de hacerlo).
    cursor.execute("""
        INSERT INTO parcelas (fecha, operador, parcela, variedad, area_ha, tipo_corte, geometria)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (fecha, operador, parcela, variedad, area_ha, tipo_corte, geometria))

    conexion.commit()

    # cursor.lastrowid nos da el fid que SQLite acaba de asignar automaticamente
    fid_generado = cursor.lastrowid

    conexion.close()
    return fid_generado


def obtener_todas_las_parcelas():
    """
    Devuelve una lista con todos los registros guardados hasta ahora.
    La usaremos mas adelante (y tambien nos sirve ahora para verificar
    que todo se este guardando bien).
    """
    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM parcelas ORDER BY fid DESC")
    filas = cursor.fetchall()
    conexion.close()
    return filas
