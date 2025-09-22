from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Recorrido, Viaje, Chofer, EstadoViaje, Bus
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import datetime
import logging

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

        messages.success(request, f'Viaje al recorrido {viaje_asignado.recorrido.color_recorrido} iniciado correctamente.')
        return redirect('viaje-en-curso')

    def _simular_recorrido_ideal(self, viaje: Viaje):
        """
        Genera ubicaciones futuras a intervalos regulares recorriendo las paradas del recorrido.
        La API pública ignora timestamps futuros, por lo que el mapa mostrará el avance con el tiempo.
        """
        recorrido = viaje.recorrido
        now = timezone.now()

        # 1) Intentar usar las paradas del recorrido cargadas en DB
        rps = list(RecorridoParada.objects.filter(recorrido=recorrido).select_related('parada').order_by('orden'))

        coords = []
        if len(rps) >= 2:
            coords = [(rp.parada.latitud_parada, rp.parada.longitud_parada) for rp in rps]
        else:
            # 2) Fallback: si es el Recorrido Verde, usar coordenadas aproximadas conocidas
            color = (recorrido.color_recorrido or '').strip().lower()
            if 'verde' in color:
                # Orden provisto por el usuario
                coords = [
                    (-34.5569, -58.4016),  # 03 Club de Pescadores
                    (-34.5686, -58.4100),  # 02 Planetario
                    (-34.5834, -58.4037),  # 01 MALBA (conexion)
                    (-34.5705, -58.4116),  # 11 Monumento a los Españoles (conexion)
                    (-34.5855, -58.4307),  # 10 Palermo Soho II (aprox)
                    (-34.5746, -58.4260),  # 09 Distrito Arcos II (aprox)
                    (-34.5413, -58.4313),  # 04 Parque de la Memoria
                    (-34.5453, -58.4493),  # 05 El Monumental
                    (-34.5610, -58.4491),  # 06 Belgrano Barrio Chino
                    (-34.5697, -58.4255),  # 07 Campo Argentino de Polo
                    (-34.5655, -58.4155),  # 08 Bosques de Palermo (conexion)
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

        # Parámetros de simulación: 6 pasos por tramo, cada 10 segundos
        steps_per_segment = 6
        interval_seconds = 10

        def interp(a, b, t):
            return a + (b - a) * t

        step_index = 1
        for i in range(len(coords) - 1):
            (lat1, lng1) = coords[i]
            (lat2, lng2) = coords[i + 1]
            for s in range(1, steps_per_segment + 1):
                f = s / steps_per_segment
                lat = interp(lat1, lat2, f)
                lng = interp(lng1, lng2, f)
                ts = now + datetime.timedelta(seconds=step_index * interval_seconds)
                UbicacionColectivo.objects.create(
                    latitud=lat,
                    longitud=lng,
                    timestamp_ubicacion=ts,
                    viaje=viaje,
                )
                step_index += 1
    
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