"""
============================================================
 APP DE CAMPO - TOPOGRAFIA Y CATASTRO AGRICOLA
 FASE 4b: Correcciones de uso real en Android
============================================================

Correcciones de esta fase:
1. Se solicita el permiso de GPS EN TIEMPO DE EJECUCION (obligatorio en
   Android moderno), antes de intentar leer la ubicacion real.
2. La barra de botones se reorganizo en 2 filas para que TODOS los
   botones quepan y sean tocables en una pantalla de celular normal.
3. Las parcelas guardadas ahora quedan visibles en el mapa (un marcador
   por parcela, en su punto central), tanto las nuevas como las que ya
   existian en la base de datos al abrir la app.
4. Mejoras de contraste/tamano para uso tactil real.
"""

from kivy.config import Config
from kivy.utils import platform

# ------------------------------------------------------------------
# SIMULAR TAMAÑO DE CELULAR EN LA PC (solo para pruebas)
# ------------------------------------------------------------------
# Esto hace que la ventana en tu PC tenga las mismas proporciones que
# una pantalla de celular real (ancho angosto, alto largo). Asi puedes
# ver de inmediato si algo se sale de la pantalla (como paso con los
# botones), SIN tener que compilar un APK cada vez para revisarlo.
#
# En el celular real esto no aplica (Android siempre usa pantalla
# completa), por eso solo lo activamos si NO estamos en Android.
if platform != "android":
    Config.set("graphics", "width", "392")   # ancho tipico de celular (en pixeles de ventana)
    Config.set("graphics", "height", "803")  # alto tipico de celular
    Config.set("graphics", "resizable", True)  # puedes agrandar la ventana si necesitas

from kivymd.app import MDApp
from kivy_garden.mapview import MapView, MapMarker, MapMarkerPopup, MapSource, MapLayer
from kivy.graphics import Color, Line, Ellipse
import math
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Rectangle

import database
import geometria

try:
    from plyer import gps
except Exception:
    gps = None

UBICACION_PRUEBA = (8.9824, -79.5199)

OPERADORES = ["Gregorio Atencio", "Roudy Montenegro"]
PARCELAS = ["C01P1Z27", "C02P1Z27", "C02P2Z27"]
VARIEDADES = ["B82-333", "CR74-250"]
TIPOS_CORTE = ["Manual", "Mecanizada"]


class EtiquetaConFondo(BoxLayout):
    """
    Un BoxLayout con un fondo de color solido detras del texto.
    Lo usamos para que la etiqueta de "Vertices: X" se pueda LEER bien
    sobre el mapa satelital (que a veces es muy claro y el texto blanco
    se pierde de vista sin un fondo oscuro detras).
    """
    def __init__(self, texto_inicial="", **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.55)  # negro semi-transparente
            self.rectangulo_fondo = Rectangle(pos=self.pos, size=self.size)
        # Cuando el widget cambia de tamano o posicion, actualizamos el fondo
        self.bind(pos=self._actualizar_fondo, size=self._actualizar_fondo)

        self.etiqueta = Label(text=texto_inicial, bold=True, color=(1, 1, 1, 1))
        self.add_widget(self.etiqueta)

    def _actualizar_fondo(self, *args):
        self.rectangulo_fondo.pos = self.pos
        self.rectangulo_fondo.size = self.size

    @property
    def text(self):
        return self.etiqueta.text

    @text.setter
    def text(self, valor):
        self.etiqueta.text = valor


class CapaPoligonos(MapLayer):
    """
    Capa personalizada que se agrega sobre el mapa para dibujar el
    CONTORNO (la forma real, con lineas) de cada parcela guardada.

    IMPORTANTE (correccion de un bug): la version anterior usaba una
    "matriz de cache" (pensada para poligonos rellenos muy pesados de
    calcular) que desalineaba las lineas cada vez que cambiabas el zoom,
    haciendo que los poligonos chicos parecieran "desaparecer". Ahora,
    en cada reposicionamiento, volvemos a calcular la posicion de cada
    vertice usando el zoom ACTUAL directamente, sin ningun cache. Es un
    poco mas de calculo, pero para lineas (a diferencia de rellenos) es
    barato y evita por completo el problema de desalineacion.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.poligonos = []  # lista de poligonos, cada uno es una lista de (lat, lon)

    def agregar_poligono(self, vertices):
        """ Agrega un poligono (lista de vertices lat/lon) para dibujar su contorno. """
        self.poligonos.append(vertices)
        self.redibujar()

    def reposition(self):
        """
        Kivy_garden.mapview llama a este metodo automaticamente cada vez
        que el mapa se mueve, se hace zoom, o cambia de tamano. Simplemente
        volvemos a dibujar todo desde cero con la posicion/zoom actuales.
        """
        self.redibujar()

    def _lonlat_a_xy(self, vertices):
        """ Convierte una lista de (lat, lon) a posiciones de pixel (x, y) en pantalla. """
        vista = self.parent
        zoom = vista.zoom
        puntos = []
        for lat, lon in vertices:
            punto = vista.get_window_xy_from(lat, lon, zoom)
            punto = (punto[0] - vista.delta_x, punto[1] - vista.delta_y)
            punto = vista._scatter.to_local(*punto)
            puntos.append(punto)
        return puntos

    def redibujar(self):
        """ Vuelve a dibujar TODOS los contornos guardados hasta ahora. """
        if self.parent is None:
            return

        self.canvas.clear()
        with self.canvas:
            Color(1, 0.25, 0.1, 0.9)  # color naranja-rojo, bien visible sobre el satelital
            for vertices in self.poligonos:
                if len(vertices) < 2:
                    continue
                puntos_xy = self._lonlat_a_xy(vertices)
                puntos_xy.append(puntos_xy[0])  # cerramos el contorno (vuelve al primer punto)
                puntos_planos = [coordenada for punto in puntos_xy for coordenada in punto]
                Line(points=puntos_planos, width=2)


class CapaMiUbicacion(MapLayer):
    """
    Capa que muestra la posicion GPS ACTUAL como un punto azul con un
    circulo de margen de error alrededor (igual que Google Maps o QField),
    en vez de un pin fijo. Se actualiza en tiempo real con cada lectura
    del GPS del telefono.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lat = None
        self.lon = None
        self.precision_metros = 15  # margen de error tipico de un GPS de celular

    def actualizar_posicion(self, lat, lon, precision_metros=None):
        """ Se llama cada vez que llega una nueva lectura de GPS (o al iniciar). """
        self.lat = lat
        self.lon = lon
        if precision_metros:
            self.precision_metros = precision_metros
        self.redibujar()

    def reposition(self):
        self.redibujar()

    def redibujar(self):
        if self.parent is None or self.lat is None:
            return

        vista = self.parent
        zoom = vista.zoom

        punto = vista.get_window_xy_from(self.lat, self.lon, zoom)
        punto = (punto[0] - vista.delta_x, punto[1] - vista.delta_y)
        x, y = vista._scatter.to_local(*punto)

        # Formula estandar (la misma que usan Google Maps/OpenStreetMap)
        # para saber cuantos metros representa un pixel, segun la latitud
        # actual y el nivel de zoom. Con esto convertimos el margen de
        # error (en metros reales) a un radio en pixeles en pantalla.
        metros_por_pixel = 156543.03392 * math.cos(math.radians(self.lat)) / (2 ** zoom)
        radio_pixeles = max(self.precision_metros / metros_por_pixel, 8)

        self.canvas.clear()
        with self.canvas:
            # Circulo de margen de error (translucido)
            Color(0.15, 0.45, 0.95, 0.25)
            Ellipse(pos=(x - radio_pixeles, y - radio_pixeles),
                    size=(radio_pixeles * 2, radio_pixeles * 2))

            # Borde del circulo de margen de error
            Color(0.15, 0.45, 0.95, 0.6)
            Line(circle=(x, y, radio_pixeles), width=1.5)

            # Punto central solido (mi posicion real)
            Color(0.15, 0.45, 0.95, 1)
            Ellipse(pos=(x - 9, y - 9), size=(18, 18))
            Color(1, 1, 1, 1)
            Line(circle=(x, y, 9), width=2)


class MapaTactil(MapView):
    """ MapView que agrega un vertice cuando se toca el mapa en Modo Manual. """

    def __init__(self, pantalla, **kwargs):
        super().__init__(**kwargs)
        self.pantalla = pantalla

    def on_touch_down(self, touch):
        es_scroll_del_mouse = getattr(touch, "button", "") in ("scrollup", "scrolldown")

        if (self.pantalla.modo_dibujo == "manual"
                and self.collide_point(*touch.pos)
                and not es_scroll_del_mouse):
            coordenada = self.get_latlon_at(touch.x, touch.y)
            self.pantalla.agregar_vertice(coordenada.lat, coordenada.lon)
            return True

        return super().on_touch_down(touch)


class PantallaMapa(Screen):
    """ Pantalla principal: mapa satelital + herramientas de dibujo + GPS. """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.modo_dibujo = None
        self.vertices = []               # vertices del poligono EN PROGRESO
        self.marcadores_vertices = []    # pines del poligono EN PROGRESO
        self.marcadores_guardados = []   # pines de parcelas YA GUARDADAS (permanentes)

        contenedor = FloatLayout()

        fuente_satelital = MapSource(
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            max_zoom=18,
            attribution="Esri Satelital"
        )
        self.mapa = MapaTactil(
            pantalla=self,
            lat=UBICACION_PRUEBA[0],
            lon=UBICACION_PRUEBA[1],
            zoom=15,
            map_source=fuente_satelital
        )
        contenedor.add_widget(self.mapa)

        # Capa que muestra "mi ubicacion" como un punto azul con margen de
        # error (en vez de un pin fijo), se actualiza en tiempo real con el GPS.
        self.capa_mi_ubicacion = CapaMiUbicacion()
        self.mapa.add_layer(self.capa_mi_ubicacion)
        self.capa_mi_ubicacion.actualizar_posicion(UBICACION_PRUEBA[0], UBICACION_PRUEBA[1])

        # Capa que dibuja el CONTORNO (forma real) de cada parcela guardada.
        self.capa_poligonos = CapaPoligonos()
        self.mapa.add_layer(self.capa_poligonos)

        # Mostramos en el mapa las parcelas que YA existian en la base de
        # datos (de sesiones anteriores), para que el operador vea de una
        # vez que zonas ya fueron levantadas.
        self.cargar_parcelas_guardadas()

        # Pedimos permiso de GPS (obligatorio en Android moderno) y,
        # una vez concedido, arrancamos la lectura real de ubicacion.
        self.solicitar_permisos_y_iniciar_gps()

        # ----------------------------------------------------------
        # Etiqueta de DIAGNOSTICO de GPS (arriba, chiquita) - para poder
        # ver en pantalla que esta pasando con el GPS sin necesitar
        # herramientas de programador conectadas al telefono.
        # ----------------------------------------------------------
        self.etiqueta_gps = EtiquetaConFondo(
            texto_inicial="GPS: iniciando...",
            pos_hint={"x": 0.02, "top": 0.99},
            size_hint=(0.75, 0.05)
        )
        contenedor.add_widget(self.etiqueta_gps)

        # ----------------------------------------------------------
        # Boton "Mi Ubicacion"
        # ----------------------------------------------------------
        boton_ubicacion = MDIconButton(
            icon="crosshairs-gps",
            pos_hint={"right": 0.97, "y": 0.34},
            md_bg_color=(1, 1, 1, 0.9),
            theme_icon_color="Custom",
            icon_color=(0.1, 0.4, 0.9, 1),
            on_release=self.centrar_en_mi_ubicacion
        )
        contenedor.add_widget(boton_ubicacion)

        # ----------------------------------------------------------
        # Etiqueta de estado (con fondo, para que se lea bien)
        # ----------------------------------------------------------
        self.etiqueta_estado = EtiquetaConFondo(
            texto_inicial="Vertices: 0",
            pos_hint={"center_x": 0.5, "y": 0.255},
            size_hint=(0.6, 0.05)
        )
        contenedor.add_widget(self.etiqueta_estado)

        # ----------------------------------------------------------
        # Barra de herramientas EN 2 FILAS (para que quepa en celular)
        # ----------------------------------------------------------
        barra = BoxLayout(
            orientation="vertical",
            size_hint=(1, 0.25),
            pos_hint={"x": 0, "y": 0},
            spacing=3,
            padding=3
        )

        fila_1 = BoxLayout(orientation="horizontal", spacing=3, size_hint=(1, 0.5))
        fila_2 = BoxLayout(orientation="horizontal", spacing=3, size_hint=(1, 0.5))

        self.boton_manual = MDRaisedButton(
            text="Manual", size_hint=(1, 1), font_size=19,
            on_release=self.activar_modo_manual
        )
        self.boton_recorrido = MDRaisedButton(
            text="Recorrido", size_hint=(1, 1), font_size=19,
            on_release=self.activar_modo_recorrido
        )
        boton_agregar_aqui = MDRaisedButton(
            text="+ Vertice", size_hint=(1, 1), font_size=19,
            on_release=self.agregar_vertice_en_mi_ubicacion
        )

        boton_deshacer = MDRaisedButton(
            text="Deshacer", size_hint=(1, 1), font_size=19,
            md_bg_color=(0.9, 0.6, 0.1, 1),
            on_release=self.deshacer_vertice
        )
        boton_cancelar = MDRaisedButton(
            text="Cancelar", size_hint=(1, 1), font_size=19,
            md_bg_color=(0.6, 0.6, 0.6, 1),
            on_release=self.cancelar_dibujo
        )
        boton_cerrar = MDRaisedButton(
            text="Cerrar", size_hint=(1, 1), font_size=19,
            md_bg_color=(0.1, 0.7, 0.3, 1),
            on_release=self.cerrar_poligono
        )

        fila_1.add_widget(self.boton_manual)
        fila_1.add_widget(self.boton_recorrido)
        fila_1.add_widget(boton_agregar_aqui)

        fila_2.add_widget(boton_deshacer)
        fila_2.add_widget(boton_cancelar)
        fila_2.add_widget(boton_cerrar)

        barra.add_widget(fila_1)
        barra.add_widget(fila_2)

        contenedor.add_widget(barra)

        self.add_widget(contenedor)

        self.actualizar_apariencia_botones()

    # ----------------------------------------------------------------
    # PARCELAS GUARDADAS (persistentes en el mapa)
    # ----------------------------------------------------------------
    def cargar_parcelas_guardadas(self):
        """
        Lee TODAS las parcelas ya guardadas en la base de datos (de esta
        sesion o de sesiones anteriores) y pone un marcador en el mapa
        por cada una que tenga geometria (poligono) guardado.
        """
        registros = database.obtener_todas_las_parcelas()
        for fila in registros:
            fid, fecha, operador, parcela, variedad, area_ha, tipo_corte, geometria_texto, sincronizado = fila
            if geometria_texto:
                self.agregar_marcador_guardado(geometria_texto, parcela, area_ha)

    def agregar_marcador_guardado(self, geojson_texto, parcela, area_ha):
        """
        Agrega un marcador PERMANENTE en el mapa representando una parcela
        ya guardada (a diferencia de los marcadores de vertices "en progreso",
        que se borran al cancelar/guardar). Al tocar el marcador, muestra
        un pequeno globo con el nombre de la parcela y su area.
        """
        vertices = geometria.geojson_a_vertices(geojson_texto)

        # Dibujamos el CONTORNO real del poligono en el mapa.
        self.capa_poligonos.agregar_poligono(vertices)

        centro = geometria.calcular_centroide(vertices)
        if centro is None:
            return

        lat_centro, lon_centro = centro

        marcador = MapMarkerPopup(lat=lat_centro, lon=lon_centro)
        area_texto = f"{area_ha:.2f} ha" if area_ha else ""
        etiqueta_popup = Label(
            text=f"{parcela}\n{area_texto}",
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(120, 50)
        )
        marcador.add_widget(etiqueta_popup)

        self.mapa.add_marker(marcador)
        self.marcadores_guardados.append(marcador)

    # ----------------------------------------------------------------
    # GPS REAL (Android) con permiso en tiempo de ejecucion
    # ----------------------------------------------------------------
    def solicitar_permisos_y_iniciar_gps(self):
        """
        En Android moderno, declarar el permiso en buildozer.spec NO alcanza:
        hay que pedirselo al usuario en tiempo de ejecucion (un dialogo del
        sistema). Esta funcion hace esa solicitud, y SOLO si el usuario
        acepta, arrancamos la lectura real del GPS.
        """
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission

                def al_responder(permisos, resultados):
                    if all(resultados):
                        print("Permiso de ubicacion concedido.")
                        self.etiqueta_gps.text = "GPS: permiso OK, iniciando..."
                        self.iniciar_gps()
                    else:
                        print("Permiso de ubicacion DENEGADO por el usuario. "
                              "El GPS no funcionara hasta que se conceda "
                              "desde Ajustes > Aplicaciones > Permisos.")
                        self.etiqueta_gps.text = "GPS: PERMISO DENEGADO"

                request_permissions(
                    [Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION],
                    al_responder
                )
            except Exception as error:
                print(f"No se pudo solicitar permisos de Android: {error}")
        else:
            # En PC no existe este sistema de permisos, seguimos con la
            # ubicacion de prueba (iniciar_gps() se encarga de avisarlo).
            self.iniciar_gps()

    def iniciar_gps(self):
        if platform == "android" and gps is not None:
            try:
                gps.configure(
                    on_location=self.on_gps_ubicacion,
                    on_status=self.on_gps_estado
                )
                gps.start(minTime=1000, minDistance=1)
                print("GPS iniciado correctamente (Android).")
                self.etiqueta_gps.text = "GPS: esperando primera senal..."
            except Exception as error:
                print(f"No se pudo iniciar el GPS: {error}")
                self.etiqueta_gps.text = f"GPS: error al iniciar ({error})"
        else:
            print("GPS real no disponible en este dispositivo (PC de pruebas). "
                  "Usando la ubicacion de prueba fija.")
            self.etiqueta_gps.text = "GPS: no disponible (modo PC de prueba)"

    def on_gps_ubicacion(self, **datos_gps):
        lat = datos_gps.get("lat")
        lon = datos_gps.get("lon")
        precision = datos_gps.get("accuracy")  # margen de error en metros, si el telefono lo entrega
        if lat is not None and lon is not None:
            self.capa_mi_ubicacion.actualizar_posicion(lat, lon, precision)
            texto_precision = f" (+/-{precision:.0f}m)" if precision else ""
            self.etiqueta_gps.text = f"GPS: {lat:.5f}, {lon:.5f}{texto_precision}"

    def on_gps_estado(self, stype, status):
        print(f"Estado del GPS -> tipo: {stype}, status: {status}")
        self.etiqueta_gps.text = f"GPS estado: {status}"

    def centrar_en_mi_ubicacion(self, instancia_boton):
        if self.capa_mi_ubicacion.lat is None:
            return
        self.mapa.center_on(self.capa_mi_ubicacion.lat, self.capa_mi_ubicacion.lon)

    # ----------------------------------------------------------------
    # MODOS DE DIBUJO
    # ----------------------------------------------------------------
    def activar_modo_manual(self, instancia_boton):
        self.modo_dibujo = "manual"
        self.actualizar_apariencia_botones()

    def activar_modo_recorrido(self, instancia_boton):
        self.modo_dibujo = "recorrido"
        self.actualizar_apariencia_botones()

    def actualizar_apariencia_botones(self):
        color_activo = (0.1, 0.7, 0.3, 1)
        color_inactivo = (0.5, 0.5, 0.5, 1)
        self.boton_manual.md_bg_color = (
            color_activo if self.modo_dibujo == "manual" else color_inactivo
        )
        self.boton_recorrido.md_bg_color = (
            color_activo if self.modo_dibujo == "recorrido" else color_inactivo
        )

    # ----------------------------------------------------------------
    # MANEJO DE VERTICES (poligono EN PROGRESO)
    # ----------------------------------------------------------------
    def agregar_vertice_en_mi_ubicacion(self, instancia_boton):
        if self.capa_mi_ubicacion.lat is None:
            self.etiqueta_estado.text = "Ubicacion aun no disponible"
            return
        lat = self.capa_mi_ubicacion.lat
        lon = self.capa_mi_ubicacion.lon
        self.agregar_vertice(lat, lon)

    def agregar_vertice(self, lat, lon):
        self.vertices.append((lat, lon))
        marcador = MapMarker(lat=lat, lon=lon)
        self.mapa.add_marker(marcador)
        self.marcadores_vertices.append(marcador)
        self.etiqueta_estado.text = f"Vertices: {len(self.vertices)}"

    def deshacer_vertice(self, instancia_boton):
        if not self.vertices:
            return
        self.vertices.pop()
        ultimo_marcador = self.marcadores_vertices.pop()
        self.mapa.remove_marker(ultimo_marcador)
        self.etiqueta_estado.text = f"Vertices: {len(self.vertices)}"

    def cancelar_dibujo(self, instancia_boton):
        """ Borra SOLO el poligono en progreso, NO toca las parcelas ya guardadas. """
        for marcador in self.marcadores_vertices:
            self.mapa.remove_marker(marcador)
        self.vertices = []
        self.marcadores_vertices = []
        self.modo_dibujo = None
        self.actualizar_apariencia_botones()
        self.etiqueta_estado.text = "Vertices: 0"

    def cerrar_poligono(self, instancia_boton):
        if len(self.vertices) < 3:
            self.etiqueta_estado.text = "Minimo 3 vertices"
            return

        area_ha = geometria.calcular_area_ha(self.vertices)
        geojson_texto = geometria.poligono_a_geojson(self.vertices)

        app = MDApp.get_running_app()
        app.poligono_pendiente = {
            "area_ha": area_ha,
            "geometria": geojson_texto
        }

        self.manager.current = "formulario"

    def reiniciar_dibujo(self):
        """ Llamado desde el formulario tras guardar/cancelar un registro. """
        self.cancelar_dibujo(None)


class PantallaFormulario(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.area_actual = None
        self.geometria_actual = None

        layout = BoxLayout(orientation="vertical", padding=20, spacing=12)

        layout.add_widget(Label(
            text="Nueva Parcela", font_size=24, size_hint=(1, 0.12), color=(0, 0, 0, 1)
        ))

        layout.add_widget(Label(text="Fecha", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.campo_fecha = TextInput(
            text=database.obtener_fecha_actual(), multiline=False, size_hint=(1, 0.1)
        )
        layout.add_widget(self.campo_fecha)

        layout.add_widget(Label(text="Operador", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_operador = Spinner(text=OPERADORES[0], values=OPERADORES, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_operador)

        layout.add_widget(Label(text="Parcela", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_parcela = Spinner(text=PARCELAS[0], values=PARCELAS, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_parcela)

        layout.add_widget(Label(text="Variedad", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_variedad = Spinner(text=VARIEDADES[0], values=VARIEDADES, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_variedad)

        layout.add_widget(Label(text="Tipo de Corte", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_tipo_corte = Spinner(text=TIPOS_CORTE[0], values=TIPOS_CORTE, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_tipo_corte)

        self.etiqueta_area = Label(
            text="Area (ha): --", size_hint=(1, 0.08),
            color=(0.1, 0.4, 0.9, 1), font_size=16, bold=True
        )
        layout.add_widget(self.etiqueta_area)

        fila_botones = BoxLayout(size_hint=(1, 0.12), spacing=10)
        boton_cancelar = MDRaisedButton(
            text="Cancelar", md_bg_color=(0.6, 0.6, 0.6, 1), on_release=self.cancelar
        )
        boton_guardar = MDRaisedButton(
            text="Guardar", md_bg_color=(0.1, 0.7, 0.3, 1), on_release=self.guardar_datos
        )
        fila_botones.add_widget(boton_cancelar)
        fila_botones.add_widget(boton_guardar)
        layout.add_widget(fila_botones)

        self.mensaje = Label(text="", size_hint=(1, 0.08), color=(0.1, 0.4, 0.9, 1))
        layout.add_widget(self.mensaje)

        self.add_widget(layout)

    def on_pre_enter(self):
        self.campo_fecha.text = database.obtener_fecha_actual()
        self.mensaje.text = ""

        app = MDApp.get_running_app()
        pendiente = getattr(app, "poligono_pendiente", None)

        if pendiente:
            self.area_actual = pendiente["area_ha"]
            self.geometria_actual = pendiente["geometria"]
            self.etiqueta_area.text = f"Area (ha): {self.area_actual:.4f}"
        else:
            self.area_actual = None
            self.geometria_actual = None
            self.etiqueta_area.text = "Area (ha): sin poligono dibujado"

    def cancelar(self, instancia_boton):
        app = MDApp.get_running_app()
        app.poligono_pendiente = None
        self.manager.get_screen("mapa").reiniciar_dibujo()
        self.manager.current = "mapa"

    def guardar_datos(self, instancia_boton):
        fecha = self.campo_fecha.text
        operador = self.spinner_operador.text
        parcela = self.spinner_parcela.text
        variedad = self.spinner_variedad.text
        tipo_corte = self.spinner_tipo_corte.text

        fid_generado = database.guardar_parcela(
            fecha=fecha, operador=operador, parcela=parcela, variedad=variedad,
            tipo_corte=tipo_corte, area_ha=self.area_actual, geometria=self.geometria_actual
        )

        self.mensaje.text = f"Guardado correctamente (FID {fid_generado})"

        pantalla_mapa = self.manager.get_screen("mapa")

        # Si esta parcela tenia poligono, la dejamos marcada PERMANENTEMENTE
        # en el mapa antes de limpiar el dibujo temporal.
        if self.geometria_actual:
            pantalla_mapa.agregar_marcador_guardado(
                self.geometria_actual, parcela, self.area_actual
            )

        app = MDApp.get_running_app()
        app.poligono_pendiente = None
        pantalla_mapa.reiniciar_dibujo()

        self.manager.current = "mapa"


class CampoGISApp(MDApp):
    poligono_pendiente = None

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"

        database.crear_base_datos()

        gestor_pantallas = ScreenManager()
        gestor_pantallas.add_widget(PantallaMapa(name="mapa"))
        gestor_pantallas.add_widget(PantallaFormulario(name="formulario"))

        return gestor_pantallas


if __name__ == "__main__":
    CampoGISApp().run()
