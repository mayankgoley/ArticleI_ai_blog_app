FROM python:3.10-slim

# Install system dependencies (ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for cookies and temp audio
RUN mkdir -p cookies temp_audio
RUN chmod 777 cookies temp_audio

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Start command
CMD ["gunicorn", "ai_blog_app.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120"]
