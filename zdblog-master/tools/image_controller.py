import base64
import io
import re
import uuid
import requests
from PIL import Image
from django.core.signing import loads as signing_loads
from system_config.models import SystemConfig


def _get_config(key, default=None):
    """获取系统配置，自动解密加密字段"""
    try:
        config = SystemConfig.objects.get(key=key)
        if config.is_encrypted:
            return signing_loads(config.value)
        return config.value
    except SystemConfig.DoesNotExist:
        return default
    except Exception:
        return config.value if config else default


def compress_image(image_file, max_size_bytes=1 * 1024 * 1024):
    """压缩图片：超过 1MB 时降低画质并限制最大尺寸"""
    img = Image.open(image_file)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    output = io.BytesIO()
    if image_file.size > max_size_bytes:
        img.thumbnail((1920, 1920), Image.LANCZOS)
        img.save(output, format='JPEG', quality=80, optimize=True)
    else:
        img.save(output, format='JPEG', quality=92, optimize=True)
    output.seek(0)
    return output


def upload_image_to_github(image_file, article_id=''):
    """
    上传图片到 GitHub 仓库，返回 jsDelivr CDN 链接。

    依赖 system_config 表中：
      GITHUB_TOKEN  — GitHub Personal Access Token
      GITHUB_ARTICLE_PATH   — 仓库路径，如 https://github.com/ZDQNFU/blog-image/tree/main/article
    """
    token = _get_config('GITHUB_TOKEN')
    full_path = _get_config('GITHUB_ARTICLE_PATH')

    if not token or not full_path:
        raise ValueError('系统配置中缺少 GITHUB_TOKEN 或 GITHUB_ARTICLE_PATH')

    # 从完整 URL 解析出 owner、repo、branch、base_dir
    # 匹配格式: https://github.com/{owner}/{repo}/tree/{branch}/{dir}
    pattern = r'https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)'
    match = re.match(pattern, full_path)
    
    if not match:
        raise ValueError('GITHUB_PATH 格式不正确，应为 https://github.com/owner/repo/tree/branch/dir')
    
    owner = match.group(1)
    repo = match.group(2)
    branch = match.group(3)
    base_dir = match.group(4).rstrip('/')  # 如 "article"，去掉末尾斜杠

    # SVG is already a web format Pillow cannot decode; preserve its original bytes.
    # Other supported formats are re-encoded as JPEG by compress_image, so use a
    # matching extension in the GitHub URL to keep the CDN content type accurate.
    ext = image_file.name.rsplit('.', 1)[-1].lower() if '.' in image_file.name else 'jpg'
    if ext == 'svg':
        compressed = io.BytesIO(image_file.read())
    else:
        compressed = compress_image(image_file)
        ext = 'jpg'
    img_bytes = compressed.read()

    # 生成唯一文件名
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'):
        ext = 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"

    # 构建仓库内的完整路径
    if article_id:
        file_path = f"{base_dir}/{article_id}/{filename}"
    else:
        file_path = f"{base_dir}/uncategorized/{filename}"

    # 正确的 GitHub API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    # Base64 编码图片
    content_b64 = base64.b64encode(img_bytes).decode('utf-8')

    # 上传到 GitHub
    resp = requests.put(
        api_url,
        json={
            'message': f'Upload {filename}',
            'content': content_b64,
            'branch': branch
        },
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json',
        },
        timeout=30
    )

    if resp.status_code == 401:
        raise RuntimeError('GitHub Token 无效或权限不足，请检查 GITHUB_TOKEN 是否拥有 repo 权限')
    if resp.status_code == 404:
        raise RuntimeError(f'仓库 {owner}/{repo} 不存在，请检查 GITHUB_ARTICLE_PATH 配置')
    resp.raise_for_status()

    # 返回 jsDelivr CDN 链接
    return f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@{branch}/{file_path}"
