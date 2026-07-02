from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_cliente, name='login'),
    path('registro/', views.registro_cliente, name='registro'),  # ← AGREGA ESTA LÍNEA
    path('logout/', views.logout_cliente, name='logout'),
    path('pedido/nuevo/', views.crear_pedido, name='crear_pedido'),
    path('pedido/<int:pedido_id>/', views.detalle_pedido, name='detalle_pedido'),
    path('pedido/<int:pedido_id>/modificar/', views.modificar_pedido, name='modificar_pedido'),
    path('pedido/<int:pedido_id>/eliminar/', views.cancelar_pedido, name='eliminar_pedido'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('api/calcular-resumen/', views.calcular_resumen_ajax, name='calcular_resumen_ajax'),
]