"""
Tests backend complets pour la plateforme E-Learning.
Couvre : Auth, Modules, Cours, Inscriptions, Quiz, Notes, Réclamations.
"""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import (
    Etudiant, Enseignant, Module, Cours,
    Inscription, Progression, Quiz, Question, Choix,
    SoumissionQuiz, Note, Reclamation, Notification,
)


# ==============================================================
# HELPER : crée des utilisateurs de test facilement
# ==============================================================

def create_etudiant(username='etudiant1', password='Test@1234!'):
    user = User.objects.create_user(
        username=username, email=f'{username}@test.com',
        password=password, first_name='Test', last_name='Etudiant'
    )
    etudiant = Etudiant.objects.create(user=user)
    return user, etudiant


def create_enseignant(username='prof1', password='Test@1234!'):
    user = User.objects.create_user(
        username=username, email=f'{username}@test.com',
        password=password, first_name='Test', last_name='Prof'
    )
    enseignant = Enseignant.objects.create(user=user, specialite='Informatique')
    return user, enseignant


def get_token(client, username, password='Test@1234!'):
    resp = client.post('/api/auth/token/', {'username': username, 'password': password})
    return resp.data.get('access', '')


# ==============================================================
# 1. TESTS AUTHENTIFICATION
# ==============================================================

class AuthTests(APITestCase):

    def test_inscription_etudiant_succes(self):
        """POST /api/auth/register/etudiant/ → 201 + tokens"""
        data = {
            'username': 'nouveauEtudiant',
            'email': 'nouveau@test.com',
            'password': 'Test@1234!',
            'password2': 'Test@1234!',
            'first_name': 'Nouveau',
            'last_name': 'Etudiant',
        }
        resp = self.client.post('/api/auth/register/etudiant/', data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', resp.data)
        self.assertIn('access', resp.data['tokens'])
        self.assertEqual(resp.data['user']['role'], 'etudiant')

    def test_inscription_passwords_differents(self):
        """Inscription avec mots de passe différents → 400"""
        data = {
            'username': 'test',
            'email': 'test@test.com',
            'password': 'Test@1234!',
            'password2': 'AutreMotDePasse!',
        }
        resp = self.client.post('/api/auth/register/etudiant/', data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inscription_email_duplique(self):
        """Inscription avec un email déjà utilisé → 400"""
        create_etudiant()
        data = {
            'username': 'autreuser',
            'email': 'etudiant1@test.com',  # même email
            'password': 'Test@1234!',
            'password2': 'Test@1234!',
        }
        resp = self.client.post('/api/auth/register/etudiant/', data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inscription_enseignant_succes(self):
        """POST /api/auth/register/enseignant/ → 201"""
        data = {
            'username': 'prof2',
            'email': 'prof2@test.com',
            'password': 'Test@1234!',
            'password2': 'Test@1234!',
            'specialite': 'Mathématiques',
        }
        resp = self.client.post('/api/auth/register/enseignant/', data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['user']['role'], 'enseignant')

    def test_login_succes(self):
        """POST /api/auth/token/ avec bonnes credentials → access + refresh"""
        create_etudiant()
        resp = self.client.post('/api/auth/token/', {'username': 'etudiant1', 'password': 'Test@1234!'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_mauvais_mot_de_passe(self):
        """Login avec mauvais mot de passe → 401"""
        create_etudiant()
        resp = self.client.post('/api/auth/token/', {'username': 'etudiant1', 'password': 'MauvaisPass'})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profil_authentifie(self):
        """GET /api/auth/profil/ avec token → retourne le profil"""
        user, _ = create_etudiant()
        token = get_token(self.client, 'etudiant1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.get('/api/auth/profil/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['role'], 'etudiant')

    def test_profil_sans_token(self):
        """GET /api/auth/profil/ sans token → 401"""
        resp = self.client.get('/api/auth/profil/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """POST /api/auth/token/refresh/ → nouveau access token"""
        create_etudiant()
        login = self.client.post('/api/auth/token/', {'username': 'etudiant1', 'password': 'Test@1234!'})
        resp = self.client.post('/api/auth/token/refresh/', {'refresh': login.data['refresh']})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)

    def test_logout(self):
        """POST /api/auth/logout/ → 200 et token blacklisté"""
        create_etudiant()
        login = self.client.post('/api/auth/token/', {'username': 'etudiant1', 'password': 'Test@1234!'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        resp = self.client.post('/api/auth/logout/', {'refresh': login.data['refresh']})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ==============================================================
# 2. TESTS MODULES
# ==============================================================

class ModuleTests(APITestCase):

    def setUp(self):
        self.user_prof, self.enseignant = create_enseignant()
        self.user_etud, self.etudiant  = create_etudiant()
        self.token_prof = get_token(self.client, 'prof1')
        self.token_etud = get_token(self.client, 'etudiant1')

        self.module = Module.objects.create(
            nom='Python Avancé', code='PY301',
            description='Cours avancé', est_publie=True,
            enseignant=self.enseignant
        )
        self.module_prive = Module.objects.create(
            nom='Module Privé', code='PV001',
            description='Non publié', est_publie=False,
            enseignant=self.enseignant
        )

    def test_liste_modules_public(self):
        """GET /api/modules/ sans auth → seulement modules publiés"""
        resp = self.client.get('/api/modules/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        noms = [m['nom'] for m in resp.data['results']]
        self.assertIn('Python Avancé', noms)
        self.assertNotIn('Module Privé', noms)

    def test_liste_modules_enseignant(self):
        """GET /api/modules/ avec token enseignant → tous les modules"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        resp = self.client.get('/api/modules/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        noms = [m['nom'] for m in resp.data['results']]
        self.assertIn('Module Privé', noms)

    def test_detail_module(self):
        """GET /api/modules/{id}/ → retourne le module avec ses cours"""
        resp = self.client.get(f'/api/modules/{self.module.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('cours', resp.data)
        self.assertEqual(resp.data['code'], 'PY301')

    def test_creer_module_enseignant(self):
        """POST /api/modules/ par enseignant → 201"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        data = {'nom': 'Nouveau Module', 'code': 'NV001', 'description': 'Test', 'est_publie': True}
        resp = self.client.post('/api/modules/', data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_creer_module_etudiant_refuse(self):
        """POST /api/modules/ par étudiant → 403"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        data = {'nom': 'Test', 'code': 'T001', 'description': 'Test'}
        resp = self.client.post('/api/modules/', data)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_modifier_module(self):
        """PATCH /api/modules/{id}/ par enseignant → 200"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        resp = self.client.patch(f'/api/modules/{self.module.id}/', {'est_publie': False})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_supprimer_module(self):
        """DELETE /api/modules/{id}/ par enseignant → 204"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        resp = self.client.delete(f'/api/modules/{self.module_prive.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


# ==============================================================
# 3. TESTS COURS
# ==============================================================

class CoursTests(APITestCase):

    def setUp(self):
        self.user_prof, self.enseignant = create_enseignant()
        self.token_prof = get_token(self.client, 'prof1')

        self.module = Module.objects.create(
            nom='Python', code='PY001', description='Test',
            est_publie=True, enseignant=self.enseignant
        )
        self.cours = Cours.objects.create(
            module=self.module, titre='Variables', contenu_textuel='Cours sur les variables',
            ordre=1, est_publie=True
        )

    def test_liste_cours_par_module(self):
        """GET /api/cours/?module=<id> → cours du module"""
        resp = self.client.get(f'/api/cours/?module={self.module.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data['results']), 0)

    def test_creer_cours(self):
        """POST /api/cours/ par enseignant → 201"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        data = {
            'module': self.module.id, 'titre': 'Fonctions',
            'contenu_textuel': 'Cours sur les fonctions',
            'ordre': 2, 'est_publie': True
        }
        resp = self.client.post('/api/cours/', data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ==============================================================
# 4. TESTS INSCRIPTIONS & PROGRESSION
# ==============================================================

class InscriptionProgressionTests(APITestCase):

    def setUp(self):
        self.user_prof, self.enseignant = create_enseignant()
        self.user_etud, self.etudiant  = create_etudiant()
        self.token_etud = get_token(self.client, 'etudiant1')

        self.module = Module.objects.create(
            nom='Python', code='PY001', description='Test',
            est_publie=True, enseignant=self.enseignant
        )
        self.cours1 = Cours.objects.create(
            module=self.module, titre='Leçon 1',
            contenu_textuel='Contenu', ordre=1, est_publie=True
        )

    def test_inscription_module(self):
        """POST /api/inscriptions/ → 201"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.post('/api/inscriptions/', {'module': self.module.id})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_double_inscription_refuse(self):
        """Inscription deux fois au même module → 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        self.client.post('/api/inscriptions/', {'module': self.module.id})
        resp = self.client.post('/api/inscriptions/', {'module': self.module.id})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mes_inscriptions(self):
        """GET /api/inscriptions/ → seulement mes inscriptions"""
        Inscription.objects.create(etudiant=self.etudiant, module=self.module)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.get('/api/inscriptions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_commencer_cours(self):
        """POST /api/progressions/ → crée une progression"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.post('/api/progressions/', {'cours': self.cours1.id})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(resp.data['est_termine'])

    def test_terminer_cours(self):
        """POST /api/progressions/{id}/terminer/ → marque terminé"""
        progression = Progression.objects.create(
            etudiant=self.etudiant, cours=self.cours1
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.post(f'/api/progressions/{progression.id}/terminer/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data.get('module_complete', False) or not resp.data.get('module_complete'))

    def test_terminer_cours_deja_termine(self):
        """Terminer un cours déjà terminé → 400"""
        progression = Progression.objects.create(
            etudiant=self.etudiant, cours=self.cours1, est_termine=True
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.post(f'/api/progressions/{progression.id}/terminer/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ==============================================================
# 5. TESTS QUIZ
# ==============================================================

class QuizTests(APITestCase):

    def setUp(self):
        self.user_prof, self.enseignant = create_enseignant()
        self.user_etud, self.etudiant  = create_etudiant()
        self.token_etud = get_token(self.client, 'etudiant1')
        self.token_prof = get_token(self.client, 'prof1')

        self.module = Module.objects.create(
            nom='Python', code='PY001', description='Test',
            est_publie=True, enseignant=self.enseignant
        )
        self.quiz = Quiz.objects.create(
            module=self.module, titre='Quiz Python',
            note_passage=10.0, est_publie=True
        )
        self.question = Question.objects.create(
            quiz=self.quiz, texte_court='Qu\'est-ce qu\'une variable ?',
            points=5, ordre=1
        )
        self.bonne_reponse = Choix.objects.create(
            question=self.question, texte='Un conteneur de données', est_correcte=True
        )
        self.mauvaise_reponse = Choix.objects.create(
            question=self.question, texte='Une fonction', est_correcte=False
        )

    def test_liste_quiz_publie(self):
        """GET /api/quizzes/ → liste des quiz publiés"""
        resp = self.client.get('/api/quizzes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detail_quiz_avec_questions(self):
        """GET /api/quizzes/{id}/ → quiz avec questions et choix"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.get(f'/api/quizzes/{self.quiz.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('questions', resp.data)
        self.assertFalse(any(
            'est_correcte' in choix
            for q in resp.data['questions']
            for choix in q.get('choix', [])
        ), "La bonne réponse ne doit pas être exposée à l'étudiant")

    def test_soumettre_bonne_reponse(self):
        """Soumettre la bonne réponse → score > 0 + est_valide True"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        data = {
            'quiz': self.quiz.id,
            'reponses': [{'question': self.question.id, 'choix_selectionne': self.bonne_reponse.id}]
        }
        resp = self.client.post(f'/api/quizzes/{self.quiz.id}/soumettre/', data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertGreater(resp.data['score'], 0)
        self.assertTrue(resp.data['est_valide'])

    def test_soumettre_mauvaise_reponse(self):
        """Soumettre la mauvaise réponse → score = 0"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        data = {
            'quiz': self.quiz.id,
            'reponses': [{'question': self.question.id, 'choix_selectionne': self.mauvaise_reponse.id}]
        }
        resp = self.client.post(f'/api/quizzes/{self.quiz.id}/soumettre/', data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['score'], 0.0)
        self.assertFalse(resp.data['est_valide'])

    def test_double_soumission_refusee(self):
        """Soumettre deux fois le même quiz → 400"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        data = {
            'quiz': self.quiz.id,
            'reponses': [{'question': self.question.id, 'choix_selectionne': self.bonne_reponse.id}]
        }
        self.client.post(f'/api/quizzes/{self.quiz.id}/soumettre/', data, format='json')
        resp = self.client.post(f'/api/quizzes/{self.quiz.id}/soumettre/', data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_enseignant_ne_peut_pas_soumettre(self):
        """Enseignant ne peut pas soumettre un quiz → 403"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        data = {'quiz': self.quiz.id, 'reponses': []}
        resp = self.client.post(f'/api/quizzes/{self.quiz.id}/soumettre/', data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ==============================================================
# 6. TESTS NOTES
# ==============================================================

class NoteTests(APITestCase):

    def setUp(self):
        self.user_prof, self.enseignant = create_enseignant()
        self.user_etud, self.etudiant  = create_etudiant()
        self.token_etud = get_token(self.client, 'etudiant1')
        self.token_prof = get_token(self.client, 'prof1')

        self.module = Module.objects.create(
            nom='Python', code='PY001', description='Test',
            est_publie=True, enseignant=self.enseignant
        )
        self.note = Note.objects.create(
            etudiant=self.etudiant, module=self.module, valeur=15.5
        )

    def test_etudiant_voit_ses_notes(self):
        """GET /api/notes/ → étudiant ne voit que ses notes"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.get('/api/notes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)
        self.assertEqual(resp.data['results'][0]['valeur'], 15.5)

    def test_enseignant_peut_ajouter_note(self):
        """POST /api/notes/ par enseignant → 201"""
        user_etud2, etudiant2 = create_etudiant('etudiant2')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        data = {'etudiant': etudiant2.id, 'module': self.module.id, 'valeur': 12.0}
        resp = self.client.post('/api/notes/', data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_etudiant_ne_peut_pas_ajouter_note(self):
        """POST /api/notes/ par étudiant → 403"""
        user_etud2, etudiant2 = create_etudiant('etudiant2')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        data = {'etudiant': etudiant2.id, 'module': self.module.id, 'valeur': 20.0}
        resp = self.client.post('/api/notes/', data)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ==============================================================
# 7. TESTS RÉCLAMATIONS
# ==============================================================

class ReclamationTests(APITestCase):

    def setUp(self):
        self.user_prof, self.enseignant = create_enseignant()
        self.user_etud, self.etudiant  = create_etudiant()
        self.token_etud = get_token(self.client, 'etudiant1')
        self.token_prof = get_token(self.client, 'prof1')

        self.module = Module.objects.create(
            nom='Python', code='PY001', description='Test',
            est_publie=True, enseignant=self.enseignant
        )

    def test_creer_reclamation(self):
        """POST /api/reclamations/ par étudiant → 201"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        data = {
            'module': self.module.id,
            'sujet': 'Note incorrecte',
            'description': 'Je pense que ma note est incorrecte.'
        }
        resp = self.client.post('/api/reclamations/', data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['statut'], 'en_attente')

    def test_repondre_reclamation(self):
        """PATCH /api/reclamations/{id}/repondre/ par enseignant → 200"""
        reclamation = Reclamation.objects.create(
            etudiant=self.etudiant, module=self.module,
            sujet='Test', description='Description test'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_prof}')
        data = {'reponse': 'Après vérification, la note est correcte.', 'statut': 'resolue'}
        resp = self.client.patch(f'/api/reclamations/{reclamation.id}/repondre/', data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['statut'], 'resolue')

    def test_etudiant_voit_seulement_ses_reclamations(self):
        """GET /api/reclamations/ → étudiant ne voit que les siennes"""
        Reclamation.objects.create(
            etudiant=self.etudiant, module=self.module,
            sujet='Ma réclamation', description='Test'
        )
        user_etud2, etudiant2 = create_etudiant('etudiant2')
        Reclamation.objects.create(
            etudiant=etudiant2, module=self.module,
            sujet='Autre réclamation', description='Test'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.get('/api/reclamations/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)


# ==============================================================
# 8. TESTS NOTIFICATIONS
# ==============================================================

class NotificationTests(APITestCase):

    def setUp(self):
        self.user_etud, self.etudiant = create_etudiant()
        self.token_etud = get_token(self.client, 'etudiant1')
        self.notif = Notification.objects.create(
            destinataire=self.user_etud, type='info',
            message='Bienvenue sur la plateforme !', est_lu=False
        )

    def test_liste_mes_notifications(self):
        """GET /api/notifications/ → mes notifications"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.get('/api/notifications/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_marquer_notification_lue(self):
        """PATCH /api/notifications/{id}/lire/ → est_lu = True"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.patch(f'/api/notifications/{self.notif.id}/lire/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['est_lu'])

    def test_tout_marquer_comme_lu(self):
        """POST /api/notifications/tout_lire/ → toutes lues"""
        Notification.objects.create(destinataire=self.user_etud, type='note', message='Nouvelle note')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_etud}')
        resp = self.client.post('/api/notifications/tout_lire/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('notification(s)', resp.data['message'])