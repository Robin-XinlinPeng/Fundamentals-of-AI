import os
import json
from collections import defaultdict
from typing import Dict, Any

PREFERENCES_FILE = "user_preferences.json"

class UserPreferences:
    def __init__(self):
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """加载用户偏好数据"""
        if os.path.exists(PREFERENCES_FILE):
            try:
                with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {"preferred_areas": {}, "preferred_years": {}}
        return {"preferred_areas": {}, "preferred_years": {}}
    
    def save_preferences(self):
        """保存用户偏好数据到文件"""
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=4)
    
    def update_area_preference(self, area: str):
        """更新地区偏好"""
        areas = self.preferences.setdefault("preferred_areas", {})
        areas[area] = areas.get(area, 0) + 1
        self.save_preferences()
    
    def update_year_preference(self, year: int):
        """更新年份偏好"""
        years = self.preferences.setdefault("preferred_years", {})
        years[str(year)] = years.get(str(year), 0) + 1
        self.save_preferences()
    
    def get_top_areas(self, n: int = 3) -> list:
        """获取最常查询的n个地区"""
        areas = self.preferences.get("preferred_areas", {})
        sorted_areas = sorted(areas.items(), key=lambda x: x[1], reverse=True)
        return [area for area, _ in sorted_areas[:n]]
    
    def get_year_range(self) -> Dict[str, int]:
        """获取最常查询的年份范围"""
        years = self.preferences.get("preferred_years", {})
        if not years:
            return {"min": 2020, "max": 2024}  # 默认范围
        
        year_counts = {int(y): c for y, c in years.items()}
        min_year = min(year_counts.keys())
        max_year = max(year_counts.keys())
        
        # 确保范围合理
        return {
            "min": min(min_year, max_year - 5),  # 至少5年范围
            "max": max(max_year, min_year + 5)
        }

# 全局用户偏好实例
user_prefs = UserPreferences()