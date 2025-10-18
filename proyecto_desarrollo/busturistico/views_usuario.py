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
from .models import Consulta, Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido, ParadaAtractivo, RecorridoParada
from django.views import View
from django.shortcuts import render, redirect

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
        today = now.date()
        page_obj = context.get('page_obj')
        if page_obj:
            for recorrido in page_obj.object_list:
                viajes_qs = (
                    Viaje.objects
                    .filter(
                        recorrido=recorrido,
                        fecha_hora_inicio_real__isnull=True,
                        fecha_programada=today,
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
        today = now.date()
        viajes_qs = (
            Viaje.objects
            .filter(
                recorrido=self.object,
                fecha_hora_inicio_real__isnull=True,
                fecha_programada=today,
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

        viaje_id = self.request.GET.get('viaje_id')

        paradas_qs = list(
            RecorridoParada.objects
            .filter(recorrido=recorrido)
            .select_related('parada')
            .order_by('orden')
        )

        if len(paradas_qs) < 2:
            context['error'] = 'Se necesitan al menos dos paradas con coordenadas para trazar la ruta.'
            context['recorrido'] = recorrido
            return context
        warnings_list = []

        color_palette = {
            'rojo': '#dc3545',
            'verde': '#198754',
            'azul': '#0d6efd',
            'amarillo': '#ffc107',
            'naranja': '#fd7e14',
            'violeta': '#6f42c1',
            'purpura': '#6f42c1',
            'morado': '#6f42c1',
            'rosa': '#e83e8c',
            'celeste': '#0dcaf0',
            'cian': '#0dcaf0',
            'gris': '#6c757d',
        }

        def resolve_color(nombre: str) -> str:
            if not nombre:
                return '#0d6efd'
            key = nombre.strip().lower()
            return color_palette.get(key, '#0d6efd')

        def build_route_data(recorrido_obj, paradas_list):
            waypoints = [
                [p.parada.longitud_parada, p.parada.latitud_parada]
                for p in paradas_list
            ]
            osrm_route = None
            osrm_ok = False
            base_url = getattr(settings, 'OSRM_BASE_URL', '').strip() or 'https://router.project-osrm.org'
            base_url = base_url.rstrip('/')
            coordinates = ';'.join(f"{lon},{lat}" for lon, lat in waypoints)
            params = {'overview': 'full', 'geometries': 'geojson'}
            try:
                response = requests.get(f"{base_url}/route/v1/driving/{coordinates}", params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                if data.get('code') == 'Ok' and data.get('routes'):
                    osrm_route = data['routes'][0]['geometry']['coordinates']
                    osrm_ok = True
                else:
                    warnings_list.append(
                        f"OSRM no devolvió una ruta óptima para el recorrido {recorrido_obj.color_recorrido}."
                    )
            except requests.exceptions.HTTPError:
                warnings_list.append(
                    f"OSRM devolvió un estado inesperado para el recorrido {recorrido_obj.color_recorrido}."
                )
            except requests.RequestException:
                warnings_list.append(
                    f"No se pudo contactar a OSRM para el recorrido {recorrido_obj.color_recorrido}."
                )

            if osrm_ok and osrm_route:
                route_coords = [[coord[1], coord[0]] for coord in osrm_route]
                line_dash = None
            else:
                route_coords = [[wp[1], wp[0]] for wp in waypoints]
                line_dash = '6,6'

            coords_for_bounds = route_coords or [[wp[1], wp[0]] for wp in waypoints]
            if not coords_for_bounds:
                return None

            latitudes = [coord[0] for coord in coords_for_bounds]
            longitudes = [coord[1] for coord in coords_for_bounds]
            bounds = [
                [min(latitudes), min(longitudes)],
                [max(latitudes), max(longitudes)]
            ]
            center = [
                sum(latitudes) / len(latitudes),
                sum(longitudes) / len(longitudes)
            ]

            paradas_geo = [
                {
                    'lat': parada.parada.latitud_parada,
                    'lng': parada.parada.longitud_parada,
                    'nombre': parada.parada.nombre_parada,
                    'orden': parada.orden,
                }
                for parada in paradas_list
            ]

            return {
                'route_coords': route_coords,
                'route_color': resolve_color(recorrido_obj.color_recorrido),
                'line_dash': line_dash,
                'paradas_geo': paradas_geo,
                'bounds_points': coords_for_bounds,
                'bounds': bounds,
                'center': center,
                'paradas_objs': paradas_list,
            }

        default_delay_ms = 2000

        def build_animation_points(viaje_obj, route_coords):
            ubicaciones_qs = (
                UbicacionColectivo.objects
                .filter(viaje=viaje_obj)
                .exclude(latitud__isnull=True)
                .exclude(longitud__isnull=True)
                .order_by('timestamp_ubicacion')
            )

            ubicaciones = list(ubicaciones_qs)
            if ubicaciones:
                now_dt = timezone.now()
                past_points = [u for u in ubicaciones if u.timestamp_ubicacion <= now_dt]
                current_point = past_points[-1] if past_points else ubicaciones[0]
                future_candidates = [
                    u for u in ubicaciones
                    if u.timestamp_ubicacion > current_point.timestamp_ubicacion
                ]

                initial = {
                    'lat': current_point.latitud,
                    'lng': current_point.longitud,
                    'timestamp': current_point.timestamp_ubicacion.isoformat(),
                }

                future_points = []
                min_delay_ms = 500
                previous_ts = max(current_point.timestamp_ubicacion, now_dt)
                for punto in future_candidates:
                    delta = punto.timestamp_ubicacion - previous_ts
                    diff_ms = int(delta.total_seconds() * 1000) if delta else 0
                    if diff_ms <= 0:
                        diff_ms = default_delay_ms
                    future_points.append({
                        'lat': punto.latitud,
                        'lng': punto.longitud,
                        'delay_ms': max(diff_ms, min_delay_ms),
                        'timestamp': punto.timestamp_ubicacion.isoformat(),
                    })
                    previous_ts = punto.timestamp_ubicacion

                return initial, future_points

            if route_coords:
                now_dt = timezone.now()
                initial = {
                    'lat': route_coords[0][0],
                    'lng': route_coords[0][1],
                    'timestamp': now_dt.isoformat(),
                }
                future_points = [
                    {
                        'lat': coord[0],
                        'lng': coord[1],
                        'delay_ms': default_delay_ms,
                        'timestamp': now_dt.isoformat(),
                    }
                    for coord in route_coords[1:]
                ]
                return initial, future_points

            return None, []

        selected_route_data = build_route_data(recorrido, paradas_qs)
        if not selected_route_data:
            context['error'] = 'No se pudo construir la ruta para el recorrido seleccionado.'
            context['recorrido'] = recorrido
            return context

        route_cache = {recorrido.id: selected_route_data}
        paradas_cache = {recorrido.id: paradas_qs}

        base_active_viajes_qs = (
            Viaje.objects
            .filter(
                fecha_hora_inicio_real__isnull=False,
                fecha_hora_fin_real__isnull=True
            )
            .select_related('recorrido', 'patente_bus', 'chofer')
            .order_by('recorrido_id', 'fecha_hora_inicio_real')
        )

        base_active_viajes = list(base_active_viajes_qs)

        recorridos_filtrables = []
        seen_recorridos = set()
        for viaje in base_active_viajes:
            if viaje.recorrido_id not in seen_recorridos:
                seen_recorridos.add(viaje.recorrido_id)
                recorridos_filtrables.append(viaje.recorrido)

        selected_viaje_id = None
        if viaje_id and viaje_id.isdigit():
            selected_viaje_id = int(viaje_id)

        if selected_viaje_id:
            active_viajes = [v for v in base_active_viajes if v.id == selected_viaje_id]
        else:
            active_viajes = base_active_viajes

        map_payloads = []
        active_viajes_info = []
        all_coords = list(selected_route_data['bounds_points'])

        for viaje in active_viajes:
            data = route_cache.get(viaje.recorrido_id)
            if data is None:
                otras_paradas = list(
                    RecorridoParada.objects
                    .filter(recorrido=viaje.recorrido)
                    .select_related('parada')
                    .order_by('orden')
                )
                paradas_cache[viaje.recorrido_id] = otras_paradas
                if len(otras_paradas) < 2:
                    continue
                data = build_route_data(viaje.recorrido, otras_paradas)
                if not data:
                    continue
                route_cache[viaje.recorrido_id] = data

            initial_point, future_points = build_animation_points(viaje, data['route_coords'])
            bus_data = None
            if initial_point or future_points:
                if not initial_point and future_points:
                    initial_point = future_points[0]
                bus_data = {
                    'tooltip': f"Viaje #{viaje.id} · {viaje.recorrido.color_recorrido} · Bus {viaje.patente_bus.patente_bus}",
                    'initial_point': initial_point,
                    'future_points': future_points,
                    'marker_color': data['route_color'],
                    'pan_map': viaje.recorrido_id == recorrido.id,
                }

            map_payloads.append({
                'viaje_id': viaje.id,
                'recorrido_id': viaje.recorrido_id,
                'recorrido_color': viaje.recorrido.color_recorrido,
                'paradas_total': len(paradas_cache.get(viaje.recorrido_id, [])),
                'route_coords': data['route_coords'],
                'route_color': data['route_color'],
                'line_dash': data['line_dash'],
                'paradas': data['paradas_geo'],
                'bus': bus_data,
                'is_focused': viaje.recorrido_id == recorrido.id,
                'show_paradas': viaje.recorrido_id == recorrido.id,
            })
            all_coords.extend(data['bounds_points'])

            active_viajes_info.append({
                'viaje_id': viaje.id,
                'recorrido_id': viaje.recorrido_id,
                'recorrido_color': viaje.recorrido.color_recorrido,
                'bus_patente': viaje.patente_bus.patente_bus,
                'chofer': str(viaje.chofer),
                'is_focused': viaje.recorrido_id == recorrido.id,
            })

        if not any(payload['recorrido_id'] == recorrido.id for payload in map_payloads):
            map_payloads.append({
                'viaje_id': None,
                'recorrido_id': recorrido.id,
                'recorrido_color': recorrido.color_recorrido,
                'paradas_total': len(paradas_qs),
                'route_coords': selected_route_data['route_coords'],
                'route_color': selected_route_data['route_color'],
                'line_dash': selected_route_data['line_dash'],
                'paradas': selected_route_data['paradas_geo'],
                'bus': None,
                'is_focused': True,
                'show_paradas': True,
            })

        if not all_coords:
            all_coords = list(selected_route_data['bounds_points'])

        if all_coords:
            latitudes = [coord[0] for coord in all_coords]
            longitudes = [coord[1] for coord in all_coords]
            bounds = [
                [min(latitudes), min(longitudes)],
                [max(latitudes), max(longitudes)]
            ]
            map_center = [
                (min(latitudes) + max(latitudes)) / 2,
                (min(longitudes) + max(longitudes)) / 2
            ]
        else:
            bounds = selected_route_data['bounds']
            map_center = selected_route_data['center']

        context['recorrido'] = recorrido
        context['paradas'] = [p.parada for p in paradas_qs]
        context['active_viajes_info'] = active_viajes_info
        context['map_payloads'] = map_payloads
        context['map_payloads_json'] = json.dumps(map_payloads)
        context['map_center_json'] = json.dumps(map_center)
        context['map_bounds_json'] = json.dumps(bounds)
        context['animation_default_delay_ms'] = default_delay_ms
        context['selected_recorrido_id'] = recorrido.id
        context['selected_viaje_id'] = selected_viaje_id
        context['viajes_filtrables'] = base_active_viajes
        context['recorridos_filtrables'] = recorridos_filtrables
        context['has_active_viajes'] = bool(active_viajes_info)
        if warnings_list:
            context['warnings'] = warnings_list
        return context
