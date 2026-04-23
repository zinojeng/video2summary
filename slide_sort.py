"""幻燈片排序工具。

幻燈片擷取腳本產生的檔名格式通常為：
    slide_001_t5m23.5s_g01_h1a2b3c.jpg   # 分+秒 時間標記
    slide_001_t330.5s.jpg                # 僅秒數
    slide_001_t330.5s_anim1-2.jpg

本模組把這些檔名按「影片中的時間點」排序；若檔名沒有時間標記，
則 fallback 至檔案建立時間（macOS: st_birthtime，其他: st_mtime）。
"""

from __future__ import annotations

import os
import re
from typing import Iterable, List

# `_t<分>m<秒>s`（分+秒）
_T_MIN_SEC = re.compile(r"_t(\d+)m(\d+(?:\.\d+)?)s", re.IGNORECASE)
# `_t<秒>s`（只有秒；`s` 後必須不是字母，避免誤吃 `_tsomething`）
_T_SEC = re.compile(r"_t(\d+(?:\.\d+)?)s(?![a-z])", re.IGNORECASE)
# Natural-sort：把連續數字當成整數比，避免 `slide_10` < `slide_2`
_NAT = re.compile(r"(\d+)")

_DEFAULT_EXTS = (".png", ".jpg", ".jpeg", ".heic", ".heif")


def _natural_key(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in _NAT.split(name)]


def slide_sort_key(path: str):
    """回傳排序 key：先檔名時間標記，無標記則 fallback 至檔案建立時間。

    Tuple 結構：(有無標記, 時間值, natural-name key)
    - 有標記的檔案（bucket 0）排在無標記（bucket 1）前；bucket 內用時間值排序。
    """
    name = os.path.basename(path)

    m = _T_MIN_SEC.search(name)
    if m:
        total = int(m.group(1)) * 60 + float(m.group(2))
        return (0, total, _natural_key(name))

    m = _T_SEC.search(name)
    if m:
        return (0, float(m.group(1)), _natural_key(name))

    # Fallback：檔案建立時間（macOS 有 st_birthtime；其他平台用 mtime）
    try:
        st = os.stat(path)
        t = getattr(st, "st_birthtime", None) or st.st_mtime
    except OSError:
        t = 0.0
    return (1, t, _natural_key(name))


def sorted_image_paths(
    folder: str,
    extensions: Iterable[str] = _DEFAULT_EXTS,
) -> List[str]:
    """列出 folder 下所有圖片並按 slide_sort_key 排序，回傳絕對路徑列表。

    會跳過 macOS 的 `._*` 隱藏檔。
    """
    exts = {e.lower() for e in extensions}
    paths: List[str] = []
    for name in os.listdir(folder):
        if name.startswith("._"):
            continue
        if os.path.splitext(name)[1].lower() in exts:
            paths.append(os.path.join(folder, name))
    paths.sort(key=slide_sort_key)
    return paths


def sort_paths_in_place(paths: List[str]) -> List[str]:
    """給現成的路徑列表排序（in-place）。用於已經過濾好的 list 場景。"""
    paths.sort(key=slide_sort_key)
    return paths
