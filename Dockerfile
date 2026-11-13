FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 tesseract-ocr tesseract-ocr-chi-sim && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-enterprise.txt ./
RUN pip install --no-cache-dir -r requirements-enterprise.txt
RUN useradd --create-home --uid 1000 rag
RUN mkdir -p /state /home/rag/.cache/huggingface && chown -R rag:rag /state /home/rag
COPY --chown=rag:rag app ./app
COPY --chown=rag:rag *.py ./
USER rag
CMD ["uvicorn", "app.enterprise.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
