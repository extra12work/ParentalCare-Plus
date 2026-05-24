# ParentalCare+ Module: negotiation_dialog.py
# Phase 4: The Negotiation Protocol (Child-Facing UI)

import sys
import os
import customtkinter as ctk
from app.models.database import NegotiationRequest, engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.controllers.telegram_service import TelegramAlertService

# THEME CONFIGURATION
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

CARBON_BLACK = "#1e2019"
GUNMETAL = "#393e41"
DUST_GREY = "#d3d0cb"
OLD_GOLD = "#e2c044"
PINE_BLUE = "#587b7f"


class NegotiationDialog(ctk.CTk):
    def __init__(self, target_name, target_type="app"):
        super().__init__()

        self.app_name = target_name
        self.target_type = target_type

        # Window Setup
        self.title("ParentalCare+ Notification")
        window_width = 450
        window_height = 320
        self.configure(fg_color=CARBON_BLACK)

        # Forces the window to stay on top
        self.attributes("-topmost", True)
        self.focus_force()

        # Center the window on the screen dynamically
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 1.5) - (window_width / 1.5))
        y = int((screen_height / 3) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Alert Header
        header_text = " ⚠️ Website Blocked " if self.target_type == "web" else " ⚠️ Application Blocked "

        self.warning_label = ctk.CTkLabel(
            self,
            text=header_text,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=OLD_GOLD
        )
        self.warning_label.pack(pady=(20, 5))

        self.blocked_app_label = ctk.CTkLabel(
            self,
            text=f"{self.app_name} is restricted.",
            font=ctk.CTkFont(size=16),
            text_color=DUST_GREY
        )
        self.blocked_app_label.pack(pady=(0, 20))

        # Input and Submit Area
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(padx=30, fill="x")

        self.reason_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Reason (e.g., school assignment) ",
            text_color=DUST_GREY,
            fg_color=GUNMETAL,
            border_color=PINE_BLUE
        )
        self.reason_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.time_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Mins (e.g., 15) ",
            width=100,
            text_color=DUST_GREY,
            fg_color=GUNMETAL,
            border_color=PINE_BLUE
        )
        self.time_entry.pack(side="left")

        self.submit_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.submit_frame.pack(padx=30, pady=(10, 0), fill="x")

        self.send_request_btn = ctk.CTkButton(
            self.submit_frame,
            text="Send Request",
            width=120,
            fg_color=OLD_GOLD,
            hover_color="#c9a636",
            text_color=CARBON_BLACK,
            command=self.send_request_list
        )
        self.send_request_btn.pack(side="right")

        # The Footer Area (Cancel button)
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        self.cancel_btn = ctk.CTkButton(
            self.footer_frame,
            text="Cancel",
            width=80,
            fg_color="transparent",
            border_width=1,
            border_color=GUNMETAL,
            text_color=DUST_GREY,
            hover_color=GUNMETAL,
            command=self.destroy
        )
        self.cancel_btn.pack(side="right")

    def send_request_list(self):
        """Validating input and save the Negotiation request to DB """
        raw_reason = self.reason_entry.get().strip()
        raw_time = self.time_entry.get().strip()

        try:
             minutes = int(raw_time)
             if minutes <= 0:
                 raise ValueError
        except ValueError:
            self.time_entry.configure(border_color="#cf4444")
            self.time_entry.delete(0, "end")
            self.time_entry.insert(0, "Invalid")
            return

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            new_request = NegotiationRequest(
                target_name=self.app_name,
                requested_minutes=minutes,
                reason=raw_reason,
                status="PENDING"
            )
            session.add(new_request)
            session.commit()
            print(f" ✅ Saved Request: {minutes} min for {self.app_name} (Reason: {raw_reason})")

            # Transmit the request to the parent's phone
            try:
                tele = TelegramAlertService()
                msg = f"⏳ <b>TIME REQUEST</b> ⏳\n\n<b>Target:</b> {self.app_name}\n<b>Requested Time:</b> {minutes} mins\n<b>Reason:</b> {raw_reason}\n\nTo approve, reply with:\n/allow {self.app_name} {minutes}"
                tele.send_alert(msg)
            except Exception as tele_err:
                print(f" ⚠️ Telegram transmission failed: {tele_err}")

            # Disable the button so they can't spam it, then wait 1.5 seconds before closing
            self.send_request_btn.configure(text="Sent!", state="disabled")
            self.after(1500, self.destroy)

        except Exception as e:
            print(f" ❌ Database Error: {e}")
        finally:
            session.close()


if __name__ == "__main__":
    target_app = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    t_type = sys.argv[2] if len(sys.argv) > 2 else "app"

    app = NegotiationDialog(target_app, t_type)
    app.mainloop()