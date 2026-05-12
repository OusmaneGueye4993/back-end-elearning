import os
from django.core.exceptions import ValidationError

def validate_file_size(value):
    """Limite la taille des fichiers à 50Mo"""
    filesize = value.size
    if filesize > 52428800:
        raise ValidationError("La taille maximale est de 50 Mo")

def validate_is_video(value):
    """Vérifie si le fichier est une vidéo"""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.wmv', '.avi']
    if ext not in valid_extensions:
        raise ValidationError("Format vidéo non supporté (.mp4, .mkv, .wmv, .avi uniquement)")

def validate_is_pdf(value):
    """Vérifie si le fichier est un PDF"""
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError("Le fichier doit être au format PDF.")