"""
Douyin Creator spider — comment management via Playwright persistent_context.
Mimics the douyin-creator-tools Node.js workflow in Python.

Three functions:
  list_works() → [{title, publishTime}]
  export_comments(work_title) → [{username, commentText, imageUrls}]
  reply_comments(reply_plan_json_path) → {results: [...]}
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time

from app.config import settings

logger = logging.getLogger(__name__)

COMMENT_PAGE_URL = "https://creator.douyin.com/creator-micro/interactive/comment"

_session_lock = threading.Lock()


def _launch_session():
    """Launch persistent browser session for Douyin creator center."""
    with _session_lock:
        from playwright.sync_api import sync_playwright

        p = sync_playwright().start()
        context = p.chromium.launch_persistent_context(
            user_data_dir=settings.edge_user_data,
            headless=False,
            channel="msedge",
            args=[f"--profile-directory={settings.edge_profile_dir}"],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            window.chrome = { runtime: {} };
        """)
        context.set_default_timeout(30000)

        # Login check — navigate to creator center and verify session
        try:
            page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            cur_url = page.url
            if "login" in cur_url.lower() or "passport" in cur_url.lower() or "douyinec.com" in cur_url:
                logger.warning("Douyin: Not logged into creator.douyin.com — login required in Edge")
                context.close()
                p.stop()
                return None, None, None
        except Exception as e:
            logger.warning(f"Douyin: Login check failed — {e}")
            context.close()
            p.stop()
            return None, None, None

        return p, context, page


def list_works() -> list[dict[str, Any]]:
    """List all published works from Douyin creator center."""
    p, context, page = _launch_session()
    if not page:
        return []
    works: list[dict[str, Any]] = []

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Click "选择作品" button
        select_btn = page.locator('button:has-text("选择作品"), [role="button"]:has-text("选择作品")').first
        if not select_btn:
            logger.warning("Douyin: '选择作品' button not found — may need manual login")
            context.close()
            p.stop()
            return []
        select_btn.click()
        page.wait_for_timeout(3000)

        # Extract works from side panel
        works = page.evaluate("""
        () => {
            const panel = document.querySelector('.douyin-creator-interactive-sidesheet-body');
            if (!panel) return [];
            const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();
            const items = panel.querySelectorAll('[class*="work"], [class*="item"], [class*="card"]');
            return Array.from(items).slice(0, 50).map(el => {
                const text = normalize(el.innerText || el.textContent || '');
                const lines = text.split('\\n').filter(l => l.trim());
                return {
                    title: lines[0] || '',
                    publishTime: lines.find(l => /\\d/.test(l)) || '',
                    raw: text.substring(0, 200),
                };
            }).filter(w => w.title.length > 0);
        }
        """)

        logger.info(f"Douyin: Found {len(works)} works")
    except Exception as e:
        logger.warning(f"Douyin list_works failed: {e}")
    finally:
        context.close()
        p.stop()

    return works


def export_comments(work_title: str, limit: int = 200) -> dict[str, Any]:
    """Export unreplied comments for a specific work."""
    p, context, page = _launch_session()
    if not page:
        return {"selectedWork": {"title": work_title}, "count": 0, "comments": [], "error": "login_required"}
    result: dict[str, Any] = {"selectedWork": {"title": work_title}, "count": 0, "comments": []}

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Click "选择作品"
        select_btn = page.locator('button:has-text("选择作品"), [role="button"]:has-text("选择作品")').first
        select_btn.click()
        page.wait_for_timeout(3000)

        # Find and click the target work
        page.evaluate(f"""
        () => {{
            const panel = document.querySelector('.douyin-creator-interactive-sidesheet-body');
            if (!panel) return;
            const items = panel.querySelectorAll('[class*="work"], [class*="item"], [class*="card"]');
            for (const item of items) {{
                if (item.innerText.includes('{work_title[:30]}')) {{
                    item.click();
                    return;
                }}
            }}
        }}
        """)
        page.wait_for_timeout(4000)

        # Wait for comments to load
        page.wait_for_selector('[comment-item], button:has-text("回复")', timeout=15000).catch(lambda: None)
        page.wait_for_timeout(3000)

        # Extract comments
        comments = page.evaluate(f"""
        () => {{
            const items = document.querySelectorAll('[comment-item]');
            const results = [];
            for (const item of items) {{
                const text = (item.innerText || '').replace(/\\s+/g, ' ').trim();
                const replyBtn = item.querySelector('button:has-text("回复")');
                // Unreplied comments have a "回复" button; replied ones don't
                if (!replyBtn) continue;
                const lines = text.split('\\n').filter(l => l.trim());
                results.push({{
                    username: lines[0] || '',
                    commentText: lines.slice(1).join(' ').substring(0, 500),
                    replyMessage: '',
                }});
                if (results.length >= {limit}) break;
            }}
            return results;
        }}
        """)

        result["count"] = len(comments)
        result["comments"] = comments
        logger.info(f"Douyin: Exported {len(comments)} unreplied comments from '{work_title}'")
    except Exception as e:
        logger.warning(f"Douyin export_comments failed: {e}")
    finally:
        context.close()
        p.stop()

    return result


def reply_comments(reply_plan: list[dict[str, Any]], work_title: str) -> dict[str, Any]:
    """Batch reply to comments."""
    p, context, page = _launch_session()
    if not page:
        return {"total": 0, "replied": 0, "results": [], "error": "login_required"}
    results: list[dict] = []

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        select_btn = page.locator('button:has-text("选择作品"), [role="button"]:has-text("选择作品")').first
        select_btn.click()
        page.wait_for_timeout(3000)

        # Select work
        page.evaluate(f"""
        () => {{
            const panel = document.querySelector('.douyin-creator-interactive-sidesheet-body');
            if (!panel) return;
            const items = panel.querySelectorAll('[class*="work"], [class*="item"]');
            for (const item of items) {{
                if (item.innerText.includes('{work_title[:30]}')) {{ item.click(); return; }}
            }}
        }}
        """)
        page.wait_for_timeout(4000)
        page.wait_for_selector('[comment-item], button:has-text("回复")', timeout=15000).catch(lambda: None)
        page.wait_for_timeout(3000)

        # Reply to each comment
        for plan in reply_plan[:20]:  # limit 20 for safety
            try:
                username = plan.get("username", "")
                reply_msg = plan.get("replyMessage", "")
                if not reply_msg or len(reply_msg) > 400:
                    continue

                # Find and click reply button for matching comment
                page.evaluate(f"""
                () => {{
                    const items = document.querySelectorAll('[comment-item]');
                    for (const item of items) {{
                        if (item.innerText.includes('{username[:10]}')) {{
                            const btn = item.querySelector('button:has-text("回复")');
                            if (btn) btn.click();
                            return;
                        }}
                    }}
                }}
                """)
                page.wait_for_timeout(1500)

                # Type reply
                reply_input = page.query_selector('textarea, [contenteditable="true"], input[type="text"]')
                if reply_input:
                    reply_input.fill(reply_msg)
                    page.wait_for_timeout(500)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000)
                    results.append({"username": username, "status": "replied"})
                else:
                    results.append({"username": username, "status": "input_not_found"})
            except Exception as e:
                logger.warning(f"Douyin reply failed for {username}: {e}")
                results.append({"username": username, "status": f"error: {e}"})

    except Exception as e:
        logger.warning(f"Douyin reply_comments failed: {e}")
    finally:
        context.close()
        p.stop()

    return {"total": len(reply_plan), "replied": sum(1 for r in results if r.get("status") == "replied"), "results": results}


def publish_article(title: str, content: str, image_path: str = "",
                    subtitle: str = "", tags: list[str] | None = None,
                    dry_run: bool = False) -> dict[str, Any]:
    p, context, page = _launch_session()
    if not page:
        return {"status": "login_required", "title": title, "error": "login_required"}
    result = {"status": "dry_run" if dry_run else "published", "title": title}

    try:
        url = "https://creator.douyin.com/creator-micro/content/post/article"
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Dismiss popups
        for _ in range(3):
            dismiss = page.query_selector('text="我知道了"')
            if not dismiss:
                break
            try:
                dismiss.click()
                page.wait_for_timeout(500)
            except Exception:
                break

        # Fill title
        title_input = page.get_by_placeholder("请输入文章标题").first
        title_input.fill(title[:30])
        page.wait_for_timeout(300)

        # Fill subtitle
        if subtitle:
            sub = page.get_by_placeholder("添加内容摘要").first
            sub.fill(subtitle[:30])
            page.wait_for_timeout(300)

        # Fill content
        body = content[:8000] if content else ""
        if tags:
            body += "\n\n" + " ".join(f"#{t}" for t in tags[:5])
        editor = page.locator('[contenteditable="true"]').first
        editor.click()
        page.wait_for_timeout(300)
        editor.fill(body)
        page.wait_for_timeout(500)

        # Upload header image
        if image_path and os.path.exists(image_path):
            upload_area = page.get_by_text("点击上传图片").first
            with page.expect_file_chooser(timeout=10000) as fc_info:
                upload_area.click()
            fc_info.value.set_files(image_path)
            page.wait_for_timeout(3000)
            confirm = page.locator('button:has-text("确定")').last
            confirm.click()
            page.wait_for_timeout(3000)

        if not dry_run:
            publish_btn = page.get_by_role("button", name="发布", exact=True).first
            publish_btn.click()
            page.wait_for_timeout(3000)
            result["status"] = "published"

        logger.info(f"Douyin: Article published: {title[:30]}")
    except Exception as e:
        logger.warning(f"Douyin publish_article failed: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
    finally:
        context.close()
        p.stop()

    return result


def publish_imagetext(title: str, image_paths: list[str],
                      description: str = "", dry_run: bool = False) -> dict[str, Any]:
    p, context, page = _launch_session()
    if not page:
        return {"status": "login_required", "title": title, "error": "login_required"}
    result = {"status": "dry_run" if dry_run else "published", "title": title}

    try:
        url = "https://creator.douyin.com/creator-micro/content/upload?default-tab=3"
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Dismiss popups
        for _ in range(3):
            dismiss = page.query_selector('text="我知道了"')
            if not dismiss:
                break
            try:
                dismiss.click()
                page.wait_for_timeout(500)
            except Exception:
                break

        # Upload images
        if image_paths:
            upload_btn = page.get_by_text("上传图文").first
            with page.expect_file_chooser(timeout=10000) as fc_info:
                upload_btn.click()
            fc_info.value.set_files(image_paths)
            # Wait for images to appear in the upload area
            try:
                page.wait_for_selector('img[src], [class*="upload"] img, [class*="image"]', timeout=15000)
            except Exception:
                page.wait_for_timeout(8000)

        # Fill title
        if title:
            title_input = page.get_by_placeholder("添加作品标题").first
            title_input.fill(title[:20])
            page.wait_for_timeout(300)

        # Fill description
        if description:
            desc_input = page.get_by_placeholder("添加描述").first
            try:
                desc_input.fill(description[:1000])
            except Exception:
                # Fallback: Tab to next field
                title_input.press("Tab")
                page.wait_for_timeout(300)
                page.keyboard.type(description[:1000])
            page.wait_for_timeout(500)

        if not dry_run:
            publish_btn = page.get_by_role("button", name="发布", exact=True).first
            publish_btn.click()
            page.wait_for_timeout(3000)
            result["status"] = "published"

        logger.info(f"Douyin: Imagetext published: {title[:30]}")
    except Exception as e:
        logger.warning(f"Douyin publish_imagetext failed: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
    finally:
        context.close()
        p.stop()

    return result
