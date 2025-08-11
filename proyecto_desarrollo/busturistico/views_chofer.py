# views_chofer.py
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, View
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from .models import Recorrido, Viaje, Chofer, EstadoViaje, Bus

@method_decorator(login_required, name='dispatch')
class ChoferRecorridosView(ListView):
    model = Recorrido
    template_name = 'chofer/recorridos.html'
    context_object_name = 'recorridos'
    paginate_by = 6

    def get_queryset(self):
        # CORREGIDO: usar color_recorrido en lugar de nombre_recorrido
        return Recorrido.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Asumiendo que vincularás User con Chofer en el futuro
        # Por ahora, podrías usar el primer chofer o manejarlo de otra forma
        try:
            context['chofer'] = Chofer.objects.first()  # Temporal
        except Chofer.DoesNotExist:
            context['chofer'] = None
        return context

@method_decorator(login_required, name='dispatch')
class IniciarRecorridoView(View):
    def post(self, request, pk):
        # Temporal: usar el primer chofer disponible
        chofer = Chofer.objects.filter(activo=True).first()
        if not chofer:
            # Redireccionar con mensaje de error
            return redirect('chofer-recorridos')
            
        recorrido = get_object_or_404(Recorrido, pk=pk)
        
        # Obtener o crear estado "En curso"
        estado_en_curso, created = EstadoViaje.objects.get_or_create(
            nombre_estado='En curso',
            defaults={'descripcion_estado': 'Viaje en curso'}
        )
        
        # Obtener un bus disponible (el primer operativo)
        try:
            bus_disponible = Bus.objects.filter(
                estadobushistorial__estado_bus__nombre_estado='Operativo'
            ).first()
            
            if not bus_disponible:
                # Si no hay buses disponibles, usar el primero que encuentres
                bus_disponible = Bus.objects.first()
                
        except Bus.DoesNotExist:
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
        
        return redirect('chofer-recorridos')