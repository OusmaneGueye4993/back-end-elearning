from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views
from .auth_views import (
    EtudiantRegisterView,
    EnseignantRegisterView,
    MonProfilView,
    LogoutView,
)

# ==============================================================
# ROUTER DRF — enregistrement de tous les ViewSets
# ==============================================================

router = DefaultRouter()
router.register(r'modules',       views.ModuleViewSet,         basename='module')
router.register(r'cours',         views.CoursViewSet,          basename='cours')
router.register(r'ressources',    views.RessourceViewSet,      basename='ressource')
router.register(r'inscriptions',  views.InscriptionViewSet,    basename='inscription')
router.register(r'progressions',  views.ProgressionViewSet,    basename='progression')
router.register(r'quizzes',       views.QuizViewSet,           basename='quiz')
router.register(r'soumissions',   views.SoumissionQuizViewSet, basename='soumission')
router.register(r'notes',         views.NoteViewSet,           basename='note')
router.register(r'reclamations',  views.ReclamationViewSet,    basename='reclamation')
router.register(r'notifications', views.NotificationViewSet,   basename='notification')
# NOUVEAU : certificats
router.register(r'certificats',   views.CertificatViewSet,     basename='certificat')

# ==============================================================
# URLs AUTH
# ==============================================================

auth_patterns = [
    path('register/etudiant/',   EtudiantRegisterView.as_view(),  name='register-etudiant'),
    path('register/enseignant/', EnseignantRegisterView.as_view(), name='register-enseignant'),
    path('token/',               TokenObtainPairView.as_view(),    name='token-obtain'),
    path('token/refresh/',       TokenRefreshView.as_view(),       name='token-refresh'),
    path('token/verify/',        TokenVerifyView.as_view(),        name='token-verify'),
    path('profil/',              MonProfilView.as_view(),          name='mon-profil'),
    path('logout/',              LogoutView.as_view(),             name='logout'),
]

# ==============================================================
# URL PATTERNS PRINCIPAL
# ==============================================================

urlpatterns = [
    path('api/auth/', include(auth_patterns)),
    path('api/',      include(router.urls)),
]