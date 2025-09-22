from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import get_object_or_404
import json
from math import radians, sin, cos, sqrt, atan2

from .models import (
    Viaje, UbicacionColectivo, Recorrido, RecorridoParada
)


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


@require_http_methods(["GET"])
def proximos_horarios_recorrido(request, pk):
    recorrido = get_object_or_404(Recorrido, pk=pk)
    now = timezone.localtime()
    viajes_qs = (
        Viaje.objects
        .filter(
            recorrido=recorrido,
            fecha_hora_inicio_real__isnull=True,
            fecha_programada__date=now.date(),
            hora_inicio_programada__gte=now.time(),
        )
        .order_by('hora_inicio_programada')
    )
    horarios = [v.hora_inicio_programada.strftime('%H:%M') for v in viajes_qs[:6]]
    return JsonResponse({
        'recorrido_id': recorrido.id,
        'proximos_horarios': horarios,
    })


@require_http_methods(["GET"])
def paradas_recorrido(request, pk):
    recorrido = get_object_or_404(Recorrido, pk=pk)
    rps = RecorridoParada.objects.filter(recorrido=recorrido).select_related('parada').order_by('orden')
    data = [
        {
            'orden': rp.orden,
            'parada': {
                'id': rp.parada.id,
                'nombre': rp.parada.nombre_parada,
                'lat': rp.parada.latitud_parada,
                'lng': rp.parada.longitud_parada,
                'direccion': rp.parada.direccion_parada,
            },
        }
        for rp in rps
    ]
    return JsonResponse({'recorrido_id': recorrido.id, 'paradas': data})


@csrf_exempt
@require_http_methods(["POST"])
def post_ubicacion_viaje(request, viaje_id):
    """
    Registra una nueva ubicación para un viaje en curso.
    Espera JSON: {"lat": float, "lng": float, "timestamp": ISO8601 opcional}
    """
    viaje = get_object_or_404(Viaje, pk=viaje_id)
    if not (viaje.fecha_hora_inicio_real and not viaje.fecha_hora_fin_real):
        return JsonResponse({'error': 'Viaje no está en curso.'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('JSON inválido')

    try:
        lat = float(payload.get('lat'))
        lng = float(payload.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'lat/lng inválidos.'}, status=400)

    ts = payload.get('timestamp')
    timestamp = timezone.now()
    # Se puede parsear ts si llega; mantenerlo simple por ahora

    UbicacionColectivo.objects.create(
        latitud=lat,
        longitud=lng,
        timestamp_ubicacion=timestamp,
        viaje=viaje,
    )
    return JsonResponse({'ok': True, 'viaje_id': viaje.id, 'timestamp': timestamp.isoformat()})


@require_http_methods(["GET"])
def ubicaciones_activas(request):
    """
    Devuelve viajes en curso con su última ubicación y estimación simple
    hacia la parada más cercana.
    """
    viajes = (
        Viaje.objects
        .filter(fecha_hora_inicio_real__isnull=False, fecha_hora_fin_real__isnull=True)
        .select_related('patente_bus', 'recorrido')
    )

    items = []
    for v in viajes:
        # Tomar la última ubicación pasada (ignorar timestamps futuros por simulación)
        last = (
            UbicacionColectivo.objects
            .filter(viaje=v, timestamp_ubicacion__lte=timezone.now())
            .order_by('-timestamp_ubicacion')
            .first()
        )
        if not last:
            continue

        # Parada más cercana del recorrido
        rps = RecorridoParada.objects.filter(recorrido=v.recorrido).select_related('parada')
        closest = None
        closest_km = None
        for rp in rps:
            d = _haversine_km(last.latitud, last.longitud, rp.parada.latitud_parada, rp.parada.longitud_parada)
            if closest_km is None or d < closest_km:
                closest_km = d
                closest = rp

        # ETA simple asumiendo 30 km/h
        eta_min = None
        if closest_km is not None:
            eta_min = int((closest_km / 30.0) * 60)  # minutos
            if eta_min < 0:
                eta_min = 0

        items.append({
            'viaje_id': v.id,
            'recorrido': {
                'id': v.recorrido.id,
                'color': v.recorrido.color_recorrido,
            },
            'bus': {
                'patente': v.patente_bus.patente_bus,
                'unidad': v.patente_bus.numero_unidad,
            },
            'ubicacion': {
                'lat': last.latitud,
                'lng': last.longitud,
                'timestamp': last.timestamp_ubicacion.isoformat(),
            },
            'closest_parada': None if not closest else {
                'id': closest.parada.id,
                'nombre': closest.parada.nombre_parada,
                'orden': closest.orden,
                'distancia_km': round(closest_km, 3) if closest_km is not None else None,
                'eta_min': eta_min,
            },
        })

    return JsonResponse({'items': items})
