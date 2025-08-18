from django import forms
from .models import Chofer, Bus,Parada
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class ChoferLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de Legajo',
            'id': 'legajo'
        }),
        label='Legajo'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'DNI (sin puntos)',
            'id': 'dni'
        }),
        label='DNI'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        legajo = cleaned_data.get('username')
        dni = cleaned_data.get('password')
        
        if not legajo or not dni:
            raise ValidationError("Por favor, ingrese su legajo y DNI.")

        try:
            chofer = Chofer.objects.get(legajo_chofer=legajo, dni_chofer=dni)
            
            # 1. Verificar si el chofer tiene un usuario asociado
            user_to_login = chofer.user
            if not user_to_login:
                raise ValidationError("Este chofer no tiene una cuenta de usuario asociada.")

            # 2. Verificar si el chofer está activo
            if not chofer.activo:
                raise ValidationError("Su cuenta de chofer está desactivada. Contacte al administrador.")

            # 3. Verificar si el usuario está activo
            if not user_to_login.is_active:
                raise ValidationError("Su cuenta de usuario está desactivada.")
                
            self.user_cache = user_to_login
            
        except Chofer.DoesNotExist:
            raise ValidationError("Legajo o DNI incorrectos.")
        
        return cleaned_data
        
    def get_user(self):
        return self.user_cache
    

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
