import csv
from openpyxl import Workbook


# Исходный список словарей
def into_csv_data(data, csv_file):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["name",
                                                      'last_match',
                                                      'matches_played',
                                                      'goals',
                                                      'assists',
                                                      'points',
                                                      'season_name'])
        writer.writeheader()
        writer.writerows(data)


def into_excel_data(data, excel_file):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Player Stats"
    headers = ["name", "last_match", "matches_played", "goals", "assists", "points", "season_name"]
    sheet.append(headers)
    for row in data:
        sheet.append([row.get(key, "") for key in headers])
    workbook.save(excel_file)
