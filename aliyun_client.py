#!/usr/bin/env python3
"""
阿里云百炼 万相 wan2.2-s2v 数字人客户端
使用百炼自带临时存储上传文件 → oss:// URL → 数字人视频
"""

import base64
import json
import time
import requests
from pathlib import Path

ENDPOINT = "https://dashscope.aliyuncs.com"


def get_upload_policy(api_key: str, model_name: str) -> dict:
    url = f"{ENDPOINT}/api/v1/uploads"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    params = {"action": "getPolicy", "model": model_name}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"getPolicy 失败 {r.status_code}: {r.text[:300]}")
    return r.json()["data"]


def upload_to_temp_storage(api_key: str, model_name: str, file_path: Path) -> str:
    """上传文件到百炼临时存储, 返回 oss:// URL"""
    policy = get_upload_policy(api_key, model_name)
    key = f"{policy['upload_dir']}/{file_path.name}"

    with open(file_path, "rb") as f:
        files = {
            "OSSAccessKeyId": (None, policy["oss_access_key_id"]),
            "Signature": (None, policy["signature"]),
            "policy": (None, policy["policy"]),
            "x-oss-object-acl": (None, policy["x_oss_object_acl"]),
            "x-oss-forbid-overwrite": (None, policy["x_oss_forbid_overwrite"]),
            "key": (None, key),
            "success_action_status": (None, "200"),
            "file": (file_path.name, f),
        }
        r = requests.post(policy["upload_host"], files=files, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"OSS 上传失败 {r.status_code}: {r.text[:300]}")
    oss_url = f"oss://{key}"
    print(f"    上传成功: {oss_url}")
    return oss_url


def img_to_base64(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = "image/jpeg"
    if image_path.suffix.lower() == ".png":
        mime = "image/png"
    return f"data:{mime};base64,{b64}"


def create_talk(api_key: str, workspace_id: str | None,
                 image_data_url: str, audio_oss_url: str,
                 resolution: str = "480P") -> str:
    if workspace_id:
        url = f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis"
    else:
        url = f"{ENDPOINT}/api/v1/services/aigc/image2video/video-synthesis"

    payload = {
        "model": "wan2.2-s2v",
        "input": {
            "image_url": image_data_url,
            "audio_url": audio_oss_url,
        },
        "parameters": {"resolution": resolution},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
        "X-DashScope-OssResourceResolve": "enable",
    }

    print(f"  [阿里云] 创建 wan2.2-s2v 任务 (resolution={resolution}) ...")
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"阿里云创建失败 {r.status_code}: {r.text[:400]}")

    data = r.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"阿里云无 task_id: {json.dumps(data)[:400]}")
    print(f"    task_id={task_id}")
    return task_id


def wait_and_download(api_key: str, workspace_id: str | None,
                      task_id: str, out_path: Path,
                      poll_interval: int = 15, max_wait: int = 600) -> Path:
    if workspace_id:
        url = f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id}"
    else:
        url = f"{ENDPOINT}/api/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"阿里云查询失败: {r.status_code} {r.text[:200]}")
        data = r.json()
        status = data.get("output", {}).get("task_status", "")
        elapsed = int(time.time() - start)
        print(f"    [{elapsed}s] {status}")

        if status == "SUCCEEDED":
            video_url = data.get("output", {}).get("results", {}).get("video_url")
            if not video_url:
                raise RuntimeError(f"无 video_url: {json.dumps(data)[:300]}")
            print(f"  [阿里云] 下载视频 ...")
            vr = requests.get(video_url, timeout=120, stream=True)
            with open(out_path, "wb") as f:
                for chunk in vr.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"    OK: {out_path} ({out_path.stat().st_size // 1024}KB)")
            return out_path

        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"阿里云任务失败: {json.dumps(data)[:400]}")

        time.sleep(poll_interval)

    raise TimeoutError(f"阿里云任务 {task_id} 在 {max_wait}s 内未完成")


def generate_talking_head(api_key: str, workspace_id: str | None,
                          avatar_path: Path, audio_path: Path,
                          out_path: Path, resolution: str = "480P") -> Path:
    """完整流程: 头像转base64 → 音频上传百炼临时存储 → 创建任务 → 轮询 → 下载"""
    print(f"  [头像] 转 base64 ...")
    image_data_url = img_to_base64(avatar_path)
    print(f"    {avatar_path.name} → {len(image_data_url) // 1024}KB base64")

    print(f"  [音频] 上传百炼临时存储 ...")
    audio_oss_url = upload_to_temp_storage(api_key, "wan2.2-s2v", audio_path)

    task_id = create_talk(api_key, workspace_id, image_data_url, audio_oss_url, resolution)
    return wait_and_download(api_key, workspace_id, task_id, out_path)
