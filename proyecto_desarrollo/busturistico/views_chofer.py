from django.contrib.auth.decorators import login_required
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
            raise PermissionDenied("No tiene permisos de chofer.")
        
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

