
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

API_KEY = os.environ["API_FOOTBALL_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BASE_URL = "https://v3.football.api-sports.io"
TIMEZONE = ZoneInfo("America/Fortaleza")
STATE_FILE = Path("sent_matches.json")

# Brasileirão Série A
LEAGUE_ID = 71
SEASON = 2026

FINISHED_STATUSES = {"FT", "AET", "PEN"}


def load_sent_matches():
    if not STATE_FILE.exists():
        return set()

    with STATE_FILE.open("r", encoding="utf-8") as file:
        return set(json.load(file))


def save_sent_matches(sent):
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(sorted(sent), file, ensure_ascii=False, indent=2)


def get_fixtures():
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)

    response = requests.get(
        f"{BASE_URL}/fixtures",
        headers={"x-apisports-key": API_KEY},
        params={
            "league": LEAGUE_ID,
            "season": SEASON,
            "from": yesterday.isoformat(),
            "to": today.isoformat(),
            "timezone": "America/Fortaleza",
        },
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("errors"):
        raise RuntimeError(f"Erro da API: {data['errors']}")

    return data["response"]


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Erro do Telegram: {result}")


def main():
    sent = load_sent_matches()
    fixtures = get_fixtures()
    new_sent = set(sent)

    for fixture in fixtures:
        match = fixture["fixture"]
        status = match["status"]["short"]
        match_id = str(match["id"])

        if status not in FINISHED_STATUSES:
            continue

        if match_id in sent:
            continue

        teams = fixture["teams"]
        goals = fixture["goals"]
        league = fixture["league"]

        home = teams["home"]["name"]
        away = teams["away"]["name"]
        home_goals = goals["home"]
        away_goals = goals["away"]

        if home_goals is None or away_goals is None:
            continue

        message = (
            "🏁 FIM DE JOGO — BRASILEIRÃO\n\n"
            f"⚽ {home} {home_goals} x {away_goals} {away}\n\n"
            f"🏆 {league['name']}\n"
            "✅ Partida encerrada"
        )

        # Marcar como enviado somente após o Telegram confirmar.
        send_telegram_message(message)
        new_sent.add(match_id)
        save_sent_matches(new_sent)

        print(f"Resultado enviado: {home} x {away}")

    print("Verificação concluída.")


if __name__ == "__main__":
    main()
