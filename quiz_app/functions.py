import yt_dlp
import tempfile
import whisper
from functools import lru_cache
from google import genai
import json
from django.db import transaction

from quiz_app.models import Quiz, Question


def get_gemini_client():
    """Create a Gemini client using the configured API key."""
    return genai.Client()


def build_quiz_prompt(transcript, question_count=10):
    """Build a prompt for quiz details and questions."""
    return (
        f"Create a German quiz with exactly {question_count} questions. "
        "Use only information from the transcript. "
        "Return a JSON object with 'title', 'description' and 'questions'. "
        "The title and description must summarize the video in German. "
        "Each question must contain 'question_title', 'question_options' "
        "(exactly 4 non-empty strings) and 'answer' "
        "(the exact text of the correct option). "
        f"Transcript:\n{transcript}"
    )


def generate_questions(transcript):
    """Generate quiz questions from a video transcript."""
    prompt = build_quiz_prompt(transcript)
    with get_gemini_client() as client:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={'response_mime_type': 'application/json'},
        )
    data = json.loads(response.text)
    validate_questions(data)
    return data


def validate_options(options):
    """Validate the answer options of a quiz question."""
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError('Each question must have exactly 4 options.')
    if not all(isinstance(option, str) and option.strip() for option in options):
        raise ValueError('Each answer option must be a non-empty string.')


def validate_question(question):
    """Validate the structure of a single quiz question."""
    if not isinstance(question, dict):
        raise ValueError('Gemini returned an invalid question.')
    options = question.get('question_options')
    validate_options(options)
    if question.get('answer') not in options:
        raise ValueError('The correct answer must match an option.')
    title = question.get('question_title')
    if not isinstance(title, str) or not title.strip():
        raise ValueError('Each question must have a title.')


def validate_questions(data, question_count=10):
    """Validate the structure of generated quiz questions."""
    if not isinstance(data, dict):
        raise ValueError('Gemini returned an invalid response.')
    for field in ('title', 'description'):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Gemini returned an invalid {field}.')
    questions = data.get('questions')
    if not isinstance(questions, list) or len(questions) != question_count:
        raise ValueError('Gemini returned an invalid number of questions.')
    for question in questions:
        validate_question(question)


def generate_quiz(video_url):
    """Generate quiz data from a YouTube video."""

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = f'{temp_dir}/audio'
        mp3_path = download_audio(video_url, audio_path)
        transcript = transcribe_audio(mp3_path)
        return generate_questions(transcript)


def get_download_options(output_path):
    """Build yt-dlp options for downloading MP3 audio."""

    return {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }


def download_audio(video_url, output_path):
    """Download a YouTube video's audio to the given path."""

    options = get_download_options(output_path)
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([video_url])
    return f'{output_path}.mp3'


def transcribe_audio(audio_path):
    """Transcribe an audio file using a local Whisper model."""

    model = get_whisper_model()
    result = model.transcribe(audio_path)
    return result['text'].strip()


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load and cache the local Whisper model."""
    return whisper.load_model('base')


@transaction.atomic
def save_quiz(user, video_url, quiz_data):
    """Save generated quiz details and questions atomically."""
    quiz = Quiz.objects.create(
        user=user,
        title=quiz_data['title'],
        description=quiz_data['description'],
        video_url=video_url,
    )
    for question in quiz_data['questions']:
        Question.objects.create(quiz=quiz, **question)
    return quiz


def create_quiz_from_url(user, video_url):
    """Generate a quiz from a video and save it for the user."""
    questions = generate_quiz(video_url)
    return save_quiz(user, video_url, questions)
