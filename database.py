import sqlite3

DB_FILE = "baseball.db"

def connect():
    return sqlite3.connect(DB_FILE)

def create_tables():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = 1")
    cursor = conn.cursor()
    
    # Rozšířená tabulka hráčů
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            team TEXT,
            jersey_number INTEGER,
            throws TEXT,
            bats TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pitches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            pitcher_id INTEGER,
            batter_id INTEGER,
            pitch_type TEXT,
            pitch_result TEXT,
            x_location TEXT,
            y_location TEXT,
            FOREIGN KEY (pitcher_id) REFERENCES players (id),
            FOREIGN KEY (batter_id) REFERENCES players (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_player(first_name, last_name, team, jersey_number, throws, bats):
    """Nyní přijímá i číslo dresu, ruku pro nadhoz (L/R) a stranu pro pálku (L/R/S)."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (first_name, last_name, team, jersey_number, throws, bats)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (first_name, last_name, team, jersey_number, throws, bats))
    conn.commit()
    conn.close()

def insert_pitch(pitcher_id, batter_id, pitch_type, pitch_result, x_location, y_location, date_time=None):
    conn = connect()
    cursor = conn.cursor()
    if date_time:
        cursor.execute('''
            INSERT INTO pitches (date_time, pitcher_id, batter_id, pitch_type, pitch_result, x_location, y_location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date_time, pitcher_id, batter_id, pitch_type, pitch_result, x_location, y_location))
    else:
        cursor.execute('''
            INSERT INTO pitches (pitcher_id, batter_id, pitch_type, pitch_result, x_location, y_location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (pitcher_id, batter_id, pitch_type, pitch_result, x_location, y_location))
    conn.commit()
    conn.close()

def get_all_players():
    """Vrátí všechny sloupce hráčů."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, last_name, team, jersey_number, throws, bats FROM players")
    players = cursor.fetchall()
    conn.close()
    return players

def get_all_teams():
    """Vrátí seznam všech unikátních týmů."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT team FROM players ORDER BY team")
    teams = [row[0] for row in cursor.fetchall()]
    conn.close()
    return teams

def get_players_by_team(team):
    """Vrátí všechny hráče z konkrétního týmu."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, last_name, team, jersey_number, throws, bats FROM players WHERE team = ? ORDER BY jersey_number", (team,))
    players = cursor.fetchall()
    conn.close()
    return players

def get_player_by_id(player_id):
    """Vrátí hráče podle ID."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, last_name, team, jersey_number, throws, bats FROM players WHERE id = ?", (player_id,))
    player = cursor.fetchone()
    conn.close()
    return player

def update_player(player_id, first_name, last_name, team, jersey_number, throws, bats):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players
        SET first_name = ?, last_name = ?, team = ?, jersey_number = ?, throws = ?, bats = ?
        WHERE id = ?
    ''', (first_name, last_name, team, jersey_number, throws, bats, player_id))
    conn.commit()
    conn.close()

# Testovací blok
if __name__ == "__main__":
    create_tables()
    # Pokud je prázdno, přidáme vzorová data
    if not get_all_players():
        insert_player("Tomáš", "Satoranský", "Draci Brno", 12, "R", "R")
        insert_player("Jan", "Novák", "Eagles Praha", 5, "L", "L")
        insert_player("Pavel", "Kubala", "Eagles Praha", 23, "R", "R")
        insert_player("Petr", "Svoboda", "Draci Brno", 7, "R", "L")
        insert_player("David", "Mareš", "Sokoli Ostrava", 15, "L", "R")
        insert_player("Lukáš", "Čech", "Sokoli Ostrava", 3, "R", "R")