init:
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	docker compose exec django python manage.py migrate
	docker compose exec django python manage.py seed_subway_lines
restart:
	docker compose down
	docker compose up -d
	docker compose exec django python manage.py migrate