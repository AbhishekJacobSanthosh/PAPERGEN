"""
Cache Manager - Manage RAG cache operations
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any
from config.settings import CACHE_DIR, CACHE_EXPIRY_HOURS

import re

class CacheManager:
    """Utility class for cache management"""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, query: str) -> str:
        """Generate cache key from query - uses readable topic name"""
        # Clean the query to make a safe filename
        clean = re.sub(r'[^\w\s-]', '', query.lower())  # Remove special chars
        clean = re.sub(r'\s+', '_', clean.strip())       # Replace spaces with underscore
        clean = clean[:60]  # Limit length
        # Add short hash suffix for uniqueness
        hash_suffix = hashlib.md5(query.lower().encode()).hexdigest()[:8]
        return f"{clean}_{hash_suffix}"
    
    def get(self, key: str, max_age_hours: int = CACHE_EXPIRY_HOURS) -> Optional[Any]:
        """Get cached data if available and fresh"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check expiry
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=max_age_hours):
                return None
            
            return cache_data.get('data')
            
        except Exception as e:
            print(f"[CACHE] Read error: {e}")
            return None
    
    def set(self, key: str, data: Any):
        """Save data to cache"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"[CACHE] Write error: {e}")
    
    def clear_expired(self, max_age_hours: int = CACHE_EXPIRY_HOURS):
        """Clear expired cache files"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    
                    with open(filepath, 'r') as f:
                        cache_data = json.load(f)
                    
                    cached_time = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - cached_time > timedelta(hours=max_age_hours):
                        os.remove(filepath)
                        print(f"[CACHE] Removed expired: {filename}")
                        
        except Exception as e:
            print(f"[CACHE] Clear error: {e}")
    
    def clear_all(self):
        """Clear all cache files"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("[CACHE] Cleared all cache")
        except Exception as e:
            print(f"[CACHE] Clear all error: {e}")
