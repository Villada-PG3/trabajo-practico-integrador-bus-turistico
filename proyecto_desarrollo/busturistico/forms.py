from django import forms
from .models import Chofer, Bus, Viaje, Parada, Recorrido, EstadoBus, EstadoViaje

class ChoferForm(forms.ModelForm):
    class Meta:
        model = Chofer
        fields = ['nombre_chofer', 'apellido_chofer', 'legajo_chofer', 'dni_chofer', 'telefono', 'fecha_ingreso', 'activo']
        widgets = {
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'nombre_chofer': 'Nombre',
            'apellido_chofer': 'Apellido',
            'legajo_chofer': 'Legajo',
            'dni_chofer': 'DNI',
            'telefono': 'Teléfono',
            'fecha_ingreso': 'Fecha de Ingreso',
            'activo': 'Activo',
        }

class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ['patente_bus', 'numero_unidad', 'fecha_compra']
        widgets = {
            'fecha_compra': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'patente_bus': 'Patente',
            'numero_unidad': 'Número de Unidad',
            'fecha_compra': 'Fecha de Compra',
        }

class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['fecha_programada', 'hora_inicio_programada', 'patente_bus', 'chofer', 'recorrido', 'estado_viaje']
        widgets = {
            'fecha_programada': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio_programada': forms.TimeInput(attrs={'type': 'time'}),
        }
        labels = {
            'fecha_programada': 'Fecha Programada',
            'hora_inicio_programada': 'Hora de Inicio Programada',
            'patente_bus': 'Bus',
            'chofer': 'Chofer',
            'recorrido': 'Recorrido',
            'estado_viaje': 'Estado',
        }

class ParadaForm(forms.ModelForm):
    class Meta:
        model = Parada
        fields = ['nombre_parada', 'direccion_parada', 'latitud_parada', 'longitud_parada']
        labels = {
            'nombre_parada': 'Nombre de la Parada',
            'direccion_parada': 'Dirección',
            'latitud_parada': 'Latitud',
            'longitud_parada': 'Longitud',
        }

class RecorridoForm(forms.ModelForm):
    class Meta:
        model = Recorrido
        fields = ['color_recorrido', 'duracion_aproximada_recorrido', 'hora_inicio', 'hora_fin', 'numero_paradas']
        labels = {
            'color_recorrido': 'Color del Recorrido',
            'duracion_aproximada_recorrido': 'Duración Aproximada',
            'hora_inicio': 'Hora de Inicio',
            'hora_fin': 'Hora de Fin',
            'numero_paradas': 'Número de Paradas',
        }