# PS C:\Users\LENOVO\Desktop\ParentalCare_v2> .venv1\Scripts\activate
# (.venv1) PS C:\Users\LENOVO\Desktop\ParentalCare_v2> python Gui_test2.py

import customtkinter as ctk

# Connecting to Brain
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, Settings


# ======================
# THEME CONFIG
# ======================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Color Palette
CARBON_BLACK = "#1e2019"
GUNMETAL = "#393e41"
DUST_GREY = "#d3d0cb"
OLD_GOLD = "#e2c044"
PINE_BLUE = "#587b7f"


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        # DB
        self.Session = sessionmaker(bind=engine)

        # Window
        self.title("ParentalCare+ Dashboard")
        self.geometry("1000x600")
        self.configure(fg_color=CARBON_BLACK)

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ======================
        # SIDEBAR
        # ======================
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=GUNMETAL
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ParentalCare+",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=OLD_GOLD
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=30)

        self.btn_dashboard = ctk.CTkButton(
            self.sidebar_frame,
            text="Dashboard",
            height=42,
            corner_radius=10,
            fg_color="transparent",
            text_color=DUST_GREY,
            hover_color=PINE_BLUE,
            command=lambda: self.select_frame("dashboard")
        )
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame,
            text="Settings",
            height=42,
            corner_radius=10,
            fg_color="transparent",
            text_color=DUST_GREY,
            hover_color=PINE_BLUE,
            command=lambda: self.select_frame("settings")
        )
        self.btn_settings.grid(row=2, column=0, padx=20, pady=10)

        # ======================
        # MAIN AREA
        # ======================
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=CARBON_BLACK,
            corner_radius=0
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        # Header
        self.header_frame = ctk.CTkFrame(
            self.main_frame,
            height=70,
            fg_color=GUNMETAL,
            corner_radius=0
        )
        self.header_frame.pack(fill="x")

        self.header_label = ctk.CTkLabel(
            self.header_frame,
            text="Dashboard Overview",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=DUST_GREY
        )
        self.header_label.pack(side="left", padx=30)

        # ======================
        # DASHBOARD
        # ======================
        self.dashboard_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=GUNMETAL,
            corner_radius=18
        )

        self.status_card = ctk.CTkFrame(
            self.dashboard_frame,
            fg_color=CARBON_BLACK,
            corner_radius=16
        )
        self.status_card.pack(pady=80, padx=80, fill="x")

        self.status_title = ctk.CTkLabel(
            self.status_card,
            text="SYSTEM STATUS",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PINE_BLUE
        )
        self.status_title.pack(pady=(25, 5))

        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="Initializing...",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=DUST_GREY
        )
        self.status_label.pack(pady=(0, 30))

        # ======================
        # SETTINGS
        # ======================
        self.settings_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=GUNMETAL,
            corner_radius=18
        )

        self.lbl_sett = ctk.CTkLabel(
            self.settings_frame,
            text="Security Configuration",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        self.lbl_sett.pack(pady=(40, 5))

        self.settings_subtitle = ctk.CTkLabel(
            self.settings_frame,
            text="Manage parental control features",
            font=ctk.CTkFont(size=14),
            text_color=PINE_BLUE
        )
        self.settings_subtitle.pack(pady=(0, 20))

        self.divider = ctk.CTkFrame(
            self.settings_frame,
            height=1,
            fg_color=PINE_BLUE
        )
        self.divider.pack(fill="x", padx=60, pady=10)

        self.var_app_blocker = ctk.StringVar(value="on")
        self.var_web_blocker = ctk.StringVar(value="on")

        self.switch_container = ctk.CTkFrame(
            self.settings_frame,
            fg_color="transparent"
        )
        self.switch_container.pack(pady=20)

        self.sw_app = ctk.CTkSwitch(
            self.switch_container,
            text="Enable App Blocker",
            text_color=DUST_GREY,
            progress_color=OLD_GOLD,
            button_color=PINE_BLUE,
            variable=self.var_app_blocker,
            onvalue="on",
            offvalue="off",
            command=self.save_settings
        )
        self.sw_app.pack(pady=12)

        self.sw_web = ctk.CTkSwitch(
            self.switch_container,
            text="Enable Web Blocker",
            text_color=DUST_GREY,
            progress_color=OLD_GOLD,
            button_color=PINE_BLUE,
            variable=self.var_web_blocker,
            onvalue="on",
            offvalue="off",
            command=self.save_settings
        )
        self.sw_web.pack(pady=12)

        # Startup
        self.load_settings()
        self.select_frame("dashboard")
        self.update_status()

    # ======================
    # NAVIGATION
    # ======================
    def select_frame(self, name):
        self.btn_dashboard.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_settings.configure(fg_color="transparent", text_color=DUST_GREY)

        self.dashboard_frame.pack_forget()
        self.settings_frame.pack_forget()

        if name == "dashboard":
            self.header_label.configure(text="Dashboard Overview")
            self.dashboard_frame.pack(fill="both", expand=True, padx=20, pady=20)
            self.btn_dashboard.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
        else:
            self.header_label.configure(text="Settings")
            self.settings_frame.pack(fill="both", expand=True, padx=20, pady=20)
            self.btn_settings.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)

    # ======================
    # DB LOGIC
    # ======================
    def load_settings(self):
        session = self.Session()
        try:
            app = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            web = session.query(Settings).filter_by(key="web_blocker_enabled").first()
            if app:
                self.var_app_blocker.set("on" if app.value == "true" else "off")
            if web:
                self.var_web_blocker.set("on" if web.value == "true" else "off")
        finally:
            session.close()

    def save_settings(self):
        session = self.Session()
        try:
            val_app = "true" if self.var_app_blocker.get() == "on" else "false"
            val_web = "true" if self.var_web_blocker.get() == "on" else "false"

            session.query(Settings).filter_by(key="app_blocker_enabled").first().value = val_app
            session.query(Settings).filter_by(key="web_blocker_enabled").first().value = val_web
            session.commit()
        finally:
            session.close()

    def update_status(self):
        session = self.Session()
        try:
            app = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            web = session.query(Settings).filter_by(key="web_blocker_enabled").first()

            app_on = app and app.value == "true"
            web_on = web and web.value == "true"

            if app_on and web_on:
                self.status_label.configure(text="ACTIVE", text_color=OLD_GOLD)
            elif app_on or web_on:
                self.status_label.configure(text="PARTIALLY ACTIVE", text_color=PINE_BLUE)
            else:
                self.status_label.configure(text="DISABLED", text_color="red")
        finally:
            session.close()

        self.after(2000, self.update_status)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
