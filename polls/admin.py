from django.contrib import admin
from .models import Cliente, Producto, Pedido, LineaPedido

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['user', 'ci', 'en_lista_negra', 'fecha_registro']
    list_filter = ['en_lista_negra']
    search_fields = ['user__username', 'user__email', 'ci']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo_sku', 'nombre', 'precio_unitario', 'cantidad_disponible', 'peso_unitario_lb', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'codigo_sku', 'descripcion']

class LineaPedidoInline(admin.TabularInline):
    model = LineaPedido
    extra = 0
    readonly_fields = ['producto', 'cantidad', 'precio_unitario', 'peso_unitario_lb', 'subtotal', 'peso_total_lb']
    
    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = 'Subtotal'

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'fecha_creacion', 'estado', 'peso_total_lb', 'monto_total', 'tipo_pedido']
    list_filter = ['estado', 'fecha_creacion', 'tipo_pedido']
    search_fields = ['cliente__user__username', 'cliente__ci']
    inlines = [LineaPedidoInline]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'peso_total_lb', 'monto_total']
    
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('cliente',)
        }),
        ('Detalles del Pedido', {
            'fields': ('estado', 'tipo_pedido', 'observaciones')
        }),
        ('Totales', {
            'fields': ('peso_total_lb', 'monto_total'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_modificacion', 'fecha_limite_recogida'),
            'classes': ('collapse',)
        }),
    )