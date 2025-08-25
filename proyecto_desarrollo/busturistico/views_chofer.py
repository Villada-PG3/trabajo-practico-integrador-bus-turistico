from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Recorrido, Viaje, Chofer, EstadoViaje, Bus
from django.contrib import messages
from django.core.exceptions import PermissionDenied

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
    model = Recorrido
    template_name = 'chofer/recorridos.html'
    context_object_name = 'recorridos'
    paginate_by = 6

    def get_queryset(self):
        return Recorrido.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chofer = self.request.chofer
        context['chofer'] = chofer

        # Buscar el viaje en curso para este chofer
        viaje_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).select_related('patente_bus', 'recorrido').first()

        # Asignar el viaje y el bus al contexto
        if viaje_en_curso:
            context['viaje_en_curso'] = viaje_en_curso
            context['bus_asignado'] = viaje_en_curso.patente_bus
            context['recorrido_en_curso_id'] = viaje_en_curso.recorrido.id
        else:
            context['viaje_en_curso'] = None
            context['bus_asignado'] = None
            context['recorrido_en_curso_id'] = None
            
        return context

class IniciarRecorridoView(ChoferRequiredMixin, View):
    def post(self, request, pk):
        chofer = request.chofer
        recorrido = get_object_or_404(Recorrido, pk=pk)

        viaje_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).first()

        if viaje_en_curso:
            messages.error(request, 'Ya tienes un viaje en curso. Debes finalizarlo antes de iniciar otro.')
            # Redirigir a la nueva página de detalles del viaje en curso
            return redirect('viaje-en-curso')
        
        # Obtener o crear estado "En curso"
        estado_en_curso, created = EstadoViaje.objects.get_or_create(
            nombre_estado='En curso',
            defaults={'descripcion_estado': 'Viaje en curso'}
        )
        
        # Obtener un bus disponible
        try:
            bus_disponible = Bus.objects.filter(
                estadobushistorial__estado_bus__nombre_estado='Operativo'
            ).first()
            
            if not bus_disponible:
                bus_disponible = Bus.objects.first()
                
        except Bus.DoesNotExist:
            messages.error(request, 'No hay buses disponibles.')
            return redirect('chofer-recorridos')
        
        # Crear viaje
        viaje = Viaje.objects.create(
            chofer=chofer,
            recorrido=recorrido,
            patente_bus=bus_disponible,
            fecha_programada=timezone.now(),
            hora_inicio_programada=timezone.now().time(),
            fecha_hora_inicio_real=timezone.now(),
        )
        
        messages.success(request, f'Recorrido {recorrido.color_recorrido} iniciado correctamente.')
        # Redirigir a la nueva página de detalles del viaje en curso
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