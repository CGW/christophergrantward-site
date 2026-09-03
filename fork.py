#!/usr/bin/env python3
"""Fork Squarespace pages into a self-hosted static build.
Downloads every referenced asset (css/js/img/font) from squarespace/typekit
domains into build/assets/<host>/<path>, rewrites references to local paths,
and strips only true tracking scripts (analytics, squarespace-cloudfront
consent/edge tooling) -- keeps everything else so layout stays byte-identical.
"""
import os, re, sys, hashlib, urllib.request, urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path("/sessions/ecstatic-sharp-allen/mnt/cgw-newsite")
ARCHIVE = ROOT / "archive/html"
BUILD = ROOT / "build"
ASSETS = BUILD / "assets"

PLATFORM_HOSTS = (
    "static1.squarespace.com", "images.squarespace-cdn.com",
    "file.squarespace-cdn.com", "assets.squarespace.com",
    "definitions.sqspcdn.com", "sqspcdn.com", "squarespace-cdn.com",
    "typekit.net", "p.typekit.net", "use.typekit.net",
)
# scripts that are pure tracking/consent and safe to drop
DROP_JS_SUBSTR = (
    "google-analytics.com", "googletagmanager.com", "sentry", "cookie-consent",
    "static1.squarespace.com/static/webpack/consent-manager",
    "scripts-compressed/performance-", "scripts-compressed/visitor-site-error-reporter-",
    "scripts-compressed/cldr-resource-pack-",
)

TRACKING_ATTR_HINTS = ("gtag(", "ga(", "fbq(")

SAFE_RE = re.compile(r'[^A-Za-z0-9._-]+')

def sanitize_segment(part):
    part = urllib.parse.unquote(part)
    part = part.replace("+", " ")
    stem, dot, ext = part.rpartition(".")
    if dot and len(ext) <= 5 and ext.isalnum():
        stem = SAFE_RE.sub("-", stem).strip("-") or "file"
        part = f"{stem}.{ext.lower()}"
    else:
        part = SAFE_RE.sub("-", part).strip("-") or "file"
    return part

def local_path_for(url):
    p = urllib.parse.urlparse(url)
    host = p.netloc
    path = p.path.lstrip("/")
    if not path:
        path = "index"
    parts = path.split("/")
    safe_parts = []
    for part in parts:
        part = sanitize_segment(part)
        if len(part.encode()) > 120:
            h = hashlib.sha1(part.encode()).hexdigest()[:16]
            ext = ""
            if "." in part[-6:]:
                ext = "." + part.rsplit(".", 1)[-1][:8]
            part = h + ext
        safe_parts.append(part)
    return ASSETS / host / Path(*safe_parts)

CACHE = {}
def fetch(url):
    if url in CACHE:
        return CACHE[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=20).read()
        CACHE[url] = data
        return data
    except Exception as e:
        print(f"  WARN fetch failed {url}: {e}")
        CACHE[url] = None
        return None

def is_platform(url):
    return any(h in url for h in PLATFORM_HOSTS)

def rel_from(build_file_path, asset_path):
    return os.path.relpath(asset_path, build_file_path.parent)

def download_and_rewrite(url, build_file_path):
    if not url or url.startswith("data:"):
        return url
    if url.startswith("//"):
        url = "https:" + url
    elif not url.startswith("http"):
        return url
    if not is_platform(url):
        return url
    lp = local_path_for(url.split("?")[0])
    if not lp.exists():
        data = fetch(url)
        if data is None:
            return url
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_bytes(data)
    if lp.suffix == ".css":
        rewrite_css_urls(lp, url)
    return rel_from(build_file_path, lp)

def rewrite_css_urls(css_path, css_url):
    try:
        text = css_path.read_text(errors="ignore")
    except Exception:
        return
    if not any(h in text for h in PLATFORM_HOSTS):
        return
    def repl(m):
        u = m.group(1).strip("'\"")
        if u.startswith("data:"):
            return m.group(0)
        abs_u = urllib.parse.urljoin(css_url, u)
        if not is_platform(abs_u):
            return m.group(0)
        lp = local_path_for(abs_u.split("?")[0])
        if not lp.exists():
            data = fetch(abs_u)
            if data is None:
                return m.group(0)
            lp.parent.mkdir(parents=True, exist_ok=True)
            lp.write_bytes(data)
        rel = os.path.relpath(lp, css_path.parent)
        return f"url({rel})"
    new_text = re.sub(r'url\(([^)]+)\)', repl, text)
    css_path.write_text(new_text)

def fork_page(src, dst):
    html = src.read_text(errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # drop pure tracking scripts
    for tag in soup.find_all("script"):
        src_attr = tag.get("src", "") or ""
        inline = tag.string or ""
        if any(d in src_attr for d in DROP_JS_SUBSTR):
            tag.decompose()
            continue
        if not src_attr and any(h in inline for h in TRACKING_ATTR_HINTS):
            tag.decompose()
            continue

    dst.parent.mkdir(parents=True, exist_ok=True)

    # drop preconnect/dns-prefetch hints to the old platform -- meaningless once localized
    for el in soup.find_all("link", rel=lambda r: r and ("preconnect" in r or "dns-prefetch" in r)):
        href = el.get("href", "") or ""
        if is_platform(href if href.startswith("http") else "https:" + href if href.startswith("//") else ""):
            el.decompose()

    for tag, attr in [("link", "href"), ("script", "src"), ("img", "src"),
                       ("img", "srcset"), ("source", "src"), ("source", "srcset")]:
        for el in soup.find_all(tag):
            val = el.get(attr)
            if not val:
                continue
            if attr == "srcset":
                parts = []
                for cand in val.split(","):
                    cand = cand.strip()
                    if not cand:
                        continue
                    bits = cand.split(" ")
                    u = bits[0]
                    new_u = download_and_rewrite(u, dst)
                    bits[0] = new_u
                    parts.append(" ".join(bits))
                el[attr] = ", ".join(parts)
            else:
                el[attr] = download_and_rewrite(val, dst)
            # also handle data-src (lazy load) and data-image (squarespace fluid engine)
    for el in soup.find_all(attrs={"data-src": True}):
        el["data-src"] = download_and_rewrite(el["data-src"], dst)
    for el in soup.find_all(attrs={"data-image": True}):
        el["data-image"] = download_and_rewrite(el["data-image"], dst)

    # inline <style> url(...) refs
    for el in soup.find_all("style"):
        if el.string:
            def repl(m):
                u = m.group(1).strip("'\"")
                if not is_platform(u):
                    return m.group(0)
                lp = local_path_for(u.split("?")[0])
                if not lp.exists():
                    data = fetch(u)
                    if data is None:
                        return m.group(0)
                    lp.parent.mkdir(parents=True, exist_ok=True)
                    lp.write_bytes(data)
                rel = rel_from(dst, lp)
                return f"url({rel})"
            el.string = re.sub(r'url\(([^)]+)\)', repl, el.string)

    dst.write_text(str(soup))

def main():
    count = 0
    for src in ARCHIVE.rglob("*.html"):
        rel = src.relative_to(ARCHIVE)
        dst = BUILD / rel
        print(f"forking {rel}")
        fork_page(src, dst)
        count += 1
    print(f"done: {count} pages forked")

if __name__ == "__main__":
    main()
