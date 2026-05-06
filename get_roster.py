import requests
from bs4 import BeautifulSoup
import database

def import_roster_from_web(url):
    print(f"Stahuji data z: {url}")
    
    # 1. Stažení stránky
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"❌ Chyba při stahování stránky: {e}")
        return

    # 2. Parsování HTML
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Automatické zjištění názvu týmu z nadpisu (např. "Soupiska týmu Arrows Ostrava")
    team_name_header = soup.find("h2", class_="h2 text-primary")
    team_name = "Neznámý tým"
    if team_name_header:
        team_name = team_name_header.text.replace("Soupiska týmu ", "").strip()

    # Hledáme všechny bloky s informacemi o hráčích (podle třídy v tvém HTML)
    players = soup.find_all("div", class_="teamItem__content")
    
    if not players:
        print("❌ Nenalezeni žádní hráči. HTML struktura je možná jiná.")
        return

    print(f"Nalezeno {len(players)} hráčů pro {team_name}. Začínám ukládat...")

    # 3. Zpracování každého hráče
    hraci_pridani = 0
    for player in players:
        try:
            # Získání čísla dresu (<div class="text-tertiary fw-bold mb-2 h4">#42</div>)
            jersey_div = player.find("div", class_="text-tertiary fw-bold mb-2 h4")
            jersey_num = 0
            if jersey_div:
                jersey_text = jersey_div.text.replace("#", "").strip()
                if jersey_text.isdigit():
                    jersey_num = int(jersey_text)

            # Získání jména (<div class="fw-bold text-primary h4">Boris Bokaj</div>)
            name_div = player.find("div", class_="fw-bold text-primary h4")
            if not name_div:
                continue
            
            full_name = name_div.text.strip()
            name_parts = full_name.split()
            
            # Rozdělení na jméno a příjmení
            if len(name_parts) >= 2:
                last_name = name_parts[-1]
                first_name = " ".join(name_parts[:-1])
            else:
                first_name = full_name
                last_name = ""

            # Podle zadání nastavíme všechny napevno jako praváky
            throws = "R"
            bats = "R"

            # 4. Odeslání do databáze (přes tvůj soubor database.py)
            database.insert_player(first_name, last_name, team_name, jersey_num, throws, bats)
            print(f"✅ Uloženo: #{jersey_num} {first_name} {last_name} [Pálí: {bats} / Háze: {throws}]")
            hraci_pridani += 1
            
        except Exception as e:
            print(f"⚠️ Chyba při zpracování hráče: {e}")

    print(f"\n🎉 Hotovo! Úspěšně přidáno {hraci_pridani} hráčů do databáze.")

if __name__ == "__main__":
    # Ujistíme se, že tabulky existují
    database.create_tables()
    
    # URL adresa z tvého zadání
    URL = "https://baseball.cz/competition/roster/1?team=5830&season=21"
    
    # Spuštění importu
    import_roster_from_web(URL)