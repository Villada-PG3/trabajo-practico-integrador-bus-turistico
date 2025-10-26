from django.views.generic import TemplateView, ListView, CreateView, DetailView, View
from django.db.models import Count, Q
from django.utils import timezone
from .models import Consulta, Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido, ParadaAtractivo, RecorridoParada, Precio
from django.views import View
from django.shortcuts import render, redirect,  get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.conf import settings
from datetime import timedelta
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
                total_paradas=Count('recorridoparadas')  # usando recorridoparadas
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
        ctx = {
            "recorridos": Recorrido.objects.order_by("color_recorrido"),
            # opcional: si usás estos en el template
            "contacto_info": {
                "telefono": "5493513844333",
                "whatsapp": "5493513844333",
                "email": "busturistico49@gmail.com",
                "direccion": "Plaza de Mayo, CABA",
            },
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        # si querés guardar el NOMBRE del recorrido en la consulta
        rec_id = request.POST.get("recorrido_interes")
        rec_nombre = ""
        if rec_id:
            try:
                rec_nombre = Recorrido.objects.get(pk=rec_id).color_recorrido
            except Recorrido.DoesNotExist:
                rec_nombre = ""

        Consulta.objects.create(
            nombre=request.POST.get("nombre"),
            email=request.POST.get("email"),
            telefono=request.POST.get("telefono"),
            personas=request.POST.get("personas"),
            fecha_interes=request.POST.get("fecha_interes") or None,
            recorrido_interes=rec_nombre or request.POST.get("recorrido_interes"),  # guarda nombre si lo encontró
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
        context['precios'] = Precio.objects.all()
        return context

class UsuarioMapaFoliumView(TemplateView):
    template_name = 'usuario/mapa_folium.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recorridos_disponibles = (
            Recorrido.objects
            .filter(recorridoparadas__isnull=False)
            .distinct()
        )

        recorrido = None
        recorrido_id = self.request.GET.get('recorrido')
        if recorrido_id:
            recorrido = recorridos_disponibles.filter(pk=recorrido_id).first()
        if not recorrido:
            recorrido = recorridos_disponibles.first()

        if not recorrido:
            context['error'] = 'No hay recorridos con paradas cargadas para mostrar.'
            return context

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
            }

        route_data = build_route_data(recorrido, paradas_qs)
        if not route_data:
            context['error'] = 'No se pudo construir la ruta para el recorrido seleccionado.'
            context['recorrido'] = recorrido
            return context

        default_delay_ms = 2000
        now_dt = timezone.localtime()
        route_coords = route_data['route_coords']

        if not route_coords:
            context['error'] = 'No hay coordenadas suficientes para animar este recorrido.'
            context['recorrido'] = recorrido
            return context

        total_points = len(route_coords)
        period_ms = default_delay_ms * total_points
        cycle_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed_ms = int((now_dt - cycle_start).total_seconds() * 1000) % period_ms
        current_index = elapsed_ms // default_delay_ms
        ms_into_segment = elapsed_ms % default_delay_ms

        initial_point = {
            'lat': route_coords[current_index][0],
            'lng': route_coords[current_index][1],
            'timestamp': now_dt.isoformat(),
        }

        future_points = []
        time_cursor = now_dt
        remaining_delay = default_delay_ms - ms_into_segment if ms_into_segment else default_delay_ms

        loops = 2  # mantener el bus en movimiento un buen rato
        for step in range(1, total_points * loops + 1):
            next_index = (current_index + step) % total_points
            delay_ms = remaining_delay if step == 1 else default_delay_ms
            time_cursor += timedelta(milliseconds=delay_ms)
            future_points.append({
                'lat': route_coords[next_index][0],
                'lng': route_coords[next_index][1],
                'delay_ms': delay_ms,
                'timestamp': time_cursor.isoformat(),
            })
            remaining_delay = default_delay_ms

        map_payloads = [{
            'viaje_id': None,
            'recorrido_id': recorrido.id,
            'recorrido_color': recorrido.color_recorrido,
            'paradas_total': len(paradas_qs),
            'route_coords': route_coords,
            'route_color': route_data['route_color'],
            'line_dash': route_data['line_dash'],
            'paradas': route_data['paradas_geo'],
            'bus': {
                'tooltip': f"Simulación · Recorrido {recorrido.color_recorrido}",
                'initial_point': initial_point,
                'future_points': future_points,
                'marker_color': route_data['route_color'],
                'pan_map': True,
            },
            'is_focused': True,
            'show_paradas': True,
        }]

        active_viajes_info = [{
            'viaje_id': None,
            'recorrido_id': recorrido.id,
            'recorrido_color': recorrido.color_recorrido,
            'bus_patente': f"SIM-{recorrido.id}",
            'chofer': 'Simulación',
            'is_focused': True,
        }]

        context['recorrido'] = recorrido
        context['paradas'] = [p.parada for p in paradas_qs]
        context['active_viajes_info'] = active_viajes_info
        context['map_payloads'] = map_payloads
        context['map_payloads_json'] = json.dumps(map_payloads)
        context['map_center_json'] = json.dumps(route_data['center'])
        context['map_bounds_json'] = json.dumps(route_data['bounds'])
        context['animation_default_delay_ms'] = default_delay_ms
        context['selected_recorrido_id'] = recorrido.id
        context['selected_viaje_id'] = None
        context['viajes_filtrables'] = []
        context['recorridos_filtrables'] = list(recorridos_disponibles)
        context['has_active_viajes'] = True
        if warnings_list:
            context['warnings'] = warnings_list
        return context
