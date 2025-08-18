from django import forms
from .models import Chofer, Bus,Parada
#admin
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
        
class ParadaForm(forms.ModelForm):
    class Meta:
        model = Parada
        fields = ['nombre_parada', 'direccion_parada', 'descripcion_parada', 'foto_parada', 'latitud_parada', 'longitud_parada']
        widgets = {
            'descripcion_parada': forms.Textarea(attrs={'rows': 3}),
            'latitud_parada': forms.NumberInput(attrs={'step': 'any'}),
            'longitud_parada': forms.NumberInput(attrs={'step': 'any'}),
        }