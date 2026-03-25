"""
S Manage - Cloud Mode GUI
100% Cloud-based profiles - không lưu local
With local cache for fast loading
"""

import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_PATH = get_app_path()
sys.path.insert(0, APP_PATH)

from cloud_sync import CloudSync, CloudProfile, CloudFolder, TEMP_BASE
from browser_launcher import BrowserLauncher
from fingerprint import FingerprintGenerator
from local_cache import get_cache, LocalCache

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg_dark": "#1a1a1a",
    "bg_card": "#2b2b2b",
    "bg_hover": "#3a3a3a",
    "accent": "#00d26a",
    "accent_hover": "#00b85c",
    "danger": "#dc3545",
    "info": "#17a2b8",
    "warning": "#ffc107",
    "text": "#ffffff",
    "text_muted": "#888888",
    "google_blue": "#4285f4",
    "folder": "#f5a623",
    "shared": "#9b59b6",
}

# GPU Presets (simplified)
GPU_PRESETS = {
    "NVIDIA": ["GTX 1650", "GTX 1660", "RTX 2060", "RTX 3060", "RTX 3070", "RTX 4070"],
    "AMD": ["RX 5600 XT", "RX 6600", "RX 6700 XT", "RX 7600"],
    "Intel": ["UHD 630", "Iris Xe", "Arc A770"],
}


class LoginWindow(ctk.CTk):
    """Login window for Google Drive"""
    
    def __init__(self):
        super().__init__()
        
        self.cloud = CloudSync(APP_PATH)
        self.logged_in = False
        self.skip_mainloop = False
        
        self.title("S Manage Cloud")
        self.geometry("450x400")
        self.resizable(False, False)
        
        self._center_window()
        
        # Auto login if token exists
        if self.cloud.is_logged_in():
            self.logged_in = True
            self.skip_mainloop = True
            return
        
        self._create_widgets()
    
    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"450x400+{x}+{y}")
    
    def _create_widgets(self):
        # Logo
        ctk.CTkLabel(
            self, text="☁️ S Manage",
            font=ctk.CTkFont(size=36, weight="bold")
        ).pack(pady=(60, 10))
        
        ctk.CTkLabel(
            self, text="Cloud Edition",
            font=ctk.CTkFont(size=16),
            text_color=COLORS["accent"]
        ).pack()
        
        ctk.CTkLabel(
            self, text="100% Cloud-based profiles\nĐăng nhập Google để bắt đầu",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
            justify="center"
        ).pack(pady=30)
        
        # Login button
        self.login_btn = ctk.CTkButton(
            self, text="🔐 Đăng nhập với Google",
            width=280, height=55,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=COLORS["google_blue"],
            hover_color="#3367d6",
            command=self._login
        )
        self.login_btn.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(
            self, text="",
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack()
    
    def _login(self):
        self.login_btn.configure(state="disabled", text="Đang đăng nhập...")
        self.status_label.configure(text="Mở browser để đăng nhập...")
        self.update()
        
        def do_login():
            success = self.cloud.login()
            self.after(0, lambda: self._on_login_result(success))
        
        threading.Thread(target=do_login, daemon=True).start()
    
    def _on_login_result(self, success):
        if success:
            self.logged_in = True
            self.destroy()
        else:
            self.login_btn.configure(state="normal", text="🔐 Đăng nhập với Google")
            self.status_label.configure(text="❌ Đăng nhập thất bại!", text_color=COLORS["danger"])


class CloudProfileCard(ctk.CTkFrame):
    """Card hiển thị 1 cloud profile"""
    
    def __init__(self, parent, profile: CloudProfile, on_launch, on_edit, on_delete):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=10)
        
        self.profile = profile
        self.on_launch = on_launch
        self.on_edit = on_edit
        self.on_delete = on_delete
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Left side - info
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        
        # Name with folder/shared badge
        name_frame = ctk.CTkFrame(left, fg_color="transparent")
        name_frame.pack(fill="x")
        
        ctk.CTkLabel(
            name_frame, text=self.profile.name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).pack(side="left")
        
        # Folder badge
        if self.profile.folder_name:
            ctk.CTkLabel(
                name_frame, text=f"📁 {self.profile.folder_name}",
                font=ctk.CTkFont(size=10),
                text_color=COLORS["folder"],
                fg_color="#3d3000",
                corner_radius=3
            ).pack(side="left", padx=8, ipadx=4)
        
        # Shared by badge
        if self.profile.shared_by:
            ctk.CTkLabel(
                name_frame, text=f"🔗 {self.profile.shared_by.split('@')[0]}",
                font=ctk.CTkFont(size=10),
                text_color=COLORS["shared"],
                fg_color="#2d1f3d",
                corner_radius=3
            ).pack(side="left", padx=4, ipadx=4)
        
        # Config info
        config = self.profile.config
        gpu = config.get('webgl_renderer', 'Unknown GPU')
        if 'NVIDIA' in gpu:
            gpu_short = gpu.split('NVIDIA')[-1].split('Direct')[0].strip(' ,')
        elif 'AMD' in gpu:
            gpu_short = gpu.split('AMD')[-1].split('Direct')[0].strip(' ,')
        else:
            gpu_short = gpu[:30]
        
        info_text = f"🖥️ {config.get('screen_width', 1920)}x{config.get('screen_height', 1080)} | 🎮 {gpu_short}"
        
        ctk.CTkLabel(
            left, text=info_text,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w"
        ).pack(fill="x")
        
        # Cloud icon
        size_mb = self.profile.size / 1024 / 1024
        ctk.CTkLabel(
            left, text=f"☁️ {size_mb:.1f} MB",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["info"],
            anchor="w"
        ).pack(fill="x")
        
        # Right side - buttons
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="right")
        
        ctk.CTkButton(
            right, text="▶", width=45, height=40,
            font=ctk.CTkFont(size=18),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=lambda: self.on_launch(self.profile)
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            right, text="✏️", width=40, height=40,
            fg_color="#6c757d", hover_color="#5a6268",
            command=lambda: self.on_edit(self.profile)
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            right, text="🗑️", width=40, height=40,
            fg_color=COLORS["danger"], hover_color="#c82333",
            command=lambda: self.on_delete(self.profile)
        ).pack(side="left", padx=3)


class CreateProfileDialog(ctk.CTkToplevel):
    """Dialog tạo profile mới"""
    
    def __init__(self, parent, cloud: CloudSync, on_created, folder_id: str = None):
        super().__init__(parent)
        
        self.cloud = cloud
        self.on_created = on_created
        self.folder_id = folder_id  # Target folder
        self.fp_gen = FingerprintGenerator()
        
        self.title("Tạo Profile Mới")
        self.geometry("500x650")
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._randomize()
    
    def _create_widgets(self):
        # Header
        ctk.CTkLabel(
            self, text="➕ Tạo Cloud Profile",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=20)
        
        # Form
        form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=25)
        
        # Folder selection (admin only)
        if self.cloud.is_admin():
            ctk.CTkLabel(form, text="Thư mục:", anchor="w").pack(fill="x", pady=(10, 2))
            
            folders = self.cloud.list_folders()
            folder_names = ["(Không có thư mục)"] + [f.name for f in folders]
            self.folder_map = {f.name: f.id for f in folders}
            
            # Find initial folder name if folder_id was passed
            initial_folder = "(Không có thư mục)"
            if self.folder_id:
                for f in folders:
                    if f.id == self.folder_id:
                        initial_folder = f.name
                        break
            
            self.folder_var = ctk.StringVar(value=initial_folder)
            ctk.CTkComboBox(form, values=folder_names, variable=self.folder_var).pack(fill="x")
        
        # Name
        ctk.CTkLabel(form, text="Tên Profile:", anchor="w").pack(fill="x", pady=(10, 2))
        self.name_entry = ctk.CTkEntry(form, placeholder_text="My Profile")
        self.name_entry.pack(fill="x")
        
        # GPU Brand
        ctk.CTkLabel(form, text="GPU Brand:", anchor="w").pack(fill="x", pady=(15, 2))
        self.gpu_brand = ctk.StringVar(value="NVIDIA")
        brand_cb = ctk.CTkComboBox(form, values=list(GPU_PRESETS.keys()), 
                                   variable=self.gpu_brand, command=self._on_brand_change)
        brand_cb.pack(fill="x")
        
        # GPU Model
        ctk.CTkLabel(form, text="GPU Model:", anchor="w").pack(fill="x", pady=(10, 2))
        self.gpu_model = ctk.StringVar()
        self.gpu_model_cb = ctk.CTkComboBox(form, values=GPU_PRESETS["NVIDIA"],
                                            variable=self.gpu_model)
        self.gpu_model_cb.pack(fill="x")
        
        # Resolution
        ctk.CTkLabel(form, text="Resolution:", anchor="w").pack(fill="x", pady=(15, 2))
        self.resolution = ctk.StringVar(value="1920x1080")
        ctk.CTkComboBox(form, values=["1366x768", "1920x1080", "2560x1440"],
                       variable=self.resolution).pack(fill="x")
        
        # CPU Cores
        ctk.CTkLabel(form, text="CPU Cores:", anchor="w").pack(fill="x", pady=(15, 2))
        self.cpu_cores = ctk.StringVar(value="8")
        ctk.CTkComboBox(form, values=["4", "6", "8", "12", "16"],
                       variable=self.cpu_cores).pack(fill="x")
        
        # RAM
        ctk.CTkLabel(form, text="RAM (GB):", anchor="w").pack(fill="x", pady=(10, 2))
        self.ram = ctk.StringVar(value="8")
        ctk.CTkComboBox(form, values=["4", "8", "16", "32"],
                       variable=self.ram).pack(fill="x")
        
        # Timezone
        ctk.CTkLabel(form, text="Timezone:", anchor="w").pack(fill="x", pady=(15, 2))
        self.timezone = ctk.StringVar(value="Asia/Ho_Chi_Minh")
        ctk.CTkComboBox(form, values=["Asia/Ho_Chi_Minh", "America/New_York", "Europe/London", "Asia/Tokyo"],
                       variable=self.timezone).pack(fill="x")
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=20)
        
        ctk.CTkButton(
            btn_frame, text="🎲 Random",
            fg_color="#6c757d", hover_color="#5a6268",
            command=self._randomize
        ).pack(side="left")
        
        ctk.CTkButton(
            btn_frame, text="Hủy",
            fg_color=COLORS["danger"], hover_color="#c82333",
            command=self.destroy
        ).pack(side="right")
        
        ctk.CTkButton(
            btn_frame, text="✓ Tạo Profile",
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._create
        ).pack(side="right", padx=10)
    
    def _on_brand_change(self, brand):
        models = GPU_PRESETS.get(brand, [])
        self.gpu_model_cb.configure(values=models)
        if models:
            self.gpu_model.set(models[0])
    
    def _randomize(self):
        import random
        print("[DEBUG] _randomize called")
        try:
            brand = random.choice(list(GPU_PRESETS.keys()))
            print(f"[DEBUG] brand = {brand}")
            self.gpu_brand.set(brand)
            self._on_brand_change(brand)
            
            model = random.choice(GPU_PRESETS[brand])
            print(f"[DEBUG] model = {model}")
            self.gpu_model.set(model)
            
            res = random.choice(["1366x768", "1920x1080", "2560x1440"])
            print(f"[DEBUG] resolution = {res}")
            self.resolution.set(res)
            
            cpu = random.choice(["4", "6", "8", "12"])
            print(f"[DEBUG] cpu = {cpu}")
            self.cpu_cores.set(cpu)
            
            ram = random.choice(["8", "16"])
            print(f"[DEBUG] ram = {ram}")
            self.ram.set(ram)
            
            print("[DEBUG] _randomize completed successfully")
        except Exception as e:
            print(f"[ERROR] _randomize failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _create(self):
        name = self.name_entry.get().strip()
        if not name:
            name = f"Profile_{datetime.now().strftime('%H%M%S')}"
        
        # Build GPU renderer string
        brand = self.gpu_brand.get()
        model = self.gpu_model.get()
        if brand == "NVIDIA":
            renderer = f"ANGLE (NVIDIA, NVIDIA GeForce {model} Direct3D11 vs_5_0 ps_5_0, D3D11)"
            vendor = "Google Inc. (NVIDIA)"
        elif brand == "AMD":
            renderer = f"ANGLE (AMD, AMD Radeon {model} Direct3D11 vs_5_0 ps_5_0, D3D11)"
            vendor = "Google Inc. (AMD)"
        else:
            renderer = f"ANGLE (Intel, Intel(R) {model} Direct3D11 vs_5_0 ps_5_0, D3D11)"
            vendor = "Google Inc. (Intel)"
        
        res = self.resolution.get().split('x')
        
        config = {
            'screen_width': int(res[0]),
            'screen_height': int(res[1]),
            'cpu_cores': int(self.cpu_cores.get()),
            'ram_gb': int(self.ram.get()),
            'webgl_vendor': vendor,
            'webgl_renderer': renderer,
            'timezone': self.timezone.get(),
            'language': 'en-US',
            'platform': 'Win32',
        }
        
        # Get selected folder
        folder_id = None
        if hasattr(self, 'folder_var') and hasattr(self, 'folder_map'):
            folder_name = self.folder_var.get()
            if folder_name != "(Không có thư mục)":
                folder_id = self.folder_map.get(folder_name)
        
        # Create on cloud
        self.destroy()
        
        def create_thread():
            profile = self.cloud.create_cloud_profile(name, config, folder_id)
            if profile and self.on_created:
                self.on_created()
        
        threading.Thread(target=create_thread, daemon=True).start()


class ShareDialog(ctk.CTkToplevel):
    """Dialog to manage folder sharing"""
    
    def __init__(self, parent, cloud: CloudSync, folder: CloudFolder, on_updated):
        super().__init__(parent)
        
        self.cloud = cloud
        self.folder = folder
        self.on_updated = on_updated
        
        self.title(f"Chia sẻ: {folder.name}")
        self.geometry("450x400")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
    
    def _create_widgets(self):
        ctk.CTkLabel(
            self, text=f"👥 Chia sẻ thư mục: {self.folder.name}",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # Add email input
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=25, pady=10)
        
        self.email_entry = ctk.CTkEntry(
            add_frame, 
            placeholder_text="Nhập email để thêm...",
            width=280
        )
        self.email_entry.pack(side="left")
        
        ctk.CTkButton(
            add_frame, text="➕ Thêm", width=80,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._add_user
        ).pack(side="left", padx=10)
        
        # Shared users list
        ctk.CTkLabel(
            self, text="Đã chia sẻ với:",
            font=ctk.CTkFont(size=13),
            anchor="w"
        ).pack(fill="x", padx=25, pady=(20, 5))
        
        self.user_list = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_card"])
        self.user_list.pack(fill="both", expand=True, padx=25, pady=10)
        
        self._render_users()
        
        # Close button
        ctk.CTkButton(
            self, text="Đóng", width=100,
            command=self.destroy
        ).pack(pady=15)
    
    def _render_users(self):
        for widget in self.user_list.winfo_children():
            widget.destroy()
        
        if not self.folder.shared_with:
            ctk.CTkLabel(
                self.user_list,
                text="Chưa chia sẻ với ai",
                text_color=COLORS["text_muted"]
            ).pack(pady=20)
        else:
            for email in self.folder.shared_with:
                frame = ctk.CTkFrame(self.user_list, fg_color="transparent")
                frame.pack(fill="x", pady=3)
                
                ctk.CTkLabel(
                    frame, text=f"📧 {email}",
                    font=ctk.CTkFont(size=12)
                ).pack(side="left", padx=10)
                
                ctk.CTkButton(
                    frame, text="❌", width=30, height=25,
                    fg_color=COLORS["danger"], hover_color="#c82333",
                    command=lambda e=email: self._remove_user(e)
                ).pack(side="right", padx=5)
    
    def _add_user(self):
        email = self.email_entry.get().strip()
        if not email or '@' not in email:
            messagebox.showwarning("Lỗi", "Vui lòng nhập email hợp lệ")
            return
        
        def share_thread():
            if self.cloud.share_folder(self.folder.id, email):
                self.folder.shared_with.append(email)
                self.after(0, lambda: self._render_users())
                self.after(0, lambda: self.email_entry.delete(0, 'end'))
                if self.on_updated:
                    self.on_updated()
            else:
                self.after(0, lambda: messagebox.showerror("Lỗi", "Không thể chia sẻ"))
        
        threading.Thread(target=share_thread, daemon=True).start()
    
    def _remove_user(self, email: str):
        def unshare_thread():
            if self.cloud.unshare_folder(self.folder.id, email):
                self.folder.shared_with.remove(email)
                self.after(0, lambda: self._render_users())
                if self.on_updated:
                    self.on_updated()
        
        threading.Thread(target=unshare_thread, daemon=True).start()


class BrowserDownloadDialog(ctk.CTkToplevel):
    """Dialog hiển thị tiến trình tải browser"""
    
    def __init__(self, parent, cloud: CloudSync, target_dir: Path, on_complete):
        super().__init__(parent)
        
        self.cloud = cloud
        self.target_dir = target_dir
        self.on_complete = on_complete
        self.success = False
        
        self.title("Tải Browser")
        self.geometry("400x200")
        self.resizable(False, False)
        
        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 200) // 2
        self.geometry(f"400x200+{x}+{y}")
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._start_download()
    
    def _create_widgets(self):
        ctk.CTkLabel(
            self, text="📥 Đang tải Browser",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(30, 10))
        
        self.status_label = ctk.CTkLabel(
            self, text="Đang chuẩn bị...",
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=15)
        self.progress.set(0)
        
        ctk.CTkLabel(
            self, text="Chỉ tải 1 lần, lần sau sẽ dùng luôn",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        ).pack()
    
    def _start_download(self):
        def download_thread():
            def update_progress(msg):
                self.after(0, lambda: self.status_label.configure(text=msg))
                # Extract percentage if available
                if "%" in msg:
                    try:
                        pct = int(msg.split("%")[0].split()[-1])
                        self.after(0, lambda: self.progress.set(pct / 100))
                    except:
                        pass
            
            self.success = self.cloud.download_browser(self.target_dir, update_progress)
            
            if self.success:
                self.after(0, lambda: self.status_label.configure(
                    text="✅ Browser đã sẵn sàng!", text_color=COLORS["accent"]))
                self.after(1500, self._finish)
            else:
                self.after(0, lambda: self.status_label.configure(
                    text="❌ Không tìm thấy browser.zip trên Drive!", text_color=COLORS["danger"]))
                self.after(0, lambda: messagebox.showerror(
                    "Lỗi", 
                    "Không tìm thấy browser.zip trên Google Drive.\n\n"
                    "Admin cần upload browser trước khi member có thể sử dụng.\n"
                    "Hãy liên hệ admin để được hỗ trợ."
                ))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def _finish(self):
        self.destroy()
        if self.on_complete:
            self.on_complete(self.success)


class CloudApp(ctk.CTk):
    """Main Cloud App - 100% cloud-based profiles with local cache"""
    
    def __init__(self, cloud: CloudSync):
        super().__init__()
        
        self.cloud = cloud
        self.cache = get_cache()  # Local SQLite cache
        self.browser_path = None  # Will be set after check
        self.profiles: list[CloudProfile] = []
        self.folders: list[CloudFolder] = []
        self.running = {}  # profile_id -> process
        self.current_folder_id = None  # None = all, or folder ID
        self.is_admin = cloud.is_admin()
        
        self.title("S Manage Cloud" + (" - ADMIN" if self.is_admin else ""))
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        self._create_widgets()
        
        # Check browser after window shows
        self.after(100, self._check_browser)
    
    def _check_browser(self):
        """Check if browser exists, download if not"""
        browser_path = self._find_browser()
        
        if browser_path and os.path.exists(browser_path):
            self.browser_path = browser_path
            print(f"[+] Browser ready: {browser_path}")
            self._initial_load()
        else:
            # Need to download browser
            self.status_label.configure(text="⚠️ Browser chưa có, đang tải...")
            
            # Admin: upload browser option
            if self.is_admin:
                result = messagebox.askyesno(
                    "Browser không tìm thấy",
                    "Không tìm thấy browser.\n\n"
                    "Bạn có muốn upload browser lên Drive để member có thể tải không?\n\n"
                    "YES = Upload browser\n"
                    "NO = Bỏ qua"
                )
                if result:
                    self._upload_browser()
                else:
                    self._initial_load()
            else:
                # Member: download browser
                target_dir = self.cache.get_browser_dir()
                BrowserDownloadDialog(
                    self, self.cloud, target_dir,
                    on_complete=self._on_browser_download_complete
                )
    
    def _on_browser_download_complete(self, success: bool):
        """Called when browser download finishes"""
        if success:
            self.browser_path = str(self.cache.get_browser_path())
            self.status_label.configure(text="✅ Browser đã sẵn sàng!")
        else:
            self.status_label.configure(text="❌ Không thể tải browser")
        self._initial_load()
    
    def _upload_browser(self):
        """Admin: upload browser to Drive"""
        # Find local browser folder
        browser_folder = None
        possible_paths = [
            Path(APP_PATH) / "browser",
            Path(APP_PATH).parent / "browser",
            Path(r"F:\ChromiumSoncuto\browser"),
        ]
        
        for p in possible_paths:
            if p.exists() and (p / "chrome.exe").exists():
                browser_folder = p
                break
        
        if not browser_folder:
            messagebox.showerror("Lỗi", "Không tìm thấy thư mục browser để upload")
            self._initial_load()
            return
        
        self.status_label.configure(text=f"Uploading browser từ {browser_folder}...")
        
        def upload_thread():
            def update(msg):
                self.after(0, lambda: self.status_label.configure(text=msg))
            
            success = self.cloud.upload_browser_zip(browser_folder, update)
            if success:
                self.after(0, lambda: messagebox.showinfo(
                    "Thành công", 
                    "Browser đã được upload lên Drive!\n"
                    "Member có thể tải browser tự động khi mở app."
                ))
            else:
                self.after(0, lambda: messagebox.showerror("Lỗi", "Không thể upload browser"))
            self.after(0, self._initial_load)
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def _find_browser(self) -> str:
        """Find browser, check cache first"""
        # Check cache (AppData/Local/SManage/browser)
        cache_browser = self.cache.get_browser_path()
        if cache_browser:
            return str(cache_browser)
        
        # Get EXE directory if frozen
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = APP_PATH
        
        locations = [
            # Next to EXE
            os.path.join(exe_dir, "browser", "chrome.exe"),
            # Parent of EXE
            os.path.join(os.path.dirname(exe_dir), "browser", "chrome.exe"),
            # Script path
            os.path.join(APP_PATH, "browser", "chrome.exe"),
            os.path.join(os.path.dirname(APP_PATH), "browser", "chrome.exe"),
            # Hardcoded fallback (dev)
            r"F:\ChromiumSoncuto\browser\chrome.exe",
        ]
        
        for loc in locations:
            if os.path.exists(loc):
                print(f"[+] Found browser: {loc}")
                return loc
        
        print(f"[!] Browser not found!")
        return None
    
    def _initial_load(self):
        """Initial load: use cache first, then refresh from cloud"""
        # Load from cache immediately
        cached_profiles = self.cache.get_cached_profiles()
        if cached_profiles:
            self.profiles = [CloudProfile(p) for p in cached_profiles]
            self._render_profiles()
            self.status_label.configure(text=f"☁️ {len(self.profiles)} profiles (từ cache)")
        
        # Then refresh from cloud in background
        self._refresh_from_cloud()
    
    def _create_widgets(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, text="☁️ S Manage Cloud",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Admin badge
        if self.is_admin:
            ctk.CTkLabel(
                header, text="👑 ADMIN",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["warning"],
                fg_color="#3d3d00",
                corner_radius=5
            ).pack(side="left", padx=(0, 10), pady=18, ipadx=5)
        
        # User email
        email = self.cloud.get_user_email() or "Connected"
        ctk.CTkLabel(
            header, text=f"👤 {email}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["accent"]
        ).pack(side="left", padx=10)
        
        # Logout
        ctk.CTkButton(
            header, text="🚪 Đăng xuất", width=100,
            fg_color="transparent", hover_color="#333",
            command=self._logout
        ).pack(side="right", padx=15)
        
        # Admin: Upload browser button
        if self.is_admin:
            ctk.CTkButton(
                header, text="📤 Upload Browser", width=130,
                fg_color="#6c5ce7", hover_color="#5b4cdb",
                command=self._upload_browser
            ).pack(side="right", padx=5)
        
        # Main container with sidebar
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)
        
        # === SIDEBAR ===
        sidebar = ctk.CTkFrame(main, fg_color=COLORS["bg_dark"], width=220)
        sidebar.pack(side="left", fill="y", padx=(15, 0), pady=10)
        sidebar.pack_propagate(False)
        
        # Sidebar header
        ctk.CTkLabel(
            sidebar, text="📁 Thư mục",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", padx=15, pady=(15, 10))
        
        # All profiles button
        self.all_btn = ctk.CTkButton(
            sidebar, text="📋 Tất cả Profiles",
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            anchor="w", height=35,
            command=lambda: self._select_folder(None)
        )
        self.all_btn.pack(fill="x", padx=10, pady=2)
        
        # Shared with me (for non-admin)
        if not self.is_admin:
            self.shared_btn = ctk.CTkButton(
                sidebar, text="🔗 Được chia sẻ",
                fg_color=COLORS["shared"], hover_color="#8e44ad",
                anchor="w", height=35,
                command=self._show_shared
            )
            self.shared_btn.pack(fill="x", padx=10, pady=2)
        
        # Folder list
        self.folder_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.folder_list.pack(fill="both", expand=True, padx=5, pady=10)
        
        # Admin: Add folder button
        if self.is_admin:
            ctk.CTkButton(
                sidebar, text="➕ Tạo Thư mục",
                fg_color=COLORS["folder"], hover_color="#d4940c",
                height=35,
                command=self._new_folder
            ).pack(fill="x", padx=10, pady=(5, 15))
        
        # === CONTENT AREA ===
        content = ctk.CTkFrame(main, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        # Toolbar
        toolbar = ctk.CTkFrame(content, fg_color="transparent", height=50)
        toolbar.pack(fill="x")
        
        self.folder_title = ctk.CTkLabel(
            toolbar, text="📋 Tất cả Profiles",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.folder_title.pack(side="left")
        
        ctk.CTkButton(
            toolbar, text="🔄", width=40, height=35,
            fg_color=COLORS["info"], hover_color="#138496",
            command=self._refresh
        ).pack(side="left", padx=15)
        
        # Status
        self.status_label = ctk.CTkLabel(
            toolbar, text="",
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack(side="left")
        
        # Create profile button (admin or for shared folders)
        if self.is_admin:
            ctk.CTkButton(
                toolbar, text="➕ Tạo Profile", width=130, height=35,
                font=ctk.CTkFont(weight="bold"),
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                command=self._new_profile
            ).pack(side="right")
        
        # Profile list
        self.profile_list = ctk.CTkScrollableFrame(content, fg_color="transparent")
        self.profile_list.pack(fill="both", expand=True, pady=10)
        
        # Footer
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], height=35)
        footer.pack(fill="x", side="bottom")
        
        self.footer_label = ctk.CTkLabel(
            footer, text="☁️ Profiles được lưu 100% trên Google Drive",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.footer_label.pack(pady=8)
    
    def _select_folder(self, folder_id: str = None, folder_name: str = None):
        """Select a folder to view"""
        self.current_folder_id = folder_id
        if folder_id:
            self.folder_title.configure(text=f"📁 {folder_name}")
        else:
            self.folder_title.configure(text="📋 Tất cả Profiles")
        
        # Load from cache first
        cached = self.cache.get_cached_profiles(folder_id)
        if cached:
            self.profiles = [CloudProfile(p) for p in cached]
            self._render_profiles()
        
        # Then refresh from cloud
        self._refresh_from_cloud()
    
    def _show_shared(self):
        """Show profiles shared with me"""
        self.status_label.configure(text="Đang tải...")
        self.folder_title.configure(text="🔗 Được chia sẻ")
        
        def load_thread():
            self.profiles = self.cloud.list_shared_with_me()
            # Cache shared profiles too
            self.cache.cache_profiles([p.to_dict() for p in self.profiles])
            self.after(0, self._render_profiles)
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _refresh(self):
        """Manual refresh - force reload from cloud"""
        self._refresh_from_cloud()
    
    def _refresh_from_cloud(self):
        """Refresh data from cloud and update cache"""
        self.status_label.configure(text="Đang đồng bộ...")
        
        def load_thread():
            # Load folders
            if self.is_admin:
                self.folders = self.cloud.list_folders()
                # Cache folders
                self.cache.cache_folders([f.to_dict() for f in self.folders])
                self.after(0, self._render_folders)
            
            # Load profiles
            self.profiles = self.cloud.list_cloud_profiles(self.current_folder_id)
            
            # Cache profiles
            if self.profiles:
                self.cache.cache_profiles([p.to_dict() for p in self.profiles])
            
            self.after(0, self._render_profiles)
            self.after(0, lambda: self.status_label.configure(
                text=f"☁️ {len(self.profiles)} profiles (đã sync)"))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _render_folders(self):
        """Render folder list in sidebar"""
        for widget in self.folder_list.winfo_children():
            widget.destroy()
        
        for folder in self.folders:
            frame = ctk.CTkFrame(self.folder_list, fg_color="transparent")
            frame.pack(fill="x", pady=1)
            
            btn = ctk.CTkButton(
                frame, 
                text=f"📁 {folder.name} ({folder.profile_count})",
                fg_color="transparent" if folder.id != self.current_folder_id else COLORS["folder"],
                hover_color=COLORS["bg_hover"],
                anchor="w", height=32,
                font=ctk.CTkFont(size=12),
                command=lambda f=folder: self._select_folder(f.id, f.name)
            )
            btn.pack(side="left", fill="x", expand=True)
            
            # Share button for admin
            if self.is_admin:
                share_btn = ctk.CTkButton(
                    frame, text="👥", width=30, height=28,
                    fg_color=COLORS["shared"] if folder.shared_with else "transparent",
                    hover_color=COLORS["shared"],
                    command=lambda f=folder: self._manage_sharing(f)
                )
                share_btn.pack(side="right", padx=2)
    
    def _new_folder(self):
        """Create new folder dialog"""
        dialog = ctk.CTkInputDialog(
            text="Nhập tên thư mục:",
            title="Tạo Thư mục mới"
        )
        name = dialog.get_input()
        if name:
            def create_thread():
                folder = self.cloud.create_folder(name)
                if folder:
                    self.after(0, lambda: self._refresh())
                    self.after(0, lambda: self.status_label.configure(text=f"✓ Đã tạo thư mục: {name}"))
                else:
                    self.after(0, lambda: messagebox.showerror("Lỗi", "Không thể tạo thư mục"))
            threading.Thread(target=create_thread, daemon=True).start()
    
    def _manage_sharing(self, folder: CloudFolder):
        """Open sharing management dialog"""
        ShareDialog(self, self.cloud, folder, self._refresh)
    
    def _render_profiles(self):
        # Clear existing
        for widget in self.profile_list.winfo_children():
            widget.destroy()
        
        if not self.profiles:
            ctk.CTkLabel(
                self.profile_list,
                text="Chưa có profile nào\nClick '➕ Tạo Profile' để bắt đầu",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_muted"],
                justify="center"
            ).pack(pady=50)
        else:
            for p in self.profiles:
                card = CloudProfileCard(
                    self.profile_list, p,
                    on_launch=self._launch,
                    on_edit=self._edit,
                    on_delete=self._delete
                )
                card.pack(fill="x", pady=5)
        
        self.status_label.configure(text=f"☁️ {len(self.profiles)} profiles")
    
    def _new_profile(self):
        CreateProfileDialog(self, self.cloud, self._on_profile_created, self.current_folder_id)
    
    def _on_profile_created(self):
        """Called when new profile is created - refresh from cloud"""
        self._refresh_from_cloud()
    
    def _edit(self, profile: CloudProfile):
        # TODO: Edit dialog
        messagebox.showinfo("Edit", f"Edit {profile.name} - Coming soon!")
    
    def _delete(self, profile: CloudProfile):
        if messagebox.askyesno("Xóa Profile", f"Xóa '{profile.name}' khỏi cloud?"):
            def delete_thread():
                self.cloud.delete_cloud_profile(profile.file_id)
                # Update cache
                self.cache.delete_profile(profile.id)
                self.after(0, self._refresh_from_cloud)
            
            threading.Thread(target=delete_thread, daemon=True).start()
    
    def _launch(self, profile: CloudProfile):
        if profile.id in self.running:
            messagebox.showwarning("Đang chạy", f"Profile '{profile.name}' đang chạy!")
            return
        
        # Check browser
        if not self.browser_path or not os.path.exists(self.browser_path):
            messagebox.showerror(
                "Lỗi", 
                "Browser chưa sẵn sàng!\n"
                "Hãy khởi động lại app để tải browser."
            )
            return
        
        self.status_label.configure(text=f"Đang tải {profile.name}...")
        
        def launch_thread():
            try:
                def update_status(msg):
                    self.after(0, lambda: self.status_label.configure(text=msg))
                
                # Download from cloud to temp
                print(f"[DEBUG] Starting download for {profile.name}")
                temp_path = self.cloud.download_for_launch(profile, update_status)
                if not temp_path:
                    update_status("❌ Không thể tải profile!")
                    return
                
                print(f"[DEBUG] Downloaded to: {temp_path}")
                
                # Launch browser
                update_status(f"Đang mở {profile.name}...")
                
                launcher = BrowserLauncher(self.browser_path)
                
                config = profile.config
                fp = {
                    'screen_width': config.get('screen_width', 1920),
                    'screen_height': config.get('screen_height', 1080),
                    'hardware_concurrency': config.get('cpu_cores', 8),
                    'device_memory': config.get('ram_gb', 8),
                    'webgl_vendor': config.get('webgl_vendor', 'Google Inc. (NVIDIA)'),
                    'webgl_renderer': config.get('webgl_renderer', 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650)'),
                    'timezone': config.get('timezone', 'Asia/Ho_Chi_Minh'),
                    'language': config.get('language', 'en-US'),
                    'platform': 'Win32',
                }
                
                user_data = str(temp_path / "UserData")
                print(f"[DEBUG] UserData: {user_data}")
                print(f"[DEBUG] Fingerprint: {fp}")
                
                process = launcher.launch(user_data_dir=user_data, fingerprint=fp)
                
                if process:
                    self.running[profile.id] = process
                    update_status(f"✓ {profile.name} đang chạy")
                    print(f"[DEBUG] Browser started, PID: {process.pid}")
                    
                    # Watch for close and upload
                    self.cloud.watch_browser_and_upload(
                        process, profile.id, profile.file_id,
                        callback=lambda msg: self.after(0, lambda: self._on_browser_close(profile, msg))
                    )
                else:
                    update_status("❌ Không thể mở browser!")
                    print("[DEBUG] launcher.launch returned None")
                    
            except Exception as e:
                print(f"[ERROR] Launch failed: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda: self.status_label.configure(text=f"❌ Lỗi: {e}"))
        
        threading.Thread(target=launch_thread, daemon=True).start()
    
    def _on_browser_close(self, profile: CloudProfile, msg: str):
        if profile.id in self.running:
            del self.running[profile.id]
        self.status_label.configure(text=msg)
    
    def _logout(self):
        self.cloud.logout()
        self.cloud.cleanup_temp()
        self.destroy()


def main():
    # Login window
    login = LoginWindow()
    
    if not login.skip_mainloop:
        login.mainloop()
    
    if login.logged_in:
        # Main app
        app = CloudApp(login.cloud)
        app.mainloop()


if __name__ == "__main__":
    main()
