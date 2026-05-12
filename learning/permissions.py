from rest_framework import permissions

class IsEnseignantOrReadOnly(permissions.BasePermission):
    """
    Autorise la lecture (GET) à tout le monde.
    Autorise la modification (POST, PUT, DELETE) uniquement aux enseignants et admins.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (
            hasattr(request.user, 'enseignant') or request.user.is_staff
        )

class IsAdminOrEnseignant(permissions.BasePermission):
    """
    Accès réservé exclusivement aux enseignants et administrateurs.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            hasattr(request.user, 'enseignant') or request.user.is_staff
        )

class IsEtudiant(permissions.BasePermission):
    """
    Accès réservé exclusivement aux étudiants.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'etudiant')

class IsProprietaireOuReadOnly(permissions.BasePermission):
    """
    Permission de niveau objet : 
    - Lecture autorisée pour tous.
    - Modification autorisée seulement si l'utilisateur est l'enseignant propriétaire.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Si l'objet est un Module
        if hasattr(obj, 'enseignant'):
            return obj.enseignant.user == request.user
        
        # Si l'objet est un Cours ou une Ressource (lié indirectement via le module)
        if hasattr(obj, 'module'):
            return obj.module.enseignant.user == request.user
            
        return request.user.is_staff