from django.contrib import admin
from .models import (
    Recorrido, RecorridoParada, Parada, ParadaAtractivo, Atractivo,
    Bus, EstadoBus, EstadoBusHistorial,
    Chofer, Viaje, EstadoViaje
)

@admin.register(Recorrido)
class RecorridoAdmin(admin.ModelAdmin):
    list_display = ('id', 'color_recorrido', 'duracion_aproximada_recorrido', 'hora_inicio', 'hora_fin', 'numero_paradas')
    search_fields = ('color_recorrido',)

@admin.register(RecorridoParada)
class RecorridoParadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'recorrido', 'parada', 'orden')

@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_parada', 'direccion_parada', 'latitud_parada', 'longitud_parada')
    search_fields = ('nombre_parada',)

@admin.register(ParadaAtractivo)
class ParadaAtractivoAdmin(admin.ModelAdmin):
    list_display = ('id', 'parada', 'atractivo')

@admin.register(Atractivo)
class AtractivoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_atractivo', 'calificacion_estrellas', 'latitud_atractivo', 'longitud_atractivo')
    search_fields = ('nombre_atractivo',)

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('patente_bus', 'numero_unidad', 'fecha_compra')
    search_fields = ('patente_bus',)

@admin.register(EstadoBus)
class EstadoBusAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_estado', 'descripcion_estado')

@admin.register(EstadoBusHistorial)
class EstadoBusHistorialAdmin(admin.ModelAdmin):
    list_display = ('id', 'patente_bus', 'id_estado_bus', 'fecha_inicio_estado')

@admin.register(Chofer)
class ChoferAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_chofer', 'apellido_chofer', 'legajo_chofer', 'dni_chofer', 'activo')
    search_fields = ('nombre_chofer', 'apellido_chofer', 'legajo_chofer')

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'fecha_programada', 'hora_inicio_programada',
        'fecha_hora_inicio_real', 'fecha_hora_fin_real',
        'demora_inicio_minutos', 'duracion_minutos_real',
        'patente_bus', 'id_chofer', 'id_recorrido', 'id_estado_viaje'
    )
    list_filter = ('id_estado_viaje',)

@admin.register(EstadoViaje)
class EstadoViajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_estado', 'descripcion_estado')
