import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.template import response
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from quiz_app.functions import (
    download_audio,
    generate_questions,
    generate_quiz,
    save_quiz,
    transcribe_audio,
    validate_question,
    validate_questions,
)
from quiz_app.models import Quiz, Question
from quiz_app.api.permissions import IsOwner

from google.genai.errors import ClientError


class QuestionValidationTests(SimpleTestCase):
    """Test validation of generated quiz questions."""

    def test_rejects_question_with_three_options(self):
        """Reject a question that does not have four options."""
        question = {
            'question_title': 'Was ist Python?',
            'question_options': ['Sprache', 'Framework', 'Browser'],
            'answer': 'Sprache',
        }

        with self.assertRaisesMessage(ValueError, 'exactly 4 options'):
            validate_question(question)

    def test_accepts_valid_question(self):
        """Accept a question with four valid answer options."""
        question = {
            'question_title': 'Was ist Python?',
            'question_options': ['Sprache', 'Framework', 'Browser', 'Datenbank'],
            'answer': 'Sprache',
        }
        validate_question(question)

    def test_rejects_wrong_question_count(self):
        """Reject a quiz with fewer than ten questions."""
        data = {'questions': []}
        data.update({
            'title': 'Testquiz',
            'description': 'Ein Quiz für die Validierungstests.',
        })

        with self.assertRaisesMessage(ValueError, 'invalid number of questions'):
            validate_questions(data)

    def test_accepts_ten_valid_questions(self):
        """Accept a quiz containing ten valid questions."""
        question = {
            'question_title': 'Was ist Python?',
            'question_options': ['Sprache', 'Framework', 'Browser', 'Datenbank'],
            'answer': 'Sprache',
        }
        data = {'questions': [question.copy() for _ in range(10)]}
        data.update({
            'title': 'Testquiz',
            'description': 'Ein Quiz für die Validierungstests.',
        })
        validate_questions(data)


class GeminiGenerationTests(SimpleTestCase):
    """Test quiz generation without calling the Gemini API."""

    @patch('quiz_app.functions.validate_questions')
    @patch('quiz_app.functions.get_gemini_client')
    def test_generate_questions_returns_gemini_questions(
        self, mock_client, mock_validate
    ):
        """Return complete quiz data after validation."""
        quiz_data = {
            'title': 'Python-Grundlagen',
            'description': 'Ein Quiz über Python.',
            'questions': [{'question_title': 'Testfrage'}],
        }

        gemini = mock_client.return_value.__enter__.return_value
        gemini.models.generate_content.return_value.text = json.dumps(
            quiz_data)

        self.assertEqual(generate_questions('Testtranskript'), quiz_data)
        mock_validate.assert_called_once_with(quiz_data)

    def test_validate_questions_rejects_empty_quiz_details(self):
        """Reject empty generated titles and descriptions."""
        data = {'title': 'Quiz', 'description': 'Beschreibung', 'questions': []}
        for field in ('title', 'description'):
            with self.subTest(field=field):
                data[field] = '  '
                with self.assertRaisesRegex(ValueError, f'invalid {field}'):
                    validate_questions(data)
                data[field] = 'CorrectText'


class QuizCreationTests(TestCase):
    """Test quiz creation through the API."""

    def setUp(self):
        """Create an authenticated API client."""
        self.user = get_user_model().objects.create_user(
            username='quiztester', password='test-password-123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('quiz_app.functions.generate_quiz')
    def test_create_quiz_saves_questions(self, mock_generate):
        """Save and return a quiz with its generated questions."""
        question = {
            'question_title': 'Was ist Python?',
            'question_options': ['Sprache', 'Framework', 'Browser', 'Datenbank'],
            'answer': 'Sprache',
        }
        mock_generate.return_value = {
            'title': 'Python-Grundlagen',
            'description': 'Ein Quiz über die Grundlagen von Python.',
            'questions': [question.copy() for _ in range(10)],
        }
        response = self.client.post(
            '/api/quizzes/',
            {'url': 'https://www.youtube.com/watch?v=y3CBt6i0qYw'},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'Python-Grundlagen')
        self.assertEqual(
            response.data['description'],
            'Ein Quiz über die Grundlagen von Python.',
        )
        self.assertEqual(Quiz.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Question.objects.count(), 10)
        self.assertEqual(len(response.data['questions']), 10)

    def test_create_quiz_rejects_invalid_url(self):
        """Reject an invalid URL without creating a quiz."""
        response = self.client.post(
            '/api/quizzes/',
            {'url': 'https://example.com/video'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Quiz.objects.count(), 0)

    @patch('quiz_app.functions.generate_quiz')
    def test_create_quiz_handles_generation_error(self, mock_generate):
        """Return 503 without saving a quiz if generation fails."""
        mock_generate.side_effect = RuntimeError('Gemini unavailable')

        response = self.client.post(
            '/api/quizzes/',
            {'url': 'https://www.youtube.com/watch?v=y3CBt6i0qYw'},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(Quiz.objects.count(), 0)
        self.assertEqual(Question.objects.count(), 0)

    @patch('quiz_app.functions.generate_quiz')
    def test_create_quiz_handles_gemini_client_error(self, mock_generate):
        """Return an API error without saving a quiz."""
        mock_generate.side_effect = ClientError(
            400, {'error': {'message': 'Invalid request'}}
        )
        response = self.client.post(
            '/api/quizzes/',
            {'url': 'https://www.youtube.com/watch?v=y3CBt6i0qYw'},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Quiz.objects.count(), 0)
        self.assertEqual(Question.objects.count(), 0)


class QuizSavingTests(TestCase):
    """Test atomic saving of quizzes and questions."""

    @patch('quiz_app.functions.Question.objects.create')
    def test_save_quiz_rolls_back_on_question_error(self, mock_create):
        """Remove the quiz if saving a question fails."""
        user = get_user_model().objects.create_user(
            username='rollbacktester', password='test-password-123'
        )
        mock_create.side_effect = RuntimeError('Saving failed')

        with self.assertRaises(RuntimeError):
            save_quiz(user, 'https://youtu.be/y3CBt6i0qYw', {
                'title': 'Testquiz',
                'description': 'Testbeschreibung',
                'questions': [{}],
            })

        self.assertEqual(Quiz.objects.count(), 0)
        self.assertEqual(Question.objects.count(), 0)


class AudioDownloadTests(SimpleTestCase):
    """Test audio downloads without accessing YouTube."""

    @patch('quiz_app.functions.yt_dlp.YoutubeDL')
    def test_download_audio_returns_mp3_path(self, mock_downloader):
        """Download audio and return the expected MP3 path."""
        downloader = mock_downloader.return_value.__enter__.return_value
        result = download_audio('https://youtu.be/test', 'temp/audio')

        downloader.download.assert_called_once_with(
            ['https://youtu.be/test']
        )
        self.assertEqual(result, 'temp/audio.mp3')


class AudioTranscriptionTests(SimpleTestCase):
    """Test transcription without loading Whisper."""

    @patch('quiz_app.functions.get_whisper_model')
    def test_transcribe_audio_returns_clean_text(self, mock_model):
        """Return the transcript without surrounding whitespace."""
        mock_model.return_value.transcribe.return_value = {
            'text': '  Das ist ein Test.  '
        }

        result = transcribe_audio('temp/audio.mp3')

        mock_model.return_value.transcribe.assert_called_once_with(
            'temp/audio.mp3'
        )
        self.assertEqual(result, 'Das ist ein Test.')


class QuizGenerationFlowTests(SimpleTestCase):
    """Test the generation flow without external services."""

    @patch('quiz_app.functions.generate_questions')
    @patch('quiz_app.functions.transcribe_audio')
    @patch('quiz_app.functions.download_audio')
    def test_generate_quiz_connects_all_steps(
        self, mock_download, mock_transcribe, mock_questions
    ):
        """Pass downloaded audio through transcription to generation."""
        mock_download.return_value = 'temp/audio.mp3'
        mock_transcribe.return_value = 'Testtranskript'
        mock_questions.return_value = [{'question_title': 'Testfrage'}]

        result = generate_quiz('https://youtu.be/test')

        mock_download.assert_called_once()
        mock_transcribe.assert_called_once_with('temp/audio.mp3')
        mock_questions.assert_called_once_with('Testtranskript')
        self.assertEqual(result, mock_questions.return_value)


class QuizPermissionTests(TestCase):
    """Test access to quizzes based on ownership."""

    def test_is_owner_allows_only_quiz_owner(self):
        """Allow the owner and reject another user."""
        user_model = get_user_model()
        owner = user_model.objects.create_user(username='owner')
        other = user_model.objects.create_user(username='other')
        quiz = Quiz.objects.create(
            user=owner,
            title='Testquiz',
            description='',
            video_url='https://youtu.be/test',
        )
        permission = IsOwner()
        request = self.client.request().wsgi_request
        request.user = owner
        self.assertTrue(permission.has_object_permission(request, None, quiz))
        request.user = other
        self.assertFalse(permission.has_object_permission(request, None, quiz))


class QuizAccessTests(TestCase):
    """Test access to quizzes through the API."""

    def test_user_cannot_retrieve_another_users_quiz(self):
        """Return 404 when requesting another user's quiz."""
        owner = get_user_model().objects.create_user(username='quizowner')
        other = get_user_model().objects.create_user(username='quizother')
        quiz = Quiz.objects.create(
            user=owner, title='Privates Quiz',
            description='', video_url='https://youtu.be/test',
        )
        client = APIClient()
        client.force_authenticate(user=other)
        response = client.get(f'/api/quizzes/{quiz.id}/')
        self.assertEqual(response.status_code, 403)


class QuizListTests(TestCase):
    """Test listing quizzes through the API."""

    def setUp(self):
        """Create users, quizzes and an authenticated client."""
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='listuser')
        self.other = user_model.objects.create_user(username='otheruser')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        Quiz.objects.create(
            user=self.user,
            title='Eigenes Quiz',
            description='',
            video_url='https://youtu.be/own',
        )
        Quiz.objects.create(
            user=self.other,
            title='Fremdes Quiz',
            description='',
            video_url='https://youtu.be/other',
        )

    def test_list_returns_only_own_quizzes(self):
        """Return only quizzes belonging to the authenticated user."""
        response = self.client.get('/api/quizzes/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Eigenes Quiz')

    def test_retrieve_returns_own_quiz(self):
        """Return a quiz belonging to the authenticated user."""
        quiz = Quiz.objects.get(title='Eigenes Quiz')

        response = self.client.get(f'/api/quizzes/{quiz.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Eigenes Quiz')

    def test_update_changes_own_quiz(self):
        """Update a quiz belonging to the authenticated user."""
        quiz = Quiz.objects.get(title='Eigenes Quiz')

        response = self.client.patch(
            f'/api/quizzes/{quiz.id}/',
            {'title': 'Geändertes Quiz'},
        )

        self.assertEqual(response.data['title'], 'Geändertes Quiz')
        self.assertIn('questions', response.data)
        self.assertEqual(response.status_code, 200)
        quiz.refresh_from_db()
        self.assertEqual(quiz.title, 'Geändertes Quiz')

    def test_delete_removes_own_quiz(self):
        """Delete a quiz belonging to the authenticated user."""
        quiz = Quiz.objects.get(title='Eigenes Quiz')

        response = self.client.delete(f'/api/quizzes/{quiz.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Quiz.objects.filter(id=quiz.id).exists())

    def test_user_cannot_update_another_users_quiz(self):
        """Prevent updating another user's quiz."""
        owner = get_user_model().objects.create_user(username='updateowner')
        quiz = Quiz.objects.create(
            user=owner,
            title='Fremdes Quiz',
            description='',
            video_url='https://youtu.be/test',
        )

        response = self.client.patch(
            f'/api/quizzes/{quiz.id}/',
            {'title': 'Manipuliert'},
        )

        self.assertEqual(response.status_code, 403)
        quiz.refresh_from_db()
        self.assertEqual(quiz.title, 'Fremdes Quiz')

    def test_user_cannot_delete_another_users_quiz(self):
        """Prevent deleting another user's quiz."""
        owner = get_user_model().objects.create_user(username='deleteowner')
        quiz = Quiz.objects.create(
            user=owner,
            title='Fremdes Quiz',
            description='',
            video_url='https://youtu.be/test',
        )

        response = self.client.delete(f'/api/quizzes/{quiz.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Quiz.objects.filter(id=quiz.id).exists())


class QuizCookieIntegrationTests(TestCase):
    """Test cookie authentication across auth and quiz APIs."""

    def test_login_cookie_allows_quiz_access(self):
        """Access the quiz API using the cookie from login."""
        get_user_model().objects.create_user(
            username='cookieuser', password='test-password-123'
        )
        client = APIClient()
        login = client.post(
            '/api/login/',
            {'username': 'cookieuser', 'password': 'test-password-123'},
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn('access_token', client.cookies)
        response = client.get('/api/quizzes/')
        self.assertEqual(response.status_code, 200)
