#!/usr/bin/env python3
"""
MasseurBoost Auto-Login + Auto-Availability
============================================
Users provide their RentMasseur password ONCE. It's encrypted and stored
in the local keychain. Selenium auto-logs in and manages availability.

Usage:
  python3 rm_autologin.py setup     # Enter credentials (once per user)
  python3 rm_autologin.py login     # Auto-login to RentMasseur
  python3 rm_autologin.py available # Set status to Available
  python3 rm_autologin.py away      # Set status to Away
  python3 rm_autologin.py status    # Check current login status
  python3 rm_autologin.py users     # List stored users
  python3 rm_autologin.py remove <email>  # Remove stored credentials
  python3 rm_autologin.py server          # Start HTTP API server (port 8124)
"""

import os
import sys
import json
import time
import base64
import hashlib
import getpass
import subprocess
from pathlib import Path
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# === CONFIG ===
RM_URL = "https://rentmasseur.com/"
RM_LOGIN_URL = "https://rentmasseur.com/login"
RM_DASHBOARD_URL = "https://rentmasseur.com/dashboard"
STORAGE_DIR = Path.home() / ".masseurboost"
CRED_FILE = STORAGE_DIR / "credentials.enc"
KEY_FILE = STORAGE_DIR / ".key"
USERS_FILE = STORAGE_DIR / "users.json"
SESSION_DIR = STORAGE_DIR / "sessions"
TIMEOUT = 30  # seconds for page loads

# === CRYPTO ===

def _get_or_create_key() -> bytes:
    """Get or create encryption key stored in keychain."""
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    
    key = Fernet.generate_key()
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    
    # Try to store in macOS keychain too
    try:
        subprocess.run(
            ["security", "add-generic-password", "-a", os.environ.get("USER", "user"),
             "-s", "masseurboost-key", "-w", key.decode(), "-U"],
            check=True, capture_output=True
        )
    except Exception:
        pass
    
    return key

def encrypt_data(data: dict) -> bytes:
    key = _get_or_create_key()
    f = Fernet(key)
    return f.encrypt(json.dumps(data).encode())

def decrypt_data(encrypted: bytes) -> dict:
    key = _get_or_create_key()
    f = Fernet(key)
    return json.loads(f.decrypt(encrypted))

# === CREDENTIAL STORAGE ===

def save_user(email: str, password: str, name: str = "", city: str = ""):
    """Save user credentials encrypted."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    users = load_users()
    users[email] = {
        "name": name,
        "city": city,
        "added_at": time.time()
    }
    
    # Store password separately in encrypted file keyed by email hash
    cred_key = hashlib.sha256(email.encode()).hexdigest()
    creds = {}
    if CRED_FILE.exists():
        try:
            creds = decrypt_data(CRED_FILE.read_bytes())
        except Exception:
            creds = {}
    creds[cred_key] = password
    CRED_FILE.write_bytes(encrypt_data(creds))
    CRED_FILE.chmod(0o600)
    
    USERS_FILE.write_text(json.dumps(users, indent=2))
    USERS_FILE.chmod(0o600)
    
    # Also try macOS keychain for the password
    try:
        subprocess.run(
            ["security", "add-generic-password", "-a", email,
             "-s", "masseurboost-rm", "-w", password, "-U"],
            check=True, capture_output=True
        )
    except Exception:
        pass
    
    print(f"✓ Credentials saved for {email}")

def load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text())

def get_password(email: str) -> str:
    """Retrieve password from encrypted storage or keychain."""
    # Try keychain first
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", email,
             "-s", "masseurboost-rm", "-w"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    
    # Fall back to encrypted file
    if CRED_FILE.exists():
        try:
            creds = decrypt_data(CRED_FILE.read_bytes())
            cred_key = hashlib.sha256(email.encode()).hexdigest()
            return creds.get(cred_key, "")
        except Exception:
            pass
    return ""

def remove_user(email: str):
    """Remove user credentials."""
    users = load_users()
    if email in users:
        del users[email]
        USERS_FILE.write_text(json.dumps(users, indent=2))
    
    cred_key = hashlib.sha256(email.encode()).hexdigest()
    if CRED_FILE.exists():
        try:
            creds = decrypt_data(CRED_FILE.read_bytes())
            if cred_key in creds:
                del creds[cred_key]
                CRED_FILE.write_bytes(encrypt_data(creds))
        except Exception:
            pass
    
    try:
        subprocess.run(
            ["security", "delete-generic-password", "-a", email,
             "-s", "masseurboost-rm"],
            capture_output=True
        )
    except Exception:
        pass
    
    print(f"✓ Removed credentials for {email}")

# === SELENIUM ===

def create_driver(headless: bool = False, user_email: str = None) -> webdriver.Chrome:
    """Create Chrome driver with session persistence."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    profile_dir = SESSION_DIR / (hashlib.sha256(user_email.encode()).hexdigest()[:12] if user_email else "default")
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if headless:
        options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(TIMEOUT)
    return driver

def auto_login(driver, email: str, password: str) -> bool:
    """Auto-login to RentMasseur. Returns True on success."""
    print(f"→ Navigating to {RM_LOGIN_URL}...")
    driver.get(RM_LOGIN_URL)
    time.sleep(3)
    
    # Check if already logged in
    if "/login" not in driver.current_url:
        print("✓ Already logged in")
        return True
    
    try:
        wait = WebDriverWait(driver, TIMEOUT)
        
        # Find email field
        email_field = None
        for selector in [
            (By.NAME, "email"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name*='email']"),
            (By.CSS_SELECTOR, "input[name*='user']"),
            (By.CSS_SELECTOR, "input[placeholder*='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='Email']"),
        ]:
            try:
                email_field = wait.until(EC.presence_of_element_located(selector))
                break
            except TimeoutException:
                continue
        
        if not email_field:
            print("✗ Could not find email field")
            return False
        
        # Find password field
        password_field = None
        for selector in [
            (By.NAME, "password"),
            (By.ID, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[name*='pass']"),
        ]:
            try:
                password_field = driver.find_element(*selector)
                break
            except NoSuchElementException:
                continue
        
        if not password_field:
            print("✗ Could not find password field")
            return False
        
        # Fill in credentials
        print(f"→ Entering credentials for {email}...")
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(0.5)
        
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(0.5)
        
        # Find and click login button
        login_btn = None
        for selector in [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Sign in')]"),
            (By.XPATH, "//button[contains(text(), 'Log In')]"),
            (By.CSS_SELECTOR, "button.btn-primary"),
            (By.CSS_SELECTOR, "button[class*='login']"),
        ]:
            try:
                login_btn = driver.find_element(*selector)
                break
            except NoSuchElementException:
                continue
        
        if not login_btn:
            # Try pressing Enter
            password_field.send_keys(Keys.RETURN)
        else:
            login_btn.click()
        
        print("→ Waiting for login to complete...")
        time.sleep(5)
        
        # Check if login succeeded
        if "/login" not in driver.current_url and "login" not in driver.current_url.lower():
            print("✓ Login successful!")
            return True
        
        # Check for error messages
        try:
            error = driver.find_element(By.CSS_SELECTOR, ".alert, .error, [class*='error'], [class*='alert']")
            if error.text:
                print(f"✗ Login error: {error.text}")
                return False
        except NoSuchElementException:
            pass
        
        # Wait a bit more
        time.sleep(5)
        if "/login" not in driver.current_url:
            print("✓ Login successful!")
            return True
        
        print("✗ Login failed — still on login page")
        return False
        
    except Exception as e:
        print(f"✗ Login error: {e}")
        return False

def set_availability(driver, status: str = "available") -> bool:
    """Set availability status on RentMasseur."""
    print(f"→ Setting status to {status}...")
    driver.get(RM_DASHBOARD_URL)
    time.sleep(3)
    
    try:
        # Look for availability toggle/button
        for selector in [
            (By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{status}')]"),
            (By.XPATH, f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{status}')]"),
            (By.CSS_SELECTOR, f"[class*='{status}']"),
            (By.CSS_SELECTOR, "[class*='status']"),
            (By.CSS_SELECTOR, "[class*='available']"),
            (By.CSS_SELECTOR, "[data-status]"),
        ]:
            try:
                el = driver.find_element(*selector)
                el.click()
                time.sleep(2)
                print(f"✓ Status set to {status}")
                return True
            except NoSuchElementException:
                continue
        
        # Try toggling via text search
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        if status in body:
            print(f"✓ Status appears to be {status} already")
            return True
        
        print(f"✗ Could not find availability control for '{status}'")
        return False
        
    except Exception as e:
        print(f"✗ Availability error: {e}")
        return False

def check_status(driver) -> dict:
    """Check current login and availability status."""
    driver.get(RM_DASHBOARD_URL)
    time.sleep(3)
    
    status = {
        "logged_in": "/login" not in driver.current_url,
        "url": driver.current_url,
        "title": driver.title,
    }
    
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        status["available"] = "available" in body_text
        status["away"] = "away" in body_text
    except Exception:
        pass
    
    return status

# === CLI ===

def cmd_setup():
    """Enter credentials for a user."""
    print("=== MasseurBoost Auto-Login Setup ===\n")
    email = input("RentMasseur email: ").strip()
    if not email or "@" not in email:
        print("✗ Invalid email")
        return
    
    password = getpass.getpass("RentMasseur password (input hidden): ")
    if not password:
        print("✗ No password entered")
        return
    
    name = input("Your display name (optional): ").strip()
    city = input("Your city (optional): ").strip()
    
    save_user(email, password, name, city)
    print(f"\n✓ Setup complete. Run 'python3 rm_autologin.py login {email}' to auto-login.")

def cmd_login(email: str = None, headless: bool = False):
    """Auto-login to RentMasseur."""
    users = load_users()
    if not users:
        print("✗ No users configured. Run 'python3 rm_autologin.py setup' first.")
        return
    
    if email:
        if email not in users:
            print(f"✗ User {email} not found. Run 'python3 rm_autologin.py setup' first.")
            return
    else:
        if len(users) == 1:
            email = list(users.keys())[0]
        else:
            print("Multiple users found:")
            for i, (e, d) in enumerate(users.items()):
                print(f"  {i+1}. {e} ({d.get('name', 'no name')}, {d.get('city', 'no city')})")
            choice = input("\nSelect user (number): ").strip()
            try:
                email = list(users.keys())[int(choice) - 1]
            except (ValueError, IndexError):
                print("✗ Invalid selection")
                return
    
    password = get_password(email)
    if not password:
        print(f"✗ No password found for {email}. Run 'python3 rm_autologin.py setup' first.")
        return
    
    print(f"→ Starting browser for {email}...")
    driver = create_driver(headless=headless, user_email=email)
    
    try:
        success = auto_login(driver, email, password)
        if success:
            print(f"\n✓ Logged in as {email}")
            print(f"  Dashboard: {driver.current_url}")
            
            # Keep browser open
            if not headless:
                print("\n→ Browser staying open. Press Ctrl+C to close.")
                while True:
                    time.sleep(1)
        else:
            print(f"\n✗ Login failed for {email}")
    except KeyboardInterrupt:
        print("\n→ Closing browser...")
    finally:
        driver.quit()

def cmd_available(email: str = None, status: str = "available"):
    """Login and set availability."""
    users = load_users()
    if not users:
        print("✗ No users configured. Run 'python3 rm_autologin.py setup' first.")
        return
    
    if email and email not in users:
        print(f"✗ User {email} not found.")
        return
    
    if not email and len(users) == 1:
        email = list(users.keys())[0]
    
    if not email:
        print("Usage: python3 rm_autologin.py available <email>")
        print("Or configure a single user.")
        return
    
    password = get_password(email)
    if not password:
        print(f"✗ No password found for {email}.")
        return
    
    driver = create_driver(headless=True, user_email=email)
    try:
        if auto_login(driver, email, password):
            set_availability(driver, status)
        else:
            print("✗ Login failed, cannot set availability")
    finally:
        driver.quit()

def cmd_status(email: str = None):
    """Check login status."""
    users = load_users()
    if not users:
        print("✗ No users configured.")
        return
    
    if not email and len(users) == 1:
        email = list(users.keys())[0]
    
    if not email:
        print("Usage: python3 rm_autologin.py status <email>")
        return
    
    password = get_password(email)
    if not password:
        print(f"✗ No password found for {email}.")
        return
    
    driver = create_driver(headless=True, user_email=email)
    try:
        if auto_login(driver, email, password):
            status = check_status(driver)
            print(json.dumps(status, indent=2))
        else:
            print("✗ Login failed")
    finally:
        driver.quit()

def cmd_users():
    """List stored users."""
    users = load_users()
    if not users:
        print("No users configured. Run 'python3 rm_autologin.py setup' first.")
        return
    
    print(f"Configured users ({len(users)}):")
    for email, data in users.items():
        name = data.get("name", "—")
        city = data.get("city", "—")
        added = time.strftime("%Y-%m-%d", time.localtime(data.get("added_at", 0)))
        print(f"  • {email}")
        print(f"    Name: {name}, City: {city}, Added: {added}")

def cmd_remove(email: str):
    """Remove stored user."""
    if not email:
        print("Usage: python3 rm_autologin.py remove <email>")
        return
    remove_user(email)

def cmd_server():
    """Run HTTP server for dashboard integration."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    
    active_drivers = {}
    
    class AutoLoginHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != '/api/autologin':
                self.send_error(404)
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            req = json.loads(body)
            
            action = req.get('action', '')
            email = req.get('email', '')
            
            users = load_users()
            if email not in users:
                self._json({"success": False, "error": f"User {email} not found. Run setup first."})
                return
            
            password = get_password(email)
            if not password:
                self._json({"success": False, "error": "No password stored. Run setup first."})
                return
            
            if action == 'login':
                def do_login():
                    driver = create_driver(headless=False, user_email=email)
                    active_drivers[email] = driver
                    success = auto_login(driver, email, password)
                    return success
                
                success = do_login()
                if success:
                    self._json({"success": True, "message": f"Logged in as {email}"})
                else:
                    self._json({"success": False, "error": "Login failed"})
            
            elif action in ('available', 'away'):
                driver = active_drivers.get(email)
                if not driver:
                    driver = create_driver(headless=True, user_email=email)
                    active_drivers[email] = driver
                    if not auto_login(driver, email, password):
                        self._json({"success": False, "error": "Login failed"})
                        return
                
                if set_availability(driver, action):
                    self._json({"success": True, "message": f"Status set to {action}"})
                else:
                    self._json({"success": False, "error": f"Could not set status to {action}"})
            
            elif action == 'status':
                driver = active_drivers.get(email)
                if not driver:
                    self._json({"success": False, "error": "Not logged in"})
                    return
                status = check_status(driver)
                self._json({"success": True, "status": status})
            
            else:
                self._json({"success": False, "error": f"Unknown action: {action}"})
        
        def do_GET(self):
            if self.path == '/api/health':
                self._json({"ok": True, "service": "masseurboost-autologin"})
            else:
                self.send_error(404)
        
        def _json(self, data):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        
        def log_message(self, format, *args):
            print(f"[autologin] {args[0]}")
    
    port = 8124
    server = HTTPServer(('127.0.0.1', port), AutoLoginHandler)
    print(f"✓ Auto-login server running on http://localhost:{port}")
    print(f"  Dashboard can now trigger login/availability via API")
    print(f"  Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n→ Shutting down...")
        for d in active_drivers.values():
            try:
                d.quit()
            except Exception:
                pass
        server.shutdown()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "setup":
        cmd_setup()
    elif cmd == "login":
        email = sys.argv[2] if len(sys.argv) > 2 else None
        headless = "--headless" in sys.argv
        cmd_login(email, headless)
    elif cmd == "available":
        email = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_available(email, "available")
    elif cmd == "away":
        email = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_available(email, "away")
    elif cmd == "status":
        email = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_status(email)
    elif cmd == "users":
        cmd_users()
    elif cmd == "remove":
        email = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_remove(email)
    elif cmd == "server":
        cmd_server()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
