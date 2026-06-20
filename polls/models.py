from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    """Extiende el usuario con datos específicos del cliente importador."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Usuario")
    ci = models.CharField(max_length=20, unique=True, verbose_name="Cédula de identidad")
    cuenta_banco = models.CharField(max_length=30, verbose_name="Cuenta bancaria")
    en_lista_negra = models.BooleanField(default=False, verbose_name="Lista negra")

    def __str__(self):
        return f"{self.user.get_full_name()} - CI: {self.ci}"

class Producto(models.Model):
    """Productos disponibles para importar."""
    codigo_sku = models.CharField(max_length=50, unique=True, verbose_name="Código SKU")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_disponible = models.PositiveIntegerField(default=0, verbose_name="Stock disponible")
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo_sku})"

class Pedido(models.Model):
    """Pedido realizado por un cliente."""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('completado', 'Completado'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Cliente")
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    peso_total = models.FloatField(default=0.0, help_text="Peso total en libras (calculado)")

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente}"

class LineaPedido(models.Model):
    """Cada producto solicitado en un pedido."""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"