"""
============================================================
 APP DE CAMPO - TOPOGRAFIA Y CATASTRO AGRICOLA
 FASE 1: Interfaz basica con mapa + boton de ubicacion
============================================================

Que hace este archivo:
1. Crea una ventana con un mapa interactivo (se puede mover y hacer zoom).
2. Agrega un boton flotante "Mi Ubicacion" que centra el mapa
   en una coordenada (en la PC sera una coordenada de prueba;
   en el celular usaremos el GPS real en una fase posterior).
3. Muestra un marcador (pin) en esa ubicacion.

IMPORTANTE: Este mapa por ahora usa el servidor de tiles de OpenStreetMap
via internet (para que puedas ver algo funcionando YA en tu PC).
En la Fase de "mapas offline" reemplazaremos esto por un archivo MBTiles
local, para que funcione sin internet en el campo.
"""

# ------------------------------------------------------------------
# IMPORTACIONES: traemos las piezas que necesitamos de cada libreria
# ------------------------------------------------------------------

# KivyMD: nos da la App base y widgets con estilo Material Design (botones, etc.)
from kivymd.app import MDApp

# Kivy: BoxLayout es un contenedor que organiza widgets en una fila o columna.
from kivy.uix.boxlayout import BoxLayout

# El widget de mapa y el marcador (pin), de la libreria kivy_garden.mapview
from kivy_garden.mapview import MapView, MapMarker

# MDIconButton: un boton circular con icono, estilo Material Design.
# Lo usaremos como el boton flotante de "Mi Ubicacion".
from kivymd.uix.button import MDIconButton

# FloatLayout: un contenedor donde podemos posicionar widgets
# usando coordenadas relativas (por ejemplo, "abajo a la derecha").
# Esto lo usamos para que el boton flote SOBRE el mapa, no al lado.
from kivy.uix.floatlayout import FloatLayout


# ------------------------------------------------------------------
# COORDENADA DE PRUEBA
# ------------------------------------------------------------------
# Mientras no tenemos GPS real conectado (eso es la Fase de GPS),
# usamos una coordenada fija para simular "mi ubicacion".
# Puedes cambiar estos numeros por la ubicacion de tu finca o zona de trabajo.
# Formato: (latitud, longitud)
UBICACION_PRUEBA = (8.9824, -79.5199)  # Ejemplo: Ciudad de Panama


class PantallaPrincipal(FloatLayout):
    """
    Esta clase representa la pantalla principal de la app.
    Hereda de FloatLayout para poder poner el mapa de fondo
    y el boton flotando encima, en una posicion especifica.
    """

    def __init__(self, **kwargs):
        # Siempre se debe llamar al __init__ del padre primero
        super().__init__(**kwargs)

        # ----------------------------------------------------------
        # 1. Creamos el widget de mapa
        # ----------------------------------------------------------
        # lat, lon: coordenada inicial donde se centra el mapa al abrir la app
        # zoom: nivel de acercamiento inicial (0 = todo el mundo, 18+ = calle)
        self.mapa = MapView(
            lat=UBICACION_PRUEBA[0],
            lon=UBICACION_PRUEBA[1],
            zoom=15
        )

        # Agregamos el mapa como el primer elemento de la pantalla
        # (ocupara todo el espacio disponible, de fondo)
        self.add_widget(self.mapa)

        # ----------------------------------------------------------
        # 2. Creamos el marcador (pin) de ubicacion
        # ----------------------------------------------------------
        # Lo guardamos en self.marcador_ubicacion para poder moverlo
        # despues (cuando conectemos el GPS real).
        self.marcador_ubicacion = MapMarker(
            lat=UBICACION_PRUEBA[0],
            lon=UBICACION_PRUEBA[1]
        )

        # Los marcadores se agregan AL MAPA, no a la pantalla directamente
        self.mapa.add_marker(self.marcador_ubicacion)

        # ----------------------------------------------------------
        # 3. Creamos el boton flotante "Mi Ubicacion"
        # ----------------------------------------------------------
        self.boton_ubicacion = MDIconButton(
            icon="crosshairs-gps",   # icono de mira/GPS (viene incluido en KivyMD)
            pos_hint={"right": 0.97, "y": 0.05},  # posicion: abajo a la derecha
            md_bg_color=(1, 1, 1, 0.9),  # fondo blanco semi-transparente
            theme_icon_color="Custom",
            icon_color=(0.1, 0.4, 0.9, 1),  # azul
            on_release=self.centrar_en_mi_ubicacion  # que funcion ejecutar al tocarlo
        )

        # Este boton SI va directo a la pantalla (FloatLayout),
        # para que quede flotando sobre el mapa.
        self.add_widget(self.boton_ubicacion)

    def centrar_en_mi_ubicacion(self, instancia_boton):
        """
        Esta funcion se ejecuta cuando el usuario toca el boton de ubicacion.

        Por ahora, simplemente centra el mapa en la UBICACION_PRUEBA.
        En una fase posterior, aqui conectaremos el GPS real del telefono
        y esta funcion centrara el mapa en la posicion real del usuario.

        'instancia_boton' es un parametro que Kivy siempre envia
        automaticamente indicando que boton fue presionado (no lo usamos aqui,
        pero debe estar en la funcion para que no de error).
        """
        lat, lon = UBICACION_PRUEBA

        # .center_on() mueve la camara del mapa a esa coordenada
        self.mapa.center_on(lat, lon)

        # Tambien movemos el marcador a esa misma posicion
        self.marcador_ubicacion.lat = lat
        self.marcador_ubicacion.lon = lon

        # Forzamos que el mapa recalcule la posicion del marcador en pantalla
        self.mapa.trigger_update(True)


class CampoGISApp(MDApp):
    """
    Esta es la clase principal de la aplicacion.
    Toda app de KivyMD necesita una clase que herede de MDApp
    y que tenga un metodo build() que devuelva la pantalla principal.
    """

    def build(self):
        # Configuracion visual basica (tema claro, color principal azul)
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"

        # Devolvemos una instancia de nuestra pantalla principal
        return PantallaPrincipal()


# ------------------------------------------------------------------
# PUNTO DE ENTRADA: esto se ejecuta solo si corres "python main.py"
# ------------------------------------------------------------------
if __name__ == "__main__":
    CampoGISApp().run()
