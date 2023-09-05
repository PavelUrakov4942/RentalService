# Импортирование необходимых модулей
import os
from uuid import uuid4
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, request, redirect, flash, json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_socketio import SocketIO
from datetime import date

load_dotenv(find_dotenv())

# Создание экземпляра app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Создание экземпляра socketio
socketio = SocketIO(app)

# Настройки приложения и подключения к базе данных
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')

# Создание экземпляра login_manager
login_manager = LoginManager(app)


# Создание моделей базы данных
# Пользователь
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    role = db.Column(db.String(13), nullable=True)
    phone = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(50), nullable=True, unique=True)
    hash_password = db.Column(db.String(500), nullable=True)


# Определение функции user_loader экземпляра login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# Предмет
class Item(db.Model):
    __tablename__ = 'item'
    id_item = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    rent_price = db.Column(db.Numeric, nullable=True)
    image_url = db.Column(db.String(100), nullable=True)


# Объявление аренды
class RentOut(db.Model):
    __tablename__ = 'rent_out'
    id_rent_out = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(9), nullable=True)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"))
    id_item = db.Column(db.Integer, db.ForeignKey("item.id_item"))


# Заявка на аренду
class RentIn(db.Model):
    __tablename__ = 'rent_in'
    id_rent_in = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=True)
    date_rent_start = db.Column(db.DateTime, nullable=True)
    date_rent_finish = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"))
    id_rent_out = db.Column(db.Integer, db.ForeignKey("rent_out.id_rent_out"))


# Корзина
class Bag(db.Model):
    __tablename__ = 'bag'
    id_bag = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"))
    id_rent_out = db.Column(db.Integer, db.ForeignKey("rent_out.id_rent_out"))


# Жалоба
class Complaint(db.Model):
    __tablename__ = 'complaint'
    id_complaint = db.Column(db.Integer, primary_key=True)
    id_rent_in = db.Column(db.Integer, db.ForeignKey("rent_in.id_rent_in"))
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"))
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=True)


# Обработчики адресов
# Главная страница
@app.route("/")
def home():
    return render_template("home.html")


# Страница регистрации
@app.route("/registration", methods=("POST", "GET"))
def registration():
    if request.method == "POST":
        # Получение данных из формы
        username = request.form["username"]
        dob = request.form["dob"]
        phone = request.form["phone"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm"]
        # Валидация полученных данных
        if len(username) > 20 or len(username) < 1 or username.isalpha() is False:
            flash("Имя должно состоять из алфавитных символов и быть длинной от 1 до 20 символов.")
        elif len(dob) != 10 or (
                (date.today().year - int(dob[:4])) * 12 * 30 + date.today().month * 30 + date.today().day - (
                int(dob[5:7]) * 30 + int(dob[8:10]))) / 360 < 18:
            flash(
                "Регистрация доступна только с 18 лет. Если Вы достигли указанного возраста проверьте формат даты.")
        elif len(phone) != 12 or (phone[0] + phone[1] != "+7") or phone[1:].isdigit() is False:
            flash("Неверный формат номера.")
        elif email.count("@") != 1 or email.count(".") < 1 or len(email) < 6 or len(email) > 50:
            flash("Неверный формат электронной почты.")
        elif len(password) > 20 or len(password) < 3:
            flash("Длина пароля должна составлять от 3 до 20 символов.")
        elif password != confirm:
            flash("Пароли не совпадают.")
        else:
            try:
                # Создание экземпляра класса User и добавление его в бд
                hash = generate_password_hash(password)
                user = User(
                    username=username,
                    dob=dob,
                    role="клиент",
                    phone=phone,
                    email=email,
                    hash_password=hash)
                db.session.add(user)
                db.session.commit()
                flash("Учётная запись успешно создана.", category="success")
                return redirect("/profile")
            except:
                db.session.rollback()
                flash(
                    "Проверьте корректность введённых данных. Возможно, пользователь с таким Email уже зарегистрирован.")

    return render_template("registration.html")


# Определение профиля
@app.route("/profile")
@login_required
def profile():
    # Проверка роли пользователя
    user_login = User.query.get(current_user.id)
    if user_login.role == "клиент":
        return redirect("/profile_client")
    else:
        return redirect("/profile_admin")


# Страница профиля клиента
@app.route("/profile_client")
@login_required
def profile_client():
    # Проверка роли пользователя
    user = User.query.get(current_user.id)
    if user.role != "клиент":
        return redirect("/profile")
    return render_template("profile_client.html", user=user)


# Страница профиля администратора
@app.route("/profile_admin")
@login_required
def profile_admin():
    # Определение роли пользователя
    admin = User.query.get(current_user.id)
    if admin.role != "администратор":
        return redirect("/profile")
    return render_template("profile_admin.html", admin=admin)


# Страница входа в систему
@app.route("/login", methods=("POST", "GET"))
def login():
    if request.method == "POST":
        # Получение данных из формы
        email = request.form["email"]
        password = request.form["password"]
        # Валидация полученных данных
        if email.count("@") != 1 or email.count(".") < 1 or len(email) < 6 or len(email) > 50:
            flash("Неверный формат электронной почты.")
        elif len(password) > 20 or len(password) < 3:
            flash("Длина пароля должна составлять от 3 до 20 символов.")
        else:
            # Получение из бд пользователя по полю email
            user = User.query.filter_by(email=email).first()
            # Если данные верны, то пользователь будет авторизован и перенаправлен на запрашиваемую страницу
            if user and check_password_hash(user.hash_password, password):
                login_user(user)
                next_page = request.args.get("next")
                return redirect(next_page)
            else:
                flash("Неверный логин или пароль.")

    return render_template("login.html")


# Обработчик выхода
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


# Каталог
@app.route("/catalog")
def catalog():
    return render_template("catalog.html")


# Страница модерации объявлений
@app.route("/moderation")
@login_required
def moderation():
    return render_template("moderation.html")


# Страница просмотра жалоб пользователей
@app.route("/complaint")
@login_required
def complaint():
    return render_template("complaint.html")


# Страница объявлений пользователя
@app.route("/my_rent_out")
@login_required
def my_rent_out():
    return render_template("my_rent_out.html")


# Страница избранных предметов
@app.route("/bag")
@login_required
def bag():
    return render_template("bag.html")


# Страница создания нового объявления
@app.route("/add_rent_out", methods=("POST", "GET"))
@login_required
def add_rent_out():
    if request.method == 'POST':
        try:
            name = request.form['name']
            category = request.form['category']
            description = request.form['description']
            rent_price = request.form['rent_price']
            file = request.files['file']
            file.filename = str(uuid4()) + '.png'
            save_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(save_path)

            # Создание предмета с полученными данными и запись в бд
            item = Item(name=name, category=category, description=description, rent_price=rent_price,
                        image_url=save_path)
            db.session.add(item)
            db.session.commit()

            # Получение id только что добавленного предмета
            new_item = db.session.query(Item).order_by(Item.id_item.desc()).first()
            # Создание объявления и добавление в бд
            rent_out = RentOut(status="активно", id_item=new_item.id_item, id_user=current_user.id)
            db.session.add(rent_out)
            db.session.commit()
            flash("Объявление успешно добавлено.", category="success")
        except:
            db.session.rollback()
            flash("Возникла ошибка. Не удалось добавить объявление. Попробуйте ещё раз.")

    return render_template("add_rent_out.html")


# Страница создания новой заявки
@app.route("/add_rent_in/<int:id_rent_out>")
@login_required
def add_rent_in(id_rent_out):
    return render_template("add_rent_in.html", id_rent_out=id_rent_out)


# Страница создания новой жалобы
@app.route("/add_complaint/<int:id_rent_in>")
@login_required
def add_complaint(id_rent_in):
    return render_template("add_complaint.html", id_rent_in=id_rent_in)


# Страница входящих заявок
@app.route("/incoming")
@login_required
def incoming():
    return render_template("incoming.html")


# Страница исходящих заявок
@app.route("/outgoing")
@login_required
def outgoing():
    return render_template("outgoing.html")


# Страница с действующими арендами пользователя
@app.route("/irent")
@login_required
def irent():
    return render_template("irent.html")


# Страница с действующими сдачами в аренду пользователя
@app.route("/notirent")
@login_required
def notirent():
    return render_template("notirent.html")


# История моих аренд
@app.route("/irent_histori")
@login_required
def irent_histori():
    return render_template("irent_histori.html")


# История сдачи в аренду
@app.route("/notirent_histori")
@login_required
def notirent_histori():
    return render_template("notirent_histori.html")


# Страница жалоб пользователя
@app.route("/my_complaint")
@login_required
def my_complaint():
    return render_template("my_complaint.html")


# Перенаправление для гостя
@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect("/login" + "?next=" + request.url)
    return response


# Обработчики событий socket.io
# Обновление данных каталога
@socketio.on('reload_catalog')
def handle_reload_catalog():
    # Получение данных об объявлении
    catalog = db.session.query(RentOut, Item).join(Item, RentOut.id_item == Item.id_item) \
        .filter(RentOut.status == "активно") \
        .order_by(RentOut.id_rent_out.desc()).all()
    catalog_list = [{'id_rent_out': a.RentOut.id_rent_out,
                     'id_item': a.RentOut.id_item,
                     'name': a.Item.name,
                     'category': a.Item.category,
                     'description': a.Item.description,
                     'rent_price': a.Item.rent_price,
                     'image_url': a.Item.image_url
                     } for a in catalog]
    # Упаковка данных в json
    catalog_json = json.dumps(catalog_list)
    # Отправка события 'catalog' с данными на клиент
    socketio.emit('catalog', catalog_json)


# Добавление жалобы
@socketio.on('add_complaint')
def add_complaint(data):
    # Распаковка json
    data_json = json.loads(data)
    id_rent_in = data_json['id_rent_in']
    description = data_json['description']
    status = "рассматривается"
    id_user = current_user.id

    # Создание экземпляра класса и запись в БД
    complaint = Complaint(id_rent_in=id_rent_in, description=description, status=status, id_user=id_user)
    db.session.add(complaint)
    db.session.commit()

    # Отправка события 'connect' с сервера на клиент
    socketio.emit('connect')


# Обновление страницы с жалобами
@socketio.on('reload_complaint')
def handle_reload_complaint():
    # Получение данных о всех жалобах из БД
    complaint = db.session.query(Complaint, RentIn, RentOut, Item, User) \
        .join(RentIn, Complaint.id_rent_in == RentIn.id_rent_in) \
        .join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, Complaint.id_user == User.id) \
        .order_by(RentIn.id_rent_in.desc()).all()
    complaint_list = [{'id_rent_in': a.RentIn.id_rent_in,
                       'id_rent_out': a.RentOut.id_rent_out,
                       'id_item': a.RentOut.id_item,
                       'id_complaint': a.Complaint.id_complaint,
                       'username': a.User.username,
                       'phone': a.User.phone,
                       'email': a.User.email,
                       'name': a.Item.name,
                       'category': a.Item.category,
                       'description': a.Item.description,
                       'rent_price': a.Item.rent_price,
                       'image_url': a.Item.image_url,
                       'date_rent_start': a.RentIn.date_rent_start,
                       'date_rent_finish': a.RentIn.date_rent_finish,
                       'note': a.RentIn.note,
                       'status': a.RentIn.status,
                       'status_complaint': a.Complaint.status,
                       'description_complaint': a.Complaint.description
                       } for a in complaint]
    # Упаковка в json и отправка на нужный адрес
    complaint_json = json.dumps(complaint_list, default=str)
    socketio.emit('complaint', complaint_json)


# Обновление страницы с жалобами пользователя
@socketio.on('reload_my_complaint')
def handle_reload_my_complaint():
    # Получение всех жалоб текущего пользователя из БД
    complaint = db.session.query(Complaint, RentIn, RentOut, Item, User) \
        .join(RentIn, Complaint.id_rent_in == RentIn.id_rent_in) \
        .join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, Complaint.id_user == User.id) \
        .filter(Complaint.id_user == current_user.id)\
        .order_by(RentIn.id_rent_in.desc()).all()
    complaint_list = [{'id_rent_in': a.RentIn.id_rent_in,
                       'id_rent_out': a.RentOut.id_rent_out,
                       'id_item': a.RentOut.id_item,
                       'id_complaint': a.Complaint.id_complaint,
                       'category': a.Item.category,
                       'description': a.Item.description,
                       'rent_price': a.Item.rent_price,
                       'image_url': a.Item.image_url,
                       'date_rent_start': a.RentIn.date_rent_start,
                       'date_rent_finish': a.RentIn.date_rent_finish,
                       'note': a.RentIn.note,
                       'status': a.RentIn.status,
                       'status_complaint': a.Complaint.status,
                       'description_complaint': a.Complaint.description
                       } for a in complaint]
    # Упаковка и отправка по адресу
    complaint_json = json.dumps(complaint_list, default=str)
    socketio.emit('my_complaint', complaint_json)


# Обновление статуса жалобы
@socketio.on('resolved')
def handle_resolved(id_complaint):
    complaint = Complaint.query.get(id_complaint)
    if complaint.status == "рассматривается":
        complaint.status = "жалоба закрыта"
        db.session.commit()
        socketio.emit('connect')


# Удаление объявление
@socketio.on('del_rent_out')
def handle_del_rent_out(id_rent_out):
    rent_out = RentOut.query.get(id_rent_out)
    bags = Bag.query.filter(Bag.id_rent_out == id_rent_out).all()
    for b in bags:
        db.session.delete(b)
    db.session.commit()
    rent_out.status = "удалено"
    db.session.commit()
    socketio.emit('connect')


# Обновление страницы с объявлениями текущего пользователя
@socketio.on('reload_my_rent_out')
def handle_reload_my_rent_out():
    # Получение всех действующих объявлений текущего пользователя из БД
    catalog = db.session.query(RentOut, Item).join(Item, RentOut.id_item == Item.id_item) \
        .filter(RentOut.id_user == current_user.id, RentOut.status != "удалено") \
        .order_by(RentOut.id_rent_out.desc()).all()
    catalog_list = [{'id_rent_out': a.RentOut.id_rent_out,
                     'id_item': a.RentOut.id_item,
                     'name': a.Item.name,
                     'category': a.Item.category,
                     'description': a.Item.description,
                     'rent_price': a.Item.rent_price,
                     'image_url': a.Item.image_url
                     } for a in catalog]
    # Упаковка и отправка по указанному адресу
    catalog_json = json.dumps(catalog_list)
    socketio.emit('my_rent_out', catalog_json)


# Функция добавления объявления в избранные объявления
@socketio.on('add_bag')
def handle_add_bag(id_rent_out):
    id_user = current_user.id
    id_rent_out = id_rent_out
    bag = Bag(id_user=id_user, id_rent_out=id_rent_out)
    db.session.add(bag)
    db.session.commit()
    socketio.emit('connect')


# Функция удаления объявления из избранных объявлений
@socketio.on('del_bag')
def handle_del_bag(id_bag):
    bag = Bag.query.get(id_bag)
    db.session.delete(bag)
    db.session.commit()
    socketio.emit('connect')


# Обновление страницы с избранными объявлениями
@socketio.on('reload_bag')
def handle_reload_bag():
    # Получение из БД всех активных объявлений из избранных
    bag = db.session.query(Bag, RentOut, Item).join(RentOut, Bag.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .filter(Bag.id_user == current_user.id, RentOut.status == "активно") \
        .order_by(Bag.id_bag.desc()).all()
    bags = [{'id_bag': a.Bag.id_bag,
             'id_rent_out': a.RentOut.id_rent_out,
             'id_item': a.RentOut.id_item,
             'name': a.Item.name,
             'category': a.Item.category,
             'description': a.Item.description,
             'rent_price': a.Item.rent_price,
             'image_url': a.Item.image_url
             } for a in bag]
    # Упаковка и отправка на указанный адрес
    bags_json = json.dumps(bags)
    socketio.emit('bag', bags_json)


# Создание заявки на аренду
@socketio.on('add_rent_in')
def handle_add_rent_in(data):
    #  Распаковка данных с клиента
    data_json = json.loads(data)
    status = 'подана'
    date_rent_start = data_json['date_rent_start']
    date_rent_finish = data_json['date_rent_finish']
    note = data_json['note']
    id_rent_out = data_json['id_rent_out']
    id_user = current_user.id
    # Создание экземпляра класса и запись в БД
    rent_in = RentIn(status=status, date_rent_start=date_rent_start, date_rent_finish=date_rent_finish, note=note,
                     id_rent_out=id_rent_out, id_user=id_user)
    db.session.add(rent_in)
    db.session.commit()

    socketio.emit('connect')


# Функция удаления заявки
@socketio.on('del_rent_in')
def handle_del_rent_in(id_rent_in):
    rent_in = RentIn.query.get(id_rent_in)
    db.session.delete(rent_in)
    db.session.commit()
    socketio.emit('connect')


# Функция одобрения заявки
@socketio.on('approve')
def handle_approve(id_rent_in, id_rent_out):
    rent_in = RentIn.query.get(id_rent_in)
    rent_out = RentOut.query.get(id_rent_out)
    rent_out.status = "неактивно"
    rent_in.status = "одобрена"
    db.session.commit()
    socketio.emit('connect')


# Функция изменения статуса аренды при начале аренды
@socketio.on('rent_start')
def handle_rent_start(id_rent_in):
    rent_in = RentIn.query.get(id_rent_in)
    if rent_in.status == "одобрена":
        rent_in.status = "в аренде"
        db.session.commit()
        socketio.emit('connect')


# Функция изменения статуса аренды при конце аренды
@socketio.on('rent_finish')
def handle_rent_finish(id_rent_in, id_rent_out):
    rent_in = RentIn.query.get(id_rent_in)
    if rent_in.status == "в аренде":
        rent_out = RentOut.query.get(id_rent_out)
        rent_out.status = "активно"
        rent_in.status = "аренда завершена"
        db.session.commit()
        socketio.emit('connect')


# Обновление данных на странице исходящих заявок текущего пользователя
@socketio.on('reload_outgoing')
def handle_reload_outgoing():
    # Получение всех действующих исходящих заявок пользователя из БД
    outgoing = db.session.query(RentIn, RentOut, Item).join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .filter(RentIn.id_user == current_user.id, RentIn.status == "подана") \
        .order_by(RentIn.id_rent_in.desc()).all()
    outgoings = [{'id_rent_in': a.RentIn.id_rent_in,
                  'id_rent_out': a.RentOut.id_rent_out,
                  'id_item': a.RentOut.id_item,
                  'name': a.Item.name,
                  'category': a.Item.category,
                  'description': a.Item.description,
                  'rent_price': a.Item.rent_price,
                  'image_url': a.Item.image_url,
                  'date_rent_start': a.RentIn.date_rent_start,
                  'date_rent_finish': a.RentIn.date_rent_finish,
                  'note': a.RentIn.note,
                  'status': a.RentIn.status
                  } for a in outgoing]
    # Упаковка и отправка на указанный адрес
    outgoings_json = json.dumps(outgoings)
    socketio.emit('outgoing', outgoings_json)


# Обновление данных на странице входящих заявок текущего пользователя
@socketio.on('reload_incoming')
def handle_reload_incoming():
    # Получение всех действующих входящих заявок пользователя из БД
    incoming = db.session.query(RentIn, RentOut, Item, User).join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, RentIn.id_user == User.id) \
        .filter(RentOut.id_user == current_user.id, RentIn.status == "подана") \
        .order_by(RentIn.id_rent_in.desc()).all()
    incomings = [{'id_rent_in': a.RentIn.id_rent_in,
                  'id_rent_out': a.RentOut.id_rent_out,
                  'id_item': a.RentOut.id_item,
                  'username': a.User.username,
                  'phone': a.User.phone,
                  'email': a.User.email,
                  'name': a.Item.name,
                  'category': a.Item.category,
                  'description': a.Item.description,
                  'rent_price': a.Item.rent_price,
                  'image_url': a.Item.image_url,
                  'date_rent_start': a.RentIn.date_rent_start,
                  'date_rent_finish': a.RentIn.date_rent_finish,
                  'note': a.RentIn.note,
                  'status': a.RentIn.status
                  } for a in incoming]
    # Упаковка и отправка на указанный адрес
    incomings_json = json.dumps(incomings)
    socketio.emit('incoming', incomings_json)


# Обновление данных страницы сданных предметов текущего пользователя
@socketio.on('reload_notirent')
def handle_reload_notirent():
    # Получение из БД записей текущих сдач в аренду пользователя
    notirent = db.session.query(RentIn, RentOut, Item, User).join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, RentIn.id_user == User.id) \
        .filter(RentOut.id_user == current_user.id, or_(RentIn.status == "одобрена", RentIn.status == "в аренде")) \
        .order_by(RentIn.id_rent_in.desc()).all()
    notirents = [{'id_rent_in': a.RentIn.id_rent_in,
                  'id_rent_out': a.RentOut.id_rent_out,
                  'id_item': a.RentOut.id_item,
                  'username': a.User.username,
                  'phone': a.User.phone,
                  'email': a.User.email,
                  'name': a.Item.name,
                  'category': a.Item.category,
                  'description': a.Item.description,
                  'rent_price': a.Item.rent_price,
                  'image_url': a.Item.image_url,
                  'date_rent_start': a.RentIn.date_rent_start,
                  'date_rent_finish': a.RentIn.date_rent_finish,
                  'note': a.RentIn.note,
                  'status': a.RentIn.status
                  } for a in notirent]
    # Упаковка и отправка на указанный адрес
    notirents_json = json.dumps(notirents)
    socketio.emit('notirent', notirents_json)


# Обновление данных страницы взятых в аренду предметов текущим пользователем
@socketio.on('reload_irent')
def handle_reload_irent():
    irent = db.session.query(RentIn, RentOut, Item, User).join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, RentOut.id_user == User.id) \
        .filter(RentIn.id_user == current_user.id, or_(RentIn.status == "одобрена", RentIn.status == "в аренде")) \
        .order_by(RentIn.id_rent_in.desc()).all()
    irents = [{'id_rent_in': a.RentIn.id_rent_in,
               'id_rent_out': a.RentOut.id_rent_out,
               'id_item': a.RentOut.id_item,
               'username': a.User.username,
               'phone': a.User.phone,
               'email': a.User.email,
               'name': a.Item.name,
               'category': a.Item.category,
               'description': a.Item.description,
               'rent_price': a.Item.rent_price,
               'image_url': a.Item.image_url,
               'date_rent_start': a.RentIn.date_rent_start,
               'date_rent_finish': a.RentIn.date_rent_finish,
               'note': a.RentIn.note,
               'status': a.RentIn.status
               } for a in irent]
    # Упаковка и отправка на указанный адрес
    irents_json = json.dumps(irents)
    socketio.emit('irent', irents_json)


# Обновление страницы истории взятия в аренду предметов текущим пользователем
@socketio.on('reload_irent_history')
def handle_reload_irent_history():
    irent = db.session.query(RentIn, RentOut, Item, User).join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, RentOut.id_user == User.id) \
        .filter(RentIn.id_user == current_user.id, RentIn.status == "аренда завершена") \
        .order_by(RentIn.id_rent_in.desc()).all()
    irents = [{'id_rent_in': a.RentIn.id_rent_in,
               'id_rent_out': a.RentOut.id_rent_out,
               'id_item': a.RentOut.id_item,
               'username': a.User.username,
               'phone': a.User.phone,
               'email': a.User.email,
               'name': a.Item.name,
               'category': a.Item.category,
               'description': a.Item.description,
               'rent_price': a.Item.rent_price,
               'image_url': a.Item.image_url,
               'date_rent_start': a.RentIn.date_rent_start,
               'date_rent_finish': a.RentIn.date_rent_finish,
               'note': a.RentIn.note,
               'status': a.RentIn.status
               } for a in irent]
    # Упаковка и отправка на указанный адрес
    irents_json = json.dumps(irents)
    socketio.emit('irent_history', irents_json)


# Обновление страницы истории сдачи в аренду предметов текущим пользователем
@socketio.on('reload_notirent_history')
def handle_reload_notirent_history():
    notirent = db.session.query(RentIn, RentOut, Item, User).join(RentOut, RentIn.id_rent_out == RentOut.id_rent_out) \
        .join(Item, RentOut.id_item == Item.id_item) \
        .join(User, RentIn.id_user == User.id) \
        .filter(RentOut.id_user == current_user.id, RentIn.status == "аренда завершена") \
        .order_by(RentIn.id_rent_in.desc()).all()
    notirents = [{'id_rent_in': a.RentIn.id_rent_in,
                  'id_rent_out': a.RentOut.id_rent_out,
                  'id_item': a.RentOut.id_item,
                  'username': a.User.username,
                  'phone': a.User.phone,
                  'email': a.User.email,
                  'name': a.Item.name,
                  'category': a.Item.category,
                  'description': a.Item.description,
                  'rent_price': a.Item.rent_price,
                  'image_url': a.Item.image_url,
                  'date_rent_start': a.RentIn.date_rent_start,
                  'date_rent_finish': a.RentIn.date_rent_finish,
                  'note': a.RentIn.note,
                  'status': a.RentIn.status
                  } for a in notirent]
    # Упаковка и отправка на указанный адрес
    notirents_json = json.dumps(notirents)
    socketio.emit('notirent_history', notirents_json)


# Обработчик запуска сервера
if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True)
