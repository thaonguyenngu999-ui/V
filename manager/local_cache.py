"""
S Manage - Local Cache với SQLite
Cache profiles locally, sync với cloud khi cần
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import os
import sys


def get_app_data_dir() -> Path:
    """Get app data directory for storing cache"""
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
    else:
        base = Path.home() / '.local' / 'share'
    
    app_dir = base / 'SManage'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


class LocalCache:
    """SQLite cache for profiles and settings"""
    
    def __init__(self):
        self.app_dir = get_app_data_dir()
        self.db_path = self.app_dir / 'cache.db'
        self.browser_dir = self.app_dir / 'browser'
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    file_id TEXT,
                    folder_id TEXT,
                    folder_name TEXT,
                    config TEXT,
                    modified_time TEXT,
                    size INTEGER,
                    shared_by TEXT,
                    cached_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    profile_count INTEGER,
                    cached_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            conn.commit()
    
    # ============ PROFILES ============
    
    def cache_profiles(self, profiles: List[Dict]):
        """Cache profiles from cloud"""
        with sqlite3.connect(self.db_path) as conn:
            # Clear old cache
            conn.execute('DELETE FROM profiles')
            
            # Insert new
            for p in profiles:
                conn.execute('''
                    INSERT OR REPLACE INTO profiles 
                    (id, name, file_id, folder_id, folder_name, config, modified_time, size, shared_by, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    p.get('id', ''),
                    p.get('name', ''),
                    p.get('file_id', ''),
                    p.get('folder_id', ''),
                    p.get('folder_name', ''),
                    json.dumps(p.get('config', {})),
                    p.get('modified_time', ''),
                    p.get('size', 0),
                    p.get('shared_by', ''),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
        
        print(f"[+] Cached {len(profiles)} profiles")
    
    def get_cached_profiles(self, folder_id: str = None) -> List[Dict]:
        """Get profiles from cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if folder_id:
                rows = conn.execute(
                    'SELECT * FROM profiles WHERE folder_id = ?', 
                    (folder_id,)
                ).fetchall()
            else:
                rows = conn.execute('SELECT * FROM profiles').fetchall()
            
            profiles = []
            for row in rows:
                profiles.append({
                    'id': row['id'],
                    'name': row['name'],
                    'file_id': row['file_id'],
                    'folder_id': row['folder_id'],
                    'folder_name': row['folder_name'],
                    'config': json.loads(row['config'] or '{}'),
                    'modified_time': row['modified_time'],
                    'size': row['size'],
                    'shared_by': row['shared_by']
                })
            
            return profiles
    
    def update_profile(self, profile: Dict):
        """Update single profile in cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO profiles 
                (id, name, file_id, folder_id, folder_name, config, modified_time, size, shared_by, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.get('id', ''),
                profile.get('name', ''),
                profile.get('file_id', ''),
                profile.get('folder_id', ''),
                profile.get('folder_name', ''),
                json.dumps(profile.get('config', {})),
                profile.get('modified_time', ''),
                profile.get('size', 0),
                profile.get('shared_by', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def delete_profile(self, profile_id: str):
        """Delete profile from cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM profiles WHERE id = ?', (profile_id,))
            conn.commit()
    
    def get_cache_time(self) -> Optional[str]:
        """Get last cache time"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                'SELECT cached_at FROM profiles ORDER BY cached_at DESC LIMIT 1'
            ).fetchone()
            return row[0] if row else None
    
    # ============ FOLDERS ============
    
    def cache_folders(self, folders: List[Dict]):
        """Cache folders from cloud"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM folders')
            
            for f in folders:
                conn.execute('''
                    INSERT OR REPLACE INTO folders (id, name, profile_count, cached_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    f.get('id', ''),
                    f.get('name', ''),
                    f.get('profile_count', 0),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    def get_cached_folders(self) -> List[Dict]:
        """Get folders from cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM folders').fetchall()
            
            return [{'id': r['id'], 'name': r['name'], 'profile_count': r['profile_count']} for r in rows]
    
    # ============ SETTINGS ============
    
    def set_setting(self, key: str, value: str):
        """Save a setting"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            conn.commit()
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                'SELECT value FROM settings WHERE key = ?', (key,)
            ).fetchone()
            return row[0] if row else default
    
    # ============ BROWSER ============
    
    def get_browser_path(self) -> Optional[Path]:
        """Get browser path if exists"""
        chrome = self.browser_dir / 'chrome.exe'
        if chrome.exists():
            return chrome
        return None
    
    def is_browser_installed(self) -> bool:
        """Check if browser is installed"""
        return self.get_browser_path() is not None
    
    def get_browser_dir(self) -> Path:
        """Get browser directory"""
        return self.browser_dir
    
    # ============ CLEANUP ============
    
    def clear_cache(self):
        """Clear all cached data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM profiles')
            conn.execute('DELETE FROM folders')
            conn.commit()
        print("[+] Cache cleared")


# Singleton instance
_cache = None

def get_cache() -> LocalCache:
    global _cache
    if _cache is None:
        _cache = LocalCache()
    return _cache
