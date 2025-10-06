from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, OuterRef, Subquery, Q, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
)

from math import radians, sin, cos, sqrt, atan2
import json

from .models import (
    Atractivo, Bus, Chofer, EstadoBus, EstadoBusHistorial, EstadoViaje,
    HistorialEstadoViaje, Parada, ParadaAtractivo, Recorrido, RecorridoParada,
    UbicacionColectivo, Viaje
)
from .forms import (
    AtractivoForm, BusForm, ChoferForm, EstadoBusHistorialForm, ParadaForm,
    RecorridoForm, ViajeCreateForm
)


# --- Mixins and Helper Functions ---
class SuperUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para asegurar que solo los superusuarios puedan acceder a una vista.
    """
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('admin:login')

def haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia de la gran-círculo entre dos puntos
    en la tierra (especificados en coordenadas decimales)
    """
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance


# --- Dashboard Views ---
class DashboardView(SuperUserRequiredMixin, TemplateView):
    template_name = 'admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch bus statuses with optimized query
        estado_buses = []
        for bus in Bus.objects.all():
            historial = EstadoBusHistorial.objects.filter(patente_bus=bus).order_by('-fecha_inicio_estado').first()
            estado = historial.estado_bus.nombre_estado if historial else 'Sin estado'
            estado_buses.append((bus, estado))
        # Count active buses (where the latest status is "Activo")
        buses_activos = sum(1 for bus, estado in estado_buses if estado.lower() == 'activo')
        # Fetch active drivers
        choferes_activos = Chofer.objects.filter(activo=True).count()
        # Fetch ongoing trips (for "En Curso")
        ahora = timezone.now()
        viajes_en_curso = Viaje.objects.filter(
            fecha_hora_inicio_real__lte=ahora,
            fecha_hora_fin_real__isnull=True
        ).count()
        # Fetch programmed trips (for "Programados")
        viajes_programados = Viaje.objects.filter(
            fecha_hora_inicio_real__isnull=True,  # No han comenzado
            fecha_programada__gte=ahora.date()     # Programados para hoy o futuro
        ).count()

        # Update context with dynamic data for the template
        context.update({
            'estado_buses': estado_buses,
            'buses_activos': buses_activos,
            'choferes_activos': choferes_activos,
            'viajes_en_curso': viajes_en_curso,    # Mantener para "En Curso" si lo necesitas
            'viajes_programados': viajes_programados,  # Nuevo conteo para "Programados"
        })
        return context


# --- Chofer Management Views ---
class ChoferesView(SuperUserRequiredMixin, ListView):
    template_name = 'admin/chofer.html'
    model = Chofer
    context_object_name = 'choferes_total'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estado_filter = self.request.GET.get('estado')
        
        bus_asignado_subquery = Viaje.objects.filter(
            chofer=OuterRef('pk'),
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).order_by('-fecha_hora_inicio_real').values('patente_bus__patente_bus')[:1]

        choferes_annotados = Chofer.objects.annotate(
            viajes_realizados=Count('viaje'),
            bus_asignado_actual=Subquery(bus_asignado_subquery)
        )
        
        choferes_data = []
        choferes_activos = []
        choferes_inactivos = []

        for chofer in choferes_annotados:
            is_activo = chofer.bus_asignado_actual is not None
            chofer.estado_dinamico = 'Activo' if is_activo else 'Inactivo'
            
            if is_activo:
                choferes_activos.append(chofer)
            else:
                choferes_inactivos.append(chofer)
            
            if estado_filter == 'activos' and not is_activo:
                continue
            if estado_filter == 'inactivos' and is_activo:
                continue
            
            choferes_data.append(chofer)

        context.update({
            'choferes_total': choferes_annotados,
            'choferes_activos': choferes_activos,
            'choferes_inactivos': choferes_inactivos,
            'choferes_filtrados': choferes_data,
            'estado_filter': estado_filter,
        })
        return context

class CrearChoferView(SuperUserRequiredMixin, CreateView):
    model = Chofer
    form_class = ChoferForm
    template_name = 'admin/chofer_form.html'
    success_url = reverse_lazy('admin-choferes')

class EditarChoferView(SuperUserRequiredMixin, UpdateView):
    model = Chofer
    form_class = ChoferForm
    template_name = 'admin/chofer_form.html'
    success_url = reverse_lazy('admin-choferes')
    
class EliminarChoferView(SuperUserRequiredMixin, DeleteView):
    model = Chofer
    success_url = reverse_lazy('admin-choferes')
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, f'Chofer {self.object.nombre_chofer} eliminado correctamente.')
        return redirect(self.get_success_url())

def eliminar_chofer_directo(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Acceso no autorizado'}, status=403)
        
    try:
        chofer = get_object_or_404(Chofer, pk=pk)
        chofer.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
class ChoferDetailView(SuperUserRequiredMixin, DetailView):
    model = Chofer
    template_name = 'admin/chofer_detalle.html'
    context_object_name = 'chofer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chofer = self.object
        
        # This is the key query.
        viaje_asignado = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).first()

        context['viaje_asignado'] = viaje_asignado
        return context

# --- Bus/Flota Management Views ---
class FlotaView(SuperUserRequiredMixin, TemplateView):
    template_name = 'admin/flota.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        buses_total = Bus.objects.all()
        bus_data = []
        estado_counts = {}
        estados_disponibles = EstadoBus.objects.all()

        for estado in estados_disponibles:
            estado_counts[estado.nombre_estado.lower()] = 0
        estado_counts['activo'] = 0
        estado_counts['sin_estado'] = 0

        estado_filter = self.request.GET.get('estado', '').lower()

        for bus in buses_total:
            viaje_activo = Viaje.objects.filter(
                patente_bus=bus,
                fecha_hora_inicio_real__isnull=False,
                fecha_hora_fin_real__isnull=True
            ).exists()

            if viaje_activo:
                estado_bus_nombre = 'activo'
            else:
                historial = EstadoBusHistorial.objects.filter(patente_bus=bus).order_by('-fecha_inicio_estado').first()
                estado_bus_nombre = historial.estado_bus.nombre_estado.lower() if historial else 'sin_estado'
            
            estado_counts[estado_bus_nombre] = estado_counts.get(estado_bus_nombre, 0) + 1

            if estado_filter and estado_bus_nombre != estado_filter:
                continue

            last_mant = EstadoBusHistorial.objects.filter(
                patente_bus=bus, 
                estado_bus__nombre_estado__iexact='en mantenimiento'
            ).order_by('-fecha_inicio_estado').first()
            ultimo_mantenimiento = last_mant.fecha_inicio_estado if last_mant else None

            bus_data.append({
                'bus': bus,
                'estado': estado_bus_nombre.capitalize() if estado_bus_nombre != 'sin_estado' else 'Sin Estado',
                'ultimo_mantenimiento': ultimo_mantenimiento
            })

        context.update({
            'buses_total': buses_total,
            'bus_data': bus_data,
            'estado_counts': estado_counts,
            'estados_disponibles': estados_disponibles,
            'estado_filter': estado_filter
        })
        return context

class BusDetailView(SuperUserRequiredMixin, DetailView):
    model = Bus
    template_name = 'admin/flota_detalle.html'
    context_object_name = 'bus'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bus = self.object
        ahora = timezone.now()
        viaje_actual = Viaje.objects.filter(
            patente_bus=bus,
            fecha_hora_inicio_real__lte=ahora,
            fecha_hora_fin_real__isnull=True
        ).first()
        context['viaje_actual'] = viaje_actual

        if viaje_actual:
            context['estado_actual'] = 'Activo'
            context['recorrido_actual'] = viaje_actual.recorrido
            ubicacion_actual = UbicacionColectivo.objects.filter(viaje=viaje_actual).order_by('-timestamp_ubicacion').first()
            context['ubicacion_actual'] = ubicacion_actual
            
            if ubicacion_actual:
                paradas = RecorridoParada.objects.filter(recorrido=viaje_actual.recorrido).select_related('parada')
                if paradas:
                    try:
                        closest = min(paradas, key=lambda rp: haversine(
                            ubicacion_actual.latitud, ubicacion_actual.longitud,
                            rp.parada.latitud_parada, rp.parada.longitud_parada
                        ))
                        context['closest_parada'] = closest.parada
                    except (ValueError, TypeError) as e:
                        context['closest_parada'] = None
        else:
            historial = EstadoBusHistorial.objects.filter(patente_bus=bus).order_by('-fecha_inicio_estado').first()
            context['estado_actual'] = historial.estado_bus.nombre_estado if historial else 'Sin estado'
            context['recorrido_actual'] = None
            context['ubicacion_actual'] = None
            context['closest_parada'] = None

        last_mant = EstadoBusHistorial.objects.filter(
            patente_bus=bus,
            estado_bus__nombre_estado__iexact='en mantenimiento'
        ).order_by('-fecha_inicio_estado').first()
        context['ultimo_mantenimiento'] = last_mant.fecha_inicio_estado if last_mant else None
        return context

class CrearBusView(SuperUserRequiredMixin, CreateView):
    model = Bus
    form_class = BusForm
    template_name = 'admin/flota_form.html'
    success_url = reverse_lazy('admin-flota')

    def form_valid(self, form):
        response = super().form_valid(form)
        estado_inicial = EstadoBus.objects.get_or_create(nombre_estado='Operativo')[0]
        EstadoBusHistorial.objects.create(
            patente_bus=self.object,
            estado_bus=estado_inicial,
            fecha_inicio_estado=timezone.now()
        )
        return response

class EditarBusView(SuperUserRequiredMixin, UpdateView):
    model = Bus
    form_class = BusForm
    template_name = 'admin/flota_form.html'
    success_url = reverse_lazy('admin-flota')

class EliminarBusView(SuperUserRequiredMixin, DeleteView):
    model = Bus
    template_name = 'admin/bus_confirm_delete.html'
    success_url = reverse_lazy('admin-flota')

class CambiarEstadoBusView(SuperUserRequiredMixin, CreateView):
    model = EstadoBusHistorial
    fields = ['estado_bus']
    template_name = 'admin/cambiar_estado_bus.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = get_object_or_404(Bus, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        form.instance.patente_bus = get_object_or_404(Bus, pk=self.kwargs['pk'])
        form.instance.fecha_inicio_estado = timezone.now()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('admin-detalle-bus', kwargs={'pk': self.kwargs['pk']})


# --- Viaje Management Views ---
class ViajesView(SuperUserRequiredMixin, TemplateView):
    template_name = 'admin/viajes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get('status', 'en_curso').lower()
        
        # Base queryset con prefetch para eficiencia
        all_trips = Viaje.objects.select_related('patente_bus', 'chofer', 'recorrido').prefetch_related(
            'ubicacioncolectivo_set', 
            'recorrido__recorridoparadas__parada'  # Corrige a 'recorridoparadas'
        ).order_by('-fecha_programada')
        
        trips_with_status = []
        counts = {'en_curso': 0, 'programados': 0, 'completados': 0}
        
        for viaje in all_trips:
            # Determinar estado_actual (dinámico para template)
            if viaje.fecha_hora_fin_real:
                viaje.estado_actual = 'Completado'
                counts['completados'] += 1
            elif viaje.fecha_hora_inicio_real:
                viaje.estado_actual = 'En Curso'
                counts['en_curso'] += 1
            else:
                viaje.estado_actual = 'Programado'
                counts['programados'] += 1
            
            # Calcular closest_parada solo para viajes en curso
            viaje.closest_parada = None
            if viaje.recorrido and viaje.estado_actual == 'En Curso':
                ubicacion_actual = viaje.ubicacioncolectivo_set.order_by('-timestamp_ubicacion').first()
                if ubicacion_actual and viaje.recorrido.recorridoparadas.exists():
                    try:
                        closest = min(
                            viaje.recorrido.recorridoparadas.all(),  # Usa 'recorridoparadas'
                            key=lambda rp: haversine(
                                ubicacion_actual.latitud, 
                                ubicacion_actual.longitud,
                                rp.parada.latitud_parada, 
                                rp.parada.longitud_parada
                            )
                        )
                        viaje.closest_parada = closest.parada
                    except (ValueError, TypeError, AttributeError):
                        pass  # closest_parada queda None
            
            trips_with_status.append(viaje)
        
        # Filtrar trips para display
        if status_filter == 'programados':
            trips_to_display = [v for v in trips_with_status if v.estado_actual == 'Programado']
        elif status_filter == 'completados':
            trips_to_display = [v for v in trips_with_status if v.estado_actual == 'Completado']
        else:
            trips_to_display = [v for v in trips_with_status if v.estado_actual == 'En Curso']
        
        context.update({
            'status_filter': status_filter,
            'viajes_en_curso_count': counts['en_curso'],
            'viajes_programados_count': counts['programados'],
            'viajes_completados_count': counts['completados'],
            'viajes': trips_to_display,
        })
        return context

class CrearViajeView(CreateView):
    model = Viaje
    form_class = ViajeCreateForm
    template_name = 'admin/viajes_form.html'
    success_url = reverse_lazy('admin-viajes')

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.fecha_hora_inicio_real = None
            self.object.fecha_hora_fin_real = None
            self.object.save()

            estado_inicial, _ = EstadoViaje.objects.get_or_create(
                nombre_estado='Programado',
                defaults={'descripcion_estado': 'Viaje programado'}
            )
            HistorialEstadoViaje.objects.create(
                viaje=self.object,
                estado_viaje=estado_inicial,
                fecha_cambio_estado=timezone.now()
            )
        messages.success(self.request, f'Viaje #{self.object.id} programado correctamente.')
        return redirect(self.get_success_url())


def completar_viaje_y_limpiar(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Acceso no autorizado.')
        return redirect('admin-viajes')
    
    viaje = get_object_or_404(Viaje, pk=pk)
    if viaje.fecha_hora_inicio_real is None:
        viaje.fecha_hora_inicio_real = timezone.now()
    
    viaje.fecha_hora_fin_real = timezone.now()
    viaje.save(update_fields=['fecha_hora_inicio_real', 'fecha_hora_fin_real'])
    
    estado_completado, _ = EstadoViaje.objects.get_or_create(
        nombre_estado='Completado',
        defaults={'descripcion_estado': 'Viaje completado'}
    )
    HistorialEstadoViaje.objects.create(
        viaje=viaje,
        estado_viaje=estado_completado,
        fecha_cambio_estado=timezone.now()
    )
    
    messages.success(request, f'El viaje #{viaje.id} se marcó como completado correctamente.')
    return redirect('admin-viajes')
# --- Parada Management Views ---
class ParadasView(SuperUserRequiredMixin, ListView):
    template_name = 'admin/paradas.html'
    model = Parada
    context_object_name = 'paradas'

class CrearParadaView(SuperUserRequiredMixin, CreateView):
    model = Parada
    form_class = ParadaForm
    template_name = 'admin/parada_form.html'
    success_url = reverse_lazy('admin-paradas')

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()  # Set self.object to the saved Parada instance
            recorrido_a_asignar = form.cleaned_data.get('recorrido_a_asignar')
            orden_en_recorrido = form.cleaned_data.get('orden_en_recorrido')
            if recorrido_a_asignar and orden_en_recorrido:
                RecorridoParada.objects.create(
                    recorrido=recorrido_a_asignar,
                    parada=self.object,
                    orden=orden_en_recorrido
                )
            elif recorrido_a_asignar and not orden_en_recorrido:
                orden_en_recorrido = RecorridoParada.objects.filter(recorrido=recorrido_a_asignar).count() + 1
                RecorridoParada.objects.create(
                    recorrido=recorrido_a_asignar,
                    parada=self.object,
                    orden=orden_en_recorrido
                )
        messages.success(self.request, "Parada creada correctamente.")
        return super().form_valid(form)  # Call super().form_valid(form) to handle the redirect

class EditarParadaView(SuperUserRequiredMixin, UpdateView):
    model = Parada
    form_class = ParadaForm
    template_name = 'admin/parada_form.html'
    success_url = reverse_lazy('admin-paradas')

    def form_valid(self, form):
        with transaction.atomic():
            parada = form.save()
            recorrido_seleccionado = form.cleaned_data.get('recorrido_a_asignar')
            orden_seleccionado = form.cleaned_data.get('orden_en_recorrido')
            recorrido_parada_existente = RecorridoParada.objects.filter(parada=parada).first()
            if recorrido_seleccionado:
                if recorrido_parada_existente:
                    if (recorrido_parada_existente.recorrido != recorrido_seleccionado or
                            recorrido_parada_existente.orden != orden_seleccionado):
                        recorrido_parada_existente.recorrido = recorrido_seleccionado
                        recorrido_parada_existente.orden = orden_seleccionado
                        recorrido_parada_existente.save()
                else:
                    RecorridoParada.objects.create(
                        recorrido=recorrido_seleccionado,
                        parada=parada,
                        orden=orden_seleccionado
                    )
            elif recorrido_parada_existente:
                recorrido_parada_existente.delete()

        messages.success(self.request, "Parada actualizada correctamente.")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Parada: {self.object.nombre_parada}"
        return context

class EliminarParadaView(SuperUserRequiredMixin, DeleteView):
    model = Parada
    template_name = 'admin/paradas_confirm_delete.html'
    success_url = reverse_lazy('admin-paradas')

class ParadaDetailView(SuperUserRequiredMixin, DetailView):
    model = Parada
    template_name = "admin/paradas_detalle.html"
    context_object_name = "parada"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recorrido_paradas"] = RecorridoParada.objects.filter(parada=self.object).select_related("recorrido")
        return context


# --- Recorrido Management Views ---
class RecorridosView(SuperUserRequiredMixin, ListView):
    model = Recorrido
    template_name = 'admin/recorridos.html'
    context_object_name = 'recorridos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_recorridos'] = Recorrido.objects.count()
        context['recorridos_activos'] = Recorrido.objects.exclude(descripcion_recorrido__exact='').count()
        context['recorridos_inactivos'] = Recorrido.objects.filter(descripcion_recorrido__exact='').count()
        return context

class RecorridoDetailView(SuperUserRequiredMixin, DetailView):
    model = Recorrido
    template_name = "admin/recorrido_detalle.html"
    context_object_name = "recorrido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paradas"] = RecorridoParada.objects.filter(
            recorrido=self.object
        ).select_related("parada").order_by("orden")
        return context

class CrearRecorridoView(SuperUserRequiredMixin, CreateView):
    model = Recorrido
    form_class = RecorridoForm
    template_name = 'admin/recorrido_form.html'
    success_url = reverse_lazy('admin-recorridos')

class EditarRecorridoView(SuperUserRequiredMixin, UpdateView):
    model = Recorrido
    form_class = RecorridoForm
    template_name = 'admin/recorrido_form.html'
    success_url = reverse_lazy('admin-recorridos')

class EliminarRecorridoView(SuperUserRequiredMixin, DeleteView):
    model = Recorrido
    template_name = 'admin/recorrido_confirm_delete.html'
    success_url = reverse_lazy('admin-recorridos')


# --- Atractivo Management Views ---
class AtractivoView(SuperUserRequiredMixin, ListView):
    model = Atractivo
    template_name = 'admin/atractivos.html'
    context_object_name = 'atractivos'

class AtractivoDetailView(SuperUserRequiredMixin, DetailView):
    model = Atractivo
    template_name = "admin/atractivo_detalle.html"
    context_object_name = "atractivo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parada_atractivos"] = ParadaAtractivo.objects.filter(atractivo=self.object).select_related("parada")
        return context

class CrearAtractivoView(SuperUserRequiredMixin, CreateView):
    model = Atractivo
    form_class = AtractivoForm
    template_name = 'admin/atractivo_form.html'
    success_url = reverse_lazy('admin-atractivos')

    def form_valid(self, form):
        atractivo = form.save(commit=False)
        atractivo.save()
        return super().form_valid(form)

class EditarAtractivoView(SuperUserRequiredMixin, UpdateView):
    model = Atractivo
    form_class = AtractivoForm
    template_name = 'admin/atractivo_form.html'
    success_url = reverse_lazy('admin-atractivos')

class EliminarAtractivoView(SuperUserRequiredMixin, DeleteView):
    model = Atractivo
    template_name = 'admin/atractivo_confirm_delete.html'
    success_url = reverse_lazy('admin-atractivos')


# --- Reporting Views ---
class ReportesView(SuperUserRequiredMixin, ListView):
    template_name = 'admin/reportes.html'
    context_object_name = 'reportes'

    def get_queryset(self):
        viajes = Viaje.objects.all()
        reportes = [
            {
                'id': viaje.id,
                'fecha': viaje.fecha_programada if viaje.fecha_programada else timezone.now(),
                'estado': 'Completado' if viaje.fecha_hora_fin_real else 'Pendiente',
                'descripcion': f'Reporte de viaje {viaje.id} - {viaje.recorrido}',
                'foto': None
            }
            for viaje in viajes
        ]
        return reportes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_reportes'] = Viaje.objects.count()
        context['reportes_completados'] = Viaje.objects.filter(fecha_hora_fin_real__isnull=False).count()
        context['reportes_pendientes'] = Viaje.objects.filter(fecha_hora_fin_real__isnull=True).count()
        return context

def generar_reporte(request):
    viajes = Viaje.objects.all()
    reporte_data = "Reporte de Viajes - Generado el {}\n\n".format(timezone.now().strftime('%d/%m/%Y %H:%M'))
    reporte_data += "ID,Fecha,Estado,Descripción\n"
    for viaje in viajes:
        estado = 'Completado' if viaje.fecha_hora_fin_real else 'Pendiente'
        descripcion = f"Viaje {viaje.id} - {viaje.recorrido}"
        reporte_data += f"{viaje.id},{viaje.fecha_programada.strftime('%d/%m/%Y') if viaje.fecha_programada else 'Sin fecha'},{estado},{descripcion}\n"

    response = HttpResponse(reporte_data, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="reporte_viajes_{}.txt"'.format(timezone.now().strftime('%Y%m%d_%H%M'))
    return response

from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.utils.timezone import localtime, now
from django.views.generic import TemplateView
from datetime import timedelta
from .models import Viaje

class ReportesDiariosView(SuperUserRequiredMixin, TemplateView):
    template_name = 'admin/reportes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hoy = localtime(now()).date()
        viajes_hoy = Viaje.objects.filter(fecha_programada__date=hoy)

        # Lista de viajes con duración y demora
        viajes_data = []
        duraciones = []
        demoras = []

        for viaje in viajes_hoy:
            # Calculamos duración real en minutos si existe
            duracion = viaje.duracion_minutos_real
            if duracion is None and viaje.fecha_hora_inicio_real and viaje.fecha_hora_fin_real:
                delta = viaje.fecha_hora_fin_real - viaje.fecha_hora_inicio_real
                duracion = int(delta.total_seconds() / 60)

            # Calculamos demora en minutos si existe
            demora = viaje.demora_inicio_minutos
            if demora is None and viaje.fecha_hora_inicio_real:
                programado = viaje.fecha_programada
                delta = viaje.fecha_hora_inicio_real - programado
                demora = int(delta.total_seconds() / 60)

            if duracion is not None:
                duraciones.append(duracion)
            if demora is not None:
                demoras.append(demora)

            viajes_data.append({
                'id': viaje.id,
                'recorrido': str(viaje.recorrido),
                'duracion_minutos': duracion,
                'demora_minutos': demora,
            })

        # Promedios
        promedio_duracion = round(sum(duraciones)/len(duraciones), 2) if duraciones else 0
        promedio_demora = round(sum(demoras)/len(demoras), 2) if demoras else 0

        context.update({
            'viajes_data': viajes_data,
            'promedio_duracion': promedio_duracion,
            'promedio_demora': promedio_demora,
            'fecha_reporte': hoy,
        })

        return context





# --- Other Views ---


class BaseUsuarioView(TemplateView):
    template_name = 'usuario/base_usuario.html'