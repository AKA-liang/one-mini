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
import re
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

COMMENT_PAGE_URL = "https://creator.douyin.com/creator-micro/interactive/comment"


def _launch_session():
    """Launch persistent browser session for Douyin creator center."""
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
    context.set_default_timeout(30000)
    return p, context, page


def list_works() -> list[dict[str, Any]]:
    """List all published works from Douyin creator center."""
    p, context, page = _launch_session()
    works: list[dict[str, Any]] = []

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Click "选择作品" button
        select_btn = page.query_selector('button:has-text("选择作品"), [role="button"]:has-text("选择作品")')
        if not select_btn:
            logger.warning("Douyin: '选择作品' button not found — may need manual login")
            return []

        select_btn.first.click()
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
                const isReplied = !replyBtn || replyBtn.textContent.includes('已回复');
                if (isReplied) continue;
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
