
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

API_KEY = os.environ["FOOTBALL_DATA_TOKEN"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BASE_URL = "https://api.football-data.org/v4"
TIMEZONE = ZoneInfo("America/Fortaleza")
STATE_FILE = Path("sent_matches.json")


def load_sent_matches():
    if not STATE_FILE.exists():
        return set()

    with STATE_FILE.open("r", encoding="utf-8") as file:
        return set(json.load(file))


def save_sent_matches(sent):
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(sorted(sent), file, ensure_ascii=False, indent=2)


def get_matches():
    today = datetime.now(TIMEZONE).date()
    yesterday = today - timedelta(days=1)

    response = requests.get(
        f"{BASE_URL}/competitions/BSA/matches",
        headers={"X-Auth-Token": API_KEY},
        params={
            "dateFrom": yesterday.isoformat(),
            "dateTo": today.isoformat(),
        },
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    return data.get("matches", [])


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

    if not response.json().get("ok"):
        raise RuntimeError("O Telegram não confirmou o envio.")


def main():
    sent = load_sent_matches()
    matches = get_matches()
    new_sent = set(sent)

    for match in matches:
        match_id = str(match["id"])

        if match["status"] != "FINISHED":
            continue

        if match_id in sent:
            continue

        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]

        score = match.get("score", {}).get("fullTime", {})
        home_goals = score.get("home")
        away_goals = score.get("away")

        if home_goals is None or away_goals is None:
            continue

        message = (
            "🏁 FIM DE JOGO — BRASILEIRÃO\n\n"
            f"⚽ {home} {home_goals} x {away_goals} {away}\n\n"
            "✅ Partida encerrada"
        )

        send_telegram_message(message)
        new_sent.add(match_id)
        save_sent_matches(new_sent)

        print(f"Resultado enviado: {home} x {away}")

    print(f"Verificação concluída. Jogos consultados: {len(matches)}")


if __name__ == "__main__":
    main()
