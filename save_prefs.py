import json
import os

def save_chart_to_file(filepath, chart_info):
    """
    Saves the chart's deterministic state (location & time) to a JSON file.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(chart_info, f, indent=4)
        return True
    except Exception as e:
        print(f"Failed to save chart to {filepath}: {e}")
        return False

def load_chart_from_file(filepath):
    """
    Loads chart configuration from a JSON file.
    """
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Failed to load chart from {filepath}: {e}")
        return None