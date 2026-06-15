FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN chmod +x entrypoint.sh

# El puerto real lo inyecta la plataforma vía $PORT (Render/Railway/Fly); 8000 por defecto.
# El entrypoint aplica migraciones, siembra el admin (si SEED_ADMIN_*) y arranca uvicorn.
EXPOSE 8000
CMD ["./entrypoint.sh"]
