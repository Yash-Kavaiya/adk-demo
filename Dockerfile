# BookForge production image: Python + ffmpeg + LaTeX + whisper deps.
# Runs the pipeline as a batch job (Cloud Run Job / any container runner).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg: frame extraction + audio. texlive: book compilation
# (latex-recommended: booktabs/graphics; pictures: TikZ/pgf).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-pictures \
        latexmk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY bookforge ./bookforge
RUN pip install "."

# Non-root runtime user; workspace on a mounted volume in production.
RUN useradd --create-home bookforge && mkdir -p /data && chown bookforge /data
USER bookforge
ENV BOOKFORGE_WORKSPACE_ROOT=/data

# Pass the channel URL at run time:
#   docker run -e GOOGLE_API_KEY -e CHANNEL_URL=https://youtube.com/@x <image>
ENTRYPOINT ["python", "-m", "bookforge.docker_entry"]
CMD []
