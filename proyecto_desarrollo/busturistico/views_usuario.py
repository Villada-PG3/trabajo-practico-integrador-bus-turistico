from django.views.generic import TemplateView, ListView, CreateView, DetailView
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.conf import settings
from .models import (
    Bus,
    Chofer,
    Viaje,
    EstadoBusHistorial,
    EstadoBus,
    EstadoViaje,
    Parada,
    Recorrido,
    ParadaAtractivo,
    RecorridoParada,
    UbicacionColectivo,
)
import requests
import json

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
                total_paradas=Count('recorridoparadas')  # CORREGIDO: usar recorridoparadas
            ).order_by('-total_paradas')[:3],
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

# Mapa en vivo (Leaflet + polling)
class UsuarioMapaView(TemplateView):
    template_name = 'usuario/mapa.html'


class UsuarioMapaFoliumView(TemplateView):
    template_name = 'usuario/mapa_folium.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        recorrido_id = self.request.GET.get('recorrido')
        recorrido = None

        if recorrido_id:
            recorrido = Recorrido.objects.filter(pk=recorrido_id).first()
        if not recorrido:
            recorrido = (
                Recorrido.objects
                .filter(recorridoparadas__isnull=False)
                .distinct()
                .first()
            )

        if not recorrido:
            context['error'] = 'No hay recorridos con paradas cargadas para mostrar.'
            return context

        paradas = list(
            RecorridoParada.objects
            .filter(recorrido=recorrido)
            .select_related('parada')
            .order_by('orden')
        )

        if len(paradas) < 2:
            context['error'] = 'Se necesitan al menos dos paradas con coordenadas para trazar la ruta.'
            context['recorrido'] = recorrido
            return context

        waypoints = [
            [p.parada.longitud_parada, p.parada.latitud_parada]
            for p in paradas
        ]

        base_url = getattr(settings, 'OSRM_BASE_URL', '').strip() or 'https://router.project-osrm.org'
        base_url = base_url.rstrip('/')
        coordinates = ';'.join(f"{lon},{lat}" for lon, lat in waypoints)
        params = {
            'overview': 'full',
            'geometries': 'geojson',
        }

        osrm_route = None
        try:
            response = requests.get(f"{base_url}/route/v1/driving/{coordinates}", params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'Ok' and data.get('routes'):
                    osrm_route = data['routes'][0]['geometry']['coordinates']
            else:
                context['warning'] = 'OSRM devolvió un estado inesperado.'
        except requests.RequestException:
            context['warning'] = 'No se pudo contactar al servicio OSRM.'

        route_latlon = []
        if osrm_route:
            route_latlon = [[coord[1], coord[0]] for coord in osrm_route]
        else:
            route_latlon = [[wp[1], wp[0]] for wp in waypoints]

        paradas_geo = [
            {
                'lat': parada.parada.latitud_parada,
                'lng': parada.parada.longitud_parada,
                'nombre': parada.parada.nombre_parada,
                'orden': parada.orden,
            }
            for parada in paradas
        ]

        coords_for_bounds = route_latlon or [[wp[1], wp[0]] for wp in waypoints]
        latitudes = [coord[0] for coord in coords_for_bounds]
        longitudes = [coord[1] for coord in coords_for_bounds]
        if latitudes and longitudes:
            bounds = [
                [min(latitudes), min(longitudes)],
                [max(latitudes), max(longitudes)]
            ]
        else:
            bounds = [[waypoints[0][1], waypoints[0][0]], [waypoints[0][1], waypoints[0][0]]]

        map_center = [waypoints[0][1], waypoints[0][0]]
        route_color = 'blue' if osrm_route else 'red'

        # Preparar animación para el colectivo en viaje
        default_delay_ms = 2000
        animation_points = []
        viaje_en_curso = (
            Viaje.objects
            .filter(
                recorrido=recorrido,
                fecha_hora_inicio_real__isnull=False,
                fecha_hora_fin_real__isnull=True
            )
            .select_related('patente_bus', 'chofer')
            .order_by('fecha_hora_inicio_real')
            .first()
        )

        if viaje_en_curso:
            ubicaciones_qs = (
                UbicacionColectivo.objects
                .filter(viaje=viaje_en_curso)
                .exclude(latitud__isnull=True)
                .exclude(longitud__isnull=True)
                .order_by('timestamp_ubicacion')
            )[:600]

            ubicaciones = list(ubicaciones_qs)
            if ubicaciones:
                animation_points = [
                    {
                        'lat': ubicacion.latitud,
                        'lng': ubicacion.longitud,
                        'timestamp': ubicacion.timestamp_ubicacion.isoformat()
                    }
                    for ubicacion in ubicaciones
                ]

                if len(animation_points) > 1:
                    for idx in range(len(animation_points) - 1):
                        current_ts = ubicaciones[idx].timestamp_ubicacion
                        next_ts = ubicaciones[idx + 1].timestamp_ubicacion
                        delta = next_ts - current_ts
                        diff_ms = int(delta.total_seconds() * 1000) if delta else 0
                        if diff_ms <= 0:
                            diff_ms = default_delay_ms
                        animation_points[idx]['delay_to_next_ms'] = max(diff_ms, 750)
                    animation_points[-1]['delay_to_next_ms'] = None
                else:
                    animation_points[0]['delay_to_next_ms'] = None
            elif route_latlon:
                # Fallback: animar siguiendo la polilínea calculada aunque no haya ubicaciones registradas todavía
                now_iso = timezone.now().isoformat()
                animation_points = [
                    {
                        'lat': coord[0],
                        'lng': coord[1],
                        'timestamp': now_iso,
                        'delay_to_next_ms': None,
                    }
                    for coord in route_latlon
                ]
                if len(animation_points) > 1:
                    for idx in range(len(animation_points) - 1):
                        animation_points[idx]['delay_to_next_ms'] = default_delay_ms
                    animation_points[-1]['delay_to_next_ms'] = None

        context['recorrido'] = recorrido
        context['paradas'] = [p.parada for p in paradas]
        context['map_center_json'] = json.dumps(map_center)
        context['map_bounds_json'] = json.dumps(bounds)
        context['route_coords_json'] = json.dumps(route_latlon)
        context['paradas_geo_json'] = json.dumps(paradas_geo)
        context['route_color'] = route_color
        context['viaje_en_curso'] = viaje_en_curso
        context['animation_points_json'] = json.dumps(animation_points)
        context['animation_default_delay_ms'] = default_delay_ms
        return context
