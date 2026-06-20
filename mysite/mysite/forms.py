from django import forms
from .models import Producto, LineaPedido

class PedidoForm(forms.Form):
    """
    Formulario que genera un campo de cantidad para cada producto disponible.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obtener todos los productos activos (puedes filtrar si necesario)
        productos = Producto.objects.all()
        for producto in productos:
            # Nombre del campo: cantidad_<id_producto>
            field_name = f"cantidad_{producto.id}"
            self.fields[field_name] = forms.IntegerField(
                label=f"{producto.nombre} (Stock: {producto.cantidad_disponible})",
                min_value=0,
                initial=0,
                required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'cantidad-input',
                    'data-stock': producto.cantidad_disponible,
                    'data-precio': float(producto.precio_unitario),
                })
            )

    def clean(self):
        cleaned_data = super().clean()
        # Validar que al menos un producto tenga cantidad > 0
        alguna_cantidad = any(
            value for key, value in cleaned_data.items()
            if key.startswith('cantidad_') and value
        )
        if not alguna_cantidad:
            raise forms.ValidationError("Debe seleccionar al menos un producto con cantidad mayor a 0.")
        return cleaned_data

    def obtener_lineas_pedido(self, pedido, request):
        """
        Procesa los datos del formulario y crea las líneas del pedido.
        """
        productos = Producto.objects.all()
        lineas = []
        peso_total = 0.0  # supón que cada producto tiene un peso unitario fijo (podrías añadirlo al modelo)
        for producto in productos:
            field_name = f"cantidad_{producto.id}"
            cantidad = self.cleaned_data.get(field_name, 0)
            if cantidad:
                lineas.append(
                    LineaPedido(
                        pedido=pedido,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio_unitario
                    )
                )
                # Calcular peso si el producto tuviera un campo peso_unitario
                # peso_total += producto.peso_unitario * cantidad
        return lineas, peso_total