# Not an

import csv
from datetime import datetime
import os

class ResearchLogger:
    def __init__(self, filename="research_data_paper1.csv"):

        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.filepath = os.path.join(self.log_dir, filename)

        # Create CSV with Header if doesn't exist
        if not os.path.exists(self.filepath):
            with open(self.filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Event_Type", "Value", "Frustration_Score"])

    def log_event(self, event_type, value, frustration_score=0):
        try:
            with open(self.filepath, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    event_type,
                    value,
                    frustration_score
                ])
            print(f" 🧪 [RESEARCH] Data Point Logged : {event_type}")

        except Exception as e :
            print(f"Research Log Error: {e}")
