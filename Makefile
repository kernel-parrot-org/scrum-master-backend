dcu:
	docker compose up --build -d

dcd:
	docker compose down

uhead:
	docker compose exec uv run alembic upgrade head
