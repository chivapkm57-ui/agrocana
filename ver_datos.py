"""
============================================================
 SCRIPT DE VERIFICACION - NO es parte de la app
============================================================
Este archivo es solo una herramienta para que TU puedas revisar,
desde la terminal, que datos se han guardado en la base de datos.

Como usarlo:
    python ver_datos.py

Te va a imprimir en pantalla todos los registros guardados hasta ahora.
"""

import database

registros = database.obtener_todas_las_parcelas()

if not registros:
    print("Todavia no hay ningun registro guardado.")
else:
    print(f"Se encontraron {len(registros)} registro(s):\n")
    for fila in registros:
        # Cada 'fila' viene en el mismo orden de las columnas de la tabla:
        # fid, fecha, operador, parcela, variedad, area_ha, tipo_corte, geometria, sincronizado
        fid, fecha, operador, parcela, variedad, area_ha, tipo_corte, geometria, sincronizado = fila
        print(f"FID: {fid}")
        print(f"  Fecha: {fecha}")
        print(f"  Operador: {operador}")
        print(f"  Parcela: {parcela}")
        print(f"  Variedad: {variedad}")
        print(f"  Tipo de Corte: {tipo_corte}")
        print(f"  Area (ha): {area_ha}")
        print(f"  Sincronizado: {'Si' if sincronizado else 'No'}")
        print("-" * 40)
