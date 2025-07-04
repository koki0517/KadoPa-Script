import json
import os

pipes_data = []

def load_pipe_data():
    """JSONファイルからパイプデータを読み込み"""
    global pipes_data
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, 'aluminum_pipes.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            pipes_data = json.load(f)
    except:
        pipes_data = [{"width_mm": 10, "height_mm": 10, "thickness_mm": 1}]
