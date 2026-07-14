"""
============================================================
 APP DE CAMPO - TOPOGRAFIA Y CATASTRO AGRICOLA
 FASE 3: Dibujo de poligonos (Modo Manual + Modo Recorrido)
============================================================

Que agregamos en esta fase:
1. Dos modos de dibujo de poligonos:
   - Modo Manual: tocas el mapa y cada toque agrega un vertice.
   - Modo Recorrido: presionas un boton para agregar un vertice en tu
     ubicacion actual (pensado para caminar el perimetro con el celular).
   NOTA: "tu ubicacion actual" por ahora es la UBICACION_PRUEBA fija,
   porque el GPS real se conecta en una fase posterior.
2. Boton "Deshacer" para borrar el ultimo vertice si te equivocas.
3. Boton "Cerrar Poligono": calcula el area en hectareas automaticamente
   y te lleva al formulario con esa area ya lista.
4. Boton "Cancelar": borra todo el dibujo y empieza de cero.
"""

from kivymd.app import MDApp
from kivy_garden.mapview import MapView, MapMarker, MapSource
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen

import database
import geometria

# ------------------------------------------------------------------
# COORDENADA DE PRUEBA (simula "mi ubicacion" hasta conectar GPS real)
# ------------------------------------------------------------------
UBICACION_PRUEBA = (8.9824, -79.5199)

# ------------------------------------------------------------------
# CATALOGOS FIJOS (listas desplegables del formulario)
# ------------------------------------------------------------------
OPERADORES = ["Gregorio Atencio", "Roudy Montenegro"]
PARCELAS = ["C01P1Z27", "C02P1Z27", "C02P2Z27"]
VARIEDADES = ["B82-333", "CR74-250"]
TIPOS_CORTE = ["Manual", "Mecanizada"]


class MapaTactil(MapView):
    """
    Esta clase extiende (hereda de) MapView para poder "escuchar" cuando
    el usuario toca el mapa, y decidir si ese toque debe agregar un
    vertice (si estamos en Modo Manual) o comportarse como un mapa
    normal (mover/zoom), segun el modo activo.
    """

    def __init__(self, pantalla, **kwargs):
        super().__init__(**kwargs)
        # Guardamos una referencia a la pantalla (PantallaMapa) para poder
        # llamar a sus metodos y consultar su estado (self.pantalla.modo_dibujo)
        self.pantalla = pantalla

    def on_touch_down(self, touch):
        # Detectamos si el "toque" en realidad es la rueda del mouse
        # (scroll), que se usa para hacer zoom. Si es asi, dejamos que
        # el mapa haga zoom normalmente, sin agregar un vertice.
        es_scroll_del_mouse = getattr(touch, "button", "") in ("scrollup", "scrolldown")

        if (self.pantalla.modo_dibujo == "manual"
                and self.collide_point(*touch.pos)
                and not es_scroll_del_mouse):
            # Convertimos la posicion del toque en pantalla (x, y) a
            # coordenadas reales de latitud/longitud sobre el mapa.
            coordenada = self.get_latlon_at(touch.x, touch.y)
            self.pantalla.agregar_vertice(coordenada.lat, coordenada.lon)
            return True  # "consumimos" el toque: el mapa NO se movera

        # Si no estamos en modo manual (o fue un scroll), el mapa se
        # comporta como siempre (se puede mover y hacer zoom).
        return super().on_touch_down(touch)


class PantallaMapa(Screen):
    """
    Pantalla principal: mapa satelital + herramientas de dibujo de
    poligonos + boton de ubicacion.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Estado del dibujo actual (se guarda aqui mientras el usuario dibuja)
        self.modo_dibujo = None          # None, "manual" o "recorrido"
        self.vertices = []               # lista de (lat, lon) marcados
        self.marcadores_vertices = []    # lista de los MapMarker mostrados en el mapa

        contenedor = FloatLayout()

        # ----------------------------------------------------------
        # Mapa satelital
        # ----------------------------------------------------------
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

        self.marcador_ubicacion = MapMarker(
            lat=UBICACION_PRUEBA[0],
            lon=UBICACION_PRUEBA[1]
        )
        self.mapa.add_marker(self.marcador_ubicacion)

        # ----------------------------------------------------------
        # Boton "Mi Ubicacion" (arriba de la barra de herramientas)
        # ----------------------------------------------------------
        boton_ubicacion = MDIconButton(
            icon="crosshairs-gps",
            pos_hint={"right": 0.97, "y": 0.22},
            md_bg_color=(1, 1, 1, 0.9),
            theme_icon_color="Custom",
            icon_color=(0.1, 0.4, 0.9, 1),
            on_release=self.centrar_en_mi_ubicacion
        )
        contenedor.add_widget(boton_ubicacion)

        # ----------------------------------------------------------
        # Etiqueta de estado (cuantos vertices llevas, o avisos)
        # ----------------------------------------------------------
        self.etiqueta_estado = Label(
            text="Vertices: 0",
            pos_hint={"center_x": 0.5, "y": 0.155},
            size_hint=(1, 0.05),
            color=(1, 1, 1, 1),
            bold=True
        )
        contenedor.add_widget(self.etiqueta_estado)

        # ----------------------------------------------------------
        # Barra de herramientas de dibujo (fila de botones abajo)
        # ----------------------------------------------------------
        barra = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 0.15),
            pos_hint={"x": 0, "y": 0},
            spacing=4,
            padding=4
        )

        self.boton_manual = MDRaisedButton(
            text="Manual",
            on_release=self.activar_modo_manual
        )
        self.boton_recorrido = MDRaisedButton(
            text="Recorrido",
            on_release=self.activar_modo_recorrido
        )
        boton_agregar_aqui = MDRaisedButton(
            text="+ Vertice",
            on_release=self.agregar_vertice_en_mi_ubicacion
        )
        boton_deshacer = MDRaisedButton(
            text="Deshacer",
            md_bg_color=(0.9, 0.6, 0.1, 1),
            on_release=self.deshacer_vertice
        )
        boton_cancelar = MDRaisedButton(
            text="Cancelar",
            md_bg_color=(0.6, 0.6, 0.6, 1),
            on_release=self.cancelar_dibujo
        )
        boton_cerrar = MDRaisedButton(
            text="Cerrar Poligono",
            md_bg_color=(0.1, 0.7, 0.3, 1),
            on_release=self.cerrar_poligono
        )

        barra.add_widget(self.boton_manual)
        barra.add_widget(self.boton_recorrido)
        barra.add_widget(boton_agregar_aqui)
        barra.add_widget(boton_deshacer)
        barra.add_widget(boton_cancelar)
        barra.add_widget(boton_cerrar)

        contenedor.add_widget(barra)

        self.add_widget(contenedor)

        # Pintamos los botones de modo con su apariencia inicial (ninguno activo)
        self.actualizar_apariencia_botones()

    # ----------------------------------------------------------------
    # UBICACION
    # ----------------------------------------------------------------
    def centrar_en_mi_ubicacion(self, instancia_boton):
        lat, lon = UBICACION_PRUEBA
        self.mapa.center_on(lat, lon)
        self.marcador_ubicacion.lat = lat
        self.marcador_ubicacion.lon = lon
        self.mapa.trigger_update(True)

    # ----------------------------------------------------------------
    # MODOS DE DIBUJO
    # ----------------------------------------------------------------
    def activar_modo_manual(self, instancia_boton):
        """ Activa el modo de dibujo tocando el mapa directamente. """
        self.modo_dibujo = "manual"
        self.actualizar_apariencia_botones()

    def activar_modo_recorrido(self, instancia_boton):
        """ Activa el modo de dibujo agregando vertices con un boton. """
        self.modo_dibujo = "recorrido"
        self.actualizar_apariencia_botones()

    def actualizar_apariencia_botones(self):
        """ Resalta en verde el boton del modo que este activo actualmente. """
        color_activo = (0.1, 0.7, 0.3, 1)
        color_inactivo = (0.5, 0.5, 0.5, 1)

        self.boton_manual.md_bg_color = (
            color_activo if self.modo_dibujo == "manual" else color_inactivo
        )
        self.boton_recorrido.md_bg_color = (
            color_activo if self.modo_dibujo == "recorrido" else color_inactivo
        )

    # ----------------------------------------------------------------
    # MANEJO DE VERTICES
    # ----------------------------------------------------------------
    def agregar_vertice_en_mi_ubicacion(self, instancia_boton):
        """
        Boton "+ Vertice": agrega un vertice usando la posicion actual
        del marcador de ubicacion. Pensado para usarse en Modo Recorrido
        mientras caminas, pero funciona sin importar el modo activo.
        """
        lat = self.marcador_ubicacion.lat
        lon = self.marcador_ubicacion.lon
        self.agregar_vertice(lat, lon)

    def agregar_vertice(self, lat, lon):
        """ Agrega un vertice a la lista y lo dibuja en el mapa como un pin. """
        self.vertices.append((lat, lon))

        marcador = MapMarker(lat=lat, lon=lon)
        self.mapa.add_marker(marcador)
        self.marcadores_vertices.append(marcador)

        self.etiqueta_estado.text = f"Vertices: {len(self.vertices)}"

    def deshacer_vertice(self, instancia_boton):
        """ Borra el ultimo vertice marcado (por si tocaste mal en el mapa). """
        if not self.vertices:
            return

        self.vertices.pop()
        ultimo_marcador = self.marcadores_vertices.pop()
        self.mapa.remove_marker(ultimo_marcador)

        self.etiqueta_estado.text = f"Vertices: {len(self.vertices)}"

    def cancelar_dibujo(self, instancia_boton):
        """ Borra TODOS los vertices y reinicia el dibujo desde cero. """
        for marcador in self.marcadores_vertices:
            self.mapa.remove_marker(marcador)

        self.vertices = []
        self.marcadores_vertices = []
        self.modo_dibujo = None
        self.actualizar_apariencia_botones()
        self.etiqueta_estado.text = "Vertices: 0"

    def cerrar_poligono(self, instancia_boton):
        """
        Termina el poligono: calcula el area en hectareas, la guarda
        temporalmente en la App, y navega al formulario para completar
        los demas datos (Operador, Parcela, Variedad, Tipo de Corte).
        """
        if len(self.vertices) < 3:
            self.etiqueta_estado.text = "Se necesitan al menos 3 vertices"
            return

        area_ha = geometria.calcular_area_ha(self.vertices)
        geojson_texto = geometria.poligono_a_geojson(self.vertices)

        # Guardamos el poligono "pendiente" en la App (el objeto principal
        # de la aplicacion), para que la pantalla del formulario pueda
        # leerlo cuando se abra a continuacion.
        app = MDApp.get_running_app()
        app.poligono_pendiente = {
            "area_ha": area_ha,
            "geometria": geojson_texto
        }

        self.manager.current = "formulario"

    def reiniciar_dibujo(self):
        """
        Metodo publico que llama PantallaFormulario despues de guardar
        (o cancelar) un registro, para dejar el mapa limpio y listo
        para la siguiente parcela.
        """
        self.cancelar_dibujo(None)


class PantallaFormulario(Screen):
    """ Formulario de atributos de la parcela (se abre despues de cerrar el poligono). """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Estos guardan el area y geometria calculadas en el mapa,
        # se actualizan en on_pre_enter() cada vez que se abre esta pantalla.
        self.area_actual = None
        self.geometria_actual = None

        layout = BoxLayout(orientation="vertical", padding=20, spacing=12)

        layout.add_widget(Label(
            text="Nueva Parcela", font_size=24, size_hint=(1, 0.12), color=(0, 0, 0, 1)
        ))

        # Fecha (automatica, editable)
        layout.add_widget(Label(text="Fecha", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.campo_fecha = TextInput(
            text=database.obtener_fecha_actual(),
            multiline=False,
            size_hint=(1, 0.1)
        )
        layout.add_widget(self.campo_fecha)

        # Operador
        layout.add_widget(Label(text="Operador", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_operador = Spinner(text=OPERADORES[0], values=OPERADORES, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_operador)

        # Parcela
        layout.add_widget(Label(text="Parcela", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_parcela = Spinner(text=PARCELAS[0], values=PARCELAS, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_parcela)

        # Variedad
        layout.add_widget(Label(text="Variedad", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_variedad = Spinner(text=VARIEDADES[0], values=VARIEDADES, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_variedad)

        # Tipo de Corte
        layout.add_widget(Label(text="Tipo de Corte", size_hint=(1, 0.06), color=(0, 0, 0, 1)))
        self.spinner_tipo_corte = Spinner(text=TIPOS_CORTE[0], values=TIPOS_CORTE, size_hint=(1, 0.1))
        layout.add_widget(self.spinner_tipo_corte)

        # Area (ha) -- ahora SI es automatica de verdad, calculada del poligono.
        # Es solo informativa (no editable), por eso usamos un Label y no un TextInput.
        self.etiqueta_area = Label(
            text="Area (ha): --",
            size_hint=(1, 0.08),
            color=(0.1, 0.4, 0.9, 1),
            font_size=16,
            bold=True
        )
        layout.add_widget(self.etiqueta_area)

        # Botones Cancelar / Guardar
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
        """
        Se ejecuta automaticamente justo antes de mostrar esta pantalla.
        Aqui refrescamos la fecha y leemos el poligono que se acaba de
        cerrar en el mapa (guardado temporalmente en la App).
        """
        self.campo_fecha.text = database.obtener_fecha_actual()
        self.mensaje.text = ""

        app = MDApp.get_running_app()
        pendiente = getattr(app, "poligono_pendiente", None)

        if pendiente:
            self.area_actual = pendiente["area_ha"]
            self.geometria_actual = pendiente["geometria"]
            self.etiqueta_area.text = f"Area (ha): {self.area_actual:.4f}"
        else:
            # Esto no deberia pasar en el uso normal (siempre se llega aqui
            # desde "Cerrar Poligono"), pero lo dejamos como respaldo.
            self.area_actual = None
            self.geometria_actual = None
            self.etiqueta_area.text = "Area (ha): sin poligono dibujado"

    def cancelar(self, instancia_boton):
        """ Cancela el registro actual: descarta el poligono dibujado y vuelve al mapa. """
        app = MDApp.get_running_app()
        app.poligono_pendiente = None
        self.manager.get_screen("mapa").reiniciar_dibujo()
        self.manager.current = "mapa"

    def guardar_datos(self, instancia_boton):
        """ Guarda el registro completo (atributos + area + geometria) en SQLite. """
        fecha = self.campo_fecha.text
        operador = self.spinner_operador.text
        parcela = self.spinner_parcela.text
        variedad = self.spinner_variedad.text
        tipo_corte = self.spinner_tipo_corte.text

        fid_generado = database.guardar_parcela(
            fecha=fecha,
            operador=operador,
            parcela=parcela,
            variedad=variedad,
            tipo_corte=tipo_corte,
            area_ha=self.area_actual,
            geometria=self.geometria_actual
        )

        self.mensaje.text = f"Guardado correctamente (FID {fid_generado})"

        # Limpiamos el poligono pendiente y dejamos el mapa listo para la
        # siguiente parcela.
        app = MDApp.get_running_app()
        app.poligono_pendiente = None
        self.manager.get_screen("mapa").reiniciar_dibujo()

        self.manager.current = "mapa"


class CampoGISApp(MDApp):
    """ Clase principal de la aplicacion. """

    # Aqui se guarda temporalmente el poligono recien dibujado (area +
    # geometria) mientras el usuario completa el formulario. Empieza en None.
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
