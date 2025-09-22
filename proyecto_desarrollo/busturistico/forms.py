from django import forms
from .models import Parada, Recorrido, RecorridoParada, Atractivo, Bus, Chofer, Viaje,EstadoBusHistorial,ParadaAtractivo
import datetime 
from django.utils import timezone
from django.db.models import Q
from .models import Chofer, Bus,Parada
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Parada, Recorrido, RecorridoParada, Atractivo, Bus, Chofer, Viaje
import datetime
from django import forms
from .models import Bus, EstadoBus
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
    # Campo adicional para seleccionar el recorrido
    recorrido_a_asignar = forms.ModelChoiceField(
        queryset=Recorrido.objects.all(),
        required=False,
        empty_label="No asignar a un recorrido",
        label="Asignar o reasignar a Recorrido"
    )
    # Campo para el orden dentro del recorrido
    orden_en_recorrido = forms.IntegerField(
        required=False,
        min_value=1,
        label="Orden en el Recorrido (si se asigna)"
    )

    class Meta:
        model = Parada
        fields = ['nombre_parada', 'direccion_parada', 'descripcion_parada', 'foto_parada', 'latitud_parada', 'longitud_parada']
        widgets = {
            'nombre_parada': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'direccion_parada': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'descripcion_parada': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline min-h-[100px]'}),
            'latitud_parada': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'longitud_parada': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando una parada, precargamos el recorrido y orden si existen
        if self.instance and self.instance.pk:
            # Obtener la primera relación RecorridoParada para esta parada
            # Si una parada puede estar en múltiples recorridos, esta lógica puede necesitar ajustarse
            recorrido_parada_actual = RecorridoParada.objects.filter(parada=self.instance).first()
            if recorrido_parada_actual:
                self.fields['recorrido_a_asignar'].initial = recorrido_parada_actual.recorrido
                self.fields['orden_en_recorrido'].initial = recorrido_parada_actual.orden

        # Añadir clases Tailwind a los campos extra
        for field_name in ['recorrido_a_asignar', 'orden_en_recorrido']:
            self.fields[field_name].widget.attrs.update({'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'})


    def clean(self):
        cleaned_data = super().clean()
        recorrido = cleaned_data.get('recorrido_a_asignar')
        orden = cleaned_data.get('orden_en_recorrido')

        if recorrido and not orden:
            # Si se selecciona un recorrido pero no se especifica el orden,
            # calculamos el siguiente orden disponible para ese recorrido.
            existing_paradas_count = RecorridoParada.objects.filter(recorrido=recorrido).count()
            cleaned_data['orden_en_recorrido'] = existing_paradas_count + 1
        elif orden and not recorrido:
            self.add_error('recorrido_a_asignar', "Debes seleccionar un recorrido si especificas un orden.")

        return cleaned_data

class ChoferForm(forms.ModelForm):
    class Meta:
        model = Chofer
        fields = '__all__'
        widgets = {
            'nombre_chofer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'apellido_chofer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'legajo_chofer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N.º de legajo',
                'inputmode': 'numeric'
            }),
            'dni_chofer': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'DNI (sin puntos)'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+54 9 351 123 4567',
                'inputmode': 'tel'
            }),
            'fecha_ingreso': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
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
    estado_bus = forms.ModelChoiceField(
        queryset=EstadoBus.objects.all(),
        required=False,
        empty_label="Seleccione un estado inicial",
        label="Estado Inicial"
    )

    class Meta:
        model = Bus
        fields = ['patente_bus', 'numero_unidad', 'fecha_compra']
        widgets = {
            'patente_bus': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'numero_unidad': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'fecha_compra': forms.DateTimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando, precargamos el estado actual si existe
        if self.instance.pk:
            historial = EstadoBusHistorial.objects.filter(patente_bus=self.instance).order_by('-fecha_inicio_estado').first()
            if historial:
                self.fields['estado_bus'].initial = historial.estado_bus

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        if hasattr(self, 'cleaned_data'):
            estado = self.cleaned_data.get('estado_bus')
            if estado:
                # Eliminar historial existente si hay un nuevo estado
                EstadoBusHistorial.objects.filter(patente_bus=instance).delete()
                # Crear nuevo historial con el estado seleccionado
                EstadoBusHistorial.objects.create(
                    patente_bus=instance,
                    estado_bus=estado,
                    fecha_inicio_estado=timezone.now()
                )
        return instance


class ViajeCreateForm(forms.ModelForm):
    # Mantengo hora_inicio_programada como requerida (coincide con el modelo)
    fecha_programada = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control', 'step': 60}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']
    )
    hora_inicio_programada = forms.TimeField(
        required=True,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        input_formats=['%H:%M', '%H:%M:%S']
    )
    fecha_hora_inicio_real = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control', 'step': 60}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']
    )
    fecha_hora_fin_real = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control', 'step': 60}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']
    )

    class Meta:
        model = Viaje
        exclude = ['fecha_hora_inicio_real', 'fecha_hora_fin_real', 'duracion_minutos_real']
        widgets = {
            'demora_inicio_minutos': forms.NumberInput(attrs={'min': 0, 'step': 1, 'class': 'form-control'}),
            'duracion_minutos_real': forms.NumberInput(attrs={'min': 0, 'step': 1, 'class': 'form-control'}),
            'patente_bus': forms.Select(attrs={'class': 'form-select'}),
            'chofer': forms.Select(attrs={'class': 'form-select'}),
            'recorrido': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 👇 OJO: en tus modelos el related inverso es 'viaje', no 'viajes'
        self.fields['patente_bus'].queryset = Bus.objects.exclude(
            viaje__fecha_hora_inicio_real__isnull=False,
            viaje__fecha_hora_fin_real__isnull=True
        ).distinct()

        self.fields['chofer'].queryset = Chofer.objects.exclude(
            viaje__fecha_hora_inicio_real__isnull=False,
            viaje__fecha_hora_fin_real__isnull=True
        ).distinct()

        self.fields['recorrido'].queryset = Recorrido.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        fecha_programada = cleaned_data.get('fecha_programada')
        hora_inicio_programada = cleaned_data.get('hora_inicio_programada')
        fecha_hora_inicio_real = cleaned_data.get('fecha_hora_inicio_real')
        fecha_hora_fin_real = cleaned_data.get('fecha_hora_fin_real')
        patente_bus = cleaned_data.get('patente_bus')
        chofer = cleaned_data.get('chofer')

        # fecha_programada debe ser futura
        if fecha_programada and fecha_programada < timezone.now():
            raise ValidationError({'fecha_programada': 'La fecha y hora programada debe ser futura.'})

        # Combinar fecha + hora y validar futura
        if fecha_programada and hora_inicio_programada:
            fecha_hora_completa = fecha_programada.replace(
                hour=hora_inicio_programada.hour,
                minute=hora_inicio_programada.minute,
                second=0, microsecond=0
            )
            if fecha_hora_completa < timezone.now():
                raise ValidationError({'hora_inicio_programada': 'La hora de inicio programada debe ser futura.'})

        # inicio real >= programada
        if fecha_hora_inicio_real and fecha_programada:
            if fecha_hora_inicio_real < fecha_programada:
                raise ValidationError({'fecha_hora_inicio_real': 'El inicio real no puede ser anterior a la programada.'})

        # fin > inicio real
        if fecha_hora_fin_real and fecha_hora_inicio_real:
            if fecha_hora_fin_real <= fecha_hora_inicio_real:
                raise ValidationError({'fecha_hora_fin_real': 'El fin debe ser posterior al inicio.'})

        # disponibilidad bus/chofer
        if patente_bus and Viaje.objects.filter(
            patente_bus=patente_bus,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).exists():
            raise ValidationError({'patente_bus': 'Este bus está asignado a un viaje activo.'})

        if chofer and Viaje.objects.filter(
            chofer=chofer,
            fecha_hora_inicio_real__isnull=False,
            fecha_hora_fin_real__isnull=True
        ).exists():
            raise ValidationError({'chofer': 'Este chofer está asignado a un viaje activo.'})

        return cleaned_data
class AtractivoForm(forms.ModelForm):
    parada_a_asignar = forms.ModelChoiceField(
        queryset=Parada.objects.all(),
        required=False,
        empty_label="No asignar a una parada",
        label="Asignar o reasignar a Parada"
    )

    class Meta:
        model = Atractivo
        fields = '__all__'
        widgets = {
            'nombre_atractivo': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'calificacion_estrellas': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'descripcion_atractivo': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline min-h-[100px]'}),
            'latitud_atractivo': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'longitud_atractivo': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parada_a_asignar'].queryset = Parada.objects.all()
        if self.instance.pk:
            parada_atractivo_actual = ParadaAtractivo.objects.filter(atractivo=self.instance).first()
            if parada_atractivo_actual:
                self.fields['parada_a_asignar'].initial = parada_atractivo_actual.parada

    def save(self, *args, **kwargs):
        # Save the instance first to ensure it has a PK
        instance = super().save(commit=False)
        instance.save()  # Explicitly save to assign PK
        if hasattr(self, 'cleaned_data'):
            parada = self.cleaned_data.get('parada_a_asignar')
            # Delete existing relationships
            ParadaAtractivo.objects.filter(atractivo=instance).delete()  # Use direct query instead of reverse relation
            # Create new relationship if parada is selected
            if parada:
                ParadaAtractivo.objects.get_or_create(parada=parada, atractivo=instance)
        return instance




class EstadoBusHistorialForm(forms.ModelForm):
    class Meta:
        model = EstadoBusHistorial
        fields = ['estado_bus']
        widgets = {
            'estado_bus': forms.Select(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }
        
class RecorridoForm(forms.ModelForm):
    # Número en minutos (se ve y valida como <input type="number">)
    duracion_aproximada_recorrido = forms.IntegerField(
        min_value=1,
        label='Duración (minutos)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',           # Bootstrap limpio
            'placeholder': 'Duración en minutos',
            'step': '1',
            'min': '1',
            'inputmode': 'numeric'
        })
    )

    class Meta:
        model = Recorrido
        fields = '__all__'
        widgets = {
            'color_recorrido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Azul'
            }),
            'descripcion_recorrido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Breve descripción del recorrido'
            }),
        }

 