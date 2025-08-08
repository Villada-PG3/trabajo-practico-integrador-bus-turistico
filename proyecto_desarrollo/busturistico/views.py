from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido
from .forms import ChoferForm, BusForm, ViajeForm, ParadaForm, RecorridoForm
from django.db.models import Count, OuterRef, Subquery, F
from django.utils import timezone

# Vistas principales del dashboard
def dashboard_view(request):
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
    context = {'estado_buses': estado_buses, 'choferes_activos': choferes_activos, 'viajes_en_curso': viajes_en_curso}
    return render(request, 'admin/dashboard.html', context)

# Vistas de gestión de entidades
def choferes_view(request):
    current_bus_subquery = Viaje.objects.filter(
        chofer=OuterRef('pk'),
        fecha_hora_inicio_real__isnull=False,
        fecha_hora_fin_real__isnull=True
    ).order_by('-fecha_hora_inicio_real').values('patente_bus__patente_bus')[:1]

    choferes_total = Chofer.objects.annotate(
        viajes_realizados=Count('viaje'),
        bus_asignado_actual=Subquery(current_bus_subquery)
    )
    choferes_activos = choferes_total.filter(activo=True)
    choferes_inactivos = choferes_total.filter(activo=False)
    
    context = {
        'choferes_total': choferes_total,
        'choferes_activos': choferes_activos,
        'choferes_inactivos': choferes_inactivos,
    }
    return render(request, 'admin/chofer.html', context)

def flota_view(request):
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
    context = {
        'buses_total': buses_total,
        'buses_operativos': buses_operativos,
        'buses_reparacion': buses_reparacion,
        'buses_mantenimiento': buses_mantenimiento,
    }
    return render(request, 'admin/flota.html', context)

def viajes_view(request):
    viajes_en_curso = Viaje.objects.filter(estado_viaje__nombre_estado__iexact='en curso')
    viajes_programados = Viaje.objects.filter(estado_viaje__nombre_estado__iexact='programado')
    viajes_completados = Viaje.objects.filter(estado_viaje__nombre_estado__iexact='completado')
    context = {
        'viajes_en_curso': viajes_en_curso,
        'viajes_programados': viajes_programados,
        'viajes_completados': viajes_completados,
    }
    return render(request, 'admin/viajes.html', context)

def paradas_view(request):
    paradas = Parada.objects.all()
    context = {'paradas': paradas}
    return render(request, 'admin/paradas.html', context)

def recorridos_view(request):
    recorridos = Recorrido.objects.all()
    context = {'recorridos': recorridos}
    return render(request, 'admin/recorridos.html', context)

def reportes_view(request):
    return render(request, 'admin/reportes.html')

# Vistas para la creación de nuevos elementos
def crear_chofer(request):
    if request.method == 'POST':
        form = ChoferForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin:admin-choferes')
    else:
        form = ChoferForm()
    return render(request, 'admin/crear_chofer.html', {'form': form})

def crear_bus(request):
    if request.method == 'POST':
        form = BusForm(request.POST)
        if form.is_valid():
            bus = form.save()
            # Asignar estado inicial (por ejemplo, 'Operativo')
            estado_inicial = EstadoBus.objects.get_or_create(nombre_estado='Operativo')[0]
            EstadoBusHistorial.objects.create(
                patente_bus=bus,
                estado_bus=estado_inicial,
                fecha_inicio_estado=timezone.now()
            )
            return redirect('admin:admin-flota')
    else:
        form = BusForm()
    return render(request, 'admin/crear_bus.html', {'form': form})

def crear_viaje(request):
    if request.method == 'POST':
        form = ViajeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin:admin-viajes')
    else:
        form = ViajeForm()
    return render(request, 'admin/crear_viaje.html', {'form': form})

def crear_parada(request):
    if request.method == 'POST':
        form = ParadaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin:admin-paradas')
    else:
        form = ParadaForm()
    return render(request, 'admin/crear_parada.html', {'form': form})

def crear_recorrido(request):
    if request.method == 'POST':
        form = RecorridoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin:admin-recorridos')
    else:
        form = RecorridoForm()
    return render(request, 'admin/crear_recorrido.html', {'form': form})