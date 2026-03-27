# ParentalCare+ Module: phishing_detector.py
# Phase 5 step2: Hand for blocking phishing websites

import Levenshtein
import json
import os

class PhishingDetector:
    def __init__(self):

        self.threshold = 2
        base_dir = os.path.dirname(__file__)
        golden_path = os.path.join(base_dir, '../../data/golden_whitelist.json')
        safe_list_path = os.path.join(base_dir, '../../data/safe_list.json')

        try:
            with open(golden_path, mode="r") as file:
                self.golden_whitelist = json.load(file)

        except Exception as e:
            print(f" ⚠️ Warning: Could not load Golden Whitelist: {e}")
            self.golden_whitelist = []

        try:
            with open(safe_list_path, mode="r") as file:
                self.safe_list = json.load(file)

        except Exception as e:
            print(f" ⚠️ Warning: Could not load Safe List: {e}")
            self.safe_list = []


    def check_for_phishing(self, target_domain):
        """ Check weather the target_domain is phishing website or not """

        # print(f"🧮 DEBUG: AI is checking '{target_domain}' against {len(self.golden_whitelist)} golden sites.")
        if target_domain in self.safe_list:
            return False

        if target_domain in self.golden_whitelist:
            return False

        for golden_domain in self.golden_whitelist:

            distance = Levenshtein.distance(target_domain, golden_domain)

            if 0 < distance <= self.threshold:      # This shows its typo-squatting
                return True     # Suspicious block it

        return False
