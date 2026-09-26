import logging
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from google.genai.errors import ClientError, ServerError
from quiz_app.models import Quiz
from quiz_app.functions import create_quiz_from_url
from .permissions import IsOwner
from .serializers import (
    QuizSerializer,
    QuizUpdateSerializer,
    QuizCreateSerializer,
)
from yt_dlp.utils import DownloadError


class QuizGenerationError(APIException):
    """Report a failed quiz generation to the API client."""

    status_code = 503
    default_detail = 'Quiz generation is temporarily unavailable.'
    default_code = 'quiz_generation_failed'


class QuizViewSet(viewsets.ModelViewSet):
    """Manage quizzes belonging to the authenticated user."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated & IsOwner]

    def get_queryset(self):
        """Filter lists by owner and check detail access via permissions."""
        if self.action == 'list':
            return Quiz.objects.filter(user=self.request.user)
        return Quiz.objects.all()

    def get_serializer_class(self):
        """Select the serializer for the current action."""
        if self.action == 'create':
            return QuizCreateSerializer
        if self.action in ('update', 'partial_update'):
            return QuizUpdateSerializer
        return QuizSerializer

    @staticmethod
    def handle_generation_error(exc):
        """Log the original error and return an API error."""
        logging.getLogger(__name__).exception(
            "Quiz generation failed."
        )
        if isinstance(exc, ClientError):
            raise QuizGenerationError(
                'Quiz generation failed. Please check the Gemini configuration.'
            ) from exc
        raise QuizGenerationError() from exc

    def create(self, request, *args, **kwargs):
        """Generate and save a quiz from a YouTube URL."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            quiz = create_quiz_from_url(
                request.user, serializer.validated_data['url']
            )
        except (DownloadError, ClientError, ServerError, RuntimeError, ValueError) as exc:
            self.handle_generation_error(exc)
        return Response(QuizSerializer(quiz).data, status=201)

    def update(self, request, *args, **kwargs):
        """Update a quiz and return its complete details."""
        partial = kwargs.pop('partial', False)
        quiz = self.get_object()
        serializer = self.get_serializer(
            quiz, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(QuizSerializer(quiz).data)
