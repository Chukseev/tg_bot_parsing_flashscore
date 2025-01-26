import json
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime


def is_in_season(season: str) -> bool:
    start_year, end_year = map(int, season.split('/'))
    season_start = datetime(start_year, 7, 1)
    season_end = datetime(end_year, 6, 30)
    return season_start <= datetime.now() <= season_end


def matches_list(feed) -> list: # feed = 'f_4_0_3_ru_5'
    url = f'https://d.flashscore.ru.com/x/feed/{feed}'
    response = requests.get(url=url, headers={"x-fsign": "SW9D1eZo"})
    data = response.text.split('¬')

    data_list = [{}]
    result = []
    for item in data:
        key = item.split('÷')[0]
        value = item.split('÷')[-1]

        if '~' in key:
            data_list.append({key: value})
        else:
            data_list[-1].update({key: value})
    league = ''
    for game in data_list:
        if '~ZA' in list(game.keys())[0]:
            league = game.get('~ZA')
        if 'AA' in list(game.keys())[0]:
            event_id = game.get("~AA")
            url = f'https://www.flashscore.com.ua/match/{event_id}/#/match-summary/match-summary'
            team_1 = game.get("AE")
            team_2 = game.get("AF")
            # score = f'{game.get("AG")} : {game.get("AH")}'
            # date = datetime.fromtimestamp(int(game.get("AD")))
            result.append({'url': url, 'team_1': team_1, 'team_2': team_2, "league": league})
    return result


def get_teams(url: str) -> dict:
    html_content = requests.get(url, {"x-fsign": "SW9D1eZo"}).text

    soup = BeautifulSoup(html_content, 'lxml')
    result_string = soup.find('script', string=re.compile(r"window\.environment"))
    match = re.search(r"window\.environment\s*=\s*(\{.*\});", result_string.string)

    result_dict = {}
    if match:
        json_data = json.loads(match.group(1))  # Конвертируем JSON-строку в словарь
        home_link = json_data['participantsData']['home'][0]['detail_link']
        away_link = json_data['participantsData']['away'][0]['detail_link']
        result_dict = {'home': f'https://www.flashscore.com.ua{home_link}',
                       'away': f'https://www.flashscore.com.ua{away_link}'}
    return result_dict


def player_status(url: str, name: str, team_name) -> dict:
    player_html = requests.get(url, {"x-fsign": "SW9D1eZo"}).text
    soup = BeautifulSoup(player_html, 'lxml')
    result_string = soup.find('script', string=re.compile(r"window\.playerProfilePageEnvironment"))
    if result_string:
        script_content = result_string.string
        match = re.search(r"window\.playerProfilePageEnvironment\s*=\s*(\{.*\});", script_content)

        if match:
            json_data = match.group(1)
            json_data = json.loads(json_data)

    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(json_data, file, ensure_ascii=False, indent=4)

    last_match = 'заявлен' # ''

    steps = json_data['lastMatchesData']['lastMatches']
    try:
        for step in steps:
            home_participant = step['homeParticipantName']
            away_participant = step['awayParticipantName']

            if team_name in (home_participant, away_participant) and step['absenceCategory'] != '': # <==========
                last_match = step['absenceCategory']
                break

    except IndexError:
        print('IndexError in last match')

    # try:
    #     if int(json_data['injuryHistoryTable']['injury_history'][0]['is_valid']) == 0:
    #         injury = {'is_valid': '', 'injury_from': '', 'injury_until': '', 'injury_name': '', 'hide': False}
    #     else:
    #         injury = json_data['injuryHistoryTable']['injury_history'][0]
    #         last_match = json_data['injuryHistoryTable']['injury_history'][0]['injury_name']
    # except IndexError:
    #     injury = {'is_valid': '', 'injury_from': '', 'injury_until': '', 'injury_name': '', 'hide': False}

    matches_played = ''
    goals = ''
    assists = ''
    points = ''
    season_name = ''
    try:
        seasons = json_data['careerTables'][0]['seasons']
    except IndexError:
        seasons = []
    for season in seasons:
        try:
            # Проверяем условия
            if is_in_season(season.get('season_name', '')) and season.get('team_name') == team_name:
                # Получаем данные с проверкой ключей
                matches_played = season.get('matches_played', '')
                goals = season.get('goals', '')
                assists = season.get('assists', '')
                points = season.get('points', '')
                season_name = season.get('season_name', '')
                break  # Если нашли нужный сезон, прерываем цикл
        except Exception:
            pass



    player_dict = {
        'name': name,
        'last_match': last_match,
        'matches_played': matches_played,
        'goals': goals,
        'assists': assists,
        'points': points,
        'season_name': season_name
    }
    return player_dict


def get_players_list(url: str) -> list:
    html_content = requests.get(url, {"x-fsign": "SW9D1eZo"}).text
    soup = BeautifulSoup(html_content, 'lxml')
    team_name = soup.find("div", class_="heading__name").text
    players = soup.find_all("a", class_="lineupTable__cell--name")
    players_list = []
    seen_links = set()
    for player in players:
        player_name = player.get_text(strip=True)  # Имя игрока
        player_link = f'https://www.flashscore.com.ua{player.get("href")}'  # Ссылка на игрока
        soup = BeautifulSoup(requests.get(player_link).text, 'lxml')
        coach = soup.find('strong', class_='wcl-simpleText_Asp-0').get_text(strip=True)
        if player_link not in seen_links and coach != 'Тренер':
            seen_links.add(player_link)
            player = player_status(player_link, player_name, team_name)
            players_list.append(player)

    return players_list


if __name__ == '__main__':
        print(player_status('https://www.flashscore.com.ua/player/varlamov-semyon/M9CWNN6m/', 'Семен Варламов', 'Айлендерс'))
