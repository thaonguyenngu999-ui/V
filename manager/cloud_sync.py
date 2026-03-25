"""
S Manage - Google Drive Cloud Sync
100% Cloud-based profiles - không lưu local
"""

import os
import json
import pickle
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Callable
from datetime import datetime
import threading
import time

from fingerprint_utils import DEFAULT_CHROME_VERSION

# Google API
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("[!] Google API not installed. Run: pip install google-auth-oauthlib google-api-python-client")

# Scopes cần thiết - Full Drive access để share files
SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Full access for sharing
    'https://www.googleapis.com/auth/drive.file'
]

# Admin email
ADMIN_EMAIL = "sonhangtravel@gmail.com"

# Folder name trên Drive
DRIVE_FOLDER_NAME = "SManage_Profiles"

# Temp folder cho profiles đang chạy
TEMP_BASE = Path(tempfile.gettempdir()) / "SManage_Cloud"


class CloudProfile:
    """Cloud profile metadata"""
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name = data.get('name', '')
        self.file_id = data.get('file_id', '')  # Google Drive file ID
        self.config = data.get('config', {})
        self.modified_time = data.get('modified_time', '')
        self.size = data.get('size', 0)
        self.folder_id = data.get('folder_id', '')  # Parent folder ID
        self.folder_name = data.get('folder_name', '')  # Parent folder name
        self.shared_by = data.get('shared_by', '')  # Email of owner if shared
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'file_id': self.file_id,
            'config': self.config,
            'modified_time': self.modified_time,
            'size': self.size,
            'folder_id': self.folder_id,
            'folder_name': self.folder_name,
            'shared_by': self.shared_by
        }


class CloudFolder:
    """Cloud folder/category"""
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name = data.get('name', '')
        self.profile_count = data.get('profile_count', 0)
        self.shared_with = data.get('shared_with', [])  # List of emails
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'profile_count': self.profile_count,
            'shared_with': self.shared_with
        }


class CloudSync:
    """100% Cloud-based profile management"""
    
    def __init__(self, app_path: str):
        self.app_path = Path(app_path)
        
        # Token luôn lưu vào AppData (có quyền ghi)
        import sys
        import os
        
        # AppData folder cho token
        if sys.platform == 'win32':
            appdata = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
        else:
            appdata = Path.home() / '.local' / 'share'
        
        token_dir = appdata / 'SManage'
        token_dir.mkdir(parents=True, exist_ok=True)
        self.token_path = token_dir / "cloud_token.pickle"
        
        # For PyInstaller: credentials may be in _MEIPASS or next to EXE
        if getattr(sys, 'frozen', False):
            # Running as EXE
            exe_dir = Path(sys.executable).parent
            meipass = Path(getattr(sys, '_MEIPASS', exe_dir))
            
            # Try multiple locations for credentials
            possible_creds = [
                exe_dir / "credentials.json",
                meipass / "credentials.json", 
                self.app_path / "credentials.json"
            ]
            self.credentials_path = None
            for p in possible_creds:
                if p.exists():
                    self.credentials_path = p
                    break
            if not self.credentials_path:
                self.credentials_path = exe_dir / "credentials.json"
        else:
            # Running as script
            self.credentials_path = self.app_path / "credentials.json"
        
        self.creds = None
        self.service = None
        self.drive_folder_id = None
        
        # Ensure temp folder exists
        TEMP_BASE.mkdir(parents=True, exist_ok=True)
        
        # Track running profiles (profile_id -> temp_path)
        self.running_profiles: Dict[str, Path] = {}
        
    def is_available(self) -> bool:
        """Check if Google API is available"""
        return GOOGLE_API_AVAILABLE
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        if not GOOGLE_API_AVAILABLE:
            return False
        
        if self.creds and self.creds.valid:
            return True
        
        # Try load from token file
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as f:
                    self.creds = pickle.load(f)
                
                if self.creds and self.creds.valid:
                    self._init_service()
                    return True
                
                # Refresh if expired
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                    self._save_token()
                    self._init_service()
                    return True
            except Exception as e:
                print(f"[!] Token load error: {e}")
        
        return False
    
    def get_user_email(self) -> Optional[str]:
        """Get logged in user email"""
        if not self.is_logged_in():
            return None
        
        try:
            about = self.service.about().get(fields="user").execute()
            return about.get('user', {}).get('emailAddress', 'Unknown')
        except:
            return "Connected"
    
    def is_admin(self) -> bool:
        """Check if current user is admin"""
        email = self.get_user_email()
        return email and email.lower() == ADMIN_EMAIL.lower()
    
    def login(self) -> bool:
        """Login to Google Drive"""
        if not GOOGLE_API_AVAILABLE:
            print("[!] Google API not installed")
            return False
        
        try:
            # Check for credentials.json
            print(f"[*] Looking for credentials at: {self.credentials_path}")
            if not self.credentials_path or not self.credentials_path.exists():
                print(f"[!] No credentials.json found at {self.credentials_path}")
                return False
            
            print(f"[+] Found credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), SCOPES
            )
            
            print("[*] Opening browser for login...")
            # Open browser for auth
            self.creds = flow.run_local_server(
                port=0,
                prompt='consent',
                success_message='✅ Đăng nhập thành công! Bạn có thể đóng tab này.'
            )
            
            self._save_token()
            self._init_service()
            
            print(f"[+] Logged in as: {self.get_user_email()}")
            return True
            
        except Exception as e:
            print(f"[!] Login error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def logout(self):
        """Logout and remove token"""
        self.creds = None
        self.service = None
        if self.token_path.exists():
            self.token_path.unlink()
        print("[+] Logged out")
    
    def _save_token(self):
        """Save token to file"""
        with open(self.token_path, 'wb') as f:
            pickle.dump(self.creds, f)
    
    def _init_service(self):
        """Initialize Drive service"""
        self.service = build('drive', 'v3', credentials=self.creds)
        self._ensure_folder()
    
    def _ensure_folder(self):
        """Ensure SManage folder exists on Drive"""
        try:
            # Search for existing folder
            results = self.service.files().list(
                q=f"name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                self.drive_folder_id = files[0]['id']
                print(f"[+] Found cloud folder: {DRIVE_FOLDER_NAME}")
            else:
                # Create folder
                file_metadata = {
                    'name': DRIVE_FOLDER_NAME,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(
                    body=file_metadata, fields='id'
                ).execute()
                self.drive_folder_id = folder['id']
                print(f"[+] Created cloud folder: {DRIVE_FOLDER_NAME}")
                
        except Exception as e:
            print(f"[!] Folder error: {e}")

    # ============ FOLDER/CATEGORY MANAGEMENT ============
    
    def list_folders(self) -> List[CloudFolder]:
        """List all folders/categories in main folder"""
        if not self.is_logged_in():
            return []
        
        try:
            results = self.service.files().list(
                q=f"'{self.drive_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = []
            for f in results.get('files', []):
                # Skip expensive API calls - just get basic info
                folders.append(CloudFolder({
                    'id': f['id'],
                    'name': f['name'],
                    'profile_count': 0,  # Will be updated when folder is selected
                    'shared_with': []    # Will be loaded on demand
                }))
            
            return folders
            
        except Exception as e:
            print(f"[!] List folders error: {e}")
            return []
    
    def get_folder_details(self, folder_id: str) -> Optional[CloudFolder]:
        """Get folder with profile count and sharing info (on demand)"""
        if not self.is_logged_in():
            return None
        
        try:
            # Get folder info
            folder_info = self.service.files().get(
                fileId=folder_id,
                fields='id, name'
            ).execute()
            
            # Count profiles
            count_result = self.service.files().list(
                q=f"'{folder_id}' in parents and name contains 'profile_' and trashed=false",
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            # Get sharing info
            shared_with = self._get_folder_permissions(folder_id)
            
            return CloudFolder({
                'id': folder_info['id'],
                'name': folder_info['name'],
                'profile_count': len(count_result.get('files', [])),
                'shared_with': shared_with
            })
            
        except Exception as e:
            print(f"[!] Get folder details error: {e}")
            return None
    
    def _get_folder_permissions(self, folder_id: str) -> List[str]:
        """Get list of emails folder is shared with"""
        try:
            permissions = self.service.permissions().list(
                fileId=folder_id,
                fields='permissions(emailAddress, role)'
            ).execute()
            
            emails = []
            for p in permissions.get('permissions', []):
                email = p.get('emailAddress', '')
                if email and p.get('role') in ['reader', 'writer']:
                    emails.append(email)
            return emails
        except:
            return []
    
    def create_folder(self, name: str) -> Optional[CloudFolder]:
        """Create a new folder/category"""
        if not self.is_logged_in() or not self.is_admin():
            print("[!] Only admin can create folders")
            return None
        
        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.drive_folder_id]
            }
            
            folder = self.service.files().create(
                body=file_metadata, fields='id, name'
            ).execute()
            
            print(f"[+] Created folder: {name}")
            
            return CloudFolder({
                'id': folder['id'],
                'name': folder['name'],
                'profile_count': 0,
                'shared_with': []
            })
            
        except Exception as e:
            print(f"[!] Create folder error: {e}")
            return None
    
    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder (must be empty)"""
        if not self.is_logged_in() or not self.is_admin():
            return False
        
        try:
            # Check if empty
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            if results.get('files', []):
                print("[!] Folder not empty")
                return False
            
            self.service.files().delete(fileId=folder_id).execute()
            print("[+] Folder deleted")
            return True
            
        except Exception as e:
            print(f"[!] Delete folder error: {e}")
            return False
    
    def share_folder(self, folder_id: str, email: str) -> bool:
        """Share a folder with a user (read-only)"""
        if not self.is_logged_in() or not self.is_admin():
            print("[!] Only admin can share")
            return False
        
        try:
            permission = {
                'type': 'user',
                'role': 'reader',
                'emailAddress': email
            }
            
            self.service.permissions().create(
                fileId=folder_id,
                body=permission,
                sendNotificationEmail=False
            ).execute()
            
            print(f"[+] Shared folder with: {email}")
            return True
            
        except Exception as e:
            print(f"[!] Share error: {e}")
            return False
    
    def unshare_folder(self, folder_id: str, email: str) -> bool:
        """Remove sharing from a folder"""
        if not self.is_logged_in() or not self.is_admin():
            return False
        
        try:
            permissions = self.service.permissions().list(
                fileId=folder_id,
                fields='permissions(id, emailAddress)'
            ).execute()
            
            for p in permissions.get('permissions', []):
                if p.get('emailAddress', '').lower() == email.lower():
                    self.service.permissions().delete(
                        fileId=folder_id,
                        permissionId=p['id']
                    ).execute()
                    print(f"[+] Removed access for: {email}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"[!] Unshare error: {e}")
            return False
    
    def move_profile_to_folder(self, profile_file_id: str, target_folder_id: str) -> bool:
        """Move a profile to a folder"""
        if not self.is_logged_in() or not self.is_admin():
            return False
        
        try:
            # Get current parent
            file = self.service.files().get(
                fileId=profile_file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move to new folder
            self.service.files().update(
                fileId=profile_file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            print(f"[+] Moved profile to folder")
            return True
            
        except Exception as e:
            print(f"[!] Move error: {e}")
            return False
    
    def list_shared_with_me(self) -> List[CloudProfile]:
        """List profiles shared with current user (for non-admin)"""
        if not self.is_logged_in():
            return []
        
        try:
            # Search for shared folders containing profiles
            results = self.service.files().list(
                q="sharedWithMe=true and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name, owners)'
            ).execute()
            
            profiles = []
            for folder in results.get('files', []):
                owner_email = folder.get('owners', [{}])[0].get('emailAddress', '')
                
                # Get profiles in shared folder - include description for fast config
                profile_results = self.service.files().list(
                    q=f"'{folder['id']}' in parents and name contains 'profile_' and trashed=false",
                    spaces='drive',
                    fields='files(id, name, modifiedTime, size, description)'
                ).execute()
                
                for f in profile_results.get('files', []):
                    profile_id = f['name'].replace('profile_', '').replace('.zip', '')
                    
                    # Fast: Get config from description
                    config = {}
                    desc = f.get('description', '')
                    if desc:
                        try:
                            config = json.loads(desc)
                        except:
                            pass
                    
                    # Slow fallback
                    if not config:
                        config = self._get_profile_config(f['id'])
                    
                    profiles.append(CloudProfile({
                        'id': profile_id,
                        'name': config.get('name', profile_id),
                        'file_id': f['id'],
                        'config': config,
                        'modified_time': f.get('modifiedTime', ''),
                        'size': int(f.get('size', 0)),
                        'folder_id': folder['id'],
                        'folder_name': folder['name'],
                        'shared_by': owner_email
                    }))
            
            return profiles
            
        except Exception as e:
            print(f"[!] List shared error: {e}")
            import traceback
            traceback.print_exc()
            return []

    # ============ CLOUD PROFILE MANAGEMENT ============
    
    def list_cloud_profiles(self, folder_id: str = None) -> List[CloudProfile]:
        """List profiles on Drive, optionally filtered by folder"""
        if not self.is_logged_in():
            return []
        
        try:
            profiles = []
            
            # Determine parent folder
            parent_id = folder_id if folder_id else self.drive_folder_id
            
            # Get profiles directly in parent folder - include description for fast config
            results = self.service.files().list(
                q=f"'{parent_id}' in parents and name contains 'profile_' and trashed=false",
                spaces='drive',
                fields='files(id, name, modifiedTime, size, description)'
            ).execute()
            
            for f in results.get('files', []):
                profile_id = f['name'].replace('profile_', '').replace('.zip', '')
                
                # Fast: Get config from description
                config = {}
                desc = f.get('description', '')
                if desc:
                    try:
                        config = json.loads(desc)
                    except:
                        pass
                
                # Skip slow fallback to avoid lag - just use basic info
                if not config:
                    config = {'name': profile_id, 'id': profile_id}
                
                profiles.append(CloudProfile({
                    'id': profile_id,
                    'name': config.get('name', profile_id),
                    'file_id': f['id'],
                    'config': config,
                    'modified_time': f.get('modifiedTime', ''),
                    'size': int(f.get('size', 0)),
                    'folder_id': parent_id,
                    'folder_name': ''
                }))
            
            return profiles
            
        except Exception as e:
            print(f"[!] List error: {e}")
            return []
    
    def _get_profile_config(self, file_id: str) -> dict:
        """Get config from file description (fast) or fallback to zip (slow)"""
        try:
            # First try to get from description (fast - no download needed)
            file_info = self.service.files().get(
                fileId=file_id,
                fields='description'
            ).execute()
            
            desc = file_info.get('description', '')
            if desc:
                try:
                    return json.loads(desc)
                except:
                    pass
            
            # Fallback: Download zip and read config (slow - for old profiles)
            print(f"[*] Downloading config for {file_id} (slow fallback)...")
            request = self.service.files().get_media(fileId=file_id)
            zip_path = TEMP_BASE / f"temp_{file_id}.zip"
            
            with open(zip_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            
            # Read config.json from zip
            config = {}
            with zipfile.ZipFile(zip_path, 'r') as zf:
                if 'config.json' in zf.namelist():
                    with zf.open('config.json') as cf:
                        config = json.load(cf)
            
            zip_path.unlink()
            
            # Update description for next time (migrate old profile)
            if config:
                try:
                    self.service.files().update(
                        fileId=file_id,
                        body={'description': json.dumps(config)}
                    ).execute()
                    print(f"[+] Migrated config to description")
                except:
                    pass
            
            return config
            
        except Exception as e:
            print(f"[!] Get config error: {e}")
            return {}
    
    def create_cloud_profile(self, name: str, config: dict, folder_id: str = None) -> Optional[CloudProfile]:
        """Create a new profile directly on cloud, optionally in a folder"""
        if not self.is_logged_in():
            return None
        
        try:
            import uuid
            profile_id = str(uuid.uuid4())[:8]
            
            # Create temp folder with config
            temp_path = TEMP_BASE / f"profile_{profile_id}"
            temp_path.mkdir(parents=True, exist_ok=True)
            
            # Create UserData folder structure
            user_data = temp_path / "UserData"
            user_data.mkdir(exist_ok=True)
            
            # Create Default profile folder (Chromium requires this)
            default_profile = user_data / "Default"
            default_profile.mkdir(exist_ok=True)
            
            # Create minimal Preferences file so folder is not empty
            prefs = {
                "profile": {
                    "name": name,
                    "created_by_version": DEFAULT_CHROME_VERSION
                }
            }
            with open(default_profile / "Preferences", 'w') as f:
                json.dump(prefs, f, indent=2)
            
            # Save config
            config['id'] = profile_id
            config['name'] = name
            config['created_at'] = datetime.now().isoformat()
            
            with open(temp_path / "config.json", 'w') as f:
                json.dump(config, f, indent=2)
            
            # Zip and upload
            zip_path = TEMP_BASE / f"profile_{profile_id}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(temp_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_path)
                        zf.write(file_path, arc_name)
            
            # Determine parent folder
            parent_id = folder_id if folder_id else self.drive_folder_id
            
            # Upload to Drive with config in description (for fast loading)
            file_metadata = {
                'name': f"profile_{profile_id}.zip",
                'parents': [parent_id],
                'description': json.dumps(config)  # Store config for fast access
            }
            media = MediaFileUpload(str(zip_path), mimetype='application/zip', resumable=True)
            
            uploaded = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # Close media before cleanup
            del media
            
            # Cleanup temp
            shutil.rmtree(temp_path, ignore_errors=True)
            try:
                zip_path.unlink()
            except:
                pass  # File may still be locked, ignore
            
            print(f"[+] Created cloud profile: {name} ({profile_id})")
            
            return CloudProfile({
                'id': profile_id,
                'name': name,
                'file_id': uploaded['id'],
                'config': config
            })
            
        except Exception as e:
            print(f"[!] Create error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def delete_cloud_profile(self, file_id: str) -> bool:
        """Delete a profile from cloud"""
        if not self.is_logged_in():
            return False
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            print(f"[+] Deleted cloud profile")
            return True
        except Exception as e:
            print(f"[!] Delete error: {e}")
            return False
    
    def update_cloud_profile_config(self, file_id: str, config: dict) -> bool:
        """Update profile config on cloud"""
        if not self.is_logged_in():
            return False
        
        try:
            # Download current
            temp_path = self._download_for_launch(file_id, config.get('id', 'temp'))
            if not temp_path:
                return False
            
            # Update config
            config_path = temp_path / "config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Upload back
            self._upload_after_close(temp_path, config['id'], file_id)
            
            return True
            
        except Exception as e:
            print(f"[!] Update error: {e}")
            return False
    
    # ============ LAUNCH/CLOSE FLOW ============
    
    def download_for_launch(self, profile: CloudProfile, callback: Callable = None) -> Optional[Path]:
        """Download profile to temp for launching"""
        return self._download_for_launch(profile.file_id, profile.id, callback)
    
    def _download_for_launch(self, file_id: str, profile_id: str, callback: Callable = None) -> Optional[Path]:
        """Download profile from cloud to temp folder"""
        if not self.is_logged_in():
            return None
        
        try:
            if callback:
                callback("Đang tải profile từ cloud...")
            
            # Download zip
            request = self.service.files().get_media(fileId=file_id)
            zip_path = TEMP_BASE / f"profile_{profile_id}.zip"
            
            with open(zip_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if callback and status:
                        callback(f"Đang tải... {int(status.progress() * 100)}%")
            
            # Extract to temp
            temp_path = TEMP_BASE / f"profile_{profile_id}"
            if temp_path.exists():
                shutil.rmtree(temp_path)
            
            temp_path.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_path)
            
            zip_path.unlink()
            
            # Track running profile
            self.running_profiles[profile_id] = temp_path
            
            if callback:
                callback("✅ Đã tải xong!")
            
            print(f"[+] Downloaded to temp: {temp_path}")
            return temp_path
            
        except Exception as e:
            print(f"[!] Download error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_after_close(self, profile_id: str, file_id: str, callback: Callable = None) -> bool:
        """Upload profile back to cloud after browser closes"""
        temp_path = self.running_profiles.get(profile_id)
        if not temp_path or not temp_path.exists():
            print(f"[!] No temp folder for profile {profile_id}")
            return False
        
        return self._upload_after_close(temp_path, profile_id, file_id, callback)
    
    def _upload_after_close(self, temp_path: Path, profile_id: str, file_id: str, callback: Callable = None) -> bool:
        """Upload and cleanup"""
        if not self.is_logged_in():
            return False
        
        try:
            if callback:
                callback("Đang lưu profile lên cloud...")
            
            # Zip profile
            zip_path = TEMP_BASE / f"profile_{profile_id}_upload.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(temp_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_path)
                        zf.write(file_path, arc_name)
            
            if callback:
                callback("Đang upload...")
            
            # Upload (update existing file)
            media = MediaFileUpload(str(zip_path), mimetype='application/zip')
            
            self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            # Release media handle before cleanup
            del media
            
            # Wait a bit for file release
            import time
            time.sleep(0.5)
            
            # Cleanup with error handling
            try:
                zip_path.unlink()
            except PermissionError:
                print(f"[!] Could not delete zip (file locked), will be cleaned later")
            
            try:
                shutil.rmtree(temp_path, ignore_errors=True)
            except:
                pass
            
            # Remove from tracking
            if profile_id in self.running_profiles:
                del self.running_profiles[profile_id]
            
            if callback:
                callback("✅ Đã lưu!")
            
            print(f"[+] Uploaded and cleaned: {profile_id}")
            return True
            
        except Exception as e:
            print(f"[!] Upload error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def watch_browser_and_upload(self, process, profile_id: str, file_id: str, 
                                  callback: Callable = None):
        """Watch browser process and upload when it closes"""
        def watcher():
            print(f"[>] Watching browser for profile {profile_id}...")
            
            # Wait for process to exit
            process.wait()
            
            print(f"[>] Browser closed, uploading profile {profile_id}...")
            
            # Small delay to ensure all files are written
            time.sleep(1)
            
            # Upload
            self.upload_after_close(profile_id, file_id, callback)
        
        thread = threading.Thread(target=watcher, daemon=True)
        thread.start()
        return thread
    
    def cleanup_temp(self):
        """Cleanup all temp files"""
        try:
            if TEMP_BASE.exists():
                shutil.rmtree(TEMP_BASE)
                TEMP_BASE.mkdir(parents=True, exist_ok=True)
            print("[+] Cleaned up temp folder")
        except Exception as e:
            print(f"[!] Cleanup error: {e}")
    
    # ============ BROWSER DOWNLOAD ============
    
    def get_browser_download_file_id(self) -> Optional[str]:
        """Get browser zip file ID from Drive (uploaded by admin)"""
        if not self.is_logged_in():
            return None
        
        try:
            # Search for browser zip in main folder
            results = self.service.files().list(
                q=f"'{self.drive_folder_id}' in parents and name='browser.zip' and trashed=false",
                spaces='drive',
                fields='files(id, name, size)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
        except Exception as e:
            print(f"[!] Find browser error: {e}")
            return None
    
    def download_browser(self, target_dir: Path, progress_callback: Callable = None) -> bool:
        """Download browser.zip from Drive and extract"""
        if not self.is_logged_in():
            return False
        
        try:
            file_id = self.get_browser_download_file_id()
            if not file_id:
                print("[!] No browser.zip found on Drive")
                return False
            
            # Get file size
            file_info = self.service.files().get(
                fileId=file_id, fields='size'
            ).execute()
            total_size = int(file_info.get('size', 0))
            
            if progress_callback:
                progress_callback(f"Downloading browser ({total_size // 1024 // 1024} MB)...")
            
            # Download
            request = self.service.files().get_media(fileId=file_id)
            
            zip_path = target_dir.parent / "browser_download.zip"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            import io
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status and progress_callback:
                        percent = int(status.progress() * 100)
                        progress_callback(f"Downloading... {percent}%")
            
            if progress_callback:
                progress_callback("Extracting browser...")
            
            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(target_dir)
            
            # Cleanup zip
            zip_path.unlink()
            
            if progress_callback:
                progress_callback("Browser ready!")
            
            print(f"[+] Browser extracted to: {target_dir}")
            return True
            
        except Exception as e:
            print(f"[!] Download browser error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def upload_browser_zip(self, browser_folder: Path, progress_callback: Callable = None) -> bool:
        """Admin only: Upload browser folder as browser.zip to Drive"""
        if not self.is_admin():
            print("[!] Only admin can upload browser")
            return False
        
        if not browser_folder.exists():
            print(f"[!] Browser folder not found: {browser_folder}")
            return False
        
        try:
            if progress_callback:
                progress_callback("Creating browser.zip...")
            
            # Create zip
            zip_path = browser_folder.parent / "browser_upload.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in browser_folder.rglob('*'):
                    if file.is_file():
                        arcname = file.relative_to(browser_folder)
                        zf.write(file, arcname)
                        if progress_callback:
                            progress_callback(f"Zipping: {arcname}")
            
            zip_size = zip_path.stat().st_size
            if progress_callback:
                progress_callback(f"Uploading browser.zip ({zip_size // 1024 // 1024} MB)...")
            
            # Check if exists, delete old
            old_id = self.get_browser_download_file_id()
            if old_id:
                self.service.files().delete(fileId=old_id).execute()
            
            # Upload new
            file_metadata = {
                'name': 'browser.zip',
                'parents': [self.drive_folder_id]
            }
            
            media = MediaFileUpload(str(zip_path), resumable=True)
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    percent = int(status.progress() * 100)
                    progress_callback(f"Uploading... {percent}%")
            
            # Cleanup
            zip_path.unlink()
            
            if progress_callback:
                progress_callback("Browser uploaded!")
            
            print(f"[+] Browser uploaded to Drive")
            return True
            
        except Exception as e:
            print(f"[!] Upload browser error: {e}")
            import traceback
            traceback.print_exc()
            return False


# ============ TEST ============
if __name__ == "__main__":
    sync = CloudSync(os.path.dirname(__file__))
    
    if not sync.is_available():
        print("Install: pip install google-auth-oauthlib google-api-python-client")
    elif sync.is_logged_in():
        print(f"Logged in as: {sync.get_user_email()}")
        profiles = sync.list_cloud_profiles()
        print(f"Cloud profiles: {len(profiles)}")
        for p in profiles:
            print(f"  - {p.name} ({p.id})")
    else:
        print("Not logged in. Call sync.login() to authenticate.")

