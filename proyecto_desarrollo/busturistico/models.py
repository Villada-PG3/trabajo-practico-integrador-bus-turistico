from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Recorrido(models.Model):
    color_recorrido = models.CharField(max_length=50)
    duracion_aproximada_recorrido = models.TimeField()
    descripcion_recorrido = models.TextField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    numero_paradas = models.IntegerField()


class Parada(models.Model):
    nombre_parada = models.CharField(max_length=100)
    direccion_parada = models.CharField(max_length=255)
    descripcion_parada = models.TextField()
    link_foto_parada = models.URLField()
    latitud_parada = models.FloatField()
    longitud_parada = models.FloatField()


class RecorridoParada(models.Model):
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    orden = models.IntegerField()


class Atractivo(models.Model):
    nombre_atractivo = models.CharField(max_length=100)
    calificacion_estrellas = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    descripcion_atractivo = models.TextField()
    latitud_atractivo = models.FloatField()
    longitud_atractivo = models.FloatField()


class ParadaAtractivo(models.Model):
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    atractivo = models.ForeignKey(Atractivo, on_delete=models.CASCADE)


class Bus(models.Model):
    patente_bus = models.CharField(max_length=10, primary_key=True)
    numero_unidad = models.IntegerField()
    fecha_compra = models.DateTimeField()


class EstadoBus(models.Model):
    nombre_estado = models.CharField(max_length=100)
    descripcion_estado = models.TextField()


class EstadoBusHistorial(models.Model):
    patente_bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    estado_bus = models.ForeignKey(EstadoBus, on_delete=models.CASCADE)
    fecha_inicio_estado = models.DateTimeField()


class Chofer(models.Model):
    nombre_chofer = models.CharField(max_length=100)
    apellido_chofer = models.CharField(max_length=100)
    legajo_chofer = models.CharField(max_length=20)
    dni_chofer = models.IntegerField()
    telefono = models.CharField(max_length=20)
    fecha_ingreso = models.DateField()
    activo = models.BooleanField(default=True)


class EstadoViaje(models.Model):
    nombre_estado = models.CharField(max_length=100)
    descripcion_estado = models.TextField()


class Viaje(models.Model):
    fecha_programada = models.DateTimeField()
    hora_inicio_programada = models.TimeField()
    fecha_hora_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_hora_fin_real = models.DateTimeField(null=True, blank=True)
    demora_inicio_minutos = models.IntegerField(null=True, blank=True)
    duracion_minutos_real = models.IntegerField(null=True, blank=True)
    patente_bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    chofer = models.ForeignKey(Chofer, on_delete=models.CASCADE)
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    estado_viaje = models.ForeignKey(EstadoViaje, on_delete=models.CASCADE)
