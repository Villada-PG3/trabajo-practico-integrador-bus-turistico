from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.conf import settings
from .models import (
    Recorrido,
    Viaje,
    Chofer,
    EstadoViaje,
    Bus,
    RecorridoParada,
    UbicacionColectivo,
)
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import datetime
import logging
import math
import requests


logger = logging.getLogger(__name__)

class ChoferRequiredMixin:
    """Mixin que requiere que el usuario sea un chofer activo"""
    
    @method_decorator(login_required(login_url='chofer-login'))
    def dispatch(self, request, *args, **kwargs):
        try:
            chofer = Chofer.objects.get(user=request.user, activo=True)
            request.chofer = chofer
        except Chofer.DoesNotExist:
            # Si el usuario no es un chofer activo, cerramos sesión y redirigimos a login
            logout(request)
            messages.info(request, 'Inicia sesión como chofer para continuar.')
            return redirect('chofer-login')
        
        return super().dispatch(request, *args, **kwargs)

class ChoferRecorridosView(ChoferRequiredMixin, ListView):
    """
    Pantalla principal del chofer.
    Muestra:
      - Viaje en curso (si existe)
      - Sino, el viaje asignado pendiente de iniciar (si existe)
      - Sino, un mensaje indicando que no tiene viaje asignado
    Ya no lista todos los recorridos disponibles.
    """

    model = Recorrido  # No se usa para listar, pero mantiene la firma del ListView
    template_name = 'chofer/recorridos.html'
    context_object_name = 'recorridos'

    def get_queryset(self):
        # No listamos recorridos; devolvemos queryset vacío
        return Recorrido.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chofer = self.request.chofer
        context['chofer'] = chofer

        # 1) Viaje en curso
        viaje_en_curso = (
            Viaje.objects.filter(
                chofer=chofer,
                fecha_hora_inicio_real__isnull=False,
                fecha_hora_fin_real__isnull=True
            )
            .select_related('patente_bus', 'recorrido')
            .first()
        )
        context['viaje_en_curso'] = viaje_en_curso

        if not viaje_en_curso:
            # 2) Viaje asignado aún no iniciado (tomamos el más próximo por fecha_programada)
            viaje_asignado = (
                Viaje.objects.filter(
                    chofer=chofer,
                    fecha_hora_inicio_real__isnull=True
                )
                .select_related('patente_bus', 'recorrido')
                .order_by('fecha_programada', 'id')
                .first()
            )
            context['viaje_asignado'] = viaje_asignado
        else:
            context['viaje_asignado'] = None

        return context

class IniciarRecorridoView(ChoferRequiredMixin, View):
    """
    Compatibilidad hacia atrás: si llegara a usarse con pk de recorrido,
    intenta iniciar el viaje asignado. Ya no crea viajes "ad-hoc".
    """
    def post(self, request, pk=None):
        chofer = request.chofer

        # Si ya hay un viaje en curso, redirigir a detalle
        viaje_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).first()
        if viaje_en_curso:
            messages.error(request, 'Ya tienes un viaje en curso. Debes finalizarlo antes de iniciar otro.')
            return redirect('viaje-en-curso')

        # Buscar viaje asignado no iniciado
        viaje_asignado = (
            Viaje.objects.filter(chofer=chofer, fecha_hora_inicio_real__isnull=True)
            .order_by('fecha_programada', 'id')
            .first()
        )
        if not viaje_asignado:
            messages.error(request, 'No tienes un viaje asignado para iniciar.')
            return redirect('chofer-recorridos')

        # Marcar inicio real ahora
        viaje_asignado.fecha_hora_inicio_real = timezone.now()
        try:
            estado_en_curso, _ = EstadoViaje.objects.get_or_create(
                nombre_estado='En curso',
                defaults={'descripcion_estado': 'Viaje en curso'}
            )
        except Exception:
            estado_en_curso = None
        viaje_asignado.save()

        # Simular el recorrido si aún no hay ubicaciones registradas
        if not UbicacionColectivo.objects.filter(viaje=viaje_asignado).exists():
            self._simular_recorrido_ideal(viaje_asignado)

        messages.success(request, f'Viaje al recorrido {viaje_asignado.recorrido.color_recorrido} iniciado correctamente.')
        return redirect('viaje-en-curso')

    def _simular_recorrido_ideal(self, viaje: Viaje):
        """
        Genera ubicaciones futuras a intervalos regulares recorriendo las paradas del recorrido.
        La API pública ignora timestamps futuros, por lo que el mapa mostrará el avance con el tiempo.
        """
        recorrido = viaje.recorrido
        now = timezone.now()

        # 1) Ruta basada en las paradas cargadas para el recorrido
        rps = list(
            RecorridoParada.objects
            .filter(recorrido=recorrido)
            .select_related('parada')
            .order_by('orden')
        )
        raw_points = [
            (rp.parada.latitud_parada, rp.parada.longitud_parada)
            for rp in rps
            if rp.parada.latitud_parada is not None and rp.parada.longitud_parada is not None
        ]

        def _build_city_path(points):
            if len(points) < 2:
                return points

            def _manhattan_segment(a, b, step=0.00035):
                lat1, lon1 = a
                lat2, lon2 = b
                path = [a]
                current_lat, current_lon = lat1, lon1

                # Determinar el orden de piernas para evitar cortes bruscos
                leg_order = ['lon', 'lat']
                if abs(lat2 - lat1) > abs(lon2 - lon1):
                    leg_order = ['lat', 'lon']

                for leg in leg_order:
                    if leg == 'lon':
                        diff = lon2 - current_lon
                        if abs(diff) < 1e-9:
                            continue
                        steps = max(int(abs(diff) / step), 1)
                        for s in range(1, steps + 1):
                            lon = current_lon + diff * (s / steps)
                            path.append((current_lat, lon))
                        current_lon = lon2
                    else:  # leg == 'lat'
                        diff = lat2 - current_lat
                        if abs(diff) < 1e-9:
                            continue
                        steps = max(int(abs(diff) / step), 1)
                        for s in range(1, steps + 1):
                            lat = current_lat + diff * (s / steps)
                            path.append((lat, current_lon))
                        current_lat = lat2

                if path[-1] != b:
                    path.append(b)
                return path

            expanded = [points[0]]
            for start, end in zip(points, points[1:]):
                segment = _manhattan_segment(start, end)
                expanded.extend(segment[1:])  # omitir el primer punto para no duplicar
            return expanded

        coords = self._route_with_osrm(raw_points)
        if not coords:
            # Si OSRM falla, recorrer las paradas en línea recta (ruta roja)
            coords = raw_points

        # 2) Fallback manual suave cercano al obelisco
        if len(coords) < 2:
            coords = [
                (-34.6037, -58.3816),  # Obelisco
                (-34.6045, -58.3780),  # Corrientes y Florida
                (-34.6070, -58.3790),  # Plaza Lavalle
                (-34.6090, -58.3825),  # Congreso
                (-34.6060, -58.3855),  # 9 de Julio y Belgrano
                (-34.6037, -58.3816),
            ]

        if len(coords) < 2:
            # Nada que simular
            return

        # Crear un punto inicial en la primera parada (visible de inmediato)
        UbicacionColectivo.objects.create(
            latitud=coords[0][0],
            longitud=coords[0][1],
            timestamp_ubicacion=now,
            viaje=viaje,
        )

        # Parámetros de simulación: velocidad constante aproximada para todos los recorridos
        target_speed_kmh = 25  # velocidad deseada del bus
        min_segment_seconds = 2
        interval_seconds = 1

        def haversine_km(lat1, lon1, lat2, lon2):
            """Distancia aproximada en km entre dos puntos."""
            R = 6371.0
            lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        def interp(a, b, t):
            return a + (b - a) * t

        current_ts = now
        for i in range(len(coords) - 1):
            (lat1, lng1) = coords[i]
            (lat2, lng2) = coords[i + 1]
            distance_km = haversine_km(lat1, lng1, lat2, lng2)
            if distance_km < 1e-6:
                distance_km = 0.001  # evitar tiempos nulos

            segment_seconds = max(min_segment_seconds, (distance_km / target_speed_kmh) * 3600)
            steps = max(1, int(segment_seconds / interval_seconds))
            seconds_per_step = segment_seconds / steps

            for s in range(1, steps + 1):
                f = s / steps
                lat = interp(lat1, lat2, f)
                lng = interp(lng1, lng2, f)
                current_ts += datetime.timedelta(seconds=seconds_per_step)
                UbicacionColectivo.objects.create(
                    latitud=lat,
                    longitud=lng,
                    timestamp_ubicacion=current_ts,
                    viaje=viaje,
                )

    def _route_with_osrm(self, points):
        if len(points) < 2:
            return None

        base_url = getattr(settings, 'OSRM_BASE_URL', 'https://bonnie-stoney-boorishly.ngrok-free.dev').strip() or 'https://router.project-osrm.org'
        base_url = base_url.rstrip('/')
        coordinates = ';'.join(f"{lng},{lat}" for lat, lng in points)
        params = {'overview': 'full', 'geometries': 'geojson'}
        url = f"{base_url}/route/v1/driving/{coordinates}"
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.warning("OSRM routing failed: %s", exc)
            return None

        routes = data.get('routes')
        if not routes:
            return None

        geometry = routes[0].get('geometry', {}).get('coordinates')
        if not geometry:
            return None

        return [(lat, lng) for lng, lat in geometry]
    
# Nueva vista para los detalles del viaje en curso
class DetalleViajeView(ChoferRequiredMixin, View):
    template_name = 'chofer/detalle_viaje.html'

    def get(self, request, *args, **kwargs):
        chofer = request.chofer
        viaje_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).select_related('recorrido', 'patente_bus').first()

        if not viaje_en_curso:
            messages.info(request, 'No tienes un viaje en curso.')
            return redirect('chofer-recorridos')

        context = {
            'viaje': viaje_en_curso,
            'chofer': chofer
        }
        return render(request, self.template_name, context)

# Nueva vista para finalizar el viaje
class FinalizarViajeView(ChoferRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        chofer = request.chofer
        
        # Buscar el viaje en curso
        viaje_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).first()
        
        if not viaje_en_curso:
            messages.error(request, 'No tienes un viaje en curso para finalizar.')
            return redirect('chofer-recorridos')
        
        # Finalizar el viaje
        viaje_en_curso.fecha_hora_fin_real = timezone.now()
        
        # Calcular duración real en minutos
        if viaje_en_curso.fecha_hora_inicio_real:
            duracion = timezone.now() - viaje_en_curso.fecha_hora_inicio_real
            viaje_en_curso.duracion_minutos_real = int(duracion.total_seconds() / 60)
        
        viaje_en_curso.save()
        
        # Opcional: Crear historial de estado del viaje
        try:
            estado_completado, created = EstadoViaje.objects.get_or_create(
                nombre_estado='Completado',
                defaults={'descripcion_estado': 'Viaje completado exitosamente'}
            )
            
            # Importar el modelo si no está importado
            from .models import HistorialEstadoViaje
            HistorialEstadoViaje.objects.create(
                viaje=viaje_en_curso,
                estado_viaje=estado_completado,
                fecha_cambio_estado=timezone.now()
            )
        except Exception as e:
            # Log del error pero no interrumpir el proceso
            logging.error(f"Error al crear historial de estado: {e}")
        
        messages.success(
            request, 
            f'Recorrido {viaje_en_curso.recorrido.color_recorrido} finalizado correctamente. '
            f'Duración: {viaje_en_curso.duracion_minutos_real} minutos.'
        )
        
        return redirect('chofer-recorridos')
def iniciar_viaje_chofer(request, viaje_id):
    viaje = get_object_or_404(Viaje, pk=viaje_id)
    
    # Prepara el objeto de fecha y hora programada para el cálculo
    fecha_hora_programada_completa = datetime.datetime.combine(viaje.fecha_programada.date(), viaje.hora_inicio_programada)
    
    # Calcula la demora de inicio
    ahora = timezone.now()
    demora = ahora - fecha_hora_programada_completa
    
    # Actualiza los campos del modelo
    viaje.fecha_hora_inicio_real = ahora
    viaje.demora_inicio_minutos = int(demora.total_seconds() / 60)
    viaje.save()
    
    # Aquí puedes cambiar el estado del viaje a "En Curso" en el HistorialEstadoViaje
    # ...
    
    return redirect('chofer_panel') # Redirige al panel del chofer
