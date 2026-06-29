#!/usr/bin/env python3
"""推送Dashboard数据到GitHub Pages - 通过Contents API更新docs/dashboard_data.json"""

import json
import os
import sys
import base64
import subprocess
import tempfile

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_gh_token():
    """通过gh CLI获取GitHub token"""
    result = subprocess.run(
        ["~/bin/gh", "auth", "token"],
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        print("ERROR: gh auth token failed")
        sys.exit(1)
    return result.stdout.strip()

def get_current_file_sha(token, repo, path):
    """获取远端文件的当前SHA（用于更新已有文件）"""
    cmd = [
        os.path.expanduser("~/bin/gh"), "api",
        f"repos/{repo}/contents/{path}",
        "--jq", ".sha"
    ]
    env = os.environ.copy()
    env["http_proxy"] = "http://127.0.0.1:62372"
    env["https_proxy"] = "http://127.0.0.1:62372"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"Warning: Could not get SHA for {path}, will create new file")
        return None
    return result.stdout.strip()

def push_file_to_github(token, repo, path, content_b64, message, sha=None):
    """推送文件到GitHub Contents API"""
    payload = {
        "message": message,
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha

    # Write payload to temp file for --input
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        tmp_path = f.name

    cmd = [
        os.path.expanduser("~/bin/gh"), "api",
        f"repos/{repo}/contents/{path}",
        "-X", "PUT",
        "--input", tmp_path
    ]
    env = os.environ.copy()
    env["http_proxy"] = "http://127.0.0.1:62372"
    env["https_proxy"] = "http://127.0.0.1:62372"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    os.unlink(tmp_path)

    if result.returncode != 0:
        print(f"ERROR: Push failed for {path}")
        print(result.stderr)
        return False
    print(f"OK: {path} pushed to GitHub")
    return True

def main():
    repo = "likeyourlife/539-abyss"
    dashboard_path = os.path.join(project_root, "reports", "dashboard_data.json")

    # 确保dashboard数据存在
    if not os.path.exists(dashboard_path):
        print("Dashboard数据不存在，先生成...")
        subprocess.run([
            "/Users/ioorule/.workbuddy/binaries/python/envs/default/bin/python3",
            os.path.join(project_root, "scripts", "generate_dashboard_data.py")
        ])

    # 读取dashboard数据
    with open(dashboard_path, "r") as f:
        content = f.read()

    content_b64 = base64.b64encode(content.encode()).decode()

    # 获取远端文件SHA（如果文件已存在）
    sha = get_current_file_sha(None, repo, "docs/dashboard_data.json")

    # 推送到GitHub
    success = push_file_to_github(
        None, repo, "docs/dashboard_data.json",
        content_b64,
        f"更新Dashboard数据 - {os.popen('date +%Y-%m-%d').read().strip()}",
        sha
    )

    if success:
        print("\nDashboard已更新到GitHub Pages!")
        print("访问: https://likeyourlife.github.io/539-abyss/")

        # 触发Pages重建
        env = os.environ.copy()
        env["http_proxy"] = "http://127.0.0.1:62372"
        env["https_proxy"] = "http://127.0.0.1:62372"
        subprocess.run([
            os.path.expanduser("~/bin/gh"), "api",
            "repos/likeyourlife/539-abyss/pages/builds",
            "-X", "POST"
        ], env=env)
        print("Pages重建已触发")
    else:
        print("\n推送失败，请检查gh auth和网络")

if __name__ == "__main__":
    main()
