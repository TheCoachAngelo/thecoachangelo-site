#!/usr/bin/env python3
"""Sync WordPress blog posts into the static Coach Angelo site.

This script treats WordPress as the source of truth and regenerates:
- /blog/index.html
- /blog.html
- /blog/<slug>/index.html
- /blog-<slug>.html

It keeps the existing site shell and replaces only the blog index cards and
article body content.
"""

from __future__ import annotations

import base64
import copy
import html
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

from bs4 import BeautifulSoup


SITE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_BLOG_DIR = SITE_ROOT / "blog"
DEFAULT_TEMPLATE = SITE_ROOT / "blog" / "how-to-start-trt" / "index.html"
BLOG_INDEX_TEMPLATE = SITE_ROOT / "blog.html"
CANONICAL_SITE = "https://thecoachangelo.com"


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def request_json(url: str, header: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": header,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code} calling {url}\n{body}")


def fetch_all_posts(base_url: str, header: str) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"{base_url}/wp-json/wp/v2/posts"
            f"?status=publish&per_page=100&page={page}&context=edit&_embed=1"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": header,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                batch = json.loads(raw) if raw else []
                if not isinstance(batch, list):
                    fail(f"Expected list response from {url}")
                posts.extend(batch)
                total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
                if page >= total_pages:
                    break
                page += 1
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            fail(f"HTTP {exc.code} calling {url}\n{body}")
    return posts


def fetch_category_map(base_url: str, header: str) -> dict[int, str]:
    mapping: dict[int, str] = {}
    page = 1
    while True:
        url = f"{base_url}/wp-json/wp/v2/categories?per_page=100&page={page}&context=edit"
        batch = request_json(url, header)
        if not isinstance(batch, list):
            fail(f"Expected list response from {url}")
        for item in batch:
            mapping[int(item["id"])] = str(item.get("name") or item.get("slug") or "")
        if len(batch) < 100:
            break
        page += 1
    return mapping


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_html(text: str) -> str:
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)


def first_image_url(html_text: str) -> Optional[str]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return None


def first_image_alt(html_text: str, fallback: str) -> str:
    soup = BeautifulSoup(html_text or "", "html.parser")
    img = soup.find("img")
    if img and img.get("alt"):
        return img["alt"]
    return fallback


def render_card(post: dict[str, Any], image_url: str, category_label: str) -> str:
    title = normalize_whitespace(strip_html(post["title"]["rendered"]))
    excerpt = normalize_whitespace(strip_html(post.get("excerpt", {}).get("rendered", "")))
    slug = post["slug"]
    link = f"{CANONICAL_SITE}/blog/{slug}/"
    icon = "fas fa-book-open"
    if category_label.lower() in {"trt", "hormones"}:
        icon = "fas fa-syringe"
    elif category_label.lower() in {"bloodwork", "bloodwork-biomarkers"}:
        icon = "fas fa-flask"
    elif category_label.lower() in {"compound analysis", "steroids", "steroid-guides"}:
        icon = "fas fa-vial"
    elif category_label.lower() in {"fat loss", "fat-loss-strategy", "contest prep"}:
        icon = "fas fa-fire"
    elif category_label.lower() in {"peptides", "fat-loss-peptides"}:
        icon = "fas fa-syringe"

    return (
        '<div class="calc-card">'
        f'<img src="{html.escape(image_url)}" alt="{html.escape(title)}" '
        'style="width:100%; height:220px; object-fit:cover; border-radius:12px; '
        'margin-bottom:16px; border:1px solid rgba(255,255,255,0.12);" '
        'loading="lazy" decoding="async" width="480" height="220">'
        f'<h3><i class="{icon}" aria-hidden="true"></i> {html.escape(title.upper())}</h3>'
        f'<p style="margin: 16px 0; color: var(--text-med);">{html.escape(excerpt)}</p>'
        f'<p style="margin: 0 0 18px; color: var(--text-med); font-size: 0.92rem;">Category: {html.escape(category_label)}</p>'
        f'<a href="/blog/{html.escape(slug)}/" class="calc-btn" style="display:inline-block; text-decoration:none; text-align:center;">READ ARTICLE</a>'
        '</div>'
    )


def replace_or_add_meta(soup: BeautifulSoup, selector: dict[str, str], value: str) -> None:
    tag = soup.find("meta", attrs=selector)
    if tag:
        tag["content"] = value
        return
    new_tag = soup.new_tag("meta")
    for key, val in selector.items():
        new_tag[key] = val
    new_tag["content"] = value
    if soup.head:
        soup.head.append(new_tag)


def ensure_canonical(soup: BeautifulSoup, url: str) -> None:
    link = soup.find("link", attrs={"rel": "canonical"})
    if link:
        link["href"] = url
        return
    new_link = soup.new_tag("link", rel="canonical", href=url)
    if soup.head:
        soup.head.append(new_link)


def extract_article_container(soup: BeautifulSoup) -> Optional[Any]:
    return soup.select_one("section.calculators-section .calc-card div[style*='font-family']")


def update_article_page(
    template_html: str,
    post: dict[str, Any],
    category_label: str,
    output_path: Path,
) -> None:
    soup = BeautifulSoup(template_html, "html.parser")
    title = normalize_whitespace(strip_html(post["title"]["rendered"]))
    excerpt = normalize_whitespace(strip_html(post.get("excerpt", {}).get("rendered", "")))
    content_html = post.get("content", {}).get("rendered", "")
    slug = post["slug"]
    url = f"{CANONICAL_SITE}/blog/{slug}/"

    if soup.title:
        soup.title.string = f"The Coach Angelo | {title}"

    replace_or_add_meta(soup, {"name": "description"}, excerpt)
    replace_or_add_meta(soup, {"property": "og:title"}, title)
    replace_or_add_meta(soup, {"property": "og:description"}, excerpt)
    replace_or_add_meta(soup, {"property": "og:url"}, url)
    ensure_canonical(soup, url)

    subtitle = soup.select_one("p.section-subtitle")
    if subtitle:
        subtitle.string = f"Category: {category_label}"

    article_container = extract_article_container(soup)
    if not article_container:
        fail(f"Could not find article container in template for {slug}")

    back_link = soup.find("a", string=re.compile("Back to Blog", re.I))
    if back_link:
        back_link["href"] = "/blog/"

    article_children = BeautifulSoup(content_html, "html.parser")
    article_container.clear()
    for child in article_children.contents:
        article_container.append(copy.copy(child))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(soup), encoding="utf-8")


def update_blog_index(template_html: str, posts: list[dict[str, Any]], category_map: dict[int, str]) -> str:
    soup = BeautifulSoup(template_html, "html.parser")
    grid = soup.select_one(".calc-grid")
    if not grid:
        fail("Could not find blog grid in blog.html template")

    cards: list[str] = []
    for post in sorted(posts, key=lambda p: p.get("date", ""), reverse=True):
        categories = post.get("categories") or []
        category_label = "Blog"
        if categories:
            category_label = category_map.get(int(categories[0]), "Blog")

        local_slug = post["slug"]
        local_article = SITE_ROOT / f"blog-{local_slug}.html"
        local_dir_article = SITE_ROOT / "blog" / local_slug / "index.html"

        image_url = None
        if local_article.exists():
            image_url = first_image_url(local_article.read_text(encoding="utf-8", errors="ignore"))
        if not image_url:
            image_url = first_image_url(post.get("content", {}).get("rendered", ""))
        if not image_url and post.get("_embedded"):
            featured = post["_embedded"].get("wp:featuredmedia", [])
            if featured:
                image_url = featured[0].get("source_url")
        if not image_url:
            image_url = "/assets/blog-inline/peptides-hero.jpg"

        cards.append(render_card(post, image_url, category_label))

    grid.clear()
    for card_html in cards:
        card_soup = BeautifulSoup(card_html, "html.parser")
        for node in card_soup.contents:
            grid.append(copy.copy(node))

    return str(soup)


def prune_stale_blog_outputs(posts: list[dict[str, Any]]) -> None:
    live_slugs = {post["slug"] for post in posts}

    for flat_file in SITE_ROOT.glob("blog-*.html"):
        slug = flat_file.name[len("blog-") : -len(".html")]
        if slug not in live_slugs:
            flat_file.unlink(missing_ok=True)

    if OUTPUT_BLOG_DIR.exists():
        for child in OUTPUT_BLOG_DIR.iterdir():
            if child.name == "index.html":
                continue
            if child.is_dir() and child.name not in live_slugs:
                shutil.rmtree(child, ignore_errors=True)


def choose_template() -> str:
    if DEFAULT_TEMPLATE.exists():
        return DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    candidates = sorted(SITE_ROOT.glob("blog-*.html"))
    if not candidates:
        fail("No article template found.")
    return candidates[0].read_text(encoding="utf-8")


def main() -> None:
    base_url = os.environ.get("WP_BASE_URL", "").rstrip("/")
    wp_user = os.environ.get("WP_USER", "")
    wp_pass = os.environ.get("WP_APP_PASSWORD", "")
    if not base_url or not wp_user or not wp_pass:
        fail("Missing WP_BASE_URL, WP_USER, or WP_APP_PASSWORD.")

    header = auth_header(wp_user, wp_pass)
    posts = fetch_all_posts(base_url, header)
    category_map = fetch_category_map(base_url, header)

    if not posts:
        fail("No published WordPress posts found.")

    prune_stale_blog_outputs(posts)

    template_html = choose_template()
    index_template_html = BLOG_INDEX_TEMPLATE.read_text(encoding="utf-8")

    OUTPUT_BLOG_DIR.mkdir(parents=True, exist_ok=True)

    written = []
    for post in posts:
        slug = post["slug"]
        category_ids = post.get("categories") or []
        category_label = "Blog"
        if category_ids:
            category_label = category_map.get(int(category_ids[0]), "Blog")

        article_html = template_html
        article_path = SITE_ROOT / f"blog-{slug}.html"
        pretty_path = OUTPUT_BLOG_DIR / slug / "index.html"
        update_article_page(article_html, post, category_label, article_path)
        update_article_page(article_html, post, category_label, pretty_path)
        written.append((slug, str(article_path), str(pretty_path)))

    rendered_index = update_blog_index(index_template_html, posts, category_map)
    (SITE_ROOT / "blog.html").write_text(rendered_index, encoding="utf-8")
    (OUTPUT_BLOG_DIR / "index.html").write_text(rendered_index, encoding="utf-8")

    print(f"Synced {len(posts)} posts.")
    for slug, flat_path, pretty_path in written:
        print(f"- {slug}: {flat_path} | {pretty_path}")
    print(f"- blog index: {SITE_ROOT / 'blog.html'} | {OUTPUT_BLOG_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
