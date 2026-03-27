FROM python:3.11-slim

# HF Spaces roda como usuário não-root (uid 1000)
RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Copia e instala dependências primeiro (aproveita cache do Docker)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto
COPY --chown=user . .

# HF Spaces expõe a porta 7860
EXPOSE 7860

# Gunicorn: app = server no dashboard_plotly.py
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "200", "app:server"]