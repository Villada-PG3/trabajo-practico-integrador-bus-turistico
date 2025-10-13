from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    Recorrido, RecorridoParada, Parada, ParadaAtractivo, Atractivo,
    Bus, EstadoBus, EstadoBusHistorial,
    Chofer, Viaje, EstadoViaje, Consulta
)

@admin.register(Recorrido)
class RecorridoAdmin(admin.ModelAdmin):
    list_display = ('id', 'color_recorrido', 'duracion_aproximada_recorrido',)
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
    list_display = ('id', 'patente_bus', 'estado_bus', 'fecha_inicio_estado')


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
        'patente_bus', 'chofer', 'recorrido',
    )
@admin.register(EstadoViaje)
class EstadoViajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_estado', 'descripcion_estado')

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "telefono", "fecha_interes", "recorrido_interes", "fecha_envio", "respondida")
    list_filter = ("respondida", "fecha_envio")
    search_fields = ("nombre", "email", "mensaje")
    ordering = ("-fecha_envio",)

    fields = ("nombre", "email", "telefono", "personas", "fecha_interes", "recorrido_interes", "mensaje", "respuesta", "respondida", "fecha_envio")
    readonly_fields = ("fecha_envio",)

    actions = ["enviar_respuesta"]

    @admin.action(description="Enviar respuesta por correo")
    def enviar_respuesta(self, request, queryset):
        for consulta in queryset:
            if consulta.respuesta:
                send_mail(
                    subject="Respuesta a tu consulta - Bus Turístico",
                    message=consulta.respuesta,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[consulta.email],
                )
                consulta.respondida = True
                consulta.save()
        self.message_user(request, "Respuestas enviadas correctamente.")