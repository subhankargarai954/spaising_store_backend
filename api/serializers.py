from .models import Order, OrderItem
from .models import Product
from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_admin']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at',
                  'total_price', 'is_paid', 'items']


class CheckoutSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField()  # each item: {product_id, quantity}
    )

    def validate(self, data):
        validated_items = []
        for item in data['items']:
            try:
                product = Product.objects.get(id=item['product_id'])
                quantity = int(item['quantity'])
                if product.stock < quantity:
                    raise serializers.ValidationError(
                        f"{product.name} has insufficient stock.")
                validated_items.append((product, quantity))
            except Product.DoesNotExist:
                raise serializers.ValidationError("Invalid product ID")
        return {'items': validated_items}

    def create(self, validated_data):
        user = self.context['request'].user
        items = validated_data['items']
        total = sum(p.price * qty for p, qty in items)

        order = Order.objects.create(user=user, total_price=total)
        for product, quantity in items:
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price
            )
            product.stock -= quantity
            product.save()

        # Send confirmation email (template logic can be added later)
        user.email_user(
            subject="Order Confirmation",
            message=f"Thank you for your order #{order.id}!",
        )

        return order
