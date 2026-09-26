from rest_framework import serializers

from quiz_app.models import Quiz, Question


class QuestionSerializer(serializers.ModelSerializer):
    """Serialize quiz questions."""

    class Meta:
        model = Question
        fields = (
            'id',
            'question_title',
            'question_options',
            'answer',
            'created_at',
            'updated_at',
        )


class QuizSerializer(serializers.ModelSerializer):
    """Serialize a quiz with its questions."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        )


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Validate changes to a quiz's title and description."""

    class Meta:
        model = Quiz
        fields = ('title', 'description')


class QuizCreateSerializer(serializers.Serializer):
    """Validate the URL used to generate a quiz."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Allow only supported YouTube video URLs."""
        from urllib.parse import urlparse

        hostname = urlparse(value).hostname
        allowed_hosts = ('youtube.com', 'www.youtube.com', 'youtu.be')

        if hostname not in allowed_hosts:
            raise serializers.ValidationError(
                'Please provide a valid YouTube URL.'
            )
        return value
