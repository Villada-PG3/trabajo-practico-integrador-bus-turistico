# busturistico/management/commands/crear_recorrido_verde.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from busturistico.models import (
    Recorrido, Parada, RecorridoParada, Atractivo, 
    ParadaAtractivo, Bus, EstadoBus, EstadoBusHistorial,
    Chofer, EstadoViaje
)
from datetime import time

class Command(BaseCommand):
    help = 'Crear datos iniciales del Recorrido Verde y paradas'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos iniciales...')
        
        # Crear Recorrido Verde
        recorrido_verde, created = Recorrido.objects.get_or_create(
            color_recorrido='VERDE',
            defaults={
                'duracion_aproximada_recorrido': time(8, 50),  # 8h 50min
                'descripcion_recorrido': 'Recorrido que atraviesa los barrios más emblemáticos de Buenos Aires, comenzando en el corazón del Centro Porteño con vistas panorámicas de lugares históricos, espacios culturales y barrios únicos.',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Recorrido Verde creado'))
        else:
            self.stdout.write('• Recorrido Verde ya existía')

        # Crear paradas del Recorrido Verde
        paradas_data = [
            {
                'nombre_parada': 'MALBA (Conexión)',
                'direccion_parada': 'Av. Figueroa Alcorta 3415, Buenos Aires',
                'descripcion_parada': 'Museo de Arte Latinoamericano de Buenos Aires. Punto de conexión principal del recorrido verde.',
                'latitud_parada': -34.5761,
                'longitud_parada': -58.4019,
                'orden': 1
            },
            {
                'nombre_parada': 'Planetario',
                'direccion_parada': 'Av. Sarmiento s/n, Buenos Aires',
                'descripcion_parada': 'Planetario Galileo Galilei, un ícono arquitectónico de la ciudad con espectáculos astronómicos.',
                'latitud_parada': -34.5691,
                'longitud_parada': -58.4115,
                'orden': 2
            },
            {
                'nombre_parada': 'Club de Pescadores',
                'direccion_parada': 'Costanera Norte, Buenos Aires',
                'descripcion_parada': 'Histórico club ubicado en la Costanera Norte con vista al Río de la Plata.',
                'latitud_parada': -34.5649,
                'longitud_parada': -58.4231,
                'orden': 3
            },
            {
                'nombre_parada': 'Parque de la Reserva',
                'direccion_parada': 'Reserva Ecológica Costanera Sur, Buenos Aires',
                'descripcion_parada': 'Área natural protegida con senderos y observación de fauna y flora autóctona.',
                'latitud_parada': -34.6158,
                'longitud_parada': -58.3515,
                'orden': 4
            },
            {
                'nombre_parada': 'El Monumental',
                'direccion_parada': 'Av. Figueroa Alcorta 7597, Buenos Aires',
                'descripcion_parada': 'Estadio Monumental Antonio Vespucio Liberti, casa del Club Atlético River Plate.',
                'latitud_parada': -34.5453,
                'longitud_parada': -58.4498,
                'orden': 5
            },
            {
                'nombre_parada': 'Barrio Chino',
                'direccion_parada': 'Arribeños y Mendoza, Belgrano, Buenos Aires',
                'descripcion_parada': 'Sector comercial con características de la cultura china, restaurantes y comercios típicos.',
                'latitud_parada': -34.5632,
                'longitud_parada': -58.4526,
                'orden': 6
            },
            {
                'nombre_parada': 'Campo Argentino de Polo',
                'direccion_parada': 'Av. del Libertador y Dorrego, Buenos Aires',
                'descripcion_parada': 'Campo de polo más importante de Argentina, sede del Abierto de Palermo.',
                'latitud_parada': -34.5894,
                'longitud_parada': -58.4165,
                'orden': 7
            },
            {
                'nombre_parada': 'Bosque Alegre (Conexión)',
                'direccion_parada': 'Av. Infanta Isabel 410, Buenos Aires',
                'descripcion_parada': 'Zona residencial de Núñez con espacios verdes y conexión a otros recorridos.',
                'latitud_parada': -34.5432,
                'longitud_parada': -58.4654,
                'orden': 8
            },
            {
                'nombre_parada': 'Distrito Arcos',
                'direccion_parada': 'Av. del Libertador 6090, Buenos Aires',
                'descripcion_parada': 'Complejo arquitectónico y comercial moderno en el corazón de Palermo.',
                'latitud_parada': -34.5789,
                'longitud_parada': -58.4289,
                'orden': 9
            },
            {
                'nombre_parada': 'Palermo Soho',
                'direccion_parada': 'Armenia 1894, Buenos Aires',
                'descripcion_parada': '¿Sabés que escritor y poeta vivió hasta los 14 años en esta zona? Jorge Luis Borges -popular poeta y escritor argentino- vivió hasta los 14 años en una casa de la calle Serrano al 2135. En la actualidad, esa casa ya no lleva su nombre. Conocé más sobre la vivienda de Borges y otros atractivos de la zona durante el recorrido del Bus.',
                'latitud_parada': -34.5885,
                'longitud_parada': -58.4224,
                'orden': 10
            },
            {
                'nombre_parada': 'Jardín Botánico Carlos Thays (Conexión)',
                'direccion_parada': 'Av. Santa Fe 3951, Buenos Aires',
                'descripcion_parada': 'Jardín botánico con más de 5000 especies de plantas. Punto de conexión del recorrido.',
                'latitud_parada': -34.5823,
                'longitud_parada': -58.4139,
                'orden': 11
            }
        ]

        # Crear paradas y asociarlas al recorrido
        for parada_data in paradas_data:
            orden = parada_data.pop('orden')
            
            parada, created = Parada.objects.get_or_create(
                nombre_parada=parada_data['nombre_parada'],
                defaults=parada_data
            )
            
            # Crear relación recorrido-parada
            recorrido_parada, created = RecorridoParada.objects.get_or_create(
                recorrido=recorrido_verde,
                parada=parada,
                orden=orden
            )
            
            if created:
                self.stdout.write(f'✓ Parada "{parada.nombre_parada}" creada y asociada')
            else:
                self.stdout.write(f'• Parada "{parada.nombre_parada}" ya existía')

        # Crear atractivos para Palermo Soho
        atractivos_palermo_data = [
            {
                'nombre_atractivo': 'Plazoleta Julio Cortázar (Ex Plaza Serrano)',
                'calificacion': 4,
                'descripcion_atractivo': 'Tradicional plaza del barrio de Palermo, rodeada de bares, restaurantes y diseño.',
                'latitud_atractivo': -34.5889,
                'longitud_atractivo': -58.4221
            },
            {
                'nombre_atractivo': 'Jardín Botánico Carlos Thays',
                'calificacion': 5,
                'descripcion_atractivo': 'Hermoso jardín botánico con una gran variedad de especies vegetales.',
                'latitud_atractivo': -34.5823,
                'longitud_atractivo': -58.4139
            },
            {
                'nombre_atractivo': 'Plaza Italia',
                'calificacion': 4,
                'descripcion_atractivo': 'Plaza histórica con monumento a Giuseppe Garibaldi y feria de artesanos.',
                'latitud_atractivo': -34.5842,
                'longitud_atractivo': -58.4208
            },
            {
                'nombre_atractivo': 'Ecoparque Interactivo',
                'calificacion': 4,
                'descripcion_atractivo': 'Ex zoológico convertido en ecoparque con fines educativos y de conservación.',
                'latitud_atractivo': -34.5743,
                'longitud_atractivo': -58.4026
            },
            {
                'nombre_atractivo': 'Pasajes porteños',
                'calificacion': 3,
                'descripcion_atractivo': 'Pasajes característicos de Buenos Aires con arquitectura típica del barrio.',
                'latitud_atractivo': -34.5895,
                'longitud_atractivo': -58.4235
            }
        ]

        # Crear atractivos y asociarlos a Palermo Soho
        parada_palermo = Parada.objects.get(nombre_parada='Palermo Soho')
        
        for atractivo_data in atractivos_palermo_data:
            atractivo, created = Atractivo.objects.get_or_create(
                nombre_atractivo=atractivo_data['nombre_atractivo'],
                defaults={
                    'calificacion_estrellas': atractivo_data['calificacion'],
                    'descripcion_atractivo': atractivo_data['descripcion_atractivo'],
                    'latitud_atractivo': atractivo_data['latitud_atractivo'],
                    'longitud_atractivo': atractivo_data['longitud_atractivo']
                }
            )
            
            # Asociar atractivo con parada
            parada_atractivo, created = ParadaAtractivo.objects.get_or_create(
                parada=parada_palermo,
                atractivo=atractivo
            )
            
            if created:
                self.stdout.write(f'✓ Atractivo "{atractivo.nombre_atractivo}" creado y asociado a Palermo Soho')

        # Crear algunos datos adicionales necesarios
        self.crear_datos_operacionales()
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 ¡Datos iniciales creados exitosamente!\n'
                'Ahora puedes ver el Recorrido Verde con sus 11 paradas\n'
                'y los atractivos de Palermo Soho en tu aplicación.'
            )
        )

    def crear_datos_operacionales(self):
        """Crear datos mínimos para que el sistema funcione"""
        
        # Estados de bus
        estado_operativo, _ = EstadoBus.objects.get_or_create(
            nombre_estado='Operativo',
            defaults={'descripcion_estado': 'Bus en funcionamiento normal'}
        )
        
        estado_mantenimiento, _ = EstadoBus.objects.get_or_create(
            nombre_estado='En mantenimiento',
            defaults={'descripcion_estado': 'Bus en mantenimiento programado'}
        )
        
        estado_reparacion, _ = EstadoBus.objects.get_or_create(
            nombre_estado='En reparación',
            defaults={'descripcion_estado': 'Bus fuera de servicio por reparación'}
        )

        # Estados de viaje
        EstadoViaje.objects.get_or_create(
            nombre_estado='Programado',
            defaults={'descripcion_estado': 'Viaje programado pero no iniciado'}
        )
        
        EstadoViaje.objects.get_or_create(
            nombre_estado='En curso',
            defaults={'descripcion_estado': 'Viaje en ejecución'}
        )
        
        EstadoViaje.objects.get_or_create(
            nombre_estado='Completado',
            defaults={'descripcion_estado': 'Viaje finalizado exitosamente'}
        )

        # Bus de ejemplo
        bus_ejemplo, created = Bus.objects.get_or_create(
            patente_bus='ABC123',
            defaults={
                'numero_unidad': 1,
                'fecha_compra': timezone.now()
            }
        )
        
        if created:
            # Crear historial de estado para el bus
            EstadoBusHistorial.objects.create(
                patente_bus=bus_ejemplo,
                estado_bus=estado_operativo,
                fecha_inicio_estado=timezone.now()
            )

        # Chofer de ejemplo
        Chofer.objects.get_or_create(
            dni_chofer=12345678,
            defaults={
                'nombre_chofer': 'Carlos',
                'apellido_chofer': 'Rodriguez',
                'legajo_chofer': 'CH001',
                'telefono': '+54 9 11 1234-5678',
                'fecha_ingreso': timezone.now().date(),
                'activo': True
            }
        )

        self.stdout.write('✓ Datos operacionales básicos creados')