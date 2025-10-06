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
from .models import Parada, Recorrido, RecorridoParada, Atractivo, Bus, Chofer, Viaje, Consulta
import datetime
from django import forms
import re
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
    fecha_programada = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        input_formats=['%Y-%m-%d']
    )
    hora_inicio_programada = forms.TimeField(
        required=True,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        input_formats=['%H:%M', '%H:%M:%S']
    )
    duracion_minutos_real = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'min': 0, 'step': 1, 'class': 'form-control'})
    )

    class Meta:
        model = Viaje
        fields = [
            'fecha_programada', 'hora_inicio_programada', 'duracion_minutos_real',
            'patente_bus', 'chofer', 'recorrido'
        ]
        widgets = {
            'patente_bus': forms.Select(attrs={'class': 'form-select'}),
            'chofer': forms.Select(attrs={'class': 'form-select'}),
            'recorrido': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        patente_bus = cleaned_data.get('patente_bus')
        chofer = cleaned_data.get('chofer')

        # Validate fecha_programada is today or future
        if fecha_programada and fecha_programada < timezone.now().date():
            raise ValidationError({'fecha_programada': 'La fecha programada debe ser hoy o futura.'})

        # Combine fecha_programada and hora_inicio_programada for validation
        if fecha_programada and hora_inicio_programada:
            fecha_hora_completa = timezone.datetime(
                fecha_programada.year,
                fecha_programada.month,
                fecha_programada.day,
                hora_inicio_programada.hour,
                hora_inicio_programada.minute,
                tzinfo=timezone.get_current_timezone()
            )
            if fecha_hora_completa < timezone.now():
                raise ValidationError({
                    'hora_inicio_programada': 'La fecha y hora programadas deben ser futuras.'
                })

        # Validate bus and driver availability
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



class RespuestaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ["respuesta", "respondida"]
        widgets = {
            "respuesta": forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
            "respondida": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        


class RecorridoForm(forms.ModelForm):
    duracion_aproximada_recorrido = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'HH:MM (ej: 01:30)',
            'pattern': '[0-2][0-9]:[0-5][0-9]',  # Restricción de formato HH:MM
            'title': 'Ingresa la duración en formato HH:MM (ej: 01:30)'
        }),
        label='Duración Aproximada (HH:MM)'
    )

    class Meta:
        model = Recorrido
        fields = ['color_recorrido', 'descripcion_recorrido', 'duracion_aproximada_recorrido', 'foto_recorrido']
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
            'foto_recorrido': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    def clean_duracion_aproximada_recorrido(self):
        duracion = self.cleaned_data.get('duracion_aproximada_recorrido')
        if not duracion:
            raise forms.ValidationError("Debes ingresar una duración, salame! Usa formato HH:MM (ej: 01:30).")
        # Validar formato HH:MM (horas 00-23, minutos 00-59)
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', duracion):
            raise forms.ValidationError("Formato inválido, peruano. Usa HH:MM (ej: 01:30). Horas 00-23, minutos 00-59.")
        # Convertir a objeto time para el modelo
        try:
            from django.utils.dateparse import parse_time
            parsed_time = parse_time(duracion)
            if not parsed_time:
                raise ValueError
            return parsed_time
        except ValueError:
            raise forms.ValidationError("Formato inválido, revisa de nuevo. Usa HH:MM (ej: 01:30).")

