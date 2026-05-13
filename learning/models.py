from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# IMPORT CORRIGÉ : Ajout de validate_is_pdf
from .validators import validate_file_size, validate_is_video, validate_is_pdf

# ==============================================================
# PROFILS UTILISATEURS
# ==============================================================

class Etudiant(models.Model):
    user           = models.OneToOneField(User, on_delete=models.CASCADE, related_name='etudiant')
    date_naissance = models.DateField(null=True, blank=True)
    photo          = models.ImageField(
        upload_to='photos/etudiants/', 
        null=True, 
        blank=True,
        validators=[validate_file_size]
    )
    bio            = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user'], name='etudiant_user_idx')]

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name if full_name else self.user.username


class Enseignant(models.Model):
    user           = models.OneToOneField(User, on_delete=models.CASCADE, related_name='enseignant')
    specialite     = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    photo          = models.ImageField(
        upload_to='photos/enseignants/', 
        null=True, 
        blank=True,
        validators=[validate_file_size]
    )
    bio            = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user'], name='enseignant_user_idx')]

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return f"Pr. {full_name if full_name else self.user.username}"


# ==============================================================
# CONTENU PEDAGOGIQUE
# ==============================================================

class Module(models.Model):
    nom         = models.CharField(max_length=200)
    description = models.TextField()
    image       = models.ImageField(upload_to='modules/', null=True, blank=True)
    enseignant  = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, related_name='modules')
    est_publie  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    statut      = models.CharField(max_length=20, default='en_cours')
    code        = models.CharField(max_length=20, blank=True, default='')
    def __str__(self):
        return self.nom


class Cours(models.Model):
    module      = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='cours')
    titre       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ordre       = models.PositiveIntegerField(default=0)
    est_publie  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre']
        verbose_name_plural = "Cours"

    def __str__(self):
        return f"{self.module.nom} - {self.titre}"

class Ressource(models.Model):
    TYPE_CHOICES = [
        ('video', 'Vidéo'),
        ('pdf',   'Document PDF'),
        ('link',  'Lien externe'),
    ]
    cours          = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='ressources')
    titre          = models.CharField(max_length=200)
    type_ressource = models.CharField(max_length=10, choices=TYPE_CHOICES)
    fichier        = models.FileField(
        upload_to='cours/ressources/', 
        null=True, 
        blank=True,
        validators=[validate_file_size] 
    )
    url            = models.URLField(blank=True, default="")
    ordre          = models.PositiveIntegerField(default=0)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.type_ressource == 'video' and self.fichier:
            try:
                validate_is_video(self.fichier)
            except ValidationError as e:
                raise ValidationError({'fichier': e.messages})

        if self.type_ressource == 'pdf' and self.fichier:
            try:
                validate_is_pdf(self.fichier)
            except ValidationError as e:
                raise ValidationError({'fichier': e.messages})
        
        if self.type_ressource == 'link' and not self.url:
            raise ValidationError({'url': "Veuillez renseigner une URL pour un lien externe."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return self.titre

# ==============================================================
# AUTRES MODÈLES (QUIZ, PROGRESSION, ETC.)
# ==============================================================

class Inscription(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('accepte', 'Accepté'),
        ('refuse', 'Refusé'),
    ]
    etudiant    = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='inscriptions')
    module      = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='inscriptions')
    date_inscription = models.DateTimeField(auto_now_add=True)
    est_complete = models.BooleanField(default=False) # <--- Ajoutez ceci
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente') # NOUVEAU
    class Meta:
        unique_together = ('etudiant', 'module')
        indexes = [models.Index(fields=['etudiant', 'module'], name='inscr_etud_mod_idx')]

class Progression(models.Model):
    etudiant    = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='progressions')
    cours       = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='progressions')
    date_debut  = models.DateTimeField(auto_now_add=True)
    date_fin    = models.DateTimeField(null=True, blank=True)
    est_termine = models.BooleanField(default=False)

    class Meta:
        unique_together = ('etudiant', 'cours')

class Quiz(models.Model):
    module      = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='quiz')
    titre       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    note_de_passage = models.PositiveIntegerField(default=70)
    est_publie  = models.BooleanField(default=False)

class Question(models.Model):
    quiz  = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    texte = models.TextField()
    points = models.PositiveIntegerField(default=1)

class Choix(models.Model):
    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choix')
    texte      = models.CharField(max_length=255)
    est_correct = models.BooleanField(default=False)

class SoumissionQuiz(models.Model):
    etudiant   = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='soumissions')
    quiz       = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='soumissions')
    date_soumission = models.DateTimeField(auto_now_add=True)
    score      = models.FloatField(default=0.0)
    reussi     = models.BooleanField(default=False)

class ReponseEtudiant(models.Model):
    soumission = models.ForeignKey(SoumissionQuiz, on_delete=models.CASCADE, related_name='reponses')
    question   = models.ForeignKey(Question, on_delete=models.CASCADE)
    choix_selectionne = models.ForeignKey(Choix, null=True, blank=True, on_delete=models.CASCADE)

class Note(models.Model):
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='notes')
    module   = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='notes')
    valeur   = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(20)])
    commentaire = models.TextField(blank=True)
    date_publication = models.DateTimeField(auto_now_add=True)

class Certificat(models.Model):
    uuid           = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    etudiant       = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='certificats')
    module         = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='certificats')
    date_obtention = models.DateTimeField(auto_now_add=True)

class Reclamation(models.Model):
    STATUT_CHOICES = [('en_attente', 'En attente'), ('en_cours', 'En cours'), ('resolue', 'Résolue')]
    etudiant      = models.ForeignKey(Etudiant, on_delete=models.CASCADE, blank=True, related_name='reclamations')
    module        = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, related_name='reclamations')
    sujet         = models.CharField(max_length=200)
    description   = models.TextField()
    reponse       = models.TextField(blank=True)
    statut        = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['statut'], name='reclam_statut_idx'),
            models.Index(fields=['-date_creation'], name='reclam_date_idx'),
        ]

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'), ('note', 'Nouvelle note'), 
        ('cours', 'Nouveau cours'), ('quiz', 'Nouveau quiz'), 
        ('reclamation', 'Réclamation mise à jour'), ('certificat', 'Certificat obtenu')
    ]
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notif   = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    message      = models.TextField()
    est_lu       = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['destinataire', 'est_lu'], name='notif_dest_lu_idx')]