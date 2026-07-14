[app]

# ------------------------------------------------------------------
# INFORMACION BASICA DE LA APP (esto es lo que se ve en el celular)
# ------------------------------------------------------------------
title = AgroCana
package.name = agrocana
package.domain = org.agrocana
version = 0.1

# ------------------------------------------------------------------
# ARCHIVOS QUE SE INCLUYEN EN EL PAQUETE
# ------------------------------------------------------------------
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

# ------------------------------------------------------------------
# LIBRERIAS DE PYTHON QUE NECESITA LA APP
# (equivalente movil de los "pip install" que ya hiciste en tu PC)
# ------------------------------------------------------------------
requirements = python3,kivy==2.3.1,kivymd,plyer,kivy_garden.mapview,utm

# Orientacion de pantalla: portrait = vertical (normal para celular)
orientation = portrait
fullscreen = 0

# ------------------------------------------------------------------
# PERMISOS DE ANDROID que la app necesita pedir al usuario
# ------------------------------------------------------------------
# INTERNET: para descargar los tiles del mapa satelital
# ACCESS_FINE_LOCATION / ACCESS_COARSE_LOCATION: para el GPS
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# ------------------------------------------------------------------
# CONFIGURACION DE ANDROID (version minima y objetivo)
# ------------------------------------------------------------------
android.api = 34
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
