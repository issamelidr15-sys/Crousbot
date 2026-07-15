import os
import json
import requests
from bs4 import BeautifulSoup

# ==============================================================
#  CONFIGURATION
#  (ces valeurs viennent des "secrets" GitHub, on n'écrit rien
#   en clair ici pour rester en sécurité)
# ==============================================================

# L'adresse de recherche copiée depuis le site (avec tes filtres :
# ville, prix max, surface, etc.)
SEARCH_URL = os.environ.get(
    "SEARCH_URL", "https://trouverunlogement.lescrous.fr/tools/47/search"
)

# Le token de ton bot Telegram (donné par @BotFather)
BOT_TOKEN = os.environ["BOT_TOKEN"]

# L'identifiant de ton chat Telegram (ton "numéro de boite aux lettres")
CHAT_ID = os.environ["CHAT_ID"]

# Le petit carnet où le robot note les logements déjà vus
MEMORY_FILE = "logements_connus.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def send_telegram_message(text):
    """Envoie un message sur Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    r = requests.post(url, data=payload, timeout=15)
    if not r.ok:
        print("Erreur envoi Telegram :", r.text)


def get_logements():
    """Va lire la page de résultats et récupère la liste des logements."""
    logements = {}
    resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for link in soup.select("a[href*='/accommodations/']"):
        href = link.get("href")
        if not href or "/accommodations/" not in href:
            continue
        accommodation_id = href.rstrip("/").split("/")[-1]
        if not accommodation_id.isdigit():
            continue
        title = link.get_text(strip=True) or f"Logement {accommodation_id}"
        full_url = href if href.startswith("http") else f"https://trouverunlogement.lescrous.fr{href}"
        logements[accommodation_id] = {"titre": title, "url": full_url}

    return logements


def load_known():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_known(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    known = load_known()
    current = get_logements()

    if not current:
        print("Aucun logement trouvé sur la page. Vérifie que SEARCH_URL est correcte.")
        return

    if not known:
        # Premier lancement : on mémorise tout, sans spammer Telegram
        save_known(current)
        print(f"Première exécution : {len(current)} logement(s) enregistré(s) comme déjà connus.")
        return

    new_ids = set(current) - set(known)

    if new_ids:
        print(f"{len(new_ids)} nouveau(x) logement(s) trouvé(s) !")
        for acc_id in new_ids:
            info = current[acc_id]
            message = f"🏠 Nouveau logement CROUS disponible !\n\n{info['titre']}\n{info['url']}"
            send_telegram_message(message)
    else:
        print("Aucun nouveau logement pour le moment.")

    save_known(current)


if __name__ == "__main__":
    main()
