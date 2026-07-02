from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from .models import Cliente, Producto, Pedido, LineaPedido
from .forms import FormularioPedidoForm, ModificarPedidoForm, ClienteRegistroForm
from django.contrib.auth import authenticate, login, logout


@login_required
def crear_pedido(request):
    """
    Vista para crear un nuevo pedido.
    Verifica que el cliente no esté en lista negra.
    """
    try:
        cliente = request.user.cliente
    except Cliente.DoesNotExist:
        messages.error(request, 'No tiene perfil de cliente. Contacte a la recepcionista.')
        return redirect('registro')
    
    # Verificar lista negra
    if cliente.en_lista_negra:
        messages.error(
            request, 
            '️ Usted se encuentra en la lista negra de clientes no deseados. '
            'No puede realizar pedidos. Contacte al gerente.'
        )
        return redirect('login')
    
    # Obtener productos disponibles
    productos = Producto.objects.filter(activo=True, cantidad_disponible__gt=0).order_by('nombre')
    
    if not productos:
        messages.warning(request, 'No hay productos disponibles en este momento.')
        return redirect('login')
    
    if request.method == 'POST':
        form = FormularioPedidoForm(request.POST, cliente=cliente, productos=productos)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear el pedido
                    pedido = Pedido.objects.create(
                        cliente=cliente,
                        observaciones=form.cleaned_data.get('observaciones', '')
                    )
                    
                    # Procesar productos seleccionados
                    productos_seleccionados = form.cleaned_data['productos_seleccionados']
                    
                    for producto, cantidad in productos_seleccionados.items():
                        # Verificar stock nuevamente (concurrencia)
                        if producto.cantidad_disponible < cantidad:
                            raise Exception(f"Stock insuficiente para {producto.nombre}")
                        
                        # Crear línea de pedido
                        LineaPedido.objects.create(
                            pedido=pedido,
                            producto=producto,
                            cantidad=cantidad
                        )
                        
                        # Actualizar stock
                        producto.cantidad_disponible -= cantidad
                        producto.save()
                    
                    # Calcular totales
                    pedido.calcular_totales()
                    
                    # Mensaje según tipo de pedido
                    if pedido.supera_limite_200lb:
                        messages.success(
                            request, 
                            f'✅ Pedido #{pedido.id} creado exitosamente. '
                            f'Peso total: {pedido.peso_total_lb} lb. '
                            f'Al superar 200 lb, se requiere gestión de contenedor.'
                        )
                    else:
                        messages.success(
                            request, 
                            f'✅ Pedido #{pedido.id} creado exitosamente. '
                            f'Peso total: {pedido.peso_total_lb} lb.'
                        )
                    
                    return redirect('detalle_pedido', pedido_id=pedido.id)
                    
            except Exception as e:
                messages.error(request, f'Error al crear el pedido: {str(e)}')
    else:
        form = FormularioPedidoForm(cliente=cliente, productos=productos)
    
    # Calcular resumen para mostrar en tiempo real (si hay datos GET)
    resumen = None
    if request.GET:
        form_get = FormularioPedidoForm(request.GET, cliente=cliente, productos=productos)
        if form_get.is_valid():
            resumen = form_get.obtener_resumen_pedido()
    
    return render(request, 'polls/crear_pedido.html', {
        'form': form,
        'productos': productos,
        'resumen': resumen,
        'cliente': cliente
    })


@login_required
def modificar_pedido(request, pedido_id):
    """
    Vista para modificar un pedido existente.
    """
    try:
        cliente = request.user.cliente
        pedido = get_object_or_404(Pedido, id=pedido_id, cliente=cliente)
    except Cliente.DoesNotExist:
        messages.error(request, 'No tiene perfil de cliente.')
        return redirect('registro')
    
    # Verificar que se pueda modificar
    if not pedido.puede_modificarse:
        messages.error(request, 'Este pedido no puede ser modificado en su estado actual.')
        return redirect('detalle_pedido', pedido_id=pedido.id)
    
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    
    if request.method == 'POST':
        form = ModificarPedidoForm(request.POST, pedido=pedido)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Devolver stock de líneas existentes
                    for linea in pedido.lineas.all():
                        linea.producto.cantidad_disponible += linea.cantidad
                        linea.producto.save()
                    
                    # Eliminar líneas existentes
                    pedido.lineas.all().delete()
                    
                    # Crear nuevas líneas
                    for producto in productos:
                        field_name = f"cantidad_{producto.id}"
                        cantidad = form.cleaned_data.get(field_name, 0)
                        
                        if cantidad and cantidad > 0:
                            if producto.cantidad_disponible < cantidad:
                                raise Exception(f"Stock insuficiente para {producto.nombre}")
                            
                            LineaPedido.objects.create(
                                pedido=pedido,
                                producto=producto,
                                cantidad=cantidad
                            )
                            
                            producto.cantidad_disponible -= cantidad
                            producto.save()
                    
                    # Actualizar observaciones
                    pedido.observaciones = form.cleaned_data.get('observaciones', '')
                    
                    # Recalcular totales
                    pedido.calcular_totales()
                    
                    messages.success(request, f'✅ Pedido #{pedido.id} modificado exitosamente.')
                    return redirect('detalle_pedido', pedido_id=pedido.id)
                    
            except Exception as e:
                messages.error(request, f'Error al modificar el pedido: {str(e)}')
    else:
        form = ModificarPedidoForm(pedido=pedido)
    
    return render(request, 'polls/modificar_pedido.html', {
        'form': form,
        'pedido': pedido,
        'productos': productos
    })


@login_required
def cancelar_pedido(request, pedido_id):
    """
    Vista para cancelar un pedido.
    Solo permite cancelar pedidos en estado 'pendiente' o 'en_proceso'.
    Devuelve el stock de los productos.
    """
    try:
        cliente = request.user.cliente
        pedido = get_object_or_404(Pedido, id=pedido_id, cliente=cliente)
    except Cliente.DoesNotExist:
        messages.error(request, 'No tiene perfil de cliente.')
        return redirect('registro')
    
    if not pedido.puede_cancelarse:
        messages.error(request, 'Este pedido no puede ser cancelado en su estado actual.')
        return redirect('detalle_pedido', pedido_id=pedido.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Devolver stock
                for linea in pedido.lineas.all():
                    linea.producto.cantidad_disponible += linea.cantidad
                    linea.producto.save()
                
                # Cambiar estado a cancelado
                pedido.estado = 'cancelado'
                pedido.save()
                
                messages.success(request, f'✅ Pedido #{pedido.id} cancelado exitosamente.')
                return redirect('mis_pedidos')
                
        except Exception as e:
            messages.error(request, f'Error al cancelar el pedido: {str(e)}')
    
    return render(request, 'polls/confirmar_cancelacion.html', {
        'pedido': pedido
    })


@login_required
def detalle_pedido(request, pedido_id):
    """Vista para ver el detalle de un pedido"""
    try:
        cliente = request.user.cliente
        pedido = get_object_or_404(Pedido, id=pedido_id, cliente=cliente)
        lineas = pedido.lineas.all().select_related('producto')
    except Cliente.DoesNotExist:
        messages.error(request, 'No tiene perfil de cliente.')
        return redirect('registro')
    
    return render(request, 'polls/detalle_pedido.html', {
        'pedido': pedido,
        'lineas': lineas
    })


@login_required
def mis_pedidos(request):
    """Vista para listar todos los pedidos del cliente"""
    try:
        cliente = request.user.cliente
        pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha_creacion')
    except Cliente.DoesNotExist:
        pedidos = []
        messages.error(request, 'No tiene perfil de cliente.')
    
    return render(request, 'polls/mis_pedidos.html', {
        'pedidos': pedidos
    })


# API para cálculo en tiempo real
@login_required
def calcular_resumen_ajax(request):
    """Endpoint AJAX para calcular resumen del pedido en tiempo real"""
    if request.method == 'POST':
        try:
            cliente = request.user.cliente
            productos = Producto.objects.filter(activo=True, cantidad_disponible__gt=0)
            
            form = FormularioPedidoForm(request.POST, cliente=cliente, productos=productos)
            
            if form.is_valid():
                resumen = form.obtener_resumen_pedido()
                return JsonResponse({
                    'success': True,
                    'resumen': {
                        'total_items': resumen['total_items'],
                        'peso_total_lb': float(resumen['peso_total_lb']),
                        'monto_total': float(resumen['monto_total']),
                        'supera_200lb': resumen['supera_200lb'],
                        'tipo_pedido': resumen['tipo_pedido']
                    }
                })
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

def login_cliente(request):
    """Vista para iniciar sesión"""
    if request.user.is_authenticated:
        return redirect('crear_pedido')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                cliente = user.cliente
                if cliente.en_lista_negra:
                    messages.error(request, 'Su cuenta está suspendida.')
                    return redirect('login')
                login(request, user)
                messages.success(request, f'Bienvenido {user.get_full_name() or user.username}')
                return redirect('crear_pedido')
            except Cliente.DoesNotExist:
                messages.error(request, 'No tiene perfil de cliente.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    
    return render(request, 'polls/login.html')


def registro_cliente(request):
    """Vista para registrar nuevo cliente"""
    # Si ya está autenticado Y tiene cliente, redirigir
    if request.user.is_authenticated:
        try:
            # Verificar si tiene perfil de cliente
            cliente = request.user.cliente
            # Si tiene cliente, ir a crear pedido
            return redirect('crear_pedido')
        except Cliente.DoesNotExist:
            # Si NO tiene cliente, permitir que complete el registro
            pass
    
    if request.method == 'POST':
        form = ClienteRegistroForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, '¡Registro exitoso!')
                return redirect('crear_pedido')
            except Exception as e:
                messages.error(request, f'Error al crear cliente: {str(e)}')
    else:
        form = ClienteRegistroForm()
    
    return render(request, 'polls/registro.html', {'form': form})


def logout_cliente(request):
    """Cerrar sesión"""
    logout(request)
    messages.success(request, 'Sesión cerrada.')
    return redirect('login')
