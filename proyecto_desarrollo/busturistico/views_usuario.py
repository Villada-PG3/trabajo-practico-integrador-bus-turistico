from django.views.generic import TemplateView, ListView, CreateView, DetailView, View
from django.db.models import Count, Avg, Q
from django.utils import timezone
from .models import Consulta, Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido, ParadaAtractivo, RecorridoParada, Precio
from django.views import View
from django.shortcuts import render, redirect,  get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages

class MapaView(TemplateView):
    template_name = "usuario/mapa.html"


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
                total_paradas=Count('recorridoparadas')  # usando recorridoparadas
            ).order_by('-total_paradas')[:3],
            # 🔥 Precios
            'precios': Precio.objects.all(),
        })
        
        return context

class UsuarioRecorridosView(ListView):
    model = Recorrido
    template_name = 'usuario/recorridos.html'
    context_object_name = 'recorridos'
    paginate_by = 6  # Paginación para mejor UX
    
    def get_queryset(self):
        # CORREGIDO: Usar related_name correcto
        queryset = Recorrido.objects.annotate(
            total_paradas=Count('recorridoparadas')  # CORREGIDO: usar recorridoparadas
        ).prefetch_related('recorridoparadas__parada')
        
        # Filtro por búsqueda si existe
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(color_recorrido__icontains=search) |
                Q(descripcion_recorrido__icontains=search)
            )
            
        return queryset.order_by('color_recorrido')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')

        # Adjuntar próximos horarios de viajes programados a cada recorrido de la página actual
        now = timezone.localtime()
        page_obj = context.get('page_obj')
        if page_obj:
            for recorrido in page_obj.object_list:
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

                # Guardar una lista de strings HH:MM (máximo 3) para usar en la plantilla
                recorrido.proximos_horarios = [
                    v.hora_inicio_programada.strftime('%H:%M') for v in viajes_qs[:3]
                ]
        return context

class UsuarioDetalleRecorridoView(DetailView):
    model = Recorrido
    template_name = 'usuario/detalle_recorrido.html'
    context_object_name = 'recorrido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # CORREGIDO: Usar RecorridoParada correctamente
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
        """Obtener próximos horarios de viajes programados (no iniciados) para el recorrido."""
        now = timezone.localtime()
        viajes_qs = (
            Viaje.objects
            .filter(
                recorrido=self.object,
                fecha_hora_inicio_real__isnull=True,
                fecha_programada__date=now.date(),
                hora_inicio_programada__gte=now.time(),
            )
            .order_by('hora_inicio_programada')
        )

        # Devolver hasta 6 próximos horarios como strings HH:MM
        return [v.hora_inicio_programada.strftime('%H:%M') for v in viajes_qs[:6]]

class UsuarioDetalleParadaView(DetailView):
    model = Parada
    template_name = 'usuario/detalle_parada.html'
    context_object_name = 'parada'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atractivos = ParadaAtractivo.objects.filter(parada=self.object)
        
        # Recorridos que incluyen esta parada
        # CORREGIDO: Usar recorridoparadas en lugar de recorridoparada
        recorridos_relacionados = Recorrido.objects.filter(
            recorridoparadas__parada=self.object
        ).distinct()
        
        context.update({
            'atractivos': atractivos,
            'total_atractivos': atractivos.count(),
            'recorridos_relacionados': recorridos_relacionados,
        })
        return context

class UsuarioContactoView(View):
    template_name = "usuario/contacto.html"

    def get(self, request, *args, **kwargs):
        # lo mismo que tenías
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        Consulta.objects.create(
            nombre=request.POST.get("nombre"),
            email=request.POST.get("email"),
            telefono=request.POST.get("telefono"),
            personas=request.POST.get("personas"),
            fecha_interes=request.POST.get("fecha_interes") or None,
            recorrido_interes=request.POST.get("recorrido_interes"),
            mensaje=request.POST.get("mensaje"),
        )
        return redirect("/contacto/?success=1")

# Vista adicional para búsqueda AJAX (opcional)
class UsuarioBusquedaView(TemplateView):
    template_name = 'usuario/busqueda.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        
        if query:
            recorridos = Recorrido.objects.filter(
                Q(color_recorrido__icontains=query) |
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


class UsuarioPreciosView(TemplateView):
    template_name = 'usuario/precios.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_precios'] = 'Precios Bus Turístico Buenos Aires'
        context['subtitulo_precios'] = 'Elegí el pase que más te convenga'
        context['precios'] = Precio.objects.all()  # <- asegurate que trae objetos
        return context

