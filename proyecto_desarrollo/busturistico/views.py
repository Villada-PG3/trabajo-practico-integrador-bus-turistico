from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, OuterRef, Subquery, Q, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponseNotAllowed
from django.utils import timezone
from datetime import timedelta
from django.forms import inlineformset_factory
from django.shortcuts import render
from django.db import transaction
from .forms import ParadaForm, RecorridoParadaFormSet
from .models import Parada
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
)   
from math import radians, sin, cos, sqrt, atan2
import json
from .models import (
    Atractivo, Bus, Chofer, EstadoBus, EstadoBusHistorial, EstadoViaje,
    HistorialEstadoViaje, Parada, ParadaAtractivo, Recorrido, RecorridoParada,
    UbicacionColectivo, Viaje, Consulta
)
from .forms import (
    AtractivoForm, BusForm, ChoferForm, EstadoBusHistorialForm, ParadaForm,
    RecorridoForm, ViajeCreateForm
)

from django.core.mail import send_mail
from django.conf import settings

# --- Mixins and Helper Functions ---
class SuperUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para asegurar que solo los superusuarios puedan acceder a una vista.
    """
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('admin:login')


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

    def get(self, request, *args, **kwargs):
        # Evita que intente renderizar chofer_confirm_delete.html
        return HttpResponseNotAllowed(['POST'])

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = f"{self.object.nombre_chofer} {self.object.apellido_chofer}"
        self.object.delete()
        messages.success(request, f'Chofer {nombre} eliminado correctamente.')
        return redirect(self.get_success_url())
class ChoferDetailView(SuperUserRequiredMixin, DetailView):
    model = Chofer
    template_name = 'admin/chofer_detalle.html'
    context_object_name = 'chofer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chofer = self.object

        
        buses_conducidos = (
        Viaje.objects.filter(chofer=chofer, patente_bus__isnull=False)
    .values_list("patente_bus__patente_bus", flat=True)
    .distinct()
)

        ultimos_recorridos = (
    Viaje.objects.filter(chofer=chofer)
    .select_related("recorrido", "patente_bus")
    .order_by("-id")[:5]
)

        
        
        
        viaje_asignado = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).first()

        # 🔹 Cálculos de estadísticas
        viajes_total = Viaje.objects.filter(chofer=chofer).count()
        viajes_completados = Viaje.objects.filter(chofer=chofer, fecha_hora_fin_real__isnull=False).count()
        viajes_en_curso = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_fin_real__isnull=True,
            fecha_hora_inicio_real__isnull=False
        ).count()
        viajes_programados = Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=True
        ).count()

        # Último viaje completado
        ultimo_viaje = (
            Viaje.objects.filter(chofer=chofer, fecha_hora_fin_real__isnull=False)
            .select_related("recorrido", "patente_bus")
            .order_by("-fecha_hora_fin_real")
            .first()
        )

        context.update({
            "buses_conducidos": list(buses_conducidos),
                "ultimos_recorridos": ultimos_recorridos,
            "viaje_asignado": viaje_asignado,
            "viajes_total": viajes_total,
            "viajes_completados": viajes_completados,
            "viajes_en_curso": viajes_en_curso,
            "viajes_programados": viajes_programados,
            "ultimo_viaje": ultimo_viaje,
        })
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

 

class CrearBusView(SuperUserRequiredMixin, CreateView):
    model = Bus
    form_class = BusForm
    template_name = 'admin/flota_form.html'
    success_url = reverse_lazy('admin-flota')

    def form_valid(self, form):
        response = super().form_valid(form)
        estado_inicial = EstadoBus.objects.get_or_create(nombre_estado='Activo')[0]
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

        # Traemos todos los viajes con sus relaciones para eficiencia
        all_trips = Viaje.objects.select_related(
            'patente_bus', 'chofer', 'recorrido'
        ).order_by('-fecha_programada')

        trips_with_status = []
        counts = {'en_curso': 0, 'programados': 0, 'completados': 0}

        # Clasificamos cada viaje según sus fechas
        for viaje in all_trips:
            if viaje.fecha_hora_fin_real:
                viaje.estado_actual = 'Completado'
                counts['completados'] += 1
            elif viaje.fecha_hora_inicio_real:
                viaje.estado_actual = 'En Curso'
                counts['en_curso'] += 1
            else:
                viaje.estado_actual = 'Programado'
                counts['programados'] += 1

            trips_with_status.append(viaje)

        # Filtramos según el estado seleccionado
        if status_filter == 'programados':
            trips_to_display = [v for v in trips_with_status if v.estado_actual == 'Programado']
        elif status_filter == 'completados':
            trips_to_display = [v for v in trips_with_status if v.estado_actual == 'Completado']
        else:  # en_curso o por defecto
            trips_to_display = [v for v in trips_with_status if v.estado_actual == 'En Curso']

        # Pasamos todo al contexto
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
    success_url = reverse_lazy('admin-paradas')  # ✅ redirige a la lista

    def form_valid(self, form):
        with transaction.atomic():
            # Guarda la Parada
            self.object = form.save()

            # Toma los campos auxiliares del form para una sola asignación
            recorrido_a_asignar = form.cleaned_data.get('recorrido_a_asignar')
            orden_en_recorrido = form.cleaned_data.get('orden_en_recorrido')

            if recorrido_a_asignar:
                if not orden_en_recorrido:
                    # Si no te pasan orden, lo colocamos al final
                    orden_en_recorrido = RecorridoParada.objects.filter(
                        recorrido=recorrido_a_asignar
                    ).count() + 1

                RecorridoParada.objects.create(
                    recorrido=recorrido_a_asignar,
                    parada=self.object,
                    orden=orden_en_recorrido
                )

        messages.success(self.request, "Parada creada correctamente.")
        return redirect(self.get_success_url())  # ✅ redirección

class EditarParadaView(SuperUserRequiredMixin, UpdateView):
    model = Parada
    form_class = ParadaForm
    template_name = 'admin/parada_form.html'
    success_url = reverse_lazy('admin-paradas')  # ✅ redirige a la lista

    def form_valid(self, form):
        with transaction.atomic():
            parada = form.save()

            # Campos auxiliares para una sola asignación
            recorrido_seleccionado = form.cleaned_data.get('recorrido_a_asignar')
            orden_seleccionado = form.cleaned_data.get('orden_en_recorrido')

            # Busco si ya tenía una relación
            rp_existente = RecorridoParada.objects.filter(parada=parada).first()

            if recorrido_seleccionado:
                if rp_existente:
                    # Actualizo si cambió recorrido u orden
                    if (rp_existente.recorrido != recorrido_seleccionado or
                        (orden_seleccionado and rp_existente.orden != orden_seleccionado)):
                        rp_existente.recorrido = recorrido_seleccionado
                        rp_existente.orden = orden_seleccionado or rp_existente.orden
                        rp_existente.save()
                else:
                    RecorridoParada.objects.create(
                        recorrido=recorrido_seleccionado,
                        parada=parada,
                        orden=orden_seleccionado or (
                            RecorridoParada.objects.filter(recorrido=recorrido_seleccionado).count() + 1
                        )
                    )
            else:
                # Si eligen “no asignar”, borro la relación existente
                if rp_existente:
                    rp_existente.delete()

        messages.success(self.request, "Parada actualizada correctamente.")
        return redirect(self.get_success_url())  # ✅ redirección   

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

    def post(self, request, *args, **kwargs):
        print("Datos recibidos en POST:", request.POST)  # Depuración
        response = super().post(request, *args, **kwargs)  # Llamar al método padre
        if self.request.POST and not self.object:  # Si no se guardó (error en el formulario)
            form = self.get_form()
            print("Errores del formulario:", form.errors)  # Depuración
        elif self.object:  # Si se guardó correctamente
            print("Datos limpios:", self.object.__dict__)  # Depuración con los atributos del objeto
        return response
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







# --- Other Views ---


class BaseUsuarioView(TemplateView):
    template_name = 'usuario/base_usuario.html'

class ConsultasView(SuperUserRequiredMixin, ListView):
    model = Consulta
    template_name = "admin/consultas.html"
    context_object_name = "consultas"
    ordering = ["-fecha_envio"]


class ConsultaDetailView(SuperUserRequiredMixin, UpdateView):
    model = Consulta
    fields = ["respuesta", "respondida"]
    template_name = "admin/consulta_detalle.html"
    success_url = reverse_lazy("admin-consultas")

    def form_valid(self, form):
        consulta = form.save(commit=False)

        # Si hay respuesta, enviamos el mail (aunque respondida ya sea True)
        if consulta.respuesta:
            try:
                send_mail(
                    subject=f"Respuesta a tu consulta - Bus Turístico",
                    message=consulta.respuesta,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[consulta.email],
                    fail_silently=False,
                )
            except Exception as e:
                print("Error al enviar correo:", e)

            # Marcamos como respondida siempre que haya respuesta
            consulta.respondida = True

        consulta.save()
        return super().form_valid(form)
