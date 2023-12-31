# Сервис аренды вещей

Этот репозиторий содержит серверную и клиентскую части веб-приложения для сервиса аренды вещей.

## Функционал системы

В зависимости от роли пользователя система имеет следующий функционал:

### 1. Администратор
Администратор имеет следующие функции:
- Модерация объявлений: возможность удалить объявление в случае нарушения правил платформы;
- Решение конфликтных ситуаций: администратор принимает жалобы пользователей и решает конфликтные ситуации.

### 2. Клиент (зарегистрированный пользователь)
Зарегистрированный пользователь имеет следующие возможности:
- Поиск и просмотр объявлений по категориям;
- Оформление аренды: заполнение формы с параметрами аренды и отправка заявки арендодателю;
- Ожидание ответа по заявке: заявка может быть отклонена или принята;
- Начало аренды: подтверждение договора аренды при получении предмета аренды;
- Завершение аренды: окончание аренды при возврате предмета аренды и нажатие кнопки "Закончить аренду" со стороны арендодателя;
- Сдача своих вещей в аренду.

### 3. Гость (незарегистрированный пользователь)
Гость может:
- Посмотреть товары выбранной категории без регистрации;
- Просматривать информацию по объявлениям;
- Оформить аренду после процедуры регистрации.

## Технологии реализации

### Серверная часть
- Язык программирования Python;
- Фреймворк Flask;
- Взаимодействие с WebSocket с использованием библиотеки socket.io для работы в режиме реального времени.

### Клиентская часть
- Фреймворк Bootstrap.

### СУБД
- PostgreSQL: бесплатная СУБД с открытым исходным кодом.

### Основной протокол обмена данными
- Протокол WebSocket: используется для обмена сообщениями по двустороннему соединению с минимальными задержками, обеспечивая реализацию сервиса реального времени.

## Описание архитектуры приложения

Главным файлом приложения является `app.py`. В этом файле подключаются все необходимые библиотеки и настраивается база
данных. Также в `app.py` описаны классы для работы с базой данных и все функции для работы приложения.

Остальные файлы имеют расширение `.html` и содержат графический интерфейс приложения. Файл `base.html` является шаблоном
для других HTML-файлов.