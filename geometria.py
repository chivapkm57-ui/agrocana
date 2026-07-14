"""
============================================================
 MODULO DE GEOMETRIA
============================================================
Este archivo se encarga de la parte matematica de los poligonos:
1. Calcular el area en hectareas a partir de una lista de vertices (lat, lon).
2. Convertir esa lista de vertices a formato GeoJSON (texto), que es el
   formato estandar que despues podremos abrir en QGIS.

Por que no calculamos el area directamente con lat/lon?
Porque los grados de latitud/longitud NO tienen un tamano fijo en metros
(varian segun donde esten en el planeta). Para calcular area correctamente
en metros cuadrados, primero convertimos cada punto a un sistema de
coordenadas UTM (que si se mide en metros reales), y ahi si calculamos
el area con la formula del poligono (formula del "shoelace" / cordones).
"""

import json
import utm


def calcular_area_ha(vertices):
    """
    Calcula el area de un poligono en HECTAREAS.

    Parametros:
        vertices: lista de tuplas (lat, lon), en el orden en que se
                  fueron marcando los vertices del poligono.

    Retorna:
        area en hectareas (float). Si hay menos de 3 vertices, retorna 0.0
        (no se puede formar un poligono con menos de 3 puntos).
    """
    if len(vertices) < 3:
        return 0.0

    # Convertimos cada punto (lat, lon) a coordenadas UTM (easting, northing),
    # que si estan en metros. utm.from_latlon() calcula automaticamente
    # la zona UTM correcta segun donde este el punto.
    puntos_metros = []
    for lat, lon in vertices:
        easting, northing, zona_numero, zona_letra = utm.from_latlon(lat, lon)
        puntos_metros.append((easting, northing))

    # Formula del poligono (shoelace formula): calcula el area de cualquier
    # poligono a partir de las coordenadas (x, y) de sus vertices en orden.
    n = len(puntos_metros)
    suma = 0.0
    for i in range(n):
        x1, y1 = puntos_metros[i]
        x2, y2 = puntos_metros[(i + 1) % n]  # el % n hace que el ultimo punto conecte con el primero
        suma += (x1 * y2) - (x2 * y1)

    area_metros_cuadrados = abs(suma) / 2.0

    # 1 hectarea = 10,000 metros cuadrados
    area_hectareas = area_metros_cuadrados / 10000.0

    return area_hectareas


def poligono_a_geojson(vertices):
    """
    Convierte una lista de vertices (lat, lon) a un texto en formato GeoJSON.

    IMPORTANTE: GeoJSON usa el orden [longitud, latitud] (al reves de como
    normalmente lo pensamos), y ademas un poligono debe "cerrarse" repitiendo
    el primer punto al final de la lista. Eso lo hacemos aqui automaticamente.

    Parametros:
        vertices: lista de tuplas (lat, lon)

    Retorna:
        Un string de texto con el poligono en formato GeoJSON, listo para
        guardar en la base de datos y, mas adelante, exportar a QGIS.
    """
    anillo = [[lon, lat] for lat, lon in vertices]  # invertimos a [lon, lat]
    anillo.append(anillo[0])  # cerramos el poligono repitiendo el primer punto

    geojson_diccionario = {
        "type": "Polygon",
        "coordinates": [anillo]
    }

    return json.dumps(geojson_diccionario)
