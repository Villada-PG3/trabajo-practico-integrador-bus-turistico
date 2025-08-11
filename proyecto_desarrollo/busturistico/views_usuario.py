from django.views.generic import TemplateView, ListView, CreateView, DetailView
from django.db.models import Count, Avg, Q
from django.utils import timezone
from .models import Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido, ParadaAtractivo, RecorridoParada

class UsuarioInicioView(TemplateView):
    template_name = 'usuario/inicio.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas para mostrar en la página
        context.update({
            'total_recorridos': Recorrido.objects.count(),
            'total_paradas': Parada.objects.count(),
            'buses_operativos': Bus.objects.filter(
                estadobushistorial__estado_bus__nombre_estado='Operativo'
            ).distinct().count(),
            'recorridos_populares': Recorrido.objects.annotate(
                total_paradas=Count('recorridoparada')
            ).order_by('-total_paradas')[:3],
        })
        
        return context

class UsuarioRecorridosView(ListView):
    model = Recorrido
    template_name = 'usuario/recorridos.html'
    context_object_name = 'recorridos'
    paginate_by = 6  # Paginación para mejor UX
    
    def get_queryset(self):
        queryset = Recorrido.objects.annotate(
            total_paradas=Count('recorridoparada')
        ).prefetch_related('recorridoparada__parada')
        
        # Filtro por búsqueda si existe
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre_recorrido__icontains=search) |
                Q(descripcion_recorrido__icontains=search)
            )
            
        return queryset.order_by('nombre_recorrido')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class UsuarioDetalleRecorridoView(DetailView):
    model = Recorrido
    template_name = 'usuario/detalle_recorrido.html'
    context_object_name = 'recorrido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paradas_recorrido = RecorridoParada.objects.filter(
            recorrido=self.object
        ).select_related('parada').order_by('orden')
        
        context.update({
            'paradas': paradas_recorrido,
            'total_paradas': paradas_recorrido.count(),
            'duracion_estimada': paradas_recorrido.count() * 30,  # 30 min por parada aprox
            'proximos_horarios': self.get_proximos_horarios(),
        })
        return context
    
    def get_proximos_horarios(self):
        """Simular próximos horarios (deberías ajustar según tu lógica de negocio)"""
        from datetime import datetime, timedelta
        
        base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        horarios = []
        
        for i in range(6):  # 6 horarios del día
            horario = base_time + timedelta(hours=i*2)
            if horario > datetime.now():
                horarios.append(horario.strftime('%H:%M'))
                
        return horarios

class UsuarioDetalleParadaView(DetailView):
    model = Parada
    template_name = 'usuario/detalle_parada.html'
    context_object_name = 'parada'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atractivos = ParadaAtractivo.objects.filter(parada=self.object)
        
        # Recorridos que incluyen esta parada
        recorridos_relacionados = Recorrido.objects.filter(
            recorridoparada__parada=self.object
        ).distinct()
        
        context.update({
            'atractivos': atractivos,
            'total_atractivos': atractivos.count(),
            'recorridos_relacionados': recorridos_relacionados,
        })
        return context

class UsuarioContactoView(TemplateView):
    template_name = 'usuario/contacto.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'horarios_atencion': {
                'lunes_viernes': '08:00 - 18:00',
                'sabados': '09:00 - 17:00',
                'domingos': '10:00 - 16:00',
            },
            'contacto_info': {
                'telefono': '+54 9 11 1234-5678',
                'email': 'info@busturistico.com',
                'direccion': 'La Calera, Córdoba, Argentina',
                'whatsapp': '+54 9 11 1234-5678',
            }
        })
        return context

# Vista adicional para búsqueda AJAX (opcional)
class UsuarioBusquedaView(TemplateView):
    template_name = 'usuario/busqueda.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        
        if query:
            recorridos = Recorrido.objects.filter(
                Q(nombre_recorrido__icontains=query) |
                Q(descripcion_recorrido__icontains=query)
            )[:5]
            
            paradas = Parada.objects.filter(
                Q(nombre_parada__icontains=query) |
                Q(direccion_parada__icontains=query)
            )[:5]
            
            context.update({
                'query': query,
                'recorridos': recorridos,
                'paradas': paradas,
            })
            
        return context