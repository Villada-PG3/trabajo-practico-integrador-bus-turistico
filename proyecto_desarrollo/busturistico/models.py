from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class Recorrido(models.Model):
    color_recorrido = models.CharField(max_length=50)
    duracion_aproximada_recorrido = models.TimeField()
    descripcion_recorrido = models.TextField()
    foto_recorrido = models.ImageField(upload_to='recorridos/', null=True, blank=True)

    def __str__(self):
        return f"Recorrido {self.id} - {self.color_recorrido}"


class Parada(models.Model):
    nombre_parada = models.CharField(max_length=100)
    direccion_parada = models.CharField(max_length=255)
    descripcion_parada = models.TextField()
    foto_parada = models.ImageField(upload_to='paradas/', null=True, blank=True)
    latitud_parada = models.FloatField()
    longitud_parada = models.FloatField()

    def __str__(self):
        return self.nombre_parada


class RecorridoParada(models.Model):
    recorrido = models.ForeignKey(
        Recorrido,
        on_delete=models.CASCADE,
        related_name='recorridoparadas'
    )
    parada = models.ForeignKey(
        Parada,
        on_delete=models.CASCADE,
        related_name='recorridoparadas'
    )
    orden = models.IntegerField()

    class Meta:
        unique_together = ('recorrido', 'parada', 'orden')
        verbose_name_plural = "RecorridoParadas"


class Atractivo(models.Model):
    nombre_atractivo = models.CharField(max_length=100)
    calificacion_estrellas = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    descripcion_atractivo = models.TextField()
    latitud_atractivo = models.FloatField()
    longitud_atractivo = models.FloatField()
    foto_atractivo = models.ImageField(upload_to='atractivos/', null=True, blank=True)

    def __str__(self):
        return self.nombre_atractivo


class ParadaAtractivo(models.Model):
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    atractivo = models.ForeignKey(Atractivo, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('parada', 'atractivo')
        verbose_name_plural = "ParadaAtractivos"


class Bus(models.Model):
    patente_bus = models.CharField(max_length=10, primary_key=True)
    numero_unidad = models.IntegerField()
    fecha_compra = models.DateTimeField()

    def __str__(self):
        return self.patente_bus


class EstadoBus(models.Model):
    nombre_estado = models.CharField(max_length=100)
    descripcion_estado = models.TextField()

    def __str__(self):
        return self.nombre_estado


class EstadoBusHistorial(models.Model):
    patente_bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    estado_bus = models.ForeignKey(EstadoBus, on_delete=models.CASCADE)
    fecha_inicio_estado = models.DateTimeField()

    class Meta:
        verbose_name_plural = "EstadoBusHistorial"



class Chofer(models.Model):
    # Agregar esta línea para relacionar con User
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    
    nombre_chofer = models.CharField(max_length=100)
    apellido_chofer = models.CharField(max_length=100)
    legajo_chofer = models.CharField(max_length=20, unique=True)
    dni_chofer = models.IntegerField()
    telefono = models.CharField(max_length=20)
    fecha_ingreso = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre_chofer} {self.apellido_chofer}"
    
    def save(self, *args, **kwargs):
        # Crear usuario automáticamente si no existe
        if not self.user and self.activo:
            username = f"chofer_{self.legajo_chofer}"
            user = User.objects.create_user(
                username=username,
                email=f"{username}@busturistico.com",
                password=str(self.dni_chofer),  # Usar DNI como password inicial
                first_name=self.nombre_chofer,
                last_name=self.apellido_chofer,
                is_staff=False,  # NO es admin
                is_superuser=False  # NO es superuser
            )
            self.user = user
        elif self.user and not self.activo:
            # Desactivar usuario si chofer se marca como inactivo
            self.user.is_active = False
            self.user.save()
        elif self.user and self.activo:
            # Reactivar usuario si chofer se marca como activo
            self.user.is_active = True
            self.user.save()
            
        super().save(*args, **kwargs)


class EstadoViaje(models.Model):
    nombre_estado = models.CharField(max_length=100)
    descripcion_estado = models.TextField()

    def __str__(self):
        return self.nombre_estado


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

    def __str__(self):
        return f"Viaje {self.id} - {self.recorrido}"


class UbicacionColectivo(models.Model):
    latitud = models.FloatField()
    longitud = models.FloatField()
    timestamp_ubicacion = models.DateTimeField()
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name_plural = "UbicacionColectivos"


class HistorialEstadoViaje(models.Model):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE)
    estado_viaje = models.ForeignKey(EstadoViaje, on_delete=models.CASCADE)
    fecha_cambio_estado = models.DateTimeField()

    class Meta:
        verbose_name_plural = "HistorialEstadoViajes"

    def __str__(self):
        return f"Historial Estado Viaje {self.id} - Viaje {self.viaje.id} - Estado {self.estado_viaje.nombre_estado}"


class Consulta(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    personas = models.CharField(max_length=20, blank=True, null=True)
    fecha_interes = models.DateField(blank=True, null=True)
    recorrido_interes = models.CharField(max_length=50, blank=True, null=True)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    respondida = models.BooleanField(default=False)
    respuesta = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Consulta de {self.nombre} ({self.email})"


class Precio(models.Model):
    TIPO_CHOICES = [
        ('24h', 'Pase 24 horas'),
        ('48h', 'Pase 48 horas'),
        ('familiar', 'Pase Familiar'),
    ]

    tipo = models.CharField(max_length=20, choices= TIPO_CHOICES)
    precio_usd = models.DecimalField(max_digits=6, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    

    def __str__(self):
        return f"{self.get_tipo_display()} - ${self.precio_usd} USD"


# Solo la parte relevante del modelo Traduccion actualizada

class Traduccion(models.Model):
    CLAVE_CHOICES = [
        ('inicio_titulo', 'Título sección inicio'),
        ('inicio_descripcion', 'Descripción sección inicio'),
        ('precios_titulo', 'Título sección precios'),
        ('precios_subtitulo', 'Subtítulo sección precios'),
        # Podés agregar más claves según necesites
    ]

    clave = models.CharField(max_length=50, choices=CLAVE_CHOICES)
    idioma = models.CharField(max_length=5, choices=[
        ('es', 'Español'),
        ('en', 'English'),
        ('pt', 'Português'),
    ])
    texto = models.TextField()

    class Meta:
        unique_together = ('clave', 'idioma')
        verbose_name_plural = "Traducciones"

    def __str__(self):
        return f"{self.clave} [{self.idioma}]"



# -------------------------
class Reserva(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    cantidad_personas = models.IntegerField(default=1)
    fecha_reserva = models.DateField()
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    pase = models.ForeignKey(Precio, on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    def __str__(self):
        # Mostramos tipo de pase y nombre para identificar en listas
        try:
            pase_label = self.pase.get_tipo_display()
        except Exception:
            pase_label = str(self.pase)
        return f"Reserva #{self.id} — {self.nombre} — {pase_label}"