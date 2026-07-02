from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Cliente(models.Model):
    """Extiende el usuario con datos del cliente"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente')
    ci = models.CharField(max_length=11, unique=True, verbose_name='Carnet de Identidad')
    cuenta_banco = models.CharField(max_length=20, verbose_name='Cuenta Bancaria')
    en_lista_negra = models.BooleanField(default=False, verbose_name='¿En lista negra?')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - CI: {self.ci}"


class Producto(models.Model):
    """Productos disponibles para importación"""
    codigo_sku = models.CharField(max_length=20, unique=True, verbose_name='Código SKU')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    unidad_medida = models.CharField(max_length=20, default='lb', verbose_name='Unidad de medida')
    peso_unitario_lb = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=1.0,
        verbose_name='Peso unitario (lb)',
        help_text='Peso de cada unidad en libras'
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_disponible = models.PositiveIntegerField(default=0, verbose_name='Stock disponible')
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name='¿Disponible?')
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo_sku})"
    
    @property
    def agotado(self):
        return self.cantidad_disponible == 0


class Pedido(models.Model):
    """Pedido realizado por un cliente"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    
    TIPO_PEDIDO_CHOICES = [
        ('contenedor', 'Contenedor'),
        ('paqueteria', 'Paquetería (< 200 lb)'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    tipo_pedido = models.CharField(max_length=15, choices=TIPO_PEDIDO_CHOICES, blank=True)
    
    peso_total_lb = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Peso total (lb)'
    )
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    observaciones = models.TextField(blank=True, help_text='Observaciones del cliente')
    
    # Campos para control de entrega
    fecha_limite_recogida = models.DateField(blank=True, null=True)
    dias_para_recoger = models.PositiveIntegerField(default=10)
    
    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente.user.username} ({self.estado})"
    
    def calcular_totales(self):
        """Calcula peso total y monto total del pedido"""
        peso_total = 0
        monto_total = 0
        for linea in self.lineas.all():
            peso_total += linea.peso_total_lb
            monto_total += linea.subtotal
        self.peso_total_lb = peso_total
        self.monto_total = monto_total
        self.save()
        
        # Determinar tipo de pedido según peso
        if peso_total > 200:
            self.tipo_pedido = 'contenedor'
        else:
            self.tipo_pedido = 'paqueteria'
        
        self.save()
    
    @property
    def supera_limite_200lb(self):
        return self.peso_total_lb > 200
    
    @property
    def puede_modificarse(self):
        return self.estado in ['pendiente', 'en_proceso']
    
    @property
    def puede_cancelarse(self):
        return self.estado in ['pendiente', 'en_proceso']


class LineaPedido(models.Model):
    """Detalle de productos en un pedido"""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    peso_unitario_lb = models.DecimalField(max_digits=8, decimal_places=2)
    
    class Meta:
        verbose_name = 'Línea de Pedido'
        verbose_name_plural = 'Líneas de Pedido'
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
    
    @property
    def peso_total_lb(self):
        return self.cantidad * self.peso_unitario_lb
    
    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
    
    def save(self, *args, **kwargs):
        # Actualizar precio y peso desde el producto
        self.precio_unitario = self.producto.precio_unitario
        self.peso_unitario_lb = self.producto.peso_unitario_lb
        super().save(*args, **kwargs)