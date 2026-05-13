from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.db import transaction

# Import des permissions depuis le nouveau fichier
from .permissions import (
    IsEnseignantOrReadOnly, 
    IsAdminOrEnseignant, 
    IsEtudiant,
    IsProprietaireOuReadOnly
)

from .models import (
    Module, Cours, Ressource,
    Inscription, Progression,
    Quiz, SoumissionQuiz,
    Note, Reclamation, Notification,
    Certificat,
)
from .serializers import (
    ModuleSerializer, ModuleDetailSerializer,
    CoursSerializer,
    RessourceSerializer,
    InscriptionSerializer,
    ProgressionSerializer,
    QuizSerializer,
    SoumissionQuizSerializer, SoumissionQuizCreateSerializer,
    NoteSerializer,
    ReclamationSerializer,
    NotificationSerializer,
    CertificatSerializer,
)



def _get_etudiant_or_403(user):
    """
    Retourne le profil Etudiant de l'utilisateur ou lève une 403.
    """
    if not hasattr(user, 'etudiant'):
        raise PermissionDenied("Cette action est réservée aux étudiants.")
    return user.etudiant


# backend/api/views.py

class ModuleViewSet(viewsets.ModelViewSet):
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsEnseignantOrReadOnly]

    # Dans ModuleViewSet
    def get_queryset(self):
        user = self.request.user
        
        # 1. Si c'est un enseignant : il voit ses propres modules
        if hasattr(user, 'enseignant'):
            return Module.objects.filter(enseignant=user.enseignant)
        
        # 2. Si c'est un étudiant : il doit voir TOUS les modules publiés 
        # pour pouvoir choisir celui auquel il veut s'inscrire
        if hasattr(user, 'etudiant'):
            return Module.objects.filter(est_publie=True) 
            
        # 3. Par défaut (admin)
        return Module.objects.all()

    def get_serializer_class(self):
        # Utilise un sérialiseur détaillé pour la vue par ID (pour voir les cours)
        if self.action == 'retrieve':
            return ModuleDetailSerializer
        return ModuleSerializer

    def perform_create(self, serializer):
        # Force l'enseignant connecté comme propriétaire à la création
        if hasattr(self.request.user, 'enseignant'):
            serializer.save(enseignant=self.request.user.enseignant)
        else:
            raise PermissionDenied("Seuls les enseignants peuvent créer des modules.")


class CoursViewSet(viewsets.ModelViewSet):
    serializer_class = CoursSerializer
    permission_classes = [permissions.IsAuthenticated, IsProprietaireOuReadOnly]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return Cours.objects.all()
            
        # Un enseignant voit les cours de SES modules
        if hasattr(user, 'enseignant'):
            return Cours.objects.filter(module__enseignant=user.enseignant)
            
        # Un étudiant voit les cours des modules où il est INSCRIT
        if hasattr(user, 'etudiant'):
            return Cours.objects.filter(module__inscriptions__etudiant=user.etudiant).distinct()
            
        return Cours.objects.none()

# ==============================================================
# RESSOURCE
# ==============================================================

class RessourceViewSet(viewsets.ModelViewSet):
    """
    Gestion des fichiers et liens de ressources.
    """
    serializer_class   = RessourceSerializer
    permission_classes = [IsProprietaireOuReadOnly]

    def get_queryset(self):
        qs = Ressource.objects.select_related('cours__module')
        cours_id = self.request.query_params.get('cours')
        if cours_id:
            qs = qs.filter(cours_id=cours_id)
        return qs.order_by('ordre')


# ==============================================================
# INSCRIPTION
# ==============================================================


class InscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = InscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # L'admin voit tout
        if user.is_staff:
            return Inscription.objects.all()
        # L'étudiant ne voit que SES propres inscriptions
        if hasattr(user, 'etudiant'):
            return Inscription.objects.filter(etudiant=user.etudiant)
        # L'enseignant voit les inscriptions aux modules qu'il enseigne
        if hasattr(user, 'enseignant'):
            return Inscription.objects.filter(module__enseignant=user.enseignant)
        return Inscription.objects.none()

    def perform_create(self, serializer):
        # Sécurité : Vérifier que c'est bien un étudiant qui s'inscrit
        if not hasattr(self.request.user, 'etudiant'):
            raise ValidationError("Seuls les étudiants peuvent s'inscrire aux modules.")
        
        # Sécurité : Éviter les doublons (ne pas s'inscrire deux fois au même module)
        module_id = self.request.data.get('module')
        if Inscription.objects.filter(etudiant=self.request.user.etudiant, module_id=module_id).exists():
            raise ValidationError("Vous êtes déjà inscrit à ce module.")
            
        # Sauvegarde automatique avec l'étudiant connecté et le statut par défaut
        serializer.save(etudiant=self.request.user.etudiant, statut='en_attente')

    # --- AJOUT DE L'ACTION POUR L'ENSEIGNANT (Étape suivante) ---
    @action(detail=True, methods=['post'])
    def accepter(self, request, pk=None):
        inscription = self.get_object()
        # Vérification : l'utilisateur est-il l'enseignant de ce module ?
        if inscription.module.enseignant.user != request.user:
            return Response({"error": "Vous n'êtes pas l'enseignant de ce module."}, status=403)
            
        inscription.statut = 'accepte'
        inscription.save()
        return Response({"message": "Inscription validée avec succès !"})


        
# ==============================================================
# PROGRESSION
# ==============================================================

class ProgressionViewSet(viewsets.ModelViewSet):
    serializer_class   = ProgressionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Progression.objects.select_related('etudiant__user', 'cours__module').all()
        if hasattr(user, 'etudiant'):
            return (
                Progression.objects
                .filter(etudiant=user.etudiant)
                .select_related('cours__module')
            )
        return Progression.objects.none()

    def perform_create(self, serializer):
        etudiant = _get_etudiant_or_403(self.request.user)
        serializer.save(etudiant=etudiant)

    @action(detail=True, methods=['post'], url_path='terminer')
    def terminer(self, request, pk=None):
        progression = self.get_object()
        if progression.est_termine:
            return Response({"detail": "Cours déjà terminé."}, status=400)

        with transaction.atomic():
            progression.est_termine = True
            progression.date_fin    = timezone.now()
            progression.save()

            etudiant = progression.etudiant
            module   = progression.cours.module
            cours_du_module = Cours.objects.filter(module=module, est_publie=True)
            cours_termines  = Progression.objects.filter(
                etudiant=etudiant, cours__in=cours_du_module, est_termine=True
            ).count()

            module_complete = cours_termines >= cours_du_module.count()

            if module_complete:
                Inscription.objects.filter(etudiant=etudiant, module=module).update(est_complete=True)
                certificat, cree = Certificat.objects.get_or_create(etudiant=etudiant, module=module)
                if cree:
                    Notification.objects.create(
                        destinataire=etudiant.user,
                        type_notif='certificat',
                        message=f"Félicitations ! Certificat obtenu pour {module.nom}."
                    )

        return Response({"message": "Cours terminé.", "module_complete": module_complete})


# ==============================================================
# QUIZ
# ==============================================================

class QuizViewSet(viewsets.ModelViewSet):
    serializer_class   = QuizSerializer
    permission_classes = [IsProprietaireOuReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (hasattr(user, 'enseignant') or user.is_staff):
            qs = Quiz.objects.select_related('module')
        else:
            qs = Quiz.objects.filter(est_publie=True).select_related('module')

        module_id = self.request.query_params.get('module')
        if module_id:
            qs = qs.filter(module_id=module_id)
        return qs.prefetch_related('questions__choix')

    @action(detail=True, methods=['post'], url_path='soumettre', permission_classes=[IsEtudiant])
    def soumettre(self, request, pk=None):
        serializer = SoumissionQuizCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        soumission = serializer.save()
        return Response(SoumissionQuizSerializer(soumission).data, status=status.HTTP_201_CREATED)


# ==============================================================
# SOUMISSIONS
# ==============================================================

class SoumissionQuizViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = SoumissionQuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SoumissionQuiz.objects.select_related('etudiant__user', 'quiz').prefetch_related('reponses__question', 'reponses__choix_selectionne')
        if user.is_staff:
            return qs.all()
        if hasattr(user, 'etudiant'):
            return qs.filter(etudiant=user.etudiant)
        return SoumissionQuiz.objects.none()


# ==============================================================
# NOTES
# ==============================================================

class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrEnseignant()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or hasattr(user, 'enseignant'):
            return Note.objects.select_related('etudiant__user', 'module').all()
        if hasattr(user, 'etudiant'):
            return Note.objects.filter(etudiant=user.etudiant).select_related('module')
        return Note.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        module = serializer.validated_data.get('module')
        if not user.is_staff and hasattr(user, 'enseignant'):
            if module.enseignant != user.enseignant:
                raise PermissionDenied("Vous n'êtes pas l'enseignant de ce module.")
        
        note = serializer.save()
        Notification.objects.create(
            destinataire=note.etudiant.user,
            type_notif='note',
            message=f"Nouvelle note pour {note.module.nom} : {note.valeur}/20."
        )


# ==============================================================
# RECLAMATIONS
# ==============================================================

class ReclamationViewSet(viewsets.ModelViewSet):
    serializer_class   = ReclamationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Reclamation.objects.select_related('etudiant__user', 'module').order_by('-date_creation')
        if user.is_staff or hasattr(user, 'enseignant'):
            return qs
        if hasattr(user, 'etudiant'):
            return qs.filter(etudiant=user.etudiant)
        return Reclamation.objects.none()

    def perform_create(self, serializer):
        etudiant = _get_etudiant_or_403(self.request.user)
        serializer.save(etudiant=etudiant)

    @action(detail=True, methods=['patch'], url_path='repondre', permission_classes=[IsAdminOrEnseignant])
    def repondre(self, request, pk=None):
        reclamation = self.get_object()
        reponse = request.data.get('reponse', '').strip()
        statut  = request.data.get('statut', 'en_cours')

        if not reponse:
            raise ValidationError({"reponse": "La réponse est obligatoire."})

        reclamation.reponse = reponse
        reclamation.statut  = statut
        reclamation.save()

        Notification.objects.create(
            destinataire=reclamation.etudiant.user,
            type_notif='reclamation',
            message=f"Réclamation « {reclamation.sujet} » traitée."
        )
        return Response(ReclamationSerializer(reclamation).data)


# ==============================================================
# NOTIFICATIONS
# ==============================================================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(destinataire=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['patch'], url_path='lire')
    def lire(self, request, pk=None):
        notif = self.get_object()
        notif.est_lu = True
        notif.save(update_fields=['est_lu'])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=['post'], url_path='tout_lire')
    def tout_lire(self, request):
        updated = self.get_queryset().filter(est_lu=False).update(est_lu=True)
        return Response({"message": f"{updated} notifications lues."})


# ==============================================================
# CERTIFICATS
# ==============================================================

class CertificatViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = CertificatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Certificat.objects.select_related('etudiant__user', 'module')
        if user.is_staff:
            return qs.all()
        if hasattr(user, 'etudiant'):
            return qs.filter(etudiant=user.etudiant)
        return Certificat.objects.none()

    @action(detail=False, methods=['get'], url_path='verify/(?P<uuid>[0-9a-f-]+)', permission_classes=[permissions.AllowAny])
    def verify(self, request, uuid=None):
        try:
            cert = Certificat.objects.select_related('etudiant__user', 'module').get(uuid=uuid)
            return Response({"valide": True, "etudiant": str(cert.etudiant), "module": cert.module.nom, "date": cert.date_obtention})
        except Certificat.DoesNotExist:
            return Response({"valide": False}, status=404)