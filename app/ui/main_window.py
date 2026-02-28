
# PS C:\Users\LENOVO\Desktop\ParentalCare_v2> .venv1\Scripts\activate
# (.venv1) PS C:\Users\LENOVO\Desktop\ParentalCare_v2> python -m app.ui.main_window


# FILE: app/ui/main_window.py
# Phase 3 Step 1: The Graphical User Interface (View Layer)

import sys
import customtkinter as ctk
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, Settings, get_app_usage_state
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.utils.research_logger import ResearchLogger



# THEME CONFIGURATION

# Sets the theme to Dark Mode
# Cybersecurity aesthetic
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Professional Color Palette
CARBON_BLACK = "#1e2019"  # Background
GUNMETAL = "#393e41"  # Sidebar/Cards
DUST_GREY = "#d3d0cb"  # Text
OLD_GOLD = "#e2c044"  # Accents/Active State
PINE_BLUE = "#587b7f"  # Secondary Accents


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Kill Switch
        self.running = True
        self.status_job = None
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 1. Database Connection
        # We create a private session factory for the UI thread
        self.Session = sessionmaker(bind=engine)
        self.research = ResearchLogger

        # 2. Window Setup
        self.title("ParentalCare+ Dashboard")
        self.geometry("1000x600")
        self.configure(fg_color=CARBON_BLACK)

        # 3. Grid Layout (2 Columns: Sidebar + Content)
        self.grid_columnconfigure(1, weight=1)  # Column 1 expands
        self.grid_rowconfigure(0, weight=1)  # Row 0 expands

        # 4. Initialize Components
        self._setup_sidebar()
        self._setup_dashboard_frame()
        self._setup_settings_frame()
        self._setup_stats_frame()

        # 5. Start Polling (The Heartbeat)
        self.load_settings_from_db()
        self.start_monitoring_loop()

        # Show Dashboard by default
        self.select_frame("dashboard")

    def _setup_sidebar(self):
        """Creates the left navigation panel"""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=GUNMETAL)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        # App Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ParentalCare+",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=OLD_GOLD
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=30)

        # Navigation Buttons
        self.btn_dashboard = self._create_nav_button("Dashboard", "dashboard", 1)
        self.btn_settings = self._create_nav_button("Settings", "settings", 2)
        self.btn_stats = self._create_nav_button("Analytics", "stats", 3)

    def _create_nav_button(self, text, value, row):
        """Helper to create consistent sidebar buttons"""
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            height=42,
            corner_radius=12,
            fg_color="transparent",
            text_color=DUST_GREY,
            hover_color="#4a5054",
            border_width=1,
            border_color="#2a2d2f",
            command=lambda: self.select_frame(value)
        )
        btn.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        return btn

    def _setup_dashboard_frame(self):
        """Creates the Main Overview Page"""
        self.dashboard_frame = ctk.CTkFrame(self, fg_color=CARBON_BLACK, corner_radius=0)

        # Header
        self.header_label = ctk.CTkLabel(
            self.dashboard_frame,
            text="System Overview",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        self.header_label.pack(pady=20, padx=30, anchor="w")

        # Status Card (Visual Indicator of System Health)
        self.status_card = ctk.CTkFrame(
            self.dashboard_frame,
            fg_color=GUNMETAL,
            corner_radius=20,
            border_width=1,
            border_color="#2a2d2f"
        )
        self.status_card.pack(pady=10, padx=30, fill="x")

        self.status_title = ctk.CTkLabel(
            self.status_card, text="PROTECTION STATUS",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=PINE_BLUE
        )
        self.status_title.pack(pady=(15, 0))

        self.status_indicator = ctk.CTkLabel(
            self.status_card, text="INITIALIZING...",
            font=ctk.CTkFont(size=28, weight="bold"), text_color=DUST_GREY
        )
        self.status_indicator.pack(pady=(5, 15))

    def _setup_stats_frame(self):
        self.stats_frame = ctk.CTkFrame(self, fg_color=CARBON_BLACK)

        # Page Title
        label = ctk.CTkLabel(
            self.stats_frame,
            text="Real-Time Analytics",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        # =======================
        # ✅ NEW: Card Container (Styled Like Settings Page)
        # =======================
        self.stats_card = ctk.CTkFrame(
            self.stats_frame,
            fg_color=GUNMETAL,
            corner_radius=20,
            border_width=1,
            border_color="#2a2d2f"
        )
        self.stats_card.pack(pady=20, padx=30, fill="both", expand=True)

        # =======================
        # ✅ NEW: Inner padding frame
        # =======================
        self.chart_frame = ctk.CTkFrame(
            self.stats_card,
            fg_color=GUNMETAL
        )
        self.chart_frame.pack(padx=25, pady=25, fill="both", expand=True)

        # =======================
        # Matplotlib Setup
        # =======================
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)

        # ✅ CHANGED: Background now matches card
        self.fig.patch.set_facecolor(GUNMETAL)
        self.ax.set_facecolor(GUNMETAL)

        # ✅ NEW: Remove extra borders for modern look
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)

        # ✅ NEW: Theme-colored axes
        self.ax.spines["bottom"].set_color(DUST_GREY)
        self.ax.spines["left"].set_color(DUST_GREY)

        # ✅ NEW: Themed tick colors
        self.ax.tick_params(axis="x", colors=DUST_GREY)
        self.ax.tick_params(axis="y", colors=DUST_GREY)

        # ✅ NEW: Subtle grid for premium look
        self.ax.grid(alpha=0.15)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.update_chart()

    def _setup_settings_frame(self):
        """Creates the Settings Page with Toggles"""
        self.settings_frame = ctk.CTkFrame(self, fg_color=CARBON_BLACK, corner_radius=0)

        label = ctk.CTkLabel(
            self.settings_frame, text="Configuration",
            font = ctk.CTkFont(size=24, weight="bold"), text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        # Switches Container
        self.switches_container = ctk.CTkFrame(self.settings_frame, fg_color=GUNMETAL, corner_radius=15)
        self.switches_container.pack(pady=10, padx=30, fill="both", expand=True)

        # Variables to track switch state
        self.var_app_blocker = ctk.StringVar(value="on")
        self.var_web_blocker = ctk.StringVar(value="on")

        # Switch 1: App Blocker
        self.sw_app = ctk.CTkSwitch(
            self.switches_container,
            text="Enable Application Blocker",
            variable=self.var_app_blocker,
            onvalue="on", offvalue="off",
            progress_color=OLD_GOLD,
            command=self.save_settings_to_db
        )
        self.sw_app.pack(pady=20, padx=20, anchor="w")

        # Switch 2: Web Blocker
        self.sw_web = ctk.CTkSwitch(
            self.switches_container,
            text="Enable Web Filter (DNS)",
            variable=self.var_web_blocker,
            onvalue="on", offvalue="off",
            progress_color=OLD_GOLD,
            command=self.save_settings_to_db
        )
        self.sw_web.pack(pady=20, padx=20, anchor="w")


    def select_frame(self, name):
        """Logic to switch between pages"""
        # Reset button colors
        self.btn_dashboard.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_settings.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_stats.configure(fg_color="transparent", text_color=DUST_GREY)

        # Hide all frames
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.stats_frame.grid_forget()

        # Show selected frame and highlight button
        if name == "dashboard":
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_dashboard.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
        elif name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_settings.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
        elif name == "stats":
            self.stats_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_stats.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)

    def load_settings_from_db(self):
        """Reads initial state from database"""
        session = self.Session()
        try:
            app_setting = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            web_setting = session.query(Settings).filter_by(key="web_blocker_enabled").first()

            if app_setting:
                self.var_app_blocker.set("on" if app_setting.value == "true" else "off")
            if web_setting:
                self.var_web_blocker.set("on" if web_setting.value == "true" else "off")
        except Exception as e:
            print(f"UI Load Error: {e}")
        finally:
            session.close()

    def save_settings_to_db(self):
        """Writes switch state to database"""
        session = self.Session()
        try:
            app_val = "true" if self.var_app_blocker.get() == "on" else "false"
            web_val = "true" if self.var_web_blocker.get() == "on" else "false"

            # Update DB
            session.query(Settings).filter_by(key="app_blocker_enabled").update({"value": app_val})
            session.query(Settings).filter_by(key="web_blocker_enabled").update({"value": web_val})
            session.commit()
            print(f"⚙️ Settings Updated: App={app_val}, Web={web_val}")

            # Immediately update status indicator
            self.refresh_ui()

        except Exception as e:
            print(f"UI Save Error: {e}")
        finally:
            session.close()

    def refresh_ui(self):
        """Updates the status card text based on settings"""
        if not self.running:
            return

        app_on = self.var_app_blocker.get() == "on"
        web_on = self.var_web_blocker.get() == "on"

        if app_on and web_on:
            self.status_indicator.configure(text="SYSTEM ACTIVE", text_color=OLD_GOLD, font=ctk.CTkFont(size=30, weight="bold"))
        elif not app_on and not web_on:
            self.status_indicator.configure(text="SYSTEM DISABLED", text_color="red", font=ctk.CTkFont(size=30, weight="bold"))
        else:
            self.status_indicator.configure(text="PARTIALLY ACTIVE", text_color=PINE_BLUE, font=ctk.CTkFont(size=30, weight="bold"))

        if hasattr(self, "ax"):
            self.update_chart()
        # Schedule this function to run again in 2 seconds (Polling)
        # This ensures if the database changes externally, the UI updates
        # self.status_job = self.after(2000, self.update_system_status)

    def start_monitoring_loop(self):
        """The heartbeat that runs every 2 seconds"""
        if not self.running:
            return

        self.refresh_ui()

        # Schedule next run - This is the ONLY place self.after should exist
        self.status_job = self.after(2000, self.start_monitoring_loop)

    def update_chart(self):

        if not hasattr(self, "ax"):
            return

        data = get_app_usage_state(limit=5)

        self.ax.clear()

        # ✅ Ensure background remains styled after clear
        self.ax.set_facecolor(GUNMETAL)
        self.fig.patch.set_facecolor(GUNMETAL)

        # ✅ Modern axis styling again after clear
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["bottom"].set_color(DUST_GREY)
        self.ax.spines["left"].set_color(DUST_GREY)
        self.ax.tick_params(axis="x", colors=DUST_GREY, rotation=15)
        self.ax.tick_params(axis="y", colors=DUST_GREY)

        # ✅ Subtle grid (premium dashboard style)
        self.ax.grid(alpha=0.15)

        if not data:
            self.ax.set_title("No Usage Data Available", color=DUST_GREY)
            self.canvas.draw()
            return

        names = [item["name"] for item in data]
        values = [item["seconds"] / 60 for item in data]

        # ✅ UPDATED: Slightly thicker bars for better visual weight
        self.ax.bar(
            names,
            values,
            color=OLD_GOLD,
            width=0.55,
            edgecolor="#c9a636",
            linewidth=1.2
        )
        self.ax.set_ylabel("Minutes", color=DUST_GREY)
        self.ax.set_xlabel("App Names", color=DUST_GREY)

        # ✅ UPDATED: Styled title
        self.ax.set_title(
            "Top 5 Applications (Minutes Used)",
            color=DUST_GREY,
            fontsize=12,
            pad=15
        )

        self.canvas.draw()

    def on_close(self):
        self.running = False

        if self.status_job is not None:
            try:
                self.after_cancel(self.status_job)
            except :
                pass

        # self.quit()
        # self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()


