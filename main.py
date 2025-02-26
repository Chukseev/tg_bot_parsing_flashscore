from telebot import TeleBot, types
from find_injure import matches_list, get_players_list, get_teams
from files_manager import into_csv_data, into_excel_data
from datetime import datetime, timedelta
import os
import environ
from database import SessionLocal
from crud import (get_user, create_user, get_user_role, is_admin,
                  get_all_users, update_user_status, get_status)


env = environ.Env()
environ.Env.read_env()
token = env('token', )
bot = TeleBot(token=token)


def get_leagues(match_list):
    res = []
    for league in match_list:
        league_dict = (league['league_id'], league['league'])
        if league_dict not in res:
            res.append(league_dict)
    return res


def get_matches_from_leagues(league_id, match_list):
    result = [match for match in match_list if match['league_id'] == league_id]
    return result

def get_next_seven_dates():
    today = datetime.today()
    dates = {}

    for i in range(1, 8):
        date = today + timedelta(days=i)
        dates[i] = date.strftime('%d/%m')

    return dates


def get_matches_in_page(matches, page):
    min_index = 10 * (page - 1)
    max_index = min_index + 10
    return matches[min_index:max_index]


@bot.message_handler(commands=['start'])
def start(message):
    db = SessionLocal()
    user_id = message.from_user.id
    username = message.from_user.username
    firstname = message.from_user.first_name
    lastname = message.from_user.last_name
    create_user(db=db, id=user_id, username=username, firstname=firstname, lastname=lastname)
    bot.send_message(message.chat.id, f"Привет, {firstname} \nВведи /commands - для просмотра команд")


@bot.message_handler(commands=['commands'])
def commands(message):
    db = SessionLocal()
    user_id = message.from_user.id
    if get_user_role(db, user_id) == 'admin':
        bot.send_message(message.chat.id, "1. /get_players (Статистика игроков)\n2. /info (Информация) "
                                          "\n3. /admin (Админ панель)")
    else:
        bot.send_message(message.chat.id, "1. /get_players (Статистика игроков)\n2. /info (Информация)")


@bot.message_handler(commands=['info'])
def info(message):
    bot.send_message(message.chat.id, "Администратор - @mmkkll1245\nРазработка бота - @Chukseev")


@bot.message_handler(commands=['admin'])
def admin(message):
    user_id = message.from_user.id
    db = SessionLocal()
    if not is_admin(db, user_id):  # Проверяем, админ ли
        bot.send_message(message.chat.id, "⛔ У вас нет прав администратора!")
        return
    inline_keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text=f"Просмотр пользователей", callback_data="view_users")
    inline_keyboard.add(button)
    bot.send_message(
        message.chat.id,
        "Доступные команды для администратора:",
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "view_users")
def view_users(call):
    user_id = call.from_user.id
    db = SessionLocal()
    users = get_all_users(db)
    inline_keyboard = types.InlineKeyboardMarkup()
    for user in users:
        button = types.InlineKeyboardButton(text=f"{user.username}", callback_data=f"user_{user.id}")
        inline_keyboard.add(button)
    button = types.InlineKeyboardButton(text="⬅ Назад к панели управления", callback_data="return_admin")
    inline_keyboard.add(button)
    if call.message:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите пользователя,\nчтобы изменить права:",
            reply_markup=inline_keyboard
        )
    else:
        bot.send_message(
            chat_id=call.chat.id,
            text="Выберите пользователя,\nчтобы изменить права:",
            reply_markup=inline_keyboard
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("user_"))
def crud_operation(call):
    db = SessionLocal()
    target_user_id = int(call.data.split('_')[1])

    user = get_user(db, target_user_id)
    inline_keyboard = types.InlineKeyboardMarkup()
    status = get_status(db, target_user_id)

    # Проверяем текущий статус и создаем кнопку
    if get_status(db, target_user_id):
        button = types.InlineKeyboardButton(text="Отнять права", callback_data=f"toggle_{target_user_id}")
    else:
        button = types.InlineKeyboardButton(text="Дать права", callback_data=f"toggle_{target_user_id}")

    inline_keyboard.add(button)
    button = types.InlineKeyboardButton(text="⬅ Назад к списку пользователей", callback_data="view_users")
    inline_keyboard.add(button)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Пользователь {user.username} {'имеет доступ' if status else 'не имеет доступа'}\n"
             f"Дата регисрации: {user.created_at.strftime('%d.%m.%Y')}\nДата изменения: {user.updated_at.strftime('%d.%m.%Y')}",
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_access(call):
    db = SessionLocal()
    target_user_id = int(call.data.split('_')[1])

    # Меняем права пользователя
    updated_user = update_user_status(db, target_user_id)

    # Обновляем текст кнопки
    inline_keyboard = types.InlineKeyboardMarkup()
    new_status = "Отнять права" if updated_user.has_access else "Дать права"
    button = types.InlineKeyboardButton(text=new_status, callback_data=f"toggle_{target_user_id}")
    inline_keyboard.add(button)

    button = types.InlineKeyboardButton(text="⬅ Назад к списку пользователей", callback_data="view_users")
    inline_keyboard.add(button)
    # Отправляем обновленный текст
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Пользователь {updated_user.username} {'имеет доступ' if updated_user.has_access else 'не имеет доступа'}\n"
             f"Дата регисрации: {updated_user.created_at.strftime('%d.%m.%Y')}\nДата изменения: {updated_user.updated_at.strftime('%d.%m.%Y')}",
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "return_admin")
def return_admin(call):
    inline_keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text=f"Просмотр пользователей", callback_data="view_users")
    inline_keyboard.add(button)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Доступные команды для администратора:",
        reply_markup=inline_keyboard
    )


@bot.message_handler(commands=['get_players'])
def get_players(message):
    user_id = message.from_user.id
    db = SessionLocal()

    if not get_status(db, user_id):
        bot.send_message(message.chat.id, "⛔ У вас нет прав для этого!\nОбратитесь к @mmkkll1245 для получения прав.")
        return

    days = get_next_seven_dates()
    inline_keyboard = types.InlineKeyboardMarkup()
    button_today = types.InlineKeyboardButton(text="Матчи на сегодня", callback_data="today_leagues")
    inline_keyboard.add(button_today)
    for day in days:
        button = types.InlineKeyboardButton(text=f"Матчи на {days[day]}", callback_data=f"{day}_leagues")
        inline_keyboard.add(button)
    bot.send_message(
        message.chat.id,
        "Выберите день,\nчтобы увидеть список матчей:",
        reply_markup=inline_keyboard
    )


# Обработчик кнопки "Список матчей на сегодня"
@bot.callback_query_handler(func=lambda call: "today_leagues" in call.data)
def handle_today_matches(call):
    data = call.data.split('_')
    page = int(data[2]) if len(data) > 2 else 1
    matches = matches_list('f_4_0_3_ru_5')  # Получаем список матчей на сегодня
    leagues = get_leagues(matches)
    handle_matches(call, leagues, "today", page)


# Обработчик кнопки "Список матчей на завтра"
@bot.callback_query_handler(func=lambda call: "_leagues" in call.data) #func=lambda call: "_page_" in call.data
def handle_tomorrow_matches(call):
    data = call.data.split('_')
    day = int(data[0])
    page = int(data[2]) if len(data) > 2 else 1
    matches = matches_list(f'f_4_{day}_3_ru_5')  # Получаем список матчей на завтра
    leagues = get_leagues(matches)
    handle_matches(call, leagues, f"{day}", page)


# Общий обработчик матчей
def handle_matches(call, leagues, day_type, page=1):
    days = get_next_seven_dates()
    if day_type != 'today':
        day = int(day_type)
    total_pages = (len(leagues) + 9) // 10  # Общее количество страниц
    inline_keyboard = types.InlineKeyboardMarkup()

    # Кнопки матчей
    for i, league in enumerate(get_matches_in_page(leagues, page)):
        button = types.InlineKeyboardButton(
            text=f"{league[1]}",
            callback_data=f"league_{league[0]}_{day_type}_{page}"  # Уникальный callback_data
        )
        inline_keyboard.add(button)

    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data=f"{day_type}_page_{page - 1}"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("➡ Вперед", callback_data=f"{day_type}_page_{page + 1}"))
    if nav_buttons:
        inline_keyboard.add(*nav_buttons)

    # Кнопка "Назад к выбору дат"
    back_to_dates_button = types.InlineKeyboardButton(
        text="⬅ Назад к выбору дат", callback_data="choose_dates"
    )
    inline_keyboard.add(back_to_dates_button)

    # Отправляем или редактируем сообщение
    if call.message:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Список лиг ({'Сегодня' if day_type == 'today' else days[day]}), стр. {page}/{total_pages}:",
            reply_markup=inline_keyboard
        )
    else:
        bot.send_message(
            chat_id=call.chat.id,
            text=f"Список лиг ({'Сегодня' if day_type == 'today' else days[day]}), стр. {page}/{total_pages}:",
            reply_markup=inline_keyboard
        )


@bot.callback_query_handler(func=lambda call: "_page_" in call.data)
def handle_page_callback(call):
    data = call.data.split("_")
    day_type = data[0]  # today или tomorrow
    page = int(data[2])  # Номер страницы

    # Определяем список матчей для выбранного дня
    leagues = get_leagues(matches_list('f_4_0_3_ru_5')) if day_type == "today" else get_leagues(matches_list(f'f_4_{day_type}_3_ru_5'))

    # Перезагружаем список матчей с учетом новой страницы
    handle_matches(call, leagues, day_type, page)


# Обработчик для матчей
@bot.callback_query_handler(func=lambda call: call.data.startswith("league_"))
def handle_match_callback(call):
    data = call.data.split("_")
    league_id = data[1]
    day_type = data[2]
    page = data[3]
    inline_keyboard = types.InlineKeyboardMarkup()
    if day_type == "today":
        matches = get_matches_from_leagues(league_id, matches_list('f_4_0_3_ru_5'))
    else:
        matches = get_matches_from_leagues(league_id, matches_list(f'f_4_{day_type}_3_ru_5'))

    for i, match in enumerate(matches):
        button = types.InlineKeyboardButton(
            text=f"{match['team_1']} - {match['team_2']}",
            callback_data=f"match_{day_type}_{league_id}_{i}_{page}"  # Уникальный callback_data
        )
        inline_keyboard.add(button)
    back_button = types.InlineKeyboardButton(text='⬅ Назад к лигам', callback_data=f'{day_type}_leagues_{page}')
    inline_keyboard.add(back_button)
    # Редактируем сообщение, показывая кнопки команд
    bot.edit_message_text(
        f"Лига :{match['league']}\nВыберите команду:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("match_"))
def handle_match_callback(call):
    data = call.data.split("_")
    day_type = data[1]  # today или tomorrow
    league_id = data[2]
    match_index = int(data[3])  # Индекс матча
    page = data[4]
    if day_type == "today":
        matches = get_matches_from_leagues(league_id, matches_list('f_4_0_3_ru_5'))
    else:
        matches = get_matches_from_leagues(league_id, matches_list(f'f_4_{day_type}_3_ru_5'))

    match = matches[match_index]
    # Создаем клавиатуру с выбором команд
    inline_keyboard = types.InlineKeyboardMarkup()
    button_home = types.InlineKeyboardButton(
        text=f"{match['team_1']}",
        callback_data=f"team_home_{day_type}_{league_id}_{match_index}_{page}"
    )
    button_away = types.InlineKeyboardButton(
        text=f"{match['team_2']}",
        callback_data=f"team_away_{day_type}_{league_id}_{match_index}_{page}"
    )
    button_two_teams = types.InlineKeyboardButton(
        text=f"Обе команды",
        callback_data=f"teams_{day_type}_{league_id}_{match_index}_{page}"
    )
    back_button = types.InlineKeyboardButton(
        text="⬅ Назад к списку матчей", callback_data=f"league_{league_id}_{day_type}_{page}" # f"league_{league[0]}_{day_type}_{(page - 1) * 10 + i}"
    )
    inline_keyboard.add(button_home, button_away)
    inline_keyboard.add(button_two_teams)
    inline_keyboard.add(back_button)

    # Редактируем сообщение, показывая кнопки команд
    bot.edit_message_text(
        f"Вы выбрали матч:\n{match['team_1']} - {match['team_2']}\nВыберите команду:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("teams_"))
def handle_team_callback(call):
    data = call.data.split("_")
    day_type = data[1]  # today или tomorrow
    league_id = data[2]
    match_index = int(data[3])  # Индекс матча
    page = int(data[4])
    if day_type == "today":
        matches = get_matches_from_leagues(league_id, matches_list('f_4_0_3_ru_5'))
    else:
        matches = get_matches_from_leagues(league_id, matches_list(f'f_4_{day_type}_3_ru_5'))
    # Список матчей
    match = matches[match_index]
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    # Отправляем сообщение о загрузке
    loading_message = bot.send_message(chat_id=call.message.chat.id, text='Подождите пожалуйста 🔄')

    # Получаем URL команды
    teams = get_teams(match['url'])
    away_url = teams['away']
    home_url = teams['home']
    team_name = f'{away_url.split('/')[-2]}_{home_url.split('/')[-2]}'
    result = [{'name': away_url.split('/')[-2]}]
    result += get_players_list(away_url)
    result += [{'name': ' '}, {'name': home_url.split('/')[-2]}]
    result += get_players_list(home_url)
    bot.delete_message(
        chat_id=call.message.chat.id,
        message_id=loading_message.message_id,
    )
    file_name = f'{team_name}_for_{call.message.chat.username}'
    csv_file = f'{file_name}.csv'
    excel_file = f'{file_name}.xlsx'
    into_csv_data(result, csv_file)
    into_excel_data(result, excel_file)

    try:
        with open(excel_file, 'rb') as file:  # Открываем файл в бинарном режиме
            bot.send_document(call.message.chat.id, file)

    except FileNotFoundError:
        bot.send_message(call.message.chat.id, f"Файл {excel_file} не найден. Проверьте его наличие.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Произошла ошибка: {e}")

    try:
        with open(csv_file, 'rb') as file:  # Открываем файл в бинарном режиме
            bot.send_document(call.message.chat.id, file)

    except FileNotFoundError:
        bot.send_message(call.message.chat.id, f"Файл {csv_file} не найден. Проверьте его наличие.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Произошла ошибка: {e}")

    if os.path.exists(csv_file):
        os.remove(csv_file)

    if os.path.exists(excel_file):
        os.remove(excel_file)

    back_button = types.InlineKeyboardButton(
        text="⬅ Вернуться назад", callback_data=f"match_{day_type}_{league_id}_{match_index}_{page}"
    )

    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(back_button)

    bot.send_message(
        call.message.chat.id,
        "Файлы отправлены!",
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("team_"))
def handle_team_callback(call):
    data = call.data.split("_")
    team_type = data[1]  # Тип команды (home/away)

    day_type = data[2]  # today или tomorrow
    league_id = data[3]
    match_index = int(data[4])  # Индекс матча
    page = int(data[5])
    if day_type == "today":
        matches = get_matches_from_leagues(league_id, matches_list('f_4_0_3_ru_5'))
    else:
        matches = get_matches_from_leagues(league_id, matches_list(f'f_4_{day_type}_3_ru_5'))
    # Список матчей
    match = matches[match_index]

    # Удаляем старое сообщение
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    # Отправляем сообщение о загрузке
    loading_message = bot.send_message(chat_id=call.message.chat.id, text='Подождите пожалуйста 🔄')

    # Получаем URL команды
    teams = get_teams(match['url'])
    team_url = teams[team_type]
    team_name = team_url.split('/')[-2]

    # Получаем список игроков команды
    players = get_players_list(team_url)
    # Редактируем сообщение с информацией о игроках
    bot.delete_message(
        chat_id=call.message.chat.id,
        message_id=loading_message.message_id,
    )
    file_name = f'{team_name}_for_{call.message.chat.username}'
    csv_file = f'{file_name}.csv'
    excel_file = f'{file_name}.xlsx'
    into_csv_data(players, csv_file)
    into_excel_data(players, excel_file)

    try:
        with open(excel_file, 'rb') as file:  # Открываем файл в бинарном режиме
            bot.send_document(call.message.chat.id, file)

    except FileNotFoundError:
        bot.send_message(call.message.chat.id, f"Файл {excel_file} не найден. Проверьте его наличие.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Произошла ошибка: {e}")

    try:
        with open(csv_file, 'rb') as file:  # Открываем файл в бинарном режиме
            bot.send_document(call.message.chat.id, file)

    except FileNotFoundError:
        bot.send_message(call.message.chat.id, f"Файл {csv_file} не найден. Проверьте его наличие.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Произошла ошибка: {e}")

    if os.path.exists(csv_file):
        os.remove(csv_file)

    if os.path.exists(excel_file):
        os.remove(excel_file)

    back_button = types.InlineKeyboardButton(
        text="⬅ Вернуться назад", callback_data=f"match_{day_type}_{league_id}_{match_index}_{page}"
    )

    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(back_button)

    bot.send_message(
        call.message.chat.id,
        "Файлы отправлены!",
        reply_markup=inline_keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "choose_dates")
def handle_choose_dates(call):
    days = get_next_seven_dates()
    # Создаем клавиатуру для выбора дат
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(
        types.InlineKeyboardButton("Матчи на сегодня", callback_data="today_page_1"),
    )
    for day in days:
        button = types.InlineKeyboardButton(text=f"Матчи на {days[day]}", callback_data=f"{day}_page_1")
        inline_keyboard.add(button)

    # Отправляем сообщение с выбором дат
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите даты для просмотра матчей:",
        reply_markup=inline_keyboard
    )


# Запуск бота
# while True:
#     try:
#         bot.polling(allowed_updates=["message", "callback_query"], timeout=100, long_polling_timeout=100)
#     except Exception as e:
#         print(f"Ошибка: {e}. Перезапуск через 5 секунд...")
#         time.sleep(5)

bot.polling(allowed_updates=["message", "callback_query"], timeout=100, long_polling_timeout=100)