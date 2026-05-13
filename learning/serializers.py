from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from .models import (
    Etudiant, Enseignant,
    Module, Cours, Ressource,
    Inscription, Progression,
    Quiz, Question, Choix, SoumissionQuiz, ReponseEtudiant,
    Note, Reclamation, Notification,
    Certificat,
)

# ==============================================================
# UTILISATEURS & PROFILS
# ==============================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class EtudiantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Etudiant
        fields = ['id', 'user', 'date_naissance', 'photo', 'bio', 'created_at']

class EnseignantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Enseignant
        fields = ['id', 'user', 'specialite', 'date_naissance', 'photo', 'bio', 'created_at']

# ==============================================================
# CONTENU PÉDAGOGIQUE
# ==============================================================

class RessourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ressource
        fields = ['id', 'cours', 'titre', 'type_ressource', 'fichier', 'url', 'ordre']

class CoursSerializer(serializers.ModelSerializer):
    ressources = RessourceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cours
        fields = ['id', 'module', 'titre', 'description', 'ordre', 'est_publie', 'ressources']

class ModuleSerializer(serializers.ModelSerializer):
    enseignant_nom = serializers.ReadOnlyField(source='enseignant.user.get_full_name')
    nombre_etudiants = serializers.SerializerMethodField()
    statut_inscription = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            'id', 'nom', 'description', 
            'created_at', 'enseignant_nom', 
            'nombre_etudiants', 'statut_inscription'
        ]

    def get_nombre_etudiants(self, obj):
        return obj.inscriptions.count()

    def get_statut_inscription(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'etudiant'):
                inscription = Inscription.objects.filter(
                    etudiant=request.user.etudiant, 
                    module=obj
                ).first()
                if inscription:
                    if inscription.est_complete:
                        return 'complete'
                    return inscription.statut
        return 'non_inscrit'

class ModuleDetailSerializer(ModuleSerializer):
    cours = CoursSerializer(many=True, read_only=True)

    class Meta(ModuleSerializer.Meta):
        fields = ModuleSerializer.Meta.fields + ['cours']

# ==============================================================
# QUIZ & ÉVALUATION
# ==============================================================

class ChoixSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choix
        fields = ['id', 'texte', 'est_correct']

class QuestionSerializer(serializers.ModelSerializer):
    choix = ChoixSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'quiz', 'texte', 'points', 'choix']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'module', 'titre', 'description', 'note_de_passage', 'est_publie', 'questions']

class ReponseEtudiantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReponseEtudiant
        fields = ['question', 'choix_selectionne']

class SoumissionQuizSerializer(serializers.ModelSerializer):
    quiz_titre = serializers.ReadOnlyField(source='quiz.titre')
    
    class Meta:
        model = SoumissionQuiz
        fields = ['id', 'etudiant', 'quiz', 'quiz_titre', 'score', 'reussi', 'date_soumission']
        read_only_fields = ['score', 'reussi', 'date_soumission']

class SoumissionQuizCreateSerializer(serializers.Serializer):
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())
    reponses = ReponseEtudiantSerializer(many=True)

    def create(self, validated_data):
        user = self.context['request'].user
        etudiant = user.etudiant
        quiz = validated_data['quiz']
        reponses_data = validated_data['reponses']

        with transaction.atomic():
            soumission = SoumissionQuiz.objects.create(etudiant=etudiant, quiz=quiz)
            total_points = 0
            points_obtenus = 0

            for rep in reponses_data:
                question = rep['question']
                choix = rep['choix_selectionne']
                
                ReponseEtudiant.objects.create(
                    soumission=soumission,
                    question=question,
                    choix_selectionne=choix
                )

                total_points += question.points
                if choix.est_correct:
                    points_obtenus += question.points

            score_final = (points_obtenus / total_points * 100) if total_points > 0 else 0
            soumission.score = score_final
            soumission.reussi = score_final >= quiz.note_de_passage
            soumission.save()

        return soumission

# ==============================================================
# INSCRIPTIONS & PROGRESSION
# ==============================================================

class InscriptionSerializer(serializers.ModelSerializer):
    etudiant_nom = serializers.SerializerMethodField()
    module_nom = serializers.ReadOnlyField(source='module.nom')

    class Meta:
        model = Inscription
        fields = [
            'id', 'etudiant', 'etudiant_nom', 'module', 
            'module_nom', 'date_inscription', 'statut', 'est_complete'
        ]
        read_only_fields = ['etudiant', 'statut', 'est_complete']

    def get_etudiant_nom(self, obj):
        user = obj.etudiant.user
        return f"{user.first_name} {user.last_name}".strip() or user.username

class ProgressionSerializer(serializers.ModelSerializer):
    cours_titre = serializers.ReadOnlyField(source='cours.titre')

    class Meta:
        model = Progression
        fields = ['id', 'etudiant', 'cours', 'cours_titre', 'est_termine', 'date_fin']
        read_only_fields = ['etudiant', 'date_fin']

# ==============================================================
# NOTES, RÉCLAMATIONS & NOTIFICATIONS
# ==============================================================

class NoteSerializer(serializers.ModelSerializer):
    module_nom = serializers.ReadOnlyField(source='module.nom')

    class Meta:
        model = Note
        fields = ['id', 'etudiant', 'module', 'module_nom', 'valeur', 'commentaire', 'date_publication']
        read_only_fields = ['date_publication']

class ReclamationSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    module_nom = serializers.ReadOnlyField(source='module.nom')

    class Meta:
        model = Reclamation
        fields = [
            'id', 'etudiant', 'module', 'module_nom', 'sujet', 
            'description', 'statut', 'statut_display', 'reponse', 'date_creation'
        ]
        read_only_fields = ['etudiant', 'statut', 'reponse', 'date_creation']

class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_notif_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'destinataire', 'type_notif', 'type_display', 'message', 'est_lu', 'created_at']
        read_only_fields = ['destinataire', 'created_at']

# ==============================================================
# CERTIFICATS
# ==============================================================

class CertificatSerializer(serializers.ModelSerializer):
    etudiant_nom = serializers.ReadOnlyField(source='etudiant.__str__')
    module_nom = serializers.ReadOnlyField(source='module.nom')

    class Meta:
        model = Certificat
        fields = ['id', 'uuid', 'etudiant', 'etudiant_nom', 'module', 'module_nom', 'date_obtention']
        read_only_fields = ['uuid', 'date_obtention']