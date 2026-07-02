from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Producto, Pedido, LineaPedido, Cliente


class ClienteRegistroForm(UserCreationForm):
    """
    Formulario para registrar nuevos clientes.
    Crea el usuario y el perfil de cliente asociado.
    """
    email = forms.EmailField(
        required=True,
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@correo.com'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Apellidos',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tus apellidos'
        })
    )
    ci = forms.CharField(
        max_length=11,
        required=True,
        label='Carnet de Identidad',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '11 dígitos'
        })
    )
    cuenta_banco = forms.CharField(
        max_length=20,
        required=True,
        label='Cuenta Bancaria',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cuenta'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contraseña'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirmar contraseña'
            }),
        }
    
    def clean_ci(self):
        """Validar que el CI sea único"""
        ci = self.cleaned_data.get('ci')
        if Cliente.objects.filter(ci=ci).exists():
            raise ValidationError('Este Carnet de Identidad ya está registrado.')
        return ci
    
    def clean_email(self):
        """Validar que el email sea único"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este correo electrónico ya está registrado.')
        return email
    
    def save(self, commit=True):
        """
        Guarda el usuario y crea el perfil de cliente asociado.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Crear el perfil de cliente asociado
            Cliente.objects.create(
                user=user,
                ci=self.cleaned_data['ci'],
                cuenta_banco=self.cleaned_data['cuenta_banco'],
                en_lista_negra=False
            )
        return user


class FormularioPedidoForm(forms.Form):
    """
    Formulario dinámico que genera campos para cada producto disponible.
    Permite al cliente seleccionar productos y cantidades.
    """
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones adicionales sobre el pedido (opcional)...'
        }),
        label='Observaciones'
    )
    
    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop('cliente', None)
        self.productos = kwargs.pop('productos', None)
        super().__init__(*args, **kwargs)
        
        if self.productos:
            for producto in self.productos:
                field_name = f"cantidad_{producto.id}"
                self.fields[field_name] = forms.IntegerField(
                    label=f"{producto.nombre}",
                    min_value=0,
                    max_value=producto.cantidad_disponible,
                    initial=0,
                    required=False,
                    widget=forms.NumberInput(attrs={
                        'class': 'cantidad-input',
                        'data-producto-id': producto.id,
                        'data-stock': producto.cantidad_disponible,
                        'data-precio': float(producto.precio_unitario),
                        'data-peso': float(producto.peso_unitario_lb),
                        'data-sku': producto.codigo_sku,
                        'placeholder': '0',
                        'min': '0',
                        'max': str(producto.cantidad_disponible)
                    })
                )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verificar que al menos un producto tenga cantidad > 0
        cantidades = {}
        total_items = 0
        
        for field_name, value in cleaned_data.items():
            if field_name.startswith('cantidad_') and value and value > 0:
                producto_id = field_name.replace('cantidad_', '')
                try:
                    producto = Producto.objects.get(id=producto_id, activo=True)
                    
                    # Validar stock disponible
                    if value > producto.cantidad_disponible:
                        raise ValidationError(
                            f"Stock insuficiente para {producto.nombre}. "
                            f"Disponible: {producto.cantidad_disponible} {producto.unidad_medida}"
                        )
                    
                    cantidades[producto] = value
                    total_items += value
                    
                except Producto.DoesNotExist:
                    raise ValidationError(f"Producto no encontrado o no disponible.")
        
        if total_items == 0:
            raise ValidationError("Debe seleccionar al menos un producto con cantidad mayor a 0.")
        
        cleaned_data['productos_seleccionados'] = cantidades
        return cleaned_data
    
    def obtener_resumen_pedido(self):
        """Retorna un diccionario con el resumen del pedido"""
        resumen = {
            'productos': [],
            'total_items': 0,
            'peso_total_lb': 0,
            'monto_total': 0,
            'supera_200lb': False
        }
        
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('cantidad_') and value and value > 0:
                producto_id = field_name.replace('cantidad_', '')
                try:
                    producto = Producto.objects.get(id=producto_id)
                    peso_linea = value * float(producto.peso_unitario_lb)
                    subtotal = value * float(producto.precio_unitario)
                    
                    resumen['productos'].append({
                        'producto': producto,
                        'cantidad': value,
                        'peso_unitario_lb': producto.peso_unitario_lb,
                        'peso_total_lb': peso_linea,
                        'precio_unitario': producto.precio_unitario,
                        'subtotal': subtotal
                    })
                    
                    resumen['total_items'] += value
                    resumen['peso_total_lb'] += peso_linea
                    resumen['monto_total'] += subtotal
                    
                except Producto.DoesNotExist:
                    continue
        
        resumen['supera_200lb'] = resumen['peso_total_lb'] > 200
        resumen['tipo_pedido'] = 'Contenedor' if resumen['supera_200lb'] else 'Paquetería'
        
        return resumen


class ModificarPedidoForm(forms.Form):
    """
    Formulario para modificar un pedido existente.
    Similar al formulario de creación pero precarga las cantidades existentes.
    """
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        }),
        label='Observaciones'
    )
    
    def __init__(self, *args, **kwargs):
        self.pedido = kwargs.pop('pedido', None)
        super().__init__(*args, **kwargs)
        
        if self.pedido:
            productos = Producto.objects.filter(activo=True, cantidad_disponible__gt=0)
            lineas_existentes = {linea.producto_id: linea.cantidad for linea in self.pedido.lineas.all()}
            
            for producto in productos:
                field_name = f"cantidad_{producto.id}"
                cantidad_inicial = lineas_existentes.get(producto.id, 0)
                
                self.fields[field_name] = forms.IntegerField(
                    label=f"{producto.nombre}",
                    min_value=0,
                    max_value=producto.cantidad_disponible + cantidad_inicial,  # Incluye lo ya pedido
                    initial=cantidad_inicial,
                    required=False,
                    widget=forms.NumberInput(attrs={
                        'class': 'cantidad-input',
                        'data-producto-id': producto.id,
                        'data-stock': producto.cantidad_disponible,
                        'data-precio': float(producto.precio_unitario),
                        'data-peso': float(producto.peso_unitario_lb),
                    })
                )