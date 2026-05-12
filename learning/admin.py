from django.contrib import admin
from .models import (
    Etudiant, Enseignant, Module, Cours, Ressource,
    Inscription, Progression, Quiz, Question, Choix,
    SoumissionQuiz, ReponseEtudiant, Note, Reclamation, Notification, Certificat
)

# --- UTILISATEURS ---

@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_naissance', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialite', 'created_at')
    search_fields = ('user__username', 'specialite')

# --- MODULES ET CONTENU ---

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    # CORRECTION : suppression de 'code' (absent du modèle) et 'date_creation'
    # remplacé par 'created_at' (nom réel du champ), ajout de 'est_publie'
    list_display = ('nom', 'enseignant', 'est_publie', 'created_at')
    list_filter = ('enseignant', 'created_at')
    search_fields = ('nom',)
    readonly_fields = ('created_at',)

@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ('titre', 'module', 'ordre', 'est_publie')
    list_filter = ('module',)
    search_fields = ('titre',)

@admin.register(Ressource)
class RessourceAdmin(admin.ModelAdmin):
    list_display = ('titre', 'cours', 'type_ressource', 'ordre')
    list_filter = ('type_ressource',)

# --- INSCRIPTIONS ET PROGRESSION ---

@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    # CORRECTION : suppression de 'statut' (absent du modèle)
    # remplacé par 'est_complete' (champ réel)
    list_display = ('etudiant', 'module', 'est_complete', 'date_inscription')
    list_editable = ('est_complete',)
    list_filter = ('est_complete', 'date_inscription')
    search_fields = ('etudiant__user__username', 'module__nom')

@admin.register(Progression)
class ProgressionAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'cours', 'est_termine', 'date_debut', 'date_fin')
    list_filter = ('est_termine', 'date_debut')
    search_fields = ('etudiant__user__username', 'cours__titre')
    readonly_fields = ('date_debut',)

# --- SECTION QUIZ ---

class ChoixInline(admin.TabularInline):
    model = Choix
    extra = 3

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('titre', 'module', 'note_de_passage', 'est_publie')
    search_fields = ('titre',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('texte', 'quiz', 'points')
    inlines = [ChoixInline]

@admin.register(Choix)
class ChoixAdmin(admin.ModelAdmin):
    list_display = ('texte', 'question', 'est_correct')
    list_filter = ('est_correct',)
    list_editable = ('est_correct',)

@admin.register(SoumissionQuiz)
class SoumissionQuizAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'quiz', 'score', 'reussi', 'date_soumission')
    list_filter = ('reussi', 'quiz')
    readonly_fields = ('date_soumission',)

# --- AUTRES ---

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'module', 'valeur', 'date_publication')
    readonly_fields = ('date_publication',)

@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'etudiant', 'statut', 'date_creation')
    list_filter = ('statut',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # CORRECTION : 'created_at' existe bien dans le modèle Notification
    list_display = ('destinataire', 'type_notif', 'est_lu', 'created_at')
    list_filter = ('type_notif', 'est_lu')

@admin.register(Certificat)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
class CertificatAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'module', 'uuid', 'date_obtention')
    readonly_fields = ('uuid', 'date_obtention')