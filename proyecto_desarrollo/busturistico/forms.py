from django import forms
from .models import Parada, Recorrido, RecorridoParada, Atractivo, Bus, Chofer, Viaje

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


class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = '__all__'
        widgets = {
            'patente_bus': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'numero_unidad': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'fecha_compra': forms.DateTimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'datetime-local'}),
        }


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = '__all__'
        widgets = {
            'fecha_programada': forms.DateTimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'datetime-local'}),
            'hora_inicio_programada': forms.TimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'time'}),
            'fecha_hora_inicio_real': forms.DateTimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'datetime-local'}),
            'fecha_hora_fin_real': forms.DateTimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'datetime-local'}),
            'demora_inicio_minutos': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'duracion_minutos_real': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'patente_bus': forms.Select(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'chofer': forms.Select(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'recorrido': forms.Select(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }


class AtractivoForm(forms.ModelForm):
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


class RecorridoForm(forms.ModelForm):
    class Meta:
        model = Recorrido
        fields = '__all__'
        widgets = {
            'color_recorrido': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'duracion_aproximada_recorrido': forms.TimeInput(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'type': 'time'}),
            'descripcion_recorrido': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded-md w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline min-h-[100px]'}),
        }

