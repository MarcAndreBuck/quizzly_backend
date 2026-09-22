from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'confirmed_password')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_email(self, value):
        """Validate that the email address is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'A user with this email already exists.'
            )
        return value

    def validate(self, data):
        """Validate that both passwords match."""
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        """Create a new user with the validated data."""
        validated_data.pop('confirmed_password')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate the user credentials."""
        user = authenticate(
            username=data.get('username'),
            password=data.get('password')
        )
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        data['user'] = user
        return data
