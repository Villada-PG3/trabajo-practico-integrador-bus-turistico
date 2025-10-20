from django.utils import timezone

from .models import EstadoViaje, HistorialEstadoViaje, Viaje


def finalizar_viaje(viaje: Viaje, timestamp=None, registrar_inicio=True) -> bool:
    """
    Marca un viaje como completado si todavía no se cerró.
    Retorna True cuando se realizaron cambios.
    """
    if viaje.fecha_hora_fin_real:
        return False

    ahora = timestamp or timezone.now()
    update_fields = ['fecha_hora_fin_real']

    if registrar_inicio and not viaje.fecha_hora_inicio_real:
        viaje.fecha_hora_inicio_real = ahora
        update_fields.append('fecha_hora_inicio_real')

    viaje.fecha_hora_fin_real = ahora

    if viaje.fecha_hora_inicio_real:
        duracion = max(int((viaje.fecha_hora_fin_real - viaje.fecha_hora_inicio_real).total_seconds() / 60), 0)
        viaje.duracion_minutos_real = duracion
        update_fields.append('duracion_minutos_real')

    viaje.save(update_fields=update_fields)

    estado_completado, _ = EstadoViaje.objects.get_or_create(
        nombre_estado='Completado',
        defaults={'descripcion_estado': 'Viaje completado'}
    )
    HistorialEstadoViaje.objects.create(
        viaje=viaje,
        estado_viaje=estado_completado,
        fecha_cambio_estado=ahora
    )
    return True
