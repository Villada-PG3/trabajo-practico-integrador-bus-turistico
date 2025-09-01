from django import forms
from .models import Parada, Recorrido, RecorridoParada, Atractivo, Bus, Chofer, Viaje,EstadoBusHistorial,ParadaAtractivo
from django.utils import timezone
from django.db.models import Q
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
            'nombre_chofer': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'apellido_chofer': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'legajo_chofer': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'dni_chofer': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'telefono': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'date'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
        }


from django import forms
from .models import Bus, EstadoBus

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


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = '__all__'
        widgets = {
            'fecha_programada': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'hora_inicio_programada': forms.TimeInput(attrs={'type': 'time'}),
            'fecha_hora_inicio_real': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_hora_fin_real': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'demora_inicio_minutos': forms.NumberInput(),
            'duracion_minutos_real': forms.NumberInput(),
            'patente_bus': forms.Select(),
            'chofer': forms.Select(),
            'recorrido': forms.Select(),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_programada = cleaned_data.get('fecha_programada')
        hora_inicio_programada = cleaned_data.get('hora_inicio_programada')
        fecha_hora_inicio_real = cleaned_data.get('fecha_hora_inicio_real')
        fecha_hora_fin_real = cleaned_data.get('fecha_hora_fin_real')
        patente_bus = cleaned_data.get('patente_bus')
        chofer = cleaned_data.get('chofer')
        recorrido = cleaned_data.get('recorrido')

        # Ensure required fields are provided
        if not fecha_programada:
            self.add_error('fecha_programada', 'La fecha programada es obligatoria.')
        if not hora_inicio_programada:
            self.add_error('hora_inicio_programada', 'La hora de inicio programada es obligatoria.')
        if not patente_bus:
            self.add_error('patente_bus', 'Debe seleccionar un bus.')
        if not chofer:
            self.add_error('chofer', 'Debe seleccionar un chofer.')
        if not recorrido:
            self.add_error('recorrido', 'Debe seleccionar un recorrido.')

        # Validate that fecha_hora_fin_real is after fecha_hora_inicio_real if both are provided
        if fecha_hora_inicio_real and fecha_hora_fin_real:
            if fecha_hora_fin_real <= fecha_hora_inicio_real:
                self.add_error('fecha_hora_fin_real', 'La fecha de fin debe ser posterior a la fecha de inicio.')
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

class RecorridoForm(forms.ModelForm):
    class Meta:
        model = Recorrido
        fields = '__all__'
        widgets = {
            'color_recorrido': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'duracion_aproximada_recorrido': forms.TimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'time'}),
            'descripcion_recorrido': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline min-h-[100px]'}),
        }

class EstadoBusHistorialForm(forms.ModelForm):
    class Meta:
        model = EstadoBusHistorial
        fields = ['estado_bus']
        widgets = {
            'estado_bus': forms.Select(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }