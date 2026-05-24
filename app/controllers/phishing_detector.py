# ParentalCare+ Module: phishing_detector.py
# Phase 5, Step 2: Algorithmic Phishing Detection

import Levenshtein
import json
import os


class PhishingDetector:
    def __init__(self):
        # The edit-distance threshold for typo-squatting
        self.threshold = 2

        base_dir = os.path.dirname(__file__)
        golden_path = os.path.join(base_dir, '../../data/golden_whitelist.json')
        safe_list_path = os.path.join(base_dir, '../../data/safe_list.json')

        # Load the Golden Whitelist (High-value targets commonly spoofed)
        try:
            with open(golden_path, mode="r") as file:
                self.golden_whitelist = json.load(file)
        except Exception as e:
            print(f" ⚠️ Warning: Could not load Golden Whitelist: {e}")
            self.golden_whitelist = []

        # Load the Safe List (Exceptions to prevent false positives)
        try:
            with open(safe_list_path, mode="r") as file:
                self.safe_list = json.load(file)
        except Exception as e:
            print(f" ⚠️ Warning: Could not load Safe List: {e}")
            self.safe_list = []

    def check_for_phishing(self, target_domain):
        """
        Evaluates a domain using Levenshtein distance against known high-value targets.
        Returns True if the domain is highly suspicious (typo-squatting).
        """
        # Exact matches to the safe list are instantly approved
        if target_domain in self.safe_list:
            return False

        # Exact matches to the golden list are instantly approved
        if target_domain in self.golden_whitelist:
            return False

        # Heuristic Scan: Calculate edit distance against all golden domains
        for golden_domain in self.golden_whitelist:
            distance = Levenshtein.distance(target_domain, golden_domain)

            # If the distance is between 1 and the threshold, it is likely typo-squatting
            if 0 < distance <= self.threshold:
                print(f" 🚨 Phishing Alert: '{target_domain}' is suspiciously close to '{golden_domain}'")
                return True

        return False