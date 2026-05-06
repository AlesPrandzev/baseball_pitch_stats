import customtkinter as ctk
import tkinter as tk
from datetime import date
import database
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns

sns.set_theme(style="darkgrid")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BaseballTrackerModern:
    def __init__(self, root):
        self.root = root
        self.root.title("Baseball Pitch Tracker - Pro")
        self.root.geometry("900x750") # Zvětšili jsme okno, aby se vešly grafy
        
        self.pitch_x = None
        self.pitch_y = None
        self.recent_pitches_frame = None
        
        self.load_players_from_db()
        self.create_widgets()

    def load_players_from_db(self):
        teams = database.get_all_teams()
        self.teams_list = ["Všichni"] + teams  # Přidaj "Všichni" na začátek
        self.teams_only_list = teams.copy()
        self.current_team = None
        self.player_map = {}
        self.player_names_list = []
        self.pitcher_player_map = {}
        self.batter_player_map = {}
        self.edit_player_map = {}
    
    def get_players_for_team(self, team):
        """Vrátí seznam hráčů pro daný tým."""
        player_map = {}
        player_list = []
        
        if team == "Všichni":
            players_data = database.get_all_players()
        else:
            players_data = database.get_players_by_team(team)
        
        for player in players_data:
            p_id, first_name, last_name, team_name, jersey, throws, bats = player
            display_name = f"#{jersey} {first_name} {last_name} ({team_name}) [P: {throws}, Pál: {bats}]"
            player_map[display_name] = p_id
            player_list.append(display_name)
        
        return player_list, player_map

    def get_all_player_displays(self):
        player_list = []
        player_map = {}
        players_data = database.get_all_players()
        for player in players_data:
            p_id, first_name, last_name, team_name, jersey, throws, bats = player
            display_name = f"#{jersey} {first_name} {last_name} ({team_name}) [P: {throws}, Pál: {bats}]"
            player_map[display_name] = p_id
            player_list.append(display_name)
        return player_list, player_map

    def update_stats_pitcher_players(self, team):
        player_list, self.stats_pitcher_map = self.get_players_for_team(team)
        self.stat_pitcher.configure(values=["Všichni"] + player_list)
        self.stat_pitcher.set("Všichni")

    def update_stats_batter_players(self, team):
        player_list, self.stats_batter_map = self.get_players_for_team(team)
        self.stat_batter.configure(values=["Všichni"] + player_list)
        self.stat_batter.set("Všichni")

    def refresh_edit_player_menu(self, selected_player_id=None):
        player_list, self.edit_player_map = self.get_all_player_displays()
        self.edit_player_menu.configure(values=player_list)
        if selected_player_id:
            selected_display = next((name for name, pid in self.edit_player_map.items() if pid == selected_player_id), None)
            if selected_display:
                self.edit_player_menu.set(selected_display)
                self.on_edit_player_selected(selected_display)
                return
        if player_list:
            self.edit_player_menu.set(player_list[0])
            self.on_edit_player_selected(player_list[0])

    def refresh_all_player_lists(self):
        old_pitcher_team = self.pitcher_team_menu.get() if hasattr(self, 'pitcher_team_menu') else None
        old_batter_team = self.batter_team_menu.get() if hasattr(self, 'batter_team_menu') else None
        old_edit_player_id = None
        if hasattr(self, 'edit_player_menu'):
            selected = self.edit_player_menu.get()
            old_edit_player_id = self.edit_player_map.get(selected)

        self.load_players_from_db()
        if hasattr(self, 'pitcher_team_menu'):
            self.pitcher_team_menu.configure(values=self.teams_list)
            if old_pitcher_team in self.teams_list:
                self.pitcher_team_menu.set(old_pitcher_team)
        if hasattr(self, 'batter_team_menu'):
            self.batter_team_menu.configure(values=self.teams_list)
            if old_batter_team in self.teams_list:
                self.batter_team_menu.set(old_batter_team)
        if hasattr(self, 'edit_player_menu'):
            self.refresh_edit_player_menu(old_edit_player_id)

    def on_edit_player_selected(self, display_name):
        player_id = self.edit_player_map.get(display_name)
        if not player_id:
            return
        player = database.get_player_by_id(player_id)
        if not player:
            return
        _, first_name, last_name, team_name, jersey, throws, bats = player
        self.edit_first_name.delete(0, tk.END)
        self.edit_first_name.insert(0, first_name)
        self.edit_last_name.delete(0, tk.END)
        self.edit_last_name.insert(0, last_name)
        self.edit_team.delete(0, tk.END)
        self.edit_team.insert(0, team_name)
        self.edit_jersey.delete(0, tk.END)
        self.edit_jersey.insert(0, str(jersey))
        self.edit_throws.set(throws)
        self.edit_bats.set(bats)

    def save_player_changes(self):
        selected = self.edit_player_menu.get()
        player_id = self.edit_player_map.get(selected)
        if not player_id:
            return
        first_name = self.edit_first_name.get().strip()
        last_name = self.edit_last_name.get().strip()
        team_name = self.edit_team.get().strip()
        jersey = self.edit_jersey.get().strip()
        throws = self.edit_throws.get()
        bats = self.edit_bats.get()
        if not first_name or not last_name or not team_name or not jersey:
            return
        try:
            jersey_number = int(jersey)
        except ValueError:
            return
        database.update_player(player_id, first_name, last_name, team_name, jersey_number, throws, bats)
        self.refresh_all_player_lists()

    def update_pitcher_list(self, team):
        """Aktualizuje seznam nadhazovačů pro vybraný tým."""
        player_list, self.pitcher_player_map = self.get_players_for_team(team)
        self.pitcher_menu.configure(values=player_list)
        if len(player_list) > 0:
            self.pitcher_menu.set(player_list[0])
    
    def update_batter_list(self, team):
        """Aktualizuje seznam pálkařů pro vybraný tým."""
        player_list, self.batter_player_map = self.get_players_for_team(team)
        self.batter_menu.configure(values=player_list)
        if len(player_list) > 0:
            self.batter_menu.set(player_list[0])
    
        
    
    def create_widgets(self):
        # --- ZÁLOŽKY (TABS) ---
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_zapis = self.tabview.add("Zápis nadhozů")
        self.tab_staty = self.tabview.add("Statistiky")
        self.tab_edit = self.tabview.add("Edit hráčů")
        self.tab_recent = self.tabview.add("Poslední nadhozy")
        
        self.build_zapis_tab()
        self.build_staty_tab()
        self.build_edit_players_tab()
        self.build_recent_pitches_tab()

    # ==========================================
    # STRÁNKA 1: ZÁPIS NADHOZŮ
    # ==========================================
    def build_zapis_tab(self):
        # Hlavní frame pro hráče
        frame_players = ctk.CTkFrame(self.tab_zapis)
        frame_players.pack(fill="x", padx=20, pady=10)
        
        # --- NADHAZOVAČ ---
        ctk.CTkLabel(frame_players, text="Tým nadhazovače:").grid(row=0, column=0, padx=10, pady=10)
        self.pitcher_team_menu = ctk.CTkOptionMenu(frame_players, values=self.teams_list, command=self.update_pitcher_list)
        self.pitcher_team_menu.grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(frame_players, text="Nadhazovač:").grid(row=1, column=0, padx=10, pady=10)
        self.pitcher_menu = ctk.CTkOptionMenu(frame_players, values=[])
        self.pitcher_menu.grid(row=1, column=1, padx=10)
        
        # --- PÁLKAŘ ---
        ctk.CTkLabel(frame_players, text="Tým pálkaře:").grid(row=2, column=0, padx=10, pady=10)
        self.batter_team_menu = ctk.CTkOptionMenu(frame_players, values=self.teams_list, command=self.update_batter_list)
        self.batter_team_menu.grid(row=2, column=1, padx=10)
        
        ctk.CTkLabel(frame_players, text="Pálkař:").grid(row=3, column=0, padx=10, pady=10)
        self.batter_menu = ctk.CTkOptionMenu(frame_players, values=[])
        self.batter_menu.grid(row=3, column=1, padx=10)
        
        # Inicializuj s prvním týmem
        if len(self.teams_list) > 0:
            self.pitcher_team_menu.set(self.teams_list[0])
            self.batter_team_menu.set(self.teams_list[1] if len(self.teams_list) > 1 else self.teams_list[0])
            self.update_pitcher_list(self.teams_list[0])
            self.update_batter_list(self.teams_list[1] if len(self.teams_list) > 1 else self.teams_list[0])

        # 2. Lokace
        frame_zone = ctk.CTkFrame(self.tab_zapis)
        frame_zone.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.canvas = tk.Canvas(frame_zone, width=300, height=300, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(pady=5)
        self.canvas.create_rectangle(100, 50, 200, 250, outline="#1f538d", width=3, dash=(4, 4))
        self.canvas.create_text(150, 40, text="Strike zóna", fill="white")
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        self.btn_ball = ctk.CTkButton(frame_zone, text="BALL (Mimo plátno)", fg_color="gray", command=self.set_ball)
        self.btn_ball.pack(pady=5)

        # 3. Detaily a Uložení
        frame_details = ctk.CTkFrame(self.tab_zapis)
        frame_details.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(frame_details, text="Datum (YYYY-MM-DD):").pack(side="left", padx=10, pady=10)
        self.pitch_date = ctk.CTkEntry(frame_details, width=120)
        self.pitch_date.insert(0, date.today().isoformat())
        self.pitch_date.pack(side="left", padx=0, pady=10)
        
        self.pitch_type = ctk.CTkOptionMenu(frame_details, values=["Fastball", "Curveball", "Slider", "Changeup"])
        self.pitch_type.pack(side="left", padx=10, pady=10, expand=True)
        self.pitch_result = ctk.CTkOptionMenu(frame_details, values=["Called Strike", "Swinging Strike", "Foul Ball", "Ball", "In Play", "Hard Hit", "Soft Hit"])
        self.pitch_result.pack(side="right", padx=10, pady=10, expand=True)

        self.btn_save = ctk.CTkButton(self.tab_zapis, text="ULOŽIT NADHOZ", fg_color="green", command=self.save_pitch)
        self.btn_save.pack(pady=10, fill="x", padx=20)

    def build_edit_players_tab(self):
        frame_edit = ctk.CTkFrame(self.tab_edit)
        frame_edit.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(frame_edit, text="Vyber hráče:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.edit_player_menu = ctk.CTkOptionMenu(frame_edit, values=[], command=self.on_edit_player_selected)
        self.edit_player_menu.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Jméno:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.edit_first_name = ctk.CTkEntry(frame_edit, width=160)
        self.edit_first_name.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Příjmení:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.edit_last_name = ctk.CTkEntry(frame_edit, width=160)
        self.edit_last_name.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Tým:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.edit_team = ctk.CTkEntry(frame_edit, width=160)
        self.edit_team.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Číslo dresu:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.edit_jersey = ctk.CTkEntry(frame_edit, width=80)
        self.edit_jersey.grid(row=4, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Háže:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.edit_throws = ctk.CTkOptionMenu(frame_edit, values=["L", "R"])
        self.edit_throws.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Pálí:").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        self.edit_bats = ctk.CTkOptionMenu(frame_edit, values=["L", "R", "S"])
        self.edit_bats.grid(row=6, column=1, padx=10, pady=8, sticky="w")

        self.btn_update_player = ctk.CTkButton(self.tab_edit, text="ULOŽIT ZMĚNY", fg_color="blue", command=self.save_player_changes)
        self.btn_update_player.pack(pady=10, fill="x", padx=20)

        self.refresh_edit_player_menu()

    def build_recent_pitches_tab(self):
        self.recent_pitches_frame = ctk.CTkScrollableFrame(self.tab_recent)
        self.recent_pitches_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.update_recent_pitches()

    # ==========================================
    # STRÁNKA 2: STATISTIKY (INTERAKTIVNÍ)
    # ==========================================
    def build_staty_tab(self):
        # Horní panel pro filtry
        filter_frame = ctk.CTkFrame(self.tab_staty)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        row = 0
        ctk.CTkLabel(filter_frame, text="Tým nadhazovače:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
        self.stats_pitcher_team = ctk.CTkOptionMenu(filter_frame, values=self.teams_list, command=self.update_stats_pitcher_players)
        self.stats_pitcher_team.grid(row=row, column=1, padx=5, pady=2)
        
        row += 1
        ctk.CTkLabel(filter_frame, text="Nadhazovač:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
        self.stat_pitcher = ctk.CTkOptionMenu(filter_frame, values=["Všichni"])
        self.stat_pitcher.grid(row=row, column=1, padx=5, pady=2)
        
        row += 1
        ctk.CTkLabel(filter_frame, text="Tým pálkaře:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
        self.stats_batter_team = ctk.CTkOptionMenu(filter_frame, values=self.teams_list, command=self.update_stats_batter_players)
        self.stats_batter_team.grid(row=row, column=1, padx=5, pady=2)
        
        row += 1
        ctk.CTkLabel(filter_frame, text="Pálkař:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
        self.stat_batter = ctk.CTkOptionMenu(filter_frame, values=["Všichni"])
        self.stat_batter.grid(row=row, column=1, padx=5, pady=2)
        
        row += 1
        ctk.CTkLabel(filter_frame, text="Výsledek nadhozu:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
        self.pitch_result_filter = ctk.CTkOptionMenu(filter_frame, values=["Všechny", "Called Strike", "Swinging Strike", "Foul Ball", "Ball", "In Play", "Hard Hit", "Soft Hit"])
        self.pitch_result_filter.grid(row=row, column=1, padx=5, pady=2)
        
        row += 1
        btn_show = ctk.CTkButton(filter_frame, text="Generovat grafy", command=self.draw_charts)
        btn_show.grid(row=row, column=0, columnspan=2, pady=10)

        self.stats_pitcher_team.set("Všichni")
        self.stats_batter_team.set(self.teams_list[1] if len(self.teams_list) > 1 else "Všichni")
        self.pitch_result_filter.set("Všechny")
        self.update_stats_pitcher_players("Všichni")
        self.update_stats_batter_players(self.teams_list[1] if len(self.teams_list) > 1 else "Všichni")

        # Rámeček, do kterého se vloží samotné grafy z Matplotlibu
        self.chart_frame = ctk.CTkFrame(self.tab_staty)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Proměnná pro uchování aktuálního grafu (abychom ho mohli mazat při přegenerování)
        self.canvas_widget = None

    # ==========================================
    # LOGIKA FUNKCÍ
    # ==========================================
    def on_canvas_click(self, event):
        self.canvas.delete("pitch_mark")
        self.pitch_x, self.pitch_y = event.x, event.y
        r = 6 
        self.canvas.create_oval(self.pitch_x - r, self.pitch_y - r, self.pitch_x + r, self.pitch_y + r, fill="red", outline="white", tags="pitch_mark")

    def set_ball(self):
        self.canvas.delete("pitch_mark")
        self.pitch_x, self.pitch_y = "Mimo", "Mimo"
        self.pitch_result.set("Ball")

    def save_pitch(self):
        if self.pitch_x is None:
            return
            
        p_id = self.pitcher_player_map.get(self.pitcher_menu.get())
        b_id = self.batter_player_map.get(self.batter_menu.get())
        pitch_date = self.pitch_date.get().strip() or date.today().isoformat()

        if p_id and b_id:
            database.insert_pitch(p_id, b_id, self.pitch_type.get(), self.pitch_result.get(), str(self.pitch_x), str(self.pitch_y), pitch_date)
            
        self.canvas.delete("pitch_mark")
        self.pitch_x = None
        self.update_recent_pitches()

    def draw_charts(self):
        # 1. Načtení dat z DB (teď už nám stačí jen ID a data o nadhozu)
        conn = database.connect()
        query = '''
            SELECT p.pitcher_id, p.batter_id, p.pitch_type, p.pitch_result, p.x_location, p.y_location,
                   pitcher.team AS pitcher_team, batter.team AS batter_team
            FROM pitches p
            JOIN players pitcher ON p.pitcher_id = pitcher.id
            JOIN players batter ON p.batter_id = batter.id
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()

        # 2. Filtrace podle toho, co je vybráno v menu
        sel_pitcher_team = self.stats_pitcher_team.get()
        sel_batter_team = self.stats_batter_team.get()
        sel_pitcher = self.stat_pitcher.get()
        sel_batter = self.stat_batter.get()
        sel_result = self.pitch_result_filter.get()
        
        if sel_pitcher_team != "Všichni":
            df = df[df['pitcher_team'] == sel_pitcher_team]
        if sel_batter_team != "Všichni":
            df = df[df['batter_team'] == sel_batter_team]
        
        if sel_pitcher != "Všichni" and sel_pitcher:
            p_id = self.stats_pitcher_map.get(sel_pitcher)
            if p_id:
                df = df[df['pitcher_id'] == p_id]
        
        if sel_batter != "Všichni" and sel_batter:
            b_id = self.stats_batter_map.get(sel_batter)
            if b_id:
                df = df[df['batter_id'] == b_id]

        if sel_result != "Všechny":
            df = df[df['pitch_result'] == sel_result]

        # Smazání starého grafu, pokud už tam nějaký je
        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()

        if df.empty:
            print("Žádná data pro tento výběr.")
            return

        # 3. Příprava plátna se TŘEMI grafy vedle sebe (1 řádek, 3 sloupce)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
        fig.patch.set_facecolor('#2b2b2b') # Tmavé pozadí okolo grafů

        # --- GRAF 1: Lokace nadhozů (Scatter plot) ---
        df_plot = df[(df['x_location'] != 'Mimo') & (df['y_location'] != 'Mimo')].copy()
        if not df_plot.empty:
            df_plot['x_location'] = pd.to_numeric(df_plot['x_location'])
            df_plot['y_location'] = pd.to_numeric(df_plot['y_location'])
            
            sns.scatterplot(data=df_plot, x='x_location', y='y_location', hue='pitch_type', s=100, ax=ax1, palette="bright")
            import matplotlib.patches as patches
            ax1.add_patch(patches.Rectangle((100, 50), 100, 200, linewidth=2, edgecolor='white', facecolor='none', linestyle='--'))
            ax1.set_xlim(0, 300)
            ax1.set_ylim(300, 0) # Invertovaná osa
        
        ax1.set_title("Lokace ve strike zóně", color="white")
        ax1.tick_params(colors='white')
        ax1.xaxis.label.set_color('white')
        ax1.yaxis.label.set_color('white')
        
        # --- GRAF 2: Typy nadhozů (Sloupcový graf) ---
        pitch_counts = df['pitch_type'].value_counts()
        pitch_counts.plot(kind='bar', ax=ax2, color=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
        ax2.set_title("Četnost typů nadhozů", color="white")
        ax2.tick_params(colors='white', rotation=45)

        # --- GRAF 3: Výsledky nadhozů (Sloupcový graf) ---
        result_counts = df['pitch_result'].value_counts()
        result_counts.plot(kind='bar', ax=ax3, color=['#ff6666','#66ff66','#6666ff','#ffcc99','#99ff99','#ff9999','#66b3ff'])
        ax3.set_title("Četnost výsledků nadhozů", color="white")
        ax3.tick_params(colors='white', rotation=45)

        fig.tight_layout()

        # 4. Vložení Matplotlib grafu do CustomTkinteru
        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill="both", expand=True)


    def update_recent_pitches(self):
        # Clear existing content
        for widget in self.recent_pitches_frame.winfo_children():
            widget.destroy()
        
        # Add title
        ctk.CTkLabel(self.recent_pitches_frame, text="Poslední nadhozy:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        pitches = database.get_recent_pitches(10)  # Show more pitches, say 10
        if not pitches:
            ctk.CTkLabel(self.recent_pitches_frame, text="Žádné nadhozy zatím nebyly zaznamenány.").pack(pady=20)
            return
        
        for pitch in pitches:
            pitch_id, date_time, pitcher_id, batter_id, pitch_type, pitch_result, x_loc, y_loc, pitcher_name, batter_name = pitch
            display_text = f"{date_time[:19]}: {pitcher_name} vs {batter_name} - {pitch_type} ({pitch_result})"
            frame = ctk.CTkFrame(self.recent_pitches_frame)
            frame.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(frame, text=display_text).pack(side="left", padx=5)
            btn_delete = ctk.CTkButton(frame, text="Smazat", fg_color="red", command=lambda pid=pitch_id: self.delete_pitch(pid))
            btn_delete.pack(side="right", padx=5)

    def delete_pitch(self, pitch_id):
        database.delete_pitch(pitch_id)
        self.update_recent_pitches()


if __name__ == "__main__":
    root = ctk.CTk()
    app = BaseballTrackerModern(root)
    root.mainloop()