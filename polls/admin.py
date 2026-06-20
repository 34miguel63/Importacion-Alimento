from django.contrib import admin
from .models import Cliente, Producto, Pedido, LineaPedido

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['user', 'ci', 'cuenta_banco', 'en_lista_negra']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo_sku', 'precio_unitario', 'cantidad_disponible']

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'fecha_pedido', 'estado', 'peso_total']
    list_filter = ['estado', 'fecha_pedido']

@admin.register(LineaPedido)
class LineaPediodoAdmin(admin.ModelAdmin):
    list_display = ['pedido','producto','cantidad','precio_unitario']
