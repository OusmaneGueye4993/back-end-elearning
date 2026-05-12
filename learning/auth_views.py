from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .auth_serializers import (
    EtudiantRegisterSerializer, 
    EnseignantRegisterSerializer,
    ProfilEtudiantSerializer,
    ProfilEnseignantSerializer
)

def get_tokens_for_user(user):
    """Génère manuellement les tokens Access et Refresh pour un utilisateur."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class EtudiantRegisterView(generics.CreateAPIView):
    """Crée un compte étudiant et connecte l'utilisateur immédiatement."""
    serializer_class = EtudiantRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "Compte étudiant créé avec succès.",
            "tokens": get_tokens_for_user(user),
            "user_id": user.id
        }, status=status.HTTP_201_CREATED)

class EnseignantRegisterView(generics.CreateAPIView):
    """Crée un compte enseignant et connecte l'utilisateur immédiatement."""
    serializer_class = EnseignantRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "Compte enseignant créé avec succès.",
            "tokens": get_tokens_for_user(user),
            "user_id": user.id
        }, status=status.HTTP_201_CREATED)


class MonProfilView(APIView):
    """Récupère les infos de l'utilisateur connecté."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        res_data = {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        }

        if hasattr(user, 'etudiant'):
            serializer = ProfilEtudiantSerializer(user.etudiant)
            res_data["role"] = 'etudiant'
            res_data["profil"] = serializer.data
        elif hasattr(user, 'enseignant'):
            serializer = ProfilEnseignantSerializer(user.enseignant)
            res_data["role"] = 'enseignant'
            res_data["profil"] = serializer.data
        else:
            res_data["role"] = 'admin'

        return Response(res_data)
    
    

class LogoutView(APIView):
    """Invalide le refresh token pour déconnecter l'utilisateur."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Le token de rafraîchissement est requis."}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Déconnexion réussie."}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Token invalide ou déjà expiré."}, status=status.HTTP_400_BAD_REQUEST)