from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.conf import settings
# --- Imports de Modelo ---
from .models import (
    Recorrido,
    Viaje,
    Chofer,
    EstadoViaje,
    Bus,
    RecorridoParada,
    UbicacionColectivo,
    HistorialEstadoViaje, # Asegúrate de que este modelo esté importado si lo usas
)
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import datetime
import logging
import math
import requests
# --- Nuevos Imports para Asincronía y DB ---
import threading
from django.db import connection, transaction
# --- Fin de Imports ---

from .services_viaje import finalizar_viaje

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
            request.session['chofer_login_prompt'] = True
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

# --------------------------------------------------------------------------------------
# VISTA OPTIMIZADA: IniciarRecorridoView
# --------------------------------------------------------------------------------------

class IniciarRecorridoView(ChoferRequiredMixin, View):
    """
    Inicia el viaje asignado.
    La simulación de recorrido se ejecuta en un hilo separado para 
    una respuesta **instantánea** al chofer.
    """
    def post(self, request, pk=None):
        chofer = request.chofer

        # 1. Validación de viaje en curso
        viaje_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).first()
        if viaje_en_curso:
            messages.error(request, 'Ya tienes un viaje en curso. Debes finalizarlo antes de iniciar otro.')
            return redirect('viaje-en-curso')

        # 2. Buscar viaje asignado no iniciado
        viaje_asignado = (
            Viaje.objects.filter(chofer=chofer, fecha_hora_inicio_real__isnull=True)
            .order_by('fecha_programada', 'id')
            .first()
        )
        if not viaje_asignado:
            messages.error(request, 'No tienes un viaje asignado para iniciar.')
            return redirect('chofer-recorridos')

        # 3. Operación CRÍTICA (Actualización de DB - Usamos transaction.atomic para agrupar)
        try:
            with transaction.atomic():
                now = timezone.now()
                
                # Calcular demora de inicio
                fecha_hora_programada_completa = datetime.datetime.combine(viaje_asignado.fecha_programada, viaje_asignado.hora_inicio_programada)
                # Asegúrate de que el datetime sea timezone-aware para la resta
                aware_fecha_hora_programada = timezone.make_aware(fecha_hora_programada_completa)
                demora = now - aware_fecha_hora_programada
                demora_minutos = int(demora.total_seconds() / 60)
                
                # Marcar inicio real ahora
                viaje_asignado.fecha_hora_inicio_real = now
                viaje_asignado.demora_inicio_minutos = demora_minutos
                
                # Usar update_fields para solo actualizar las columnas necesarias y ser más rápido
                viaje_asignado.save(update_fields=['fecha_hora_inicio_real', 'demora_inicio_minutos'])

                # Actualizar estado del viaje (rápido)
                estado_en_curso, _ = EstadoViaje.objects.get_or_create(
                    nombre_estado='En curso',
                    defaults={'descripcion_estado': 'Viaje en curso'}
                )
                HistorialEstadoViaje.objects.create(
                    viaje=viaje_asignado,
                    estado_viaje=estado_en_curso,
                    fecha_cambio_estado=now
                )

        except Exception as e:
            logger.error(f"Error al iniciar viaje {viaje_asignado.id} en DB: {e}")
            messages.error(request, 'Error interno al actualizar el viaje. Intente nuevamente.')
            return redirect('chofer-recorridos')

        # 4. Delegar la Simulación a un Hilo (Operación Lenta)
        # Esto permite que el flujo principal continúe de inmediato.
        UbicacionColectivo.objects.filter(viaje=viaje_asignado).delete()
        simulation_thread = threading.Thread(
            target=self._run_simulation_async,
            args=(viaje_asignado.id,),
            daemon=True,
        )
        simulation_thread.start()
        
        # 5. Respuesta RÁPIDA (Redirección Inmediata)
        messages.success(request, f'Viaje al recorrido {viaje_asignado.recorrido.color_recorrido} iniciado correctamente.')
        return redirect('viaje-en-curso') # La velocidad está aquí

    def _run_simulation_async(self, viaje_id):
        """Wrapper para ejecutar la simulación y cerrar la conexión de DB del hilo."""
        try:
            # Re-obtener el viaje dentro del hilo
            viaje = Viaje.objects.get(pk=viaje_id) 
            self._simular_recorrido_ideal_optimizado(viaje)
        except Exception as e:
            logger.error(f"Error en simulación asíncrona para viaje {viaje_id}: {e}")
        finally:
            # ¡CRUCIAL! Cierra la conexión de la base de datos del hilo
            connection.close()


    def _simular_recorrido_ideal_optimizado(self, viaje: Viaje):
        """
        Genera ubicaciones futuras a intervalos regulares, usando bulk_create 
        para insertar todas las ubicaciones en una sola consulta.
        """
        recorrido = viaje.recorrido
        now = timezone.now()

        # 1) Ruta basada en las paradas cargadas
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
        
        # Funciones locales (Haversine e Interpolar)
        def haversine_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        def interp(a, b, t):
            return a + (b - a) * t

        # Lógica de ruteo OSRM y Fallback
        coords = self._route_with_osrm(raw_points)
        if not coords:
            coords = raw_points
        
        # Fallback manual suave
        if len(coords) < 2:
            coords = [
                 (-34.6037, -58.3816), # Obelisco
                 (-34.6045, -58.3780), 
                 (-34.6037, -58.3816),
            ]
        
        if len(coords) < 2:
            return

        # Parámetros de simulación
        target_speed_kmh = 25
        min_segment_seconds = 2
        interval_seconds = 1
        
        ubicaciones_a_crear = []
        current_ts = now

        # Punto inicial (para que el bus aparezca inmediatamente)
        ubicaciones_a_crear.append(
            UbicacionColectivo(
                latitud=coords[0][0],
                longitud=coords[0][1],
                timestamp_ubicacion=now,
                viaje=viaje,
            )
        )

        # Generación de puntos futuros (la parte que antes era lenta)
        for i in range(len(coords) - 1):
            (lat1, lng1) = coords[i]
            (lat2, lng2) = coords[i + 1]
            distance_km = haversine_km(lat1, lng1, lat2, lng2)
            if distance_km < 1e-6:
                distance_km = 0.001

            segment_seconds = max(min_segment_seconds, (distance_km / target_speed_kmh) * 3600)
            steps = max(1, int(segment_seconds / interval_seconds))
            seconds_per_step = segment_seconds / steps

            for s in range(1, steps + 1):
                f = s / steps
                lat = interp(lat1, lat2, f)
                lng = interp(lng1, lng2, f)
                current_ts += datetime.timedelta(seconds=seconds_per_step)
                
                ubicaciones_a_crear.append(
                    UbicacionColectivo(
                        latitud=lat,
                        longitud=lng,
                        timestamp_ubicacion=current_ts,
                        viaje=viaje,
                    )
                )

        # 2) ¡Optimización clave: Insertar todo en una sola consulta!
        # Esto reduce cientos o miles de consultas a UNA.
        UbicacionColectivo.objects.bulk_create(ubicaciones_a_crear)

        self._schedule_finalizacion(viaje.id, current_ts)

    def _schedule_finalizacion(self, viaje_id, final_timestamp):
        delay = max((final_timestamp - timezone.now()).total_seconds(), 0)
        timer = threading.Timer(delay, self._finalize_viaje_safe, args=(viaje_id, final_timestamp))
        timer.daemon = True
        timer.start()

    def _finalize_viaje_safe(self, viaje_id, final_timestamp):
        try:
            viaje = Viaje.objects.get(pk=viaje_id)
        except Viaje.DoesNotExist:
            return

        try:
            finalizar_viaje(viaje, timestamp=final_timestamp, registrar_inicio=False)
        except Exception as exc:
            logger.error("Error auto-finalizando viaje %s: %s", viaje_id, exc)
        finally:
            connection.close()

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


# --------------------------------------------------------------------------------------
# El resto de tus vistas (sin cambios)
# --------------------------------------------------------------------------------------

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
    # NOTA: Esta función no se usa si se usa IniciarRecorridoView, pero la mantengo
    # por si es necesaria en otro lugar.
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
