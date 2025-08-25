from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count, OuterRef, Subquery
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction # Importar transaction para asegurar atomicidad

# Importa tus modelos y formularios reales
from .models import (
    Bus, Chofer, Viaje, EstadoBusHistorial, Atractivo, EstadoBus, EstadoViaje,
    Parada, Recorrido, ParadaAtractivo, RecorridoParada, HistorialEstadoViaje
)
from .forms import ChoferForm, BusForm, ParadaForm, ViajeForm, AtractivoForm, RecorridoForm


class SuperUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        # Redirigir a la página pública en lugar de mostrar 403
        return redirect('admin:login')


# Vistas principales del dashboard (restringida a superusuarios)
class DashboardView(SuperUserRequiredMixin, TemplateView):
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

# Vistas de gestión de entidades (restringidas a superusuarios)
class ChoferesView(SuperUserRequiredMixin, ListView):
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

class AtractivoView(SuperUserRequiredMixin, ListView):
    model = Atractivo
    template_name = 'admin/atractivos.html'
    context_object_name = 'atractivos'

class FlotaView(SuperUserRequiredMixin, TemplateView):
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

class ViajesView(SuperUserRequiredMixin, TemplateView):
    template_name = 'admin/viajes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener el estado más reciente de cada viaje
        latest_status = HistorialEstadoViaje.objects.filter(
            viaje=OuterRef('id')
        ).order_by('-fecha_cambio_estado').values('estado_viaje__nombre_estado')[:1]
        
        # Anotar los viajes con su estado más reciente
        viajes_annotated = Viaje.objects.annotate(
            estado=Subquery(latest_status)
        )
        
        # Filtrar por estados
        context.update({
            'viajes_en_curso': viajes_annotated.filter(estado__iexact='en curso'),
            'viajes_programados': viajes_annotated.filter(estado__iexact='programado'),
            'viajes_completados': viajes_annotated.filter(estado__iexact='completado'),
        })
        return context

class ParadasView(SuperUserRequiredMixin, ListView):
    template_name = 'admin/paradas.html'
    model = Parada
    context_object_name = 'paradas'

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

class RecorridoDetailView(DetailView):
    model = Recorrido
    template_name = "admin/recorrido_detalle.html"
    context_object_name = "recorrido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos las paradas del recorrido ordenadas por "orden"
        context["paradas"] = RecorridoParada.objects.filter(
            recorrido=self.object
        ).select_related("parada").order_by("orden")
        return context

class EditarRecorridoView(SuperUserRequiredMixin, UpdateView):
    model = Recorrido
    form_class = RecorridoForm
    template_name = 'admin/recorrido_form.html'
    success_url = reverse_lazy('admin-recorridos')

class EliminarRecorridoView(SuperUserRequiredMixin, DeleteView):
    model = Recorrido
    template_name = 'admin/recorrido_confirm_delete.html'
    success_url = reverse_lazy('admin-recorridos')    

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
    # Simular datos del reporte basado en Viaje
    viajes = Viaje.objects.all()
    reporte_data = "Reporte de Viajes - Generado el {}\n\n".format(timezone.now().strftime('%d/%m/%Y %H:%M'))
    reporte_data += "ID,Fecha,Estado,Descripción\n"
    for viaje in viajes:
        estado = 'Completado' if viaje.fecha_hora_fin_real else 'Pendiente'
        descripcion = f"Viaje {viaje.id} - {viaje.recorrido}"
        reporte_data += f"{viaje.id},{viaje.fecha_programada.strftime('%d/%m/%Y') if viaje.fecha_programada else 'Sin fecha'},{estado},{descripcion}\n"

    # Crear respuesta para descargar como archivo de texto
    response = HttpResponse(reporte_data, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="reporte_viajes_{}.txt"'.format(timezone.now().strftime('%Y%m%d_%H%M'))
    return response

# Vistas para la creación de nuevos elementos (restringidas a superusuarios)
class CrearChoferView(SuperUserRequiredMixin, CreateView):
    model = Chofer
    form_class = ChoferForm
    template_name = 'admin/chofer_form.html'
    success_url = reverse_lazy('admin-choferes')

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

class CrearViajeView(SuperUserRequiredMixin, CreateView):
    model = Viaje
    form_class = ViajeForm
    template_name = 'admin/viajes_form.html'
    success_url = reverse_lazy('admin-viajes')

    def form_valid(self, form):
        viaje = form.save(commit=False)
        # Aquí podrías añadir lógica adicional, como asignar un estado inicial vía HistorialEstadoViaje
        viaje.save()
        return super().form_valid(form)

class CrearParadaView(SuperUserRequiredMixin, CreateView):
    model = Parada
    form_class = ParadaForm
    template_name = 'admin/parada_form.html' # Asegúrate de que esta plantilla exista
    success_url = reverse_lazy('admin-paradas') # URL a la que redirigir después de crear

    def form_valid(self, form):
        with transaction.atomic():
            parada = form.save() # Guarda la instancia de Parada

            recorrido_a_asignar = form.cleaned_data.get('recorrido_a_asignar')
            orden_en_recorrido = form.cleaned_data.get('orden_en_recorrido')

            if recorrido_a_asignar and orden_en_recorrido:
                # Si se selecciona un recorrido y un orden, creamos la relación
                RecorridoParada.objects.create(
                    recorrido=recorrido_a_asignar,
                    parada=parada,
                    orden=orden_en_recorrido
                )
            elif recorrido_a_asignar and not orden_en_recorrido:
                # Esto no debería ocurrir si el clean del form funciona correctamente,
                # pero es una capa de seguridad.
                orden_en_recorrido = RecorridoParada.objects.filter(recorrido=recorrido_a_asignar).count() + 1
                RecorridoParada.objects.create(
                    recorrido=recorrido_a_asignar,
                    parada=parada,
                    orden=orden_en_recorrido
                )

        messages.success(self.request, "Parada creada correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Crear Nueva Parada"
        return context


class EditarParadaView(SuperUserRequiredMixin, UpdateView):
    model = Parada
    form_class = ParadaForm
    template_name = 'admin/parada_form.html' # Asegúrate de que esta plantilla exista
    success_url = reverse_lazy('admin-paradas') # URL a la que redirigir después de editar

    def form_valid(self, form):
        with transaction.atomic():
            parada = form.save() # Guarda los cambios en la instancia de Parada

            recorrido_seleccionado = form.cleaned_data.get('recorrido_a_asignar')
            orden_seleccionado = form.cleaned_data.get('orden_en_recorrido')

            # Intenta obtener la relación RecorridoParada existente para esta parada
            recorrido_parada_existente = RecorridoParada.objects.filter(parada=parada).first()

            if recorrido_seleccionado:
                if recorrido_parada_existente:
                    # Si ya existe una relación y los datos han cambiado, la actualizamos
                    if (recorrido_parada_existente.recorrido != recorrido_seleccionado or
                            recorrido_parada_existente.orden != orden_seleccionado):
                        recorrido_parada_existente.recorrido = recorrido_seleccionado
                        recorrido_parada_existente.orden = orden_seleccionado
                        recorrido_parada_existente.save()
                else:
                    # Si no existía una relación, la creamos
                    RecorridoParada.objects.create(
                        recorrido=recorrido_seleccionado,
                        parada=parada,
                        orden=orden_seleccionado
                    )
            elif recorrido_parada_existente:
                # Si no se seleccionó un recorrido en el formulario pero existía una relación, la eliminamos
                recorrido_parada_existente.delete()

        messages.success(self.request, "Parada actualizada correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Parada: {self.object.nombre_parada}"
        return context


class EliminarParadaView(SuperUserRequiredMixin, DeleteView):
    model = Parada
    template_name = 'admin/parada_confirm_delete.html'
    success_url = reverse_lazy('admin-paradas')

class CrearRecorridoView(SuperUserRequiredMixin, CreateView):
    model = Recorrido
    form_class = RecorridoForm
    template_name = 'admin/recorrido_form.html'
    success_url = reverse_lazy('admin-recorridos')

class CrearAtractivoView(SuperUserRequiredMixin, CreateView):
    model = Atractivo
    form_class = AtractivoForm
    template_name = 'admin/atractivo_form.html'
    success_url = reverse_lazy('admin-atractivos')  # Ajusta el nombre de la URL según tu configuración

    def form_valid(self, form):
        atractivo = form.save(commit=False)
        # Opcional: añadir lógica adicional, como un timestamp o validación personalizada
        atractivo.save()
        return super().form_valid(form)

class ParadaDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Parada
    template_name = "admin/parada_detalle.html"
    context_object_name = "parada"

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('admin:login')

# Vista pública (accesible por cualquiera)
class BaseUsuarioView(TemplateView):
    template_name = 'usuario/base_usuario.html'
