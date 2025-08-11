from django.views.generic import TemplateView, ListView, CreateView
from django.shortcuts import redirect
from django.utils import timezone
from .models import Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido, ParadaAtractivo, RecorridoParada
from .forms import ChoferForm, BusForm
from django.db.models import Count, OuterRef, Subquery
from django.urls import reverse_lazy

# Vistas principales del dashboard
class DashboardView(TemplateView):
    template_name = 'admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estado_buses = []
        for bus in Bus.objects.all():
            historial = EstadoBusHistorial.objects.filter(patente_bus=bus).order_by('-fecha_inicio_estado').first()
            estado = historial.estado_bus.nombre_estado if historial else 'Sin estado'
            estado_buses.append((bus, estado))
        choferes_activos = Chofer.objects.filter(activo=True)
        ahora = timezone.now()
        viajes_en_curso = Viaje.objects.filter(
            fecha_hora_inicio_real__lte=ahora,
            fecha_hora_fin_real__isnull=True
        )
        context.update({
            'estado_buses': estado_buses,
            'choferes_activos': choferes_activos,
            'viajes_en_curso': viajes_en_curso
        })
        return context

# Vistas de gestión de entidades
class ChoferesView(ListView):
    template_name = 'admin/chofer.html'
    model = Chofer
    context_object_name = 'choferes_total'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_bus_subquery = Viaje.objects.filter(
            chofer=OuterRef('pk'),
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).order_by('-fecha_hora_inicio_real').values('patente_bus__patente_bus')[:1]

        choferes_total = Chofer.objects.annotate(
            viajes_realizados=Count('viaje'),
            bus_asignado_actual=Subquery(current_bus_subquery)
        )
        context.update({
            'choferes_activos': choferes_total.filter(activo=True),
            'choferes_inactivos': choferes_total.filter(activo=False),
        })
        return context

class FlotaView(TemplateView):
    template_name = 'admin/flota.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        buses_total = Bus.objects.all()
        buses_operativos = []
        buses_reparacion = []
        buses_mantenimiento = []
        for bus in buses_total:
            ultimo_estado_historial = EstadoBusHistorial.objects.filter(patente_bus=bus).order_by('-fecha_inicio_estado').first()
            if ultimo_estado_historial:
                estado = ultimo_estado_historial.estado_bus.nombre_estado.lower()
                if estado == 'operativo':
                    buses_operativos.append(bus)
                elif estado == 'en reparación':
                    buses_reparacion.append(bus)
                elif estado == 'en mantenimiento':
                    buses_mantenimiento.append(bus)
        context.update({
            'buses_total': buses_total,
            'buses_operativos': buses_operativos,
            'buses_reparacion': buses_reparacion,
            'buses_mantenimiento': buses_mantenimiento,
        })
        return context

class ViajesView(TemplateView):
    template_name = 'admin/viajes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'viajes_en_curso': Viaje.objects.filter(estado_viaje__nombre_estado__iexact='en curso'),
            'viajes_programados': Viaje.objects.filter(estado_viaje__nombre_estado__iexact='programado'),
            'viajes_completados': Viaje.objects.filter(estado_viaje__nombre_estado__iexact='completado'),
        })
        return context

class ParadasView(ListView):
    template_name = 'admin/paradas.html'
    model = Parada
    context_object_name = 'paradas'

class RecorridosView(ListView):
    template_name = 'admin/recorridos.html'
    model = Recorrido
    context_object_name = 'recorridos'

class ReportesView(TemplateView):
    template_name = 'admin/reportes.html'

# Vistas para la creación de nuevos elementos
class CrearChoferView(CreateView):
    model = Chofer
    form_class = ChoferForm
    template_name = 'admin/chofer_form.html'
    success_url = reverse_lazy('admin/chofer.html')

class CrearBusView(CreateView):
    model = Bus
    form_class = BusForm
    template_name = 'admin/crear_bus.html'
    success_url = reverse_lazy('admin:admin-flota')

    def form_valid(self, form):
        response = super().form_valid(form)
        estado_inicial = EstadoBus.objects.get_or_create(nombre_estado='Operativo')[0]
        EstadoBusHistorial.objects.create(
            patente_bus=self.object,
            estado_bus=estado_inicial,
            fecha_inicio_estado=timezone.now()
        )
        return response

class CrearViajeView(TemplateView):
    template_name = 'admin/crear_viaje.html'

    def post(self, request, *args, **kwargs):
        # No form processing, just redirect to viajes page
        return redirect('admin:admin-viajes')

class CrearParadaView(TemplateView):
    template_name = 'admin/crear_parada.html'

    def post(self, request, *args, **kwargs):
        # No form processing, just redirect to paradas page
        return redirect('admin:admin-paradas')

class CrearRecorridoView(TemplateView):
    template_name = 'admin/crear_recorrido.html'

    def post(self, request, *args, **kwargs):
        # No form processing, just redirect to recorridos page
        return redirect('admin:admin-recorridos')