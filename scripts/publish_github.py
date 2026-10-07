"""Create the requested private repository using Git Credential Manager.

Never print credentials or store them in files/remote URLs.
"""
import os
import subprocess
import sys
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")
env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory", "GIT_CONFIG_VALUE_0": str(Path.cwd().resolve())})
if subprocess.run(["git", "rev-parse", "--verify", "HEAD"], capture_output=True, env=env).returncode:
    print("BLOCKED: Cần khởi tạo Git và tạo commit trước khi xuất bản.")
    sys.exit(2)
credential = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, env=env)
if credential.returncode:
    print("BLOCKED: Không có thông tin đăng nhập GitHub khả dụng trong Git Credential Manager.")
    sys.exit(2)
fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
token = fields.get("password")
if not token:
    print("BLOCKED: Git Credential Manager không cung cấp thông tin đăng nhập GitHub.")
    sys.exit(2)
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
try:
    user = requests.get("https://api.github.com/user", headers=headers, timeout=20)
    if user.status_code != 200:
        print(f"BLOCKED: Xác thực GitHub thất bại (HTTP {user.status_code}).")
        sys.exit(2)
    owner = user.json()["login"]
    url = f"https://api.github.com/repos/{owner}/sap-xep-tkb"
    existing = requests.get(url, headers=headers, timeout=20)
    if existing.status_code == 404:
        response = requests.post("https://api.github.com/user/repos", headers=headers, json={"name": "sap-xep-tkb", "private": True, "description": "MVP local sắp xếp thời khóa biểu tình nguyện viên và các bé"}, timeout=20)
        if response.status_code != 201:
            print(f"BLOCKED: Không tạo được repository (HTTP {response.status_code}).")
            sys.exit(2)
        repo = response.json()
    elif existing.status_code == 200:
        repo = existing.json()
        if not repo["private"] or repo["size"] != 0:
            print("BLOCKED: Repository cùng tên đã tồn tại và không phải repository riêng tư trống; không ghi đè.")
            sys.exit(2)
    else:
        print(f"BLOCKED: Không kiểm tra được repository (HTTP {existing.status_code}).")
        sys.exit(2)
    remote = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, env=env)
    if remote.returncode:
        subprocess.run(["git", "remote", "add", "origin", repo["clone_url"]], check=True, capture_output=True, env=env)
    elif remote.stdout.strip() != repo["clone_url"]:
        print("BLOCKED: Remote origin khác repository yêu cầu; không tự thay đổi.")
        sys.exit(2)
    pushed = subprocess.run(["git", "push", "-u", "origin", "main"], env=env, capture_output=True, text=True)
    print(f"REPOSITORY: {repo['html_url']}")
    if pushed.returncode:
        print("BLOCKED: Đã tạo repository riêng tư nhưng push thất bại.")
        sys.exit(2)
    print("PUSHED: main")
except requests.RequestException:
    print("BLOCKED: Không kết nối được API GitHub.")
    sys.exit(2)
