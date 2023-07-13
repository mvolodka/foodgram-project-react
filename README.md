# Foodgram - социальная сеть о кулинарных рецептах!
### Делитесь рецептами и пробуйте новые.
---
### Сервис доступен по адресу:
```
https://foodgrammy.ddns.net/
```

### Возможности сервиса:
- делитесь своими рецептами
- смотрите рецепты других пользователей
- добавляйте рецепты в избранное
- быстро формируйте список покупок и скачивайте его, добавляя рецепт в корзину
- следите за своими друзьями и коллегами и их рецептами

### Технологии:
- Django
- Python
- Docker

### Запуск проекта:
1. Клонируйте проект на локальный компьютер:
```
git clone git@github.com:mvolodka/foodgram-project-react.git
```
2. Подготовьте сервер:
```
scp docker-compose.yml <username>@<host>:/home/<username>/
scp nginx.conf <username>@<host>:/home/<username>/
scp .env <username>@<host>:/home/<username>/
```
3. Установите docker и docker-compose:
```
sudo apt install docker.io 
sudo apt install docker-compose
```
4. Соберите контейнер и выполните миграции:
```
sudo docker compose -f docker-compose.yml up -d
sudo docker-compose exec backend python manage.py migrate

```
5. Создайте суперюзера и соберите статику:
```
sudo docker-compose exec backend python manage.py createsuperuser
sudo docker-compose exec backend python manage.py collectstatic --no-input
```
6. Скопируйте предустановленные данные json:
```
docker-compose exec backend python manage.py load_ingredients --path data/
```
7. Данные для проверки работы приложения:
Суперпользователь:
```
email: witcher@mail.ru
password: Qw_138!@8uTh6@
```

Пользователь:
```
email: vpupkin@mail.ru
password: sufmad-kixjoj-4zafFy
```
