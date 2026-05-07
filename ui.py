import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
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
        self.root.geometry("1000x800")

        self.pitch_x = None
        self.pitch_y = None
        self.recent_pitches_frame = None

        # --- Stav zápasu ---
        self.game_active = False
        self.game_home_team = None
        self.game_away_team = None
        self.game_home_lineup = []   # seznam player_id v pořadí
        self.game_away_lineup = []
        self.game_home_names = []    # zobrazované názvy
        self.game_away_names = []
        self.game_inning = 1
        self.game_half = "away"      # "away" = hosté pálí, "home" = domácí pálí
        self.game_batter_index = 0   # aktuální pozice v soupisku
        self.away_batter_index = 0
        self.home_batter_index = 0
        self.game_pitcher_id = None
        self.game_pitcher_name = ""

        self._last_undo = None
        self._toast_frame = None
        self.load_players_from_db()
        self.create_widgets()

    def load_players_from_db(self):
        teams = database.get_all_teams()
        self.teams_list = ["Všichni"] + teams
        self.teams_only_list = teams.copy()
        self.current_team = None
        self.player_map = {}
        self.player_names_list = []
        self.pitcher_player_map = {}
        self.batter_player_map = {}
        self.edit_player_map = {}

    def get_players_for_team(self, team):
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
        player_list, self.pitcher_player_map = self.get_players_for_team(team)
        self.pitcher_menu.configure(values=player_list)
        if len(player_list) > 0:
            self.pitcher_menu.set(player_list[0])

    def update_batter_list(self, team):
        player_list, self.batter_player_map = self.get_players_for_team(team)
        self.batter_menu.configure(values=player_list)
        if len(player_list) > 0:
            self.batter_menu.set(player_list[0])

    def create_widgets(self):
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_game = self.tabview.add("Zápas")
        self.tab_zapis = self.tabview.add("Zápis nadhozů")
        self.tab_staty = self.tabview.add("Statistiky")
        self.tab_edit = self.tabview.add("Edit hráčů")
        self.tab_recent = self.tabview.add("Poslední nadhozy")

        self.build_game_tab()
        self.build_zapis_tab()
        self.build_staty_tab()
        self.build_edit_players_tab()
        self.build_recent_pitches_tab()
        self.setup_keybindings()

    # ==========================================
    # ZÁLOŽKA: ZÁPAS
    # ==========================================
    def build_game_tab(self):
        # ── Scrollovatelná záložka Zápas ──
        game_scroll = ctk.CTkScrollableFrame(self.tab_game, corner_radius=0)
        game_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        content_frame = ctk.CTkFrame(game_scroll, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Nadpis ──
        header = ctk.CTkFrame(content_frame, fg_color="#1a2a3a", corner_radius=10)
        header.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(header, text="⚾  Nový zápas", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=20, pady=12)

        # ── Výběr týmů + nadhazovač ──
        setup_outer = ctk.CTkFrame(content_frame, fg_color="transparent")
        setup_outer.pack(fill="x", padx=20, pady=4)
        setup_outer.columnconfigure((0,1,2), weight=1)

        # Hosté
        away_setup = ctk.CTkFrame(setup_outer, corner_radius=8)
        away_setup.grid(row=0, column=0, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(away_setup, text="HOSTÉ  (pálí první)", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#aaaaaa").pack(pady=(10,2))
        self.game_away_team_menu = ctk.CTkOptionMenu(away_setup, values=self.teams_only_list,
                                                      command=self.on_away_team_selected, width=200)
        self.game_away_team_menu.pack(padx=16, pady=(0,4))
        ctk.CTkLabel(away_setup, text="Nadhazovač:", font=ctk.CTkFont(size=11),
                     text_color="#aaaaaa").pack()
        self.game_away_pitcher_menu_setup = ctk.CTkOptionMenu(away_setup, values=[], width=200)
        self.game_away_pitcher_menu_setup.pack(padx=16, pady=(0,12))

        # vs
        ctk.CTkLabel(setup_outer, text="vs", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#555555").grid(row=0, column=1, padx=4)

        # Domácí
        home_setup = ctk.CTkFrame(setup_outer, corner_radius=8)
        home_setup.grid(row=0, column=2, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(home_setup, text="DOMÁCÍ", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#aaaaaa").pack(pady=(10,2))
        self.game_home_team_menu = ctk.CTkOptionMenu(home_setup, values=self.teams_only_list,
                                                      command=self.on_home_team_selected, width=200)
        self.game_home_team_menu.pack(padx=16, pady=(0,4))
        ctk.CTkLabel(home_setup, text="Nadhazovač:", font=ctk.CTkFont(size=11),
                     text_color="#aaaaaa").pack()
        self.game_pitcher_menu_setup = ctk.CTkOptionMenu(home_setup, values=[], width=200)
        self.game_pitcher_menu_setup.pack(padx=16, pady=(0,12))

        # ── Spustit zápas ──
        ctk.CTkButton(content_frame, text="▶  SPUSTIT ZÁPAS", fg_color="#1a6a1a",
                      hover_color="#22882a", font=ctk.CTkFont(size=15, weight="bold"),
                      height=42, corner_radius=10, command=self.start_game).pack(
                          fill="x", padx=20, pady=(6, 10))

        # ── Soupisky ──
        lineups_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        lineups_frame.pack(fill="both", expand=True, padx=20, pady=0)
        lineups_frame.columnconfigure((0,1), weight=1)

        def make_lineup_panel(parent, col, label_text, side):
            panel = ctk.CTkFrame(parent, corner_radius=10)
            panel.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")

            # Hlavička panelu
            ph = ctk.CTkFrame(panel, fg_color="#1a2a3a", corner_radius=8)
            ph.pack(fill="x", padx=8, pady=(8,4))
            ctk.CTkLabel(ph, text=label_text, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=6)

            # Seznam soupisky
            lf = ctk.CTkScrollableFrame(panel, height=170, corner_radius=6)
            lf.pack(fill="x", padx=8, pady=4)

            # Vyhledávání
            sv = tk.StringVar()
            sv.trace("w", lambda *a, s=side: self.update_search_results(s))
            entry = ctk.CTkEntry(panel, textvariable=sv, placeholder_text="Hledat hráče...",
                                 corner_radius=8, height=34)
            entry.pack(fill="x", padx=8, pady=(4,2))
            sr = ctk.CTkScrollableFrame(panel, height=90, corner_radius=6)
            sr.pack(fill="x", padx=8, pady=(0,4))

            # Tlačítka akcí ve dvou sloupcích
            btn_frame = ctk.CTkFrame(panel, fg_color="transparent")
            btn_frame.pack(fill="x", padx=8, pady=(0,8))
            btn_frame.columnconfigure((0,1,2,3), weight=1)
            ctk.CTkButton(btn_frame, text="+ Přidat", height=30, corner_radius=6,
                          command=lambda s=side: self.add_lineup_player(s)).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
            ctk.CTkButton(btn_frame, text="↑", height=30, width=36, corner_radius=6, fg_color="#333",
                          command=lambda s=side: self.move_lineup_player(s, -1)).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
            ctk.CTkButton(btn_frame, text="↓", height=30, width=36, corner_radius=6, fg_color="#333",
                          command=lambda s=side: self.move_lineup_player(s, 1)).grid(row=0, column=2, padx=2, pady=2, sticky="ew")
            ctk.CTkButton(btn_frame, text="✕", height=30, width=36, corner_radius=6, fg_color="#5a1515",
                          command=lambda s=side: self.remove_lineup_player(s)).grid(row=0, column=3, padx=2, pady=2, sticky="ew")
            return lf, sv, sr

        self.away_lineup_frame, self.away_search_var, self.away_search_results = make_lineup_panel(
            lineups_frame, 0, "✈  Soupiska hostů", "away")
        self.home_lineup_frame, self.home_search_var, self.home_search_results = make_lineup_panel(
            lineups_frame, 1, "🏠  Soupiska domácích", "home")

        self.away_selected_player = tk.StringVar(value="")
        self.home_selected_player = tk.StringVar(value="")

        if self.teams_only_list:
            self.game_away_team_menu.set(self.teams_only_list[0])
            self.game_home_team_menu.set(self.teams_only_list[-1] if len(self.teams_only_list) > 1 else self.teams_only_list[0])
            self.on_away_team_selected(self.teams_only_list[0])
            self.on_home_team_selected(self.teams_only_list[-1] if len(self.teams_only_list) > 1 else self.teams_only_list[0])

        self.away_lineup_map = {}
        self.away_lineup_order = []
        self.home_lineup_map = {}
        self.home_lineup_order = []
        self.selected_away_lineup_item = None
        self.selected_home_lineup_item = None

    def normalize(self, text):
        """Odstraní diakritiku pro porovnávání."""
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

    def update_search_results(self, side):
        """Aktualizuje výsledky vyhledávání pod polem."""
        if side == "away":
            query = self.away_search_var.get()
            player_map = getattr(self, 'away_team_player_map', {})
            results_frame = self.away_search_results
            selected_var = self.away_selected_player
        else:
            query = self.home_search_var.get()
            player_map = getattr(self, 'home_team_player_map', {})
            results_frame = self.home_search_results
            selected_var = self.home_selected_player

        for w in results_frame.winfo_children():
            w.destroy()

        if not query:
            return

        norm_query = self.normalize(query)
        matches = [name for name in player_map.keys() if norm_query in self.normalize(name)]

        for name in matches[:10]:
            short = name.split("(")[0].strip()
            color = "#1f538d" if name == selected_var.get() else "gray"
            btn = ctk.CTkButton(results_frame, text=short, fg_color=color, anchor="w",
                                command=lambda n=name, s=side: self.select_search_result(n, s))
            btn.pack(fill="x", pady=1, padx=2)

    def select_search_result(self, name, side):
        """Označí hráče z výsledků vyhledávání."""
        if side == "away":
            self.away_selected_player.set(name)
        else:
            self.home_selected_player.set(name)
        self.update_search_results(side)

    def on_away_team_selected(self, team):
        player_list, pmap = self.get_players_for_team(team)
        self.away_team_player_map = pmap
        if hasattr(self, 'game_away_pitcher_menu_setup'):
            self.game_away_pitcher_menu_setup.configure(values=player_list)
            if player_list:
                self.game_away_pitcher_menu_setup.set(player_list[0])
        home_team = self.game_home_team_menu.get() if hasattr(self, 'game_home_team_menu') else None
        if home_team:
            self.on_home_team_selected(home_team)

    def on_home_team_selected(self, team):
        player_list, pmap = self.get_players_for_team(team)
        self.home_team_player_map = pmap
        # Nadhazovač domácích
        self.game_pitcher_menu_setup.configure(values=player_list)
        if player_list:
            self.game_pitcher_menu_setup.set(player_list[0])

    def add_lineup_player(self, side):
        """Unified přidání hráče do soupisky."""
        if side == "away":
            self.add_away_player()
        else:
            self.add_home_player()

    def add_away_player(self):
        selected = self.away_selected_player.get()
        if not selected or selected in self.away_lineup_order:
            return
        pid = self.away_team_player_map.get(selected)
        if not pid:
            return
        self.away_lineup_order.append(selected)
        self.away_lineup_map[selected] = pid
        self.away_selected_player.set("")
        self.away_search_var.set("")
        self.update_search_results("away")
        self.refresh_lineup_display("away")

    def add_home_player(self):
        selected = self.home_selected_player.get()
        if not selected or selected in self.home_lineup_order:
            return
        pid = self.home_team_player_map.get(selected)
        if not pid:
            return
        self.home_lineup_order.append(selected)
        self.home_lineup_map[selected] = pid
        self.home_selected_player.set("")
        self.home_search_var.set("")
        self.update_search_results("home")
        self.refresh_lineup_display("home")

    def move_lineup_player(self, side, direction):
        if side == "away":
            order = self.away_lineup_order
            selected = self.selected_away_lineup_item
        else:
            order = self.home_lineup_order
            selected = self.selected_home_lineup_item

        if not selected or selected not in order:
            return
        idx = order.index(selected)
        new_idx = idx + direction
        if 0 <= new_idx < len(order):
            order[idx], order[new_idx] = order[new_idx], order[idx]
            self.refresh_lineup_display(side)

    def remove_lineup_player(self, side):
        if side == "away":
            selected = self.selected_away_lineup_item
            if selected and selected in self.away_lineup_order:
                self.away_lineup_order.remove(selected)
                del self.away_lineup_map[selected]
                self.selected_away_lineup_item = None
                self.refresh_lineup_display("away")
        else:
            selected = self.selected_home_lineup_item
            if selected and selected in self.home_lineup_order:
                self.home_lineup_order.remove(selected)
                del self.home_lineup_map[selected]
                self.selected_home_lineup_item = None
                self.refresh_lineup_display("home")

    def refresh_lineup_display(self, side):
        if side == "away":
            frame = self.away_lineup_frame
            order = self.away_lineup_order
        else:
            frame = self.home_lineup_frame
            order = self.home_lineup_order

        for w in frame.winfo_children():
            w.destroy()

        for i, name in enumerate(order):
            # Zkrácené zobrazení – jen číslo dresu a jméno
            short = name.split("(")[0].strip()
            color = "#1f538d" if (side == "away" and name == self.selected_away_lineup_item) or \
                                 (side == "home" and name == self.selected_home_lineup_item) else "gray"
            btn = ctk.CTkButton(frame, text=f"{i+1}. {short}", fg_color=color, anchor="w",
                                command=lambda n=name, s=side: self.select_lineup_item(n, s))
            btn.pack(fill="x", pady=1, padx=2)

    def select_lineup_item(self, name, side):
        if side == "away":
            self.selected_away_lineup_item = name
        else:
            self.selected_home_lineup_item = name
        self.refresh_lineup_display(side)

    def start_game(self):
        if not self.away_lineup_order or not self.home_lineup_order:
            messagebox.showwarning("Chybí soupiska", "Zadej soupisku obou týmů!")
            return

        home_pitcher_display = self.game_pitcher_menu_setup.get()
        home_pitcher_id = self.home_team_player_map.get(home_pitcher_display)
        away_pitcher_display = self.game_away_pitcher_menu_setup.get()
        away_pitcher_id = self.away_team_player_map.get(away_pitcher_display)

        if not home_pitcher_id or not away_pitcher_id:
            messagebox.showwarning("Chybí nadhazovač", "Vyber nadhazovače pro oba týmy!")
            return

        self.game_active = True
        self.game_home_team = self.game_home_team_menu.get()
        self.game_away_team = self.game_away_team_menu.get()
        self.game_inning = 1
        self.game_half = "away"  # hosté pálí první → nadhazuje domácí
        self.game_batter_index = 0
        self.away_batter_index = 0
        self.home_batter_index = 0

        # Uložíme oba nadhazovače pro přepínání
        self.game_home_pitcher_id = home_pitcher_id
        self.game_home_pitcher_name = home_pitcher_display.split("(")[0].strip()
        self.game_away_pitcher_id = away_pitcher_id
        self.game_away_pitcher_name = away_pitcher_display.split("(")[0].strip()

        # Začínáme: hosté pálí → nadhazuje domácí
        self.game_pitcher_id = home_pitcher_id
        self.game_pitcher_name = self.game_home_pitcher_name

        self.tabview.set("Zápis nadhozů")
        self.update_game_zapis_ui()

    # ==========================================
    # ZÁLOŽKA: ZÁPIS NADHOZŮ
    # ==========================================
    def build_zapis_tab(self):
        # ── Top area (game info / manual select) ──
        self.top_area = ctk.CTkFrame(self.tab_zapis, fg_color="transparent")
        self.top_area.pack(fill="x", padx=0, pady=0)

        # Info bar – aktivní zápas (skrytý dokud nezačne)
        self.game_info_frame = ctk.CTkFrame(self.top_area, fg_color="#0d2b0d", corner_radius=0)
        self.game_info_label = ctk.CTkLabel(self.game_info_frame, text="",
                                             font=ctk.CTkFont(size=14, weight="bold"), text_color="#66ff66")
        self.game_info_label.pack(side="left", padx=18, pady=8)
        self.game_batter_label = ctk.CTkLabel(self.game_info_frame, text="",
                                               font=ctk.CTkFont(size=13), text_color="#ffffff")
        self.game_batter_label.pack(side="left", padx=12, pady=8)
        self.game_pitcher_label = ctk.CTkLabel(self.game_info_frame, text="",
                                                font=ctk.CTkFont(size=13), text_color="#aaaaaa")
        self.game_pitcher_label.pack(side="left", padx=12, pady=8)

        # Ovládání zápasu řádek 1 – zarovnáno na střed
        self.game_controls_row1 = ctk.CTkFrame(self.top_area, fg_color="#111111", corner_radius=0)
        center1 = ctk.CTkFrame(self.game_controls_row1, fg_color="transparent")
        center1.pack(anchor="center", pady=5)
        btn_cfg = [
            ("⏭  Další pálkař", "#4a4a00", self.game_skip_batter),
            ("⚾  Next Inning", "#1a3a7a", self.game_next_inning),
            ("■  Ukončit", "#6a1a1a", self.game_end),
        ]
        for txt, clr, cmd in btn_cfg:
            ctk.CTkButton(center1, text=txt, fg_color=clr, hover_color=clr,
                          width=148, height=34, corner_radius=8, command=cmd).pack(side="left", padx=5)

        # Ovládání zápasu řádek 2 – změna nadhazovače
        self.game_controls_row2 = ctk.CTkFrame(self.top_area, fg_color="#0a0a0a", corner_radius=0)
        center2 = ctk.CTkFrame(self.game_controls_row2, fg_color="transparent")
        center2.pack(anchor="center", pady=5)
        ctk.CTkLabel(center2, text="Změnit nadhazovače:", text_color="#888888").pack(side="left", padx=8)
        self.game_change_pitcher_menu = ctk.CTkOptionMenu(center2, values=[], width=230, height=32)
        self.game_change_pitcher_menu.pack(side="left", padx=6)
        ctk.CTkButton(center2, text="Potvrdit", fg_color="#7a3a00", hover_color="#a04a00",
                      width=90, height=32, corner_radius=8, command=self.game_change_pitcher).pack(side="left", padx=6)

        # Manuální výběr hráčů (bez aktivního zápasu)
        self.manual_players_frame = ctk.CTkFrame(self.top_area, fg_color="#111111", corner_radius=0)
        self.manual_players_frame.pack(fill="x", padx=0, pady=0)
        mcenter = ctk.CTkFrame(self.manual_players_frame, fg_color="transparent")
        mcenter.pack(anchor="center", pady=8)
        ctk.CTkLabel(mcenter, text="Tým P:").pack(side="left", padx=(0,4))
        self.pitcher_team_menu = ctk.CTkOptionMenu(mcenter, values=self.teams_list,
                                                    command=self.update_pitcher_list, width=150)
        self.pitcher_team_menu.pack(side="left", padx=4)
        self.pitcher_menu = ctk.CTkOptionMenu(mcenter, values=[], width=190)
        self.pitcher_menu.pack(side="left", padx=4)
        ctk.CTkLabel(mcenter, text="  Tým B:").pack(side="left", padx=(8,4))
        self.batter_team_menu = ctk.CTkOptionMenu(mcenter, values=self.teams_list,
                                                   command=self.update_batter_list, width=150)
        self.batter_team_menu.pack(side="left", padx=4)
        self.batter_menu = ctk.CTkOptionMenu(mcenter, values=[], width=190)
        self.batter_menu.pack(side="left", padx=4)

        if len(self.teams_list) > 0:
            self.pitcher_team_menu.set(self.teams_list[0])
            self.batter_team_menu.set(self.teams_list[1] if len(self.teams_list) > 1 else self.teams_list[0])
            self.update_pitcher_list(self.teams_list[0])
            self.update_batter_list(self.teams_list[1] if len(self.teams_list) > 1 else self.teams_list[0])

        # ── Hlavní zóna: typ | canvas | výsledek ──
        frame_middle = ctk.CTkFrame(self.tab_zapis, fg_color="transparent")
        frame_middle.pack(padx=10, pady=4, fill="both", expand=True)
        frame_middle.columnconfigure(0, weight=0)
        frame_middle.columnconfigure(1, weight=1)
        frame_middle.columnconfigure(2, weight=0)

        # VLEVO – typ nadhozu
        # Definice: (název, zkratka_klávesa, barva_aktivní)
        self._pitch_type_cfg = [
            ("Four-Seam Fastball", "1", "#1a4a8a"),
            ("Two-Seam Fastball",  "2", "#1a4a8a"),
            ("Curveball",          "3", "#6a2a8a"),
            ("Changeup",           "4", "#1a6a4a"),
            ("Splitter",           "5", "#6a4a1a"),
            ("Slider",             "6", "#8a3a1a"),
            ("Knuckleball",        "7", "#4a4a1a"),
        ]
        self._pitch_type_keys = {cfg[1]: cfg[0] for cfg in self._pitch_type_cfg}

        frame_left = ctk.CTkFrame(frame_middle, corner_radius=10)
        frame_left.grid(row=0, column=0, padx=(8,4), pady=6, sticky="ns")
        ctk.CTkLabel(frame_left, text="Typ nadhozu",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaaa").pack(pady=(10,4))
        self.selected_pitch_type = tk.StringVar(value="Four-Seam Fastball")
        self.pitch_type_buttons = {}
        for pt, key, clr in self._pitch_type_cfg:
            row_f = ctk.CTkFrame(frame_left, fg_color="transparent")
            row_f.pack(pady=2, padx=8, fill="x")
            # Zkratka badge
            ctk.CTkLabel(row_f, text=f"[{key}]", width=28, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#ffcc44").pack(side="left")
            btn = ctk.CTkButton(row_f, text=pt, width=138, height=30, corner_radius=7,
                                fg_color=clr if pt == "Four-Seam Fastball" else "#2a2a2a",
                                hover_color=clr,
                                command=lambda p=pt: self.select_pitch_type(p))
            btn.pack(side="left")
            self.pitch_type_buttons[pt] = btn
        self._pitch_type_colors = {cfg[0]: cfg[2] for cfg in self._pitch_type_cfg}

        # UPROSTŘED – strike zóna (centrovaný)
        frame_zone_outer = ctk.CTkFrame(frame_middle, fg_color="transparent")
        frame_zone_outer.grid(row=0, column=1, padx=4, pady=6, sticky="nsew")
        frame_zone = ctk.CTkFrame(frame_zone_outer, corner_radius=10)
        frame_zone.pack(expand=True)
        self.canvas = tk.Canvas(frame_zone, width=300, height=300, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        self.canvas.create_rectangle(85, 60, 215, 230, outline="#1f538d", width=3, dash=(4,4), tags="zone")
        self.canvas.create_text(150, 40, text="Strike zóna", fill="#666666", tags="zone")
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.current_batter_hand = "R"
        self.draw_batter_silhouette("R")
        ctk.CTkButton(frame_zone, text="BALL  –  Mimo zónu", fg_color="#2a2a2a",
                      hover_color="#3a3a3a", height=32, corner_radius=8, command=self.set_ball).pack(
                          pady=(0,10), padx=10, fill="x")

        # VPRAVO – výsledek
        # (název, klávesa, barva)
        self._result_cfg = [
            ("Called Strike",   "q", "#1a6a1a"),
            ("Swinging Strike", "w", "#1a6a1a"),
            ("Foul Ball",       "e", "#6a5a00"),
            ("Ball",            "r", "#6a1a1a"),
            ("In Play",         "t", "#1a3a6a"),
            ("Hard Hit",        "y", "#6a2a00"),
            ("Soft Hit",        "u", "#333355"),
        ]
        self._result_keys = {cfg[1]: cfg[0] for cfg in self._result_cfg}

        frame_right = ctk.CTkFrame(frame_middle, corner_radius=10)
        frame_right.grid(row=0, column=2, padx=(4,8), pady=6, sticky="ns")
        ctk.CTkLabel(frame_right, text="Výsledek",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaaa").pack(pady=(10,4))
        self.selected_pitch_result = tk.StringVar(value="Called Strike")
        self.pitch_result_buttons = {}
        for pr, key, clr in self._result_cfg:
            row_f = ctk.CTkFrame(frame_right, fg_color="transparent")
            row_f.pack(pady=2, padx=8, fill="x")
            ctk.CTkLabel(row_f, text=f"[{key.upper()}]", width=32, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#ffcc44").pack(side="left")
            btn = ctk.CTkButton(row_f, text=pr, width=134, height=30, corner_radius=7,
                                fg_color=clr if pr == "Called Strike" else "#2a2a2a",
                                hover_color=clr,
                                command=lambda r=pr: self.select_pitch_result(r))
            btn.pack(side="left")
            self.pitch_result_buttons[pr] = btn
        self._result_colors = {cfg[0]: cfg[2] for cfg in self._result_cfg}

        # ── Spodní lišta: datum + uložit ──
        bottom = ctk.CTkFrame(self.tab_zapis, fg_color="#111111", corner_radius=0)
        bottom.pack(fill="x", padx=0, pady=0)
        bc = ctk.CTkFrame(bottom, fg_color="transparent")
        bc.pack(anchor="center", pady=8)
        ctk.CTkLabel(bc, text="Datum:", text_color="#888888").pack(side="left", padx=(0,4))
        self.pitch_date = ctk.CTkEntry(bc, width=115, height=32, corner_radius=8)
        self.pitch_date.insert(0, date.today().isoformat())
        self.pitch_date.pack(side="left", padx=6)
        self.btn_save = ctk.CTkButton(bc, text="⬆  ULOŽIT NADHOZ", fg_color="#1a6a1a",
                                       hover_color="#22882a", width=200, height=34,
                                       corner_radius=8, font=ctk.CTkFont(weight="bold"),
                                       command=self.save_pitch)
        self.btn_save.pack(side="left", padx=10)

        # ── Mini-historie ──
        hist_header = ctk.CTkFrame(self.tab_zapis, fg_color="transparent")
        hist_header.pack(fill="x", padx=14, pady=(4,0))
        ctk.CTkLabel(hist_header, text="Poslední nadhozy",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color="#666666").pack(side="left")
        self.zapis_history_frame = ctk.CTkScrollableFrame(self.tab_zapis, height=80, corner_radius=8)
        self.zapis_history_frame.pack(fill="x", padx=14, pady=(2,8))

    # ==========================================
    # ŘÍZENÍ ZÁPASU
    # ==========================================
    def update_game_zapis_ui(self):
        """Aktualizuje UI záložky zápisu podle aktuálního stavu zápasu."""
        if not self.game_active:
            self.game_info_frame.pack_forget()
            self.game_controls_row1.pack_forget()
            self.game_controls_row2.pack_forget()
            self.manual_players_frame.pack(fill="x", padx=10, pady=5)
            return

        self.manual_players_frame.pack_forget()
        self.game_info_frame.pack(fill="x", padx=10, pady=4)
        self.game_controls_row1.pack(fill="x", padx=10, pady=2)
        self.game_controls_row2.pack(fill="x", padx=10, pady=2)

        # Aktuální soupiska (kdo pálí)
        if self.game_half == "away":
            lineup = self.away_lineup_order
            lineup_map = self.away_lineup_map
            batting_team = self.game_away_team
            fielding_team = self.game_home_team
        else:
            lineup = self.home_lineup_order
            lineup_map = self.home_lineup_map
            batting_team = self.game_home_team
            fielding_team = self.game_away_team

        # Inning info
        half_str = "hosté pálí" if self.game_half == "away" else "domácí pálí"
        self.game_info_label.configure(text=f"Inning {self.game_inning} | {half_str}")

        # Aktuální pálkař
        if self.game_batter_index < len(lineup):
            batter_display = lineup[self.game_batter_index]
            batter_name = batter_display.split("(")[0].strip()
            self.game_batter_label.configure(text=f"🏏 Pálkař: {batter_name}")
            batter_id = lineup_map.get(batter_display)
            self.current_game_batter_id = batter_id
            # Zjisti stranu pálkaře a překresli siluetu
            batter_data = database.get_player_by_id(batter_id) if batter_id else None
            if batter_data:
                bats = batter_data[6]  # sloupec bats
                hand = "L" if bats == "L" else "R"
                self.current_batter_hand = hand
                self.draw_batter_silhouette(hand)
        else:
            self.game_batter_label.configure(text="🏏 Konec soupisky")
            self.current_game_batter_id = None

        self.game_pitcher_label.configure(text=f"⚾ Nadhazovač: {self.game_pitcher_name}")

        # Nadhazovač – menu pro změnu (hráči fielding týmu)
        fielding_players, fielding_map = self.get_players_for_team(fielding_team)
        self.game_change_pitcher_map = fielding_map
        self.game_change_pitcher_menu.configure(values=fielding_players)
        if fielding_players:
            self.game_change_pitcher_menu.set(fielding_players[0])

    def game_skip_batter(self):
        """Přeskočí aktuálního pálkaře a přepne na dalšího."""
        if not self.game_active:
            return
        lineup = self.away_lineup_order if self.game_half == "away" else self.home_lineup_order
        if not lineup:
            return
        prev_idx = self.game_batter_index
        if self.game_batter_index < len(lineup) - 1:
            self.game_batter_index += 1
            msg = f"⏭  Přeskočen na dalšího pálkaře: {lineup[prev_idx].split('(')[0].strip()}"
        else:
            self.game_batter_index = 0
            msg = f"⏭  Přeskočen na prvního pálkaře: {lineup[0].split('(')[0].strip()}"
        if self.game_half == "away":
            self.away_batter_index = self.game_batter_index
        else:
            self.home_batter_index = self.game_batter_index
        self.pitch_x = None
        self.canvas.delete("pitch_mark")
        self._last_undo = {'type': 'skip', 'batter_index': prev_idx}
        self.show_toast(msg, undo_fn=self._undo_batter_index)
        self.update_game_zapis_ui()

    def game_finish_batter(self):
        """Ukončí aktuálního pálkaře a přejde na dalšího."""
        if not self.game_active:
            return
        lineup = self.away_lineup_order if self.game_half == "away" else self.home_lineup_order
        if not lineup:
            return
        prev_idx = self.game_batter_index
        if self.game_batter_index < len(lineup) - 1:
            self.game_batter_index += 1
        else:
            self.game_batter_index = 0
        if self.game_half == "away":
            self.away_batter_index = self.game_batter_index
        else:
            self.home_batter_index = self.game_batter_index
        self.pitch_x = None
        self.canvas.delete("pitch_mark")
        finished = lineup[prev_idx].split("(")[0].strip()
        self._last_undo = {'type': 'finish', 'batter_index': prev_idx}
        self.show_toast(f"✓  Hotovo: {finished}", undo_fn=self._undo_batter_index)
        self.update_game_zapis_ui()

    def game_next_inning(self):
        """Přepne half-inning – automaticky prohazuje nadhazovače."""
        if not self.game_active:
            return

        prev_inning = self.game_inning
        prev_half = self.game_half
        prev_batter_index = self.game_batter_index
        prev_pitcher_id = self.game_pitcher_id
        prev_pitcher_name = self.game_pitcher_name

        if self.game_half == "away":
            self.away_batter_index = self.game_batter_index
            self.game_half = "home"
            # Teď pálí domácí → nadhazuje hostující nadhazovač
            self.game_pitcher_id = getattr(self, 'game_away_pitcher_id', self.game_pitcher_id)
            self.game_pitcher_name = getattr(self, 'game_away_pitcher_name', self.game_pitcher_name)
            self.game_batter_index = self.home_batter_index
            half_str = "domácí pálí"
        else:
            self.home_batter_index = self.game_batter_index
            self.game_half = "away"
            self.game_inning += 1
            # Teď pálí hosté → nadhazuje domácí nadhazovač
            self.game_pitcher_id = getattr(self, 'game_home_pitcher_id', self.game_pitcher_id)
            self.game_pitcher_name = getattr(self, 'game_home_pitcher_name', self.game_pitcher_name)
            self.game_batter_index = self.away_batter_index
            half_str = "hosté pálí"

        self.pitch_x = None
        self.canvas.delete("pitch_mark")

        # Ulož stav pro undo
        self._last_undo = {
            'type': 'next_inning',
            'inning': prev_inning,
            'half': prev_half,
            'batter_index': prev_batter_index,
            'pitcher_id': prev_pitcher_id,
            'pitcher_name': prev_pitcher_name,
        }

        self.show_toast(f"⚾  Inning {self.game_inning} – {half_str}", undo_fn=self._undo_next_inning)
        self.update_game_zapis_ui()

    def game_change_pitcher(self):
        """Změní nadhazovače během zápasu a uloží změnu do DB."""
        if not self.game_active:
            return
        selected = self.game_change_pitcher_menu.get()
        pid = self.game_change_pitcher_map.get(selected)
        if pid:
            prev_pid = self.game_pitcher_id
            prev_name = self.game_pitcher_name
            self.game_pitcher_id = pid
            self.game_pitcher_name = selected.split("(")[0].strip()
            # Aktualizuj i uloženého nadhazovače pro daný half
            if self.game_half == "away":
                self.game_home_pitcher_id = pid
                self.game_home_pitcher_name = self.game_pitcher_name
            else:
                self.game_away_pitcher_id = pid
                self.game_away_pitcher_name = self.game_pitcher_name
            pitch_date = self.pitch_date.get().strip() or date.today().isoformat()
            database.log_pitcher_change(pid, self.game_inning, self.game_half, pitch_date)
            self._last_undo = {'type': 'pitcher', 'pitcher_id': prev_pid, 'pitcher_name': prev_name}
            self.show_toast(f"🔄  Nadhazovač: {self.game_pitcher_name}", undo_fn=self._undo_pitcher)
            self.update_game_zapis_ui()

    def game_end(self):
        """Ukončí zápas."""
        if messagebox.askyesno("Ukončit zápas", "Opravdu chceš ukončit zápas?"):
            self.game_active = False
            self.game_batter_index = 0
            self.game_inning = 1
            self.game_half = "away"
            self.update_game_zapis_ui()
            self.tabview.set("Zápas")

    def select_pitch_type(self, pitch_type):
        self.selected_pitch_type.set(pitch_type)
        colors = getattr(self, '_pitch_type_colors', {})
        for pt, btn in self.pitch_type_buttons.items():
            btn.configure(fg_color=colors.get(pt, "#1a4a8a") if pt == pitch_type else "#2a2a2a")

    def select_pitch_result(self, result):
        self.selected_pitch_result.set(result)
        colors = getattr(self, '_result_colors', {})
        for pr, btn in self.pitch_result_buttons.items():
            if pr == result:
                btn.configure(fg_color=colors.get(pr, "#1a6a1a"))
            else:
                btn.configure(fg_color="#2a2a2a")

    def build_edit_players_tab(self):
        # Rozdělení na dvě sekce vedle sebe
        both_frame = ctk.CTkFrame(self.tab_edit)
        both_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # LEVÁ ČÁST – editace existujícího hráče
        frame_edit = ctk.CTkFrame(both_frame)
        frame_edit.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame_edit, text="UPRAVIT HRÁČE", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=8)

        ctk.CTkLabel(frame_edit, text="Vyber hráče:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.edit_player_menu = ctk.CTkOptionMenu(frame_edit, values=[], command=self.on_edit_player_selected)
        self.edit_player_menu.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Jméno:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.edit_first_name = ctk.CTkEntry(frame_edit, width=160)
        self.edit_first_name.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Příjmení:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.edit_last_name = ctk.CTkEntry(frame_edit, width=160)
        self.edit_last_name.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Tým:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.edit_team = ctk.CTkEntry(frame_edit, width=160)
        self.edit_team.grid(row=4, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Číslo dresu:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.edit_jersey = ctk.CTkEntry(frame_edit, width=80)
        self.edit_jersey.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Háže:").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        self.edit_throws = ctk.CTkOptionMenu(frame_edit, values=["L", "R"])
        self.edit_throws.grid(row=6, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_edit, text="Pálí:").grid(row=7, column=0, padx=10, pady=8, sticky="w")
        self.edit_bats = ctk.CTkOptionMenu(frame_edit, values=["L", "R", "S"])
        self.edit_bats.grid(row=7, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkButton(frame_edit, text="ULOŽIT ZMĚNY", fg_color="blue", command=self.save_player_changes).grid(row=8, column=0, columnspan=2, pady=15, padx=10, sticky="ew")

        # PRAVÁ ČÁST – přidání nového hráče
        frame_new = ctk.CTkFrame(both_frame)
        frame_new.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame_new, text="PŘIDAT NOVÉHO HRÁČE", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=8)

        ctk.CTkLabel(frame_new, text="Jméno:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.new_first_name = ctk.CTkEntry(frame_new, width=160)
        self.new_first_name.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_new, text="Příjmení:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.new_last_name = ctk.CTkEntry(frame_new, width=160)
        self.new_last_name.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_new, text="Tým:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.new_team = ctk.CTkEntry(frame_new, width=160)
        self.new_team.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_new, text="Číslo dresu:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.new_jersey = ctk.CTkEntry(frame_new, width=80)
        self.new_jersey.grid(row=4, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_new, text="Háže:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.new_throws = ctk.CTkOptionMenu(frame_new, values=["L", "R"])
        self.new_throws.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_new, text="Pálí:").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        self.new_bats = ctk.CTkOptionMenu(frame_new, values=["L", "R", "S"])
        self.new_bats.grid(row=6, column=1, padx=10, pady=8, sticky="w")

        self.new_player_status = ctk.CTkLabel(frame_new, text="", text_color="green")
        self.new_player_status.grid(row=7, column=0, columnspan=2, pady=5)

        ctk.CTkButton(frame_new, text="➕ PŘIDAT HRÁČE", fg_color="green", command=self.add_new_player).grid(row=8, column=0, columnspan=2, pady=15, padx=10, sticky="ew")

        self.refresh_edit_player_menu()

    def add_new_player(self):
        first_name = self.new_first_name.get().strip()
        last_name = self.new_last_name.get().strip()
        team_name = self.new_team.get().strip()
        jersey = self.new_jersey.get().strip()
        throws = self.new_throws.get()
        bats = self.new_bats.get()

        if not first_name or not last_name or not team_name or not jersey:
            self.new_player_status.configure(text="❌ Vyplň všechna pole!", text_color="red")
            return
        try:
            jersey_number = int(jersey)
        except ValueError:
            self.new_player_status.configure(text="❌ Číslo dresu musí být číslo!", text_color="red")
            return

        database.insert_player(first_name, last_name, team_name, jersey_number, throws, bats)

        self.new_first_name.delete(0, tk.END)
        self.new_last_name.delete(0, tk.END)
        self.new_team.delete(0, tk.END)
        self.new_jersey.delete(0, tk.END)
        self.new_player_status.configure(text=f"✓ Hráč {first_name} {last_name} přidán!", text_color="green")

        self.load_players_from_db()
        self.refresh_all_player_lists()

        # Obnov i dropdown menu v záložce Zápas
        away_team = self.game_away_team_menu.get() if hasattr(self, 'game_away_team_menu') else None
        home_team = self.game_home_team_menu.get() if hasattr(self, 'game_home_team_menu') else None
        if hasattr(self, 'game_away_team_menu'):
            self.game_away_team_menu.configure(values=self.teams_only_list)
        if hasattr(self, 'game_home_team_menu'):
            self.game_home_team_menu.configure(values=self.teams_only_list)
        if away_team:
            self.on_away_team_selected(away_team)
        if home_team:
            self.on_home_team_selected(home_team)

    def build_recent_pitches_tab(self):
        self.recent_pitches_frame = ctk.CTkScrollableFrame(self.tab_recent)
        self.recent_pitches_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.update_recent_pitches()

    def build_staty_tab(self):
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

        self.chart_frame = ctk.CTkFrame(self.tab_staty)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas_widget = None

    # ==========================================
    # LOGIKA FUNKCÍ
    # ==========================================
    def draw_batter_silhouette(self, hand):
        """Nakreslí siluetu pálkaře v čekací pozici + nadhazovač v dálce."""
        self.canvas.delete("silhouette")

        # --- Nadhazovač na kopci v pozadí (vždy uprostřed, velmi jemný) ---
        px, py = 150, 62  # střed kopce
        dc = "#3a3a3a"
        # Kopec
        self.canvas.create_oval(px-38, py+16, px+38, py+34, fill=dc, outline=dc, tags="silhouette")
        # Tělo
        self.canvas.create_oval(px-5, py+4, px+5, py+16, fill=dc, outline=dc, tags="silhouette")
        # Hlava
        self.canvas.create_oval(px-4, py-4, px+4, py+4, fill=dc, outline=dc, tags="silhouette")
        # Ruka s míčem dopředu
        self.canvas.create_line(px, py+10, px-10, py+6, fill=dc, width=2, tags="silhouette")
        self.canvas.create_oval(px-13, py+3, px-7, py+9, fill=dc, outline=dc, tags="silhouette")
        # Zadní ruka
        self.canvas.create_line(px, py+10, px+8, py+8, fill=dc, width=2, tags="silhouette")
        # Nohy
        self.canvas.create_line(px-2, py+16, px-5, py+26, fill=dc, width=2, tags="silhouette")
        self.canvas.create_line(px+2, py+16, px+5, py+26, fill=dc, width=2, tags="silhouette")

        # --- Pálkař ---
        if hand == "R":
            # Pravák – stojí vpravo od zóny, čelí doleva
            bx, by = 252, 105  # střed hrudníku
            # Hlava
            self.canvas.create_oval(bx-12, by-27, bx+12, by-1, fill="#555", outline="#555", tags="silhouette")
            # Přilba + kšilt doleva
            self.canvas.create_polygon(bx-12, by-22, bx+12, by-22, bx+10, by-30, bx-10, by-30,
                                       fill="#666", outline="#666", tags="silhouette")
            self.canvas.create_line(bx-12, by-20, bx-22, by-16, fill="#666", width=3,
                                    capstyle="round", tags="silhouette")
            # Krk
            self.canvas.create_line(bx, by-1, bx, by+10, fill="#555", width=5, tags="silhouette")
            # Trup
            self.canvas.create_polygon(bx-15, by+10, bx+15, by+10, bx+12, by+70, bx-12, by+70,
                                       fill="#555", outline="#555", tags="silhouette")
            # Zadní paže (pravá) – zvednutá ke gripu
            self.canvas.create_line(bx+15, by+25, bx+24, by+18, fill="#555", width=7,
                                    capstyle="round", tags="silhouette")
            # Přední paže (levá) – ke gripu
            self.canvas.create_line(bx-15, by+25, bx+22, by+15, fill="#555", width=5,
                                    capstyle="round", tags="silhouette")
            # Grip
            self.canvas.create_oval(bx+19, by+10, bx+31, by+20, fill="#666", outline="#666", tags="silhouette")
            # Pálka – svisle nahoru nad ramenem
            self.canvas.create_line(bx+25, by+12, bx+28, by-52, fill="#888", width=5,
                                    capstyle="round", tags="silhouette")
            self.canvas.create_oval(bx+23, by+12, bx+31, by+20, fill="#777", outline="#777", tags="silhouette")
            self.canvas.create_oval(bx+24, by-60, bx+32, by-46, fill="#888", outline="#888", tags="silhouette")
            # Přední noha
            self.canvas.create_line(bx-10, by+70, bx-16, by+118, fill="#555", width=8,
                                    capstyle="round", tags="silhouette")
            self.canvas.create_line(bx-16, by+118, bx-24, by+120, fill="#555", width=6,
                                    capstyle="round", tags="silhouette")
            # Zadní noha
            self.canvas.create_line(bx+10, by+70, bx+14, by+118, fill="#555", width=8,
                                    capstyle="round", tags="silhouette")
            self.canvas.create_line(bx+14, by+118, bx+22, by+120, fill="#555", width=6,
                                    capstyle="round", tags="silhouette")
        else:
            # Levák – stojí vlevo od zóny, čelí doprava
            bx, by = 48, 105
            # Hlava
            self.canvas.create_oval(bx-12, by-27, bx+12, by-1, fill="#555", outline="#555", tags="silhouette")
            # Přilba + kšilt doprava
            self.canvas.create_polygon(bx-12, by-22, bx+12, by-22, bx+10, by-30, bx-10, by-30,
                                       fill="#666", outline="#666", tags="silhouette")
            self.canvas.create_line(bx+12, by-20, bx+22, by-16, fill="#666", width=3,
                                    capstyle="round", tags="silhouette")
            # Krk
            self.canvas.create_line(bx, by-1, bx, by+10, fill="#555", width=5, tags="silhouette")
            # Trup
            self.canvas.create_polygon(bx-15, by+10, bx+15, by+10, bx+12, by+70, bx-12, by+70,
                                       fill="#555", outline="#555", tags="silhouette")
            # Zadní paže (levá)
            self.canvas.create_line(bx-15, by+25, bx-24, by+18, fill="#555", width=7,
                                    capstyle="round", tags="silhouette")
            # Přední paže (pravá)
            self.canvas.create_line(bx+15, by+25, bx-22, by+15, fill="#555", width=5,
                                    capstyle="round", tags="silhouette")
            # Grip
            self.canvas.create_oval(bx-31, by+10, bx-19, by+20, fill="#666", outline="#666", tags="silhouette")
            # Pálka svisle nahoru
            self.canvas.create_line(bx-25, by+12, bx-28, by-52, fill="#888", width=5,
                                    capstyle="round", tags="silhouette")
            self.canvas.create_oval(bx-31, by+12, bx-23, by+20, fill="#777", outline="#777", tags="silhouette")
            self.canvas.create_oval(bx-32, by-60, bx-24, by-46, fill="#888", outline="#888", tags="silhouette")
            # Přední noha
            self.canvas.create_line(bx+10, by+70, bx+16, by+118, fill="#555", width=8,
                                    capstyle="round", tags="silhouette")
            self.canvas.create_line(bx+16, by+118, bx+24, by+120, fill="#555", width=6,
                                    capstyle="round", tags="silhouette")
            # Zadní noha
            self.canvas.create_line(bx-10, by+70, bx-14, by+118, fill="#555", width=8,
                                    capstyle="round", tags="silhouette")
            self.canvas.create_line(bx-14, by+118, bx-22, by+120, fill="#555", width=6,
                                    capstyle="round", tags="silhouette")

        # Překresli zónu a značku přes siluetu
        self.canvas.tag_raise("zone")
        self.canvas.tag_raise("pitch_mark")

    # ==========================================
    # TOAST NOTIFIKACE
    # ==========================================
    def show_toast(self, message, undo_fn=None, duration=4000):
        """Zobrazí dočasnou notifikaci dole s volitelným tlačítkem Zpět."""
        if getattr(self, '_toast_frame', None) is not None and self._toast_frame.winfo_exists():
            self._toast_frame.destroy()
        if getattr(self, '_toast_after', None) is not None:
            self.root.after_cancel(self._toast_after)

        self._toast_frame = ctk.CTkFrame(self.root, fg_color="#1a1a2e", corner_radius=10,
                                          border_width=1, border_color="#333355")
        self._toast_frame.place(relx=0.5, rely=0.97, anchor="s")

        ctk.CTkLabel(self._toast_frame, text=message,
                     font=ctk.CTkFont(size=12), text_color="#dddddd").pack(side="left", padx=14, pady=8)

        if undo_fn:
            ctk.CTkButton(self._toast_frame, text="↩ Zpět", width=70, height=26,
                          fg_color="#333355", hover_color="#444477", corner_radius=6,
                          command=lambda: self._do_undo(undo_fn)).pack(side="left", padx=(0,10), pady=8)

        def hide():
            if getattr(self, '_toast_frame', None) is not None and self._toast_frame.winfo_exists():
                self._toast_frame.destroy()
        self._toast_after = self.root.after(duration, hide)

    def _do_undo(self, undo_fn):
        if getattr(self, '_toast_frame', None) is not None and self._toast_frame.winfo_exists():
            self._toast_frame.destroy()
        undo_fn()

    def _undo_batter_index(self):
        if not self._last_undo:
            return
        self.game_batter_index = self._last_undo.get('batter_index', self.game_batter_index)
        self.show_toast("↩  Vráceno zpět")
        self.update_game_zapis_ui()

    def _undo_next_inning(self):
        if not self._last_undo:
            return
        d = self._last_undo
        self.game_inning = d.get('inning', self.game_inning)
        self.game_half = d.get('half', self.game_half)
        self.game_batter_index = d.get('batter_index', 0)
        self.game_pitcher_id = d.get('pitcher_id', self.game_pitcher_id)
        self.game_pitcher_name = d.get('pitcher_name', self.game_pitcher_name)
        if self.game_half == "away":
            self.game_home_pitcher_id = self.game_pitcher_id
            self.game_home_pitcher_name = self.game_pitcher_name
        else:
            self.game_away_pitcher_id = self.game_pitcher_id
            self.game_away_pitcher_name = self.game_pitcher_name
        self.show_toast("↩  Inning vrácen zpět")
        self.update_game_zapis_ui()

    def _undo_pitcher(self):
        if not self._last_undo:
            return
        d = self._last_undo
        self.game_pitcher_id = d.get('pitcher_id', self.game_pitcher_id)
        self.game_pitcher_name = d.get('pitcher_name', self.game_pitcher_name)
        if self.game_half == "away":
            self.game_home_pitcher_id = self.game_pitcher_id
            self.game_home_pitcher_name = self.game_pitcher_name
        else:
            self.game_away_pitcher_id = self.game_pitcher_id
            self.game_away_pitcher_name = self.game_pitcher_name
        self.show_toast("↩  Nadhazovač vrácen")
        self.update_game_zapis_ui()

    def on_canvas_click(self, event):
        self.canvas.delete("pitch_mark")
        self.pitch_x, self.pitch_y = event.x, event.y
        r = 8
        self.canvas.create_oval(self.pitch_x - r, self.pitch_y - r,
                                self.pitch_x + r, self.pitch_y + r,
                                fill="red", outline="white", width=2, tags="pitch_mark")
        self.canvas.tag_raise("pitch_mark")
        # Zobraz 2s pak ulož a smaž
        self.root.after(2000, self._auto_save_and_clear)

    def _auto_save_and_clear(self):
        self.save_pitch()

    def setup_keybindings(self):
        """Nastaví všechny klávesové zkratky."""
        # Typ nadhozu – číslice 1-7
        pitch_keysyms = {
            "1": "Four-Seam Fastball",
            "2": "Two-Seam Fastball",
            "3": "Curveball",
            "4": "Changeup",
            "5": "Splitter",
            "6": "Slider",
            "7": "Knuckleball",
        }
        for keysym, pt in pitch_keysyms.items():
            self.root.bind(keysym, lambda e, p=pt: self.select_pitch_type(p))
            self.root.bind(keysym.upper(), lambda e, p=pt: self.select_pitch_type(p))
        # Výsledek: q w e r t y u
        for key, pr in self._result_keys.items():
            self.root.bind(key, lambda e, r=pr: self.select_pitch_result(r))
            self.root.bind(key.upper(), lambda e, r=pr: self.select_pitch_result(r))
        # Ball mimo zónu: B
        self.root.bind("b", lambda e: self.set_ball())
        self.root.bind("B", lambda e: self.set_ball())
        # Herní zkratky
        self.root.bind("s", lambda e: self.game_skip_batter() if self.game_active else None)
        self.root.bind("S", lambda e: self.game_skip_batter() if self.game_active else None)
        self.root.bind("n", lambda e: self.game_finish_batter() if self.game_active else None)
        self.root.bind("N", lambda e: self.game_finish_batter() if self.game_active else None)
        self.root.bind("i", lambda e: self.game_next_inning() if self.game_active else None)
        self.root.bind("I", lambda e: self.game_next_inning() if self.game_active else None)
        # Undo posledního nadhozu: Ctrl+Z
        self.root.bind("<Control-z>", lambda e: self.undo_last_pitch())

    def set_ball(self):
        self.canvas.delete("pitch_mark")
        self.pitch_x, self.pitch_y = "Mimo", "Mimo"
        self.select_pitch_result("Ball")

    def save_pitch(self):
        if self.pitch_x is None:
            return

        if self.game_active:
            p_id = self.game_pitcher_id
            b_id = self.current_game_batter_id
        else:
            p_id = self.pitcher_player_map.get(self.pitcher_menu.get())
            b_id = self.batter_player_map.get(self.batter_menu.get())

        pitch_date = self.pitch_date.get().strip() or date.today().isoformat()

        if p_id and b_id:
            database.insert_pitch(p_id, b_id, self.selected_pitch_type.get(), self.selected_pitch_result.get(), str(self.pitch_x), str(self.pitch_y), pitch_date)

        self.canvas.delete("pitch_mark")
        self.pitch_x = None

        if p_id and b_id:
            self.update_recent_pitches()
            self.update_zapis_history()
            pt = self.selected_pitch_type.get()
            pr = self.selected_pitch_result.get()
            self.show_toast(f"💾  {pt}  ·  {pr}  –  Ctrl+Z pro vrácení",
                           undo_fn=self.undo_last_pitch, duration=5000)

    def draw_charts(self):
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

        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()

        if df.empty:
            print("Žádná data pro tento výběr.")
            return

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
        fig.patch.set_facecolor('#2b2b2b')

        df_plot = df[(df['x_location'] != 'Mimo') & (df['y_location'] != 'Mimo')].copy()
        if not df_plot.empty:
            df_plot['x_location'] = pd.to_numeric(df_plot['x_location'])
            df_plot['y_location'] = pd.to_numeric(df_plot['y_location'])
            sns.scatterplot(data=df_plot, x='x_location', y='y_location', hue='pitch_type', s=100, ax=ax1, palette="bright")
            import matplotlib.patches as patches
            ax1.add_patch(patches.Rectangle((85, 60), 130, 170, linewidth=2, edgecolor='white', facecolor='none', linestyle='--'))
            ax1.set_xlim(0, 300)
            ax1.set_ylim(300, 0)

        ax1.set_title("Lokace ve strike zóně", color="white")
        ax1.tick_params(colors='white')
        ax1.xaxis.label.set_color('white')
        ax1.yaxis.label.set_color('white')

        pitch_counts = df['pitch_type'].value_counts()
        pitch_counts.plot(kind='bar', ax=ax2, color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'])
        ax2.set_title("Četnost typů nadhozů", color="white")
        ax2.tick_params(colors='white', rotation=45)

        result_counts = df['pitch_result'].value_counts()
        result_counts.plot(kind='bar', ax=ax3, color=['#ff6666', '#66ff66', '#6666ff', '#ffcc99', '#99ff99', '#ff9999', '#66b3ff'])
        ax3.set_title("Četnost výsledků nadhozů", color="white")
        ax3.tick_params(colors='white', rotation=45)

        fig.tight_layout()

        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill="both", expand=True)

    def update_recent_pitches(self):
        for widget in self.recent_pitches_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.recent_pitches_frame, text="Poslední nadhozy:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        pitches = database.get_recent_pitches(5)
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

    def update_zapis_history(self):
        """Aktualizuje mini-historii nadhozů v záložce zápisu."""
        if not hasattr(self, 'zapis_history_frame'):
            return
        for w in self.zapis_history_frame.winfo_children():
            w.destroy()
        pitches = database.get_recent_pitches(5)
        if not pitches:
            ctk.CTkLabel(self.zapis_history_frame, text="Žádné nadhozy zatím.", text_color="gray").pack(anchor="w", padx=5)
            return
        for pitch in pitches:
            pitch_id, date_time, pitcher_id, batter_id, pitch_type, pitch_result, x_loc, y_loc, pitcher_name, batter_name = pitch
            loc = f"({x_loc},{y_loc})" if x_loc != "Mimo" else "Mimo"
            color = "#1a5a1a" if "Strike" in pitch_result else ("#7a1a1a" if pitch_result == "Ball" else "#1a3a7a")
            row = ctk.CTkFrame(self.zapis_history_frame, fg_color=color, corner_radius=4)
            row.pack(fill="x", pady=1, padx=2)
            ctk.CTkLabel(row, text=f"{batter_name}  •  {pitch_type}  •  {pitch_result}  {loc}",
                         font=ctk.CTkFont(size=11)).pack(side="left", padx=8, pady=2)

    def undo_last_pitch(self):
        """Smaže poslední uložený nadhoz (Ctrl+Z)."""
        pitches = database.get_recent_pitches(1)
        if not pitches:
            self.show_toast("⚠  Žádný nadhoz ke vrácení")
            return
        pitch_id = pitches[0][0]
        database.delete_pitch(pitch_id)
        self.update_recent_pitches()
        self.update_zapis_history()
        self.show_toast("↩  Poslední nadhoz smazán")

    def delete_pitch(self, pitch_id):
        database.delete_pitch(pitch_id)
        self.update_recent_pitches()
        self.update_zapis_history()


if __name__ == "__main__":
    root = ctk.CTk()
    app = BaseballTrackerModern(root)
    root.mainloop()
