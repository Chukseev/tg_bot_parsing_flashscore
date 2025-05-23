from telebot import TeleBot, types
from find_injure import matches_list, get_players_list, get_teams
from files_manager import into_csv_data, into_excel_data
from datetime import datetime, timedelta
import time
import os
import environ

env = environ.Env()
environ.Env.read_env()
token = env('token', )
bot = TeleBot(token=token)


def get_leagues(match_list):
    res = []
    for league in match_list:
        league['league_id'] = league['league']
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
    days = get_next_seven_dates()
    inline_keyboard = types.InlineKeyboardMarkup()
    button_today = types.InlineKeyboardButton(text="Матчи на сегодня", callback_data="today_matches")
    inline_keyboard.add(button_today)
    for day in days:
        button = types.InlineKeyboardButton(text=f"Матчи на {days[day]}", callback_data=f"{day}_matches")
        inline_keyboard.add(button)
    bot.send_message(
        message.chat.id,
        "Выберите день,\nчтобы увидеть список матчей:",
        reply_markup=inline_keyboard
    )


# Обработчик кнопки "Список матчей на сегодня"
@bot.callback_query_handler(func=lambda call: call.data == "today_matches")
def handle_today_matches(call, page=1):

    matches = matches_list('f_4_0_3_ru_5')  # Получаем список матчей на сегодня
    handle_matches(call, matches, "today", page)


# Обработчик кнопки "Список матчей на завтра"
@bot.callback_query_handler(func=lambda call: "_matches" in call.data) #func=lambda call: "_page_" in call.data
def handle_tomorrow_matches(call, page=1):
    day = int(call.data.split('_')[0])
    matches = matches_list(f'f_4_{day}_3_ru_5')  # Получаем список матчей на завтра
    handle_matches(call, matches, f"{day}", page)


# Общий обработчик матчей
def handle_matches(call, matches, day_type, page=1):
    days = get_next_seven_dates()
    day = int(day_type)
    total_pages = (len(matches) + 9) // 10  # Общее количество страниц
    inline_keyboard = types.InlineKeyboardMarkup()

    # Кнопки матчей
    for i, match in enumerate(get_matches_in_page(matches, page)):
        button = types.InlineKeyboardButton(
            text=f"{match['team_1']} - {match['team_2']}",
            callback_data=f"match_{day_type}_{(page - 1) * 10 + i}"  # Уникальный callback_data
        )
        inline_keyboard.add(button)

    # Кнопки навигации
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
            text=f"Список матчей ({'Сегодня' if day_type == 'today' else days[day]}), стр. {page}/{total_pages}:",
            reply_markup=inline_keyboard
        )
    else:
        bot.send_message(
            chat_id=call.chat.id,
            text=f"Список матчей ({'Сегодня' if day_type == 'today' else days[day]}), стр. {page}/{total_pages}:",
            reply_markup=inline_keyboard
        )


@bot.callback_query_handler(func=lambda call: "_page_" in call.data)
def handle_page_callback(call):
    data = call.data.split("_")
    day_type = data[0]  # today или tomorrow
    page = int(data[2])  # Номер страницы

    # Определяем список матчей для выбранного дня
    matches = matches_list('f_4_0_3_ru_5') if day_type == "today" else matches_list(f'f_4_{day_type}_3_ru_5')

    # Перезагружаем список матчей с учетом новой страницы
    handle_matches(call, matches, day_type, page)


# Обработчик для матчей
@bot.callback_query_handler(func=lambda call: call.data.startswith("match_"))
def handle_match_callback(call):
    data = call.data.split("_")
    day_type = data[1]  # today или tomorrow
    match_index = int(data[2])  # Индекс матча
    matches = matches_list('f_4_0_3_ru_5') if day_type == "today" else matches_list(f'f_4_{day_type}_3_ru_5')  # Список матчей
    match = matches[match_index]

    # Получаем ссылки команд из функции get_teams
    teams = get_teams(match['url'])

    # Создаем клавиатуру с выбором команд
    inline_keyboard = types.InlineKeyboardMarkup()
    button_home = types.InlineKeyboardButton(
        text=f"{match['team_1']}",
        callback_data=f"team_home_{day_type}_{match_index}"
    )
    button_away = types.InlineKeyboardButton(
        text=f"{match['team_2']}",
        callback_data=f"team_away_{day_type}_{match_index}"
    )
    back_button = types.InlineKeyboardButton(
        text="⬅ Назад к списку матчей", callback_data=f"{day_type}_page_{(match_index // 10) + 1}"
    )
    inline_keyboard.add(button_home, button_away)
    inline_keyboard.add(back_button)

    # Редактируем сообщение, показывая кнопки команд
    bot.edit_message_text(
        f"Вы выбрали матч:\n{match['team_1']} - {match['team_2']}\nВыберите команду:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=inline_keyboard
    )


# Обработчик для выбора команды
@bot.callback_query_handler(func=lambda call: call.data.startswith("team_"))
def handle_team_callback(call):
    data = call.data.split("_")
    team_type = data[1]  # Тип команды (home/away)
    day_type = data[2]  # today или tomorrow
    match_index = int(data[3])  # Индекс матча
    matches = matches_list('f_4_0_3_ru_5') if day_type == "today" else matches_list(f'f_4_{day_type}_3_ru_5')  # Список матчей
    match = matches[match_index]

    # Удаляем старое сообщение
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    # Отправляем сообщение о загрузке
    loading_message = bot.send_message(chat_id=call.message.chat.id, text='Подождите пожалуйста 🔄')

    # Получаем URL команды
    teams = get_teams(match['url'])
    team_url = teams[team_type]

    # Получаем список игроков команды
    players = get_players_list(team_url)

    # Редактируем сообщение с информацией о игроках
    bot.delete_message(
        chat_id=call.message.chat.id,
        message_id=loading_message.message_id,
    )
    file_name = f'output_for_{call.message.chat.username}'
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
while True:
    try:
        bot.polling(allowed_updates=["message", "callback_query"], timeout=100, long_polling_timeout=100)
    except Exception as e:
        print(f"Ошибка: {e}. Перезапуск через 5 секунд...")
        time.sleep(5)