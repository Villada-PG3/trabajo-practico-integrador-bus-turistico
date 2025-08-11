from django.views.generic import TemplateView, ListView, CreateView, DetailView
from .models import Bus, Chofer, Viaje, EstadoBusHistorial, EstadoBus, EstadoViaje, Parada, Recorrido, ParadaAtractivo, RecorridoParada

class UsuarioInicioView(TemplateView):
    template_name = 'usuario/inicio.html'

class UsuarioRecorridosView(ListView):
    model = Recorrido
    template_name = 'usuario/recorridos.html'
    context_object_name = 'recorridos'

class UsuarioDetalleRecorridoView(DetailView):
    model = Recorrido
    template_name = 'usuario/detalle_recorrido.html'
    context_object_name = 'recorrido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['paradas'] = RecorridoParada.objects.filter(recorrido=self.object).order_by('orden')
        return context

class UsuarioDetalleParadaView(DetailView):
    model = Parada
    template_name = 'usuario/detalle_parada.html'
    context_object_name = 'parada'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['atractivos'] = ParadaAtractivo.objects.filter(parada=self.object)
        return context

class UsuarioContactoView(TemplateView):
    template_name = 'usuario/contacto.html'

