from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .models import Etudiant, Enseignant

# --- CLASSE DE BASE (DRY - Don't Repeat Yourself) ---
class BaseRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmer le mot de passe")
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'password2']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe déjà.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."})
        return attrs

# --- INSCRIPTION ÉTUDIANT ---
class EtudiantRegisterSerializer(BaseRegisterSerializer):
    date_naissance = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)

    class Meta(BaseRegisterSerializer.Meta):
        fields = BaseRegisterSerializer.Meta.fields + ['date_naissance', 'bio']

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        date_naissance = validated_data.pop('date_naissance', None)
        bio = validated_data.pop('bio', '')

        with transaction.atomic():
            user = User.objects.create(**validated_data)
            user.set_password(password)
            user.save()
            Etudiant.objects.create(user=user, date_naissance=date_naissance, bio=bio)
        return user

# --- INSCRIPTION ENSEIGNANT ---
class EnseignantRegisterSerializer(BaseRegisterSerializer):
    specialite = serializers.CharField(required=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    
    class Meta(BaseRegisterSerializer.Meta):
        fields = BaseRegisterSerializer.Meta.fields + ['specialite', 'bio']

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        specialite = validated_data.pop('specialite')
        bio = validated_data.pop('bio', '')

        with transaction.atomic():
            user = User.objects.create(**validated_data)
            user.set_password(password)
            user.save()
            Enseignant.objects.create(user=user, specialite=specialite, bio=bio)
        return user

# --- SERIALIZERS DE PROFIL (LECTURE) ---
class ProfilEtudiantSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    full_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = Etudiant
        fields = ['id', 'username', 'email', 'full_name', 'photo', 'bio', 'date_naissance', 'created_at']

class ProfilEnseignantSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    full_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = Enseignant
        fields = ['id', 'username', 'email', 'full_name', 'photo', 'bio', 'specialite', 'created_at']