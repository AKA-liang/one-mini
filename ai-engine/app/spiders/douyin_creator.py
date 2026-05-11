"""
Douyin Creator spider — comment management via Playwright persistent_context.
Rewritten with SQLite dedup, multi-tier extraction, and scroll management.

Three functions:
  list_works() → [{title, publishTime}]
  export_comments(work_title) → [{username, commentText, imageUrls}]
  reply_comments(reply_plan, work_title) → {results: [...]}
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from typing import Any

from app.config import settings
from app.spiders.douyin_db import (
    upsert_comments as db_upsert,
    get_reply_count_map,
    increment_reply_count,
    get_user_history,
)

logger = logging.getLogger(__name__)

COMMENT_PAGE_URL = "https://creator.douyin.com/creator-micro/interactive/comment"
_session_lock = threading.Lock()
META_PATTERN = re.compile(r"发布于|\d{4}[/-]\d|赞|回复|举报|置顶")
CONTROL_PATTERN = re.compile(r"^(回复|收起|暂无|没有更多|条回复)$")


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


# ─── Scroll Container Detection ─────────────────────────────────────────


def _find_comment_scroll_container(page) -> bool:
    """Mark the best comment scroll container with data-codex-comment-scroll attr.
    Scores elements by overflow style + reply-button density + scrollDelta."""
    found = page.evaluate("""
    () => {
        const marker = "data-codex-comment-scroll";
        document.querySelectorAll(`[${marker}]`).forEach(el => el.removeAttribute(marker));
        const elements = [document.documentElement, document.body];
        document.querySelectorAll("main, section, div").forEach(n => elements.push(n));

        let best = null, bestScore = -1;
        for (const el of elements) {
            if (!(el instanceof HTMLElement)) continue;
            const style = window.getComputedStyle(el);
            const overflowY = style.overflowY;
            const scrollable = overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay";
            const delta = el.scrollHeight - el.clientHeight;
            let markerCount = 0;
            el.querySelectorAll("button, div, span").forEach(n => {
                const t = (n.textContent || "").trim();
                if (t === "回复" || t.includes("条回复") || t === "收起") markerCount++;
            });
            if (markerCount === 0) continue;
            const score = markerCount * 20 + (scrollable ? 100 : 0)
                        + Math.max(delta, 0) / 50 + Math.max(el.clientHeight, 0) / 25;
            if (score > bestScore) { bestScore = score; best = el; }
        }
        const target = best instanceof HTMLElement ? best
            : (document.scrollingElement instanceof HTMLElement ? document.scrollingElement
            : document.documentElement);
        target.setAttribute(marker, "true");
        return true;
    }
    """)
    return bool(found)


# ─── Unreplied Filter ────────────────────────────────────────────────────


def _apply_unreplied_filter(page) -> bool:
    """Click the comment status filter dropdown and select '未回复' option."""
    try:
        combo = page.locator('div[role="combobox"].douyin-creator-interactive-select').first
        try:
            combo.wait_for(state="visible", timeout=5000)
        except Exception:
            return False
        txt = (combo.inner_text() or "").replace("\n", " ").strip()
        if "未回复" in txt:
            return True  # already set

        combo.click()
        try:
            page.locator(".douyin-creator-interactive-select-option").first.wait_for(
                state="visible", timeout=5000)
        except Exception:
            return False

        options = page.locator(".douyin-creator-interactive-select-option")
        count = options.count()
        for i in range(count):
            opt = options.nth(i)
            opt_text = (opt.inner_text() or "").replace("\n", " ").strip()
            if opt_text == "未回复":
                opt.click()
                page.wait_for_timeout(2000)
                combo_txt = (combo.inner_text() or "").replace("\n", " ").strip()
                if "未回复" in combo_txt:
                    return True
                break
        return False
    except Exception as e:
        logger.warning(f"Douyin: apply_unreplied_filter failed: {e}")
        return False


# ─── Comment Snapshot Extraction ──────────────────────────────────────────


def _extract_comment_snapshot(page) -> list[dict[str, Any]]:
    """Multi-tier extraction: class selectors → reply-button blocks → text-line fallback."""
    return page.evaluate("""
    () => {
        const normalize = (s) => (s || "").replace(/\\s+/g, " ").trim();
        const metaPattern = /发布于|\\d{4}[/-]\\d|赞|举报|置顶/i;
        const controlPattern = /^(回复|收起|没有更多评论|暂无符合条件的评论)$/;
        const extractImageUrls = (el) => {
            return Array.from(el.querySelectorAll('img.douyin-creator-interactive-image-img, img[class*="comment"]'))
                .map(img => img.src || img.getAttribute("data-src") || "").filter(Boolean);
        };

        const blocks = [];
        const explicitNodes = document.querySelectorAll('[comment-item]');
        if (explicitNodes.length > 0) {
            explicitNodes.forEach(n => blocks.push(n));
        } else {
            // Fallback: find reply-button parent blocks
            const replyBtns = document.querySelectorAll('button');
            const seen = new Set();
            replyBtns.forEach(btn => {
                if ((btn.textContent || "").trim() !== "回复") return;
                let parent = btn.parentElement;
                for (let i = 0; i < 4 && parent; i++) {
                    if (parent.children.length >= 2 && parent.offsetHeight > 40) {
                        if (!seen.has(parent)) { seen.add(parent); blocks.push(parent); }
                        break;
                    }
                    parent = parent.parentElement;
                }
            });
        }

        const results = [];
        for (let order = 0; order < blocks.length; order++) {
            const block = blocks[order];
            if (!(block instanceof HTMLElement)) continue;

            // Tier 1: Douyin class selectors
            const commentEl = block.querySelector('div[class*="comment-content-text-"]');
            if (commentEl) {
                const commentText = normalize(commentEl.textContent || "");
                const usernameEl = block.querySelector('div[class*="username-"]');
                let username = "";
                if (usernameEl) {
                    for (const node of usernameEl.childNodes) {
                        if (node.nodeType === 3) username += node.textContent || "";
                    }
                    username = normalize(username);
                }
                if (username && commentText) {
                    const entry = { username, commentText, order };
                    const imgs = extractImageUrls(block);
                    if (imgs.length > 0) entry.imageUrls = imgs;
                    results.push(entry);
                    continue;
                }
            }

            // Tier 2: Text-line parsing from full innerText
            const lines = (block.innerText || "").split("\\n").map(l => normalize(l)).filter(Boolean);
            if (lines.length < 2) continue;
            let username = "";
            let commentStart = 1;
            for (let i = 0; i < Math.min(lines.length, 6); i++) {
                const line = lines[i];
                if (line.length > 40 || metaPattern.test(line) || controlPattern.test(line)) continue;
                username = line;
                commentStart = i + 1;
                break;
            }
            if (!username) continue;
            const commentLines = lines.slice(commentStart).filter(
                l => !metaPattern.test(l) && !controlPattern.test(l) && l.length < 200
            );
            const commentText = commentLines.join(" ").substring(0, 500);
            if (commentText.length < 1) continue;
            const entry = { username, commentText, order };
            const imgs = extractImageUrls(block);
            if (imgs.length > 0) entry.imageUrls = imgs;
            results.push(entry);
        }
        return results;
    }
    """)


def _comment_fingerprint(page) -> str:
    """Hash first 5 visible comment usernames to detect DOM changes after scroll."""
    data = page.evaluate("""
    () => {
        const items = document.querySelectorAll('[comment-item]');
        const texts = [];
        for (let i = 0; i < Math.min(items.length, 5); i++) {
            texts.push((items[i].innerText || "").substring(0, 30));
        }
        return texts.join("|");
    }
    """)
    return hashlib.md5(data.encode()).hexdigest()[:12]


def _comment_terminal(page) -> str | None:
    """Detect 'no more comments' / 'no matching comments' end-of-list signals."""
    return page.evaluate("""
    () => {
        const body = document.body.innerText || "";
        if (body.includes("没有更多评论")) return "no_more";
        if (body.includes("暂无符合条件的评论")) return "no_match";
        return null;
    }
    """)


# ─── Scroll-Based Comment Collection ──────────────────────────────────────


def _collect_comments_scroll(page, limit: int = 200, timeout_s: int = 60) -> list[dict[str, Any]]:
    """Main scroll loop: fingerprint detect → snapshot → dedup → scroll → repeat."""
    collected: dict[str, dict] = {}  # signature → entry
    started = time.time()
    stalled = 0

    while time.time() - started < timeout_s:
        snapshot = _extract_comment_snapshot(page)
        added = 0
        for entry in snapshot:
            sig = f"{entry.get('username','')}||{entry.get('commentText','')}"
            if sig not in collected:
                collected[sig] = entry
                added += 1

        terminal = _comment_terminal(page)
        if terminal:
            logger.info(f"Douyin: collect reached terminal: {terminal}")
            break

        if len(collected) >= limit:
            break

        before_fp = _comment_fingerprint(page)

        # Scroll: try container JS scroll, fall back to mouse wheel
        scroll_moved = page.evaluate("""
        () => {
            const c = document.querySelector('[data-codex-comment-scroll="true"]');
            const target = c instanceof HTMLElement ? c : (document.scrollingElement || document.documentElement);
            const before = target.scrollTop;
            target.scrollTop += Math.max(target.clientHeight * 0.9, 400);
            return target.scrollTop > before;
        }
        """)
        if not scroll_moved:
            page.mouse.wheel(0, 600)

        # Wait for DOM to update
        for _ in range(12):
            page.wait_for_timeout(200)
            cur_fp = _comment_fingerprint(page)
            if cur_fp != before_fp:
                break

        # Post-scroll snapshot
        snapshot2 = _extract_comment_snapshot(page)
        for entry in snapshot2:
            sig = f"{entry.get('username','')}||{entry.get('commentText','')}"
            if sig not in collected:
                collected[sig] = entry
                added += 1

        terminal2 = _comment_terminal(page)
        if terminal2:
            logger.info(f"Douyin: collect reached terminal after scroll: {terminal2}")
            break

        if len(collected) >= limit:
            break

        if added > 0 or scroll_moved:
            stalled = 0
        else:
            stalled += 1

        if stalled >= 6:
            break

        if stalled >= 2 and (time.time() - started > 15):
            # No progress in ~15s, likely end of list
            break

    results = sorted(collected.values(), key=lambda x: x.get("order", 0))[:limit]
    return results


# ─── Work Title Matching ──────────────────────────────────────────────────


def _normalize_title(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _match_work_in_panel(page, work_title: str) -> bool:
    """Find and click the target work in the side panel. 3-tier: exact → fuzzy → prefix."""
    wt = _normalize_title(work_title)
    clicked = page.evaluate(f"""
    () => {{
        const panel = document.querySelector('.douyin-creator-interactive-sidesheet-body');
        if (!panel) return false;
        const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();
        const cards = panel.querySelectorAll('[class*="work"], [class*="item"], [class*="card"]');
        let best = null, bestScore = 0;

        for (const card of cards) {{
            const text = normalize(card.innerText || card.textContent || '');
            const lines = text.split('\\n').filter(l => l.trim());
            if (lines.length < 1) continue;
            const title = lines[0];

            // Tier 1: exact match
            if (title === "{_js_escape(wt)}") {{ card.click(); return true; }}
            // Tier 2: fuzzy contains (score by length ratio)
            if (title.includes("{_js_escape(wt)}")) {{
                const score = "{_js_escape(wt)}".length / title.length;
                if (score > bestScore) {{ bestScore = score; best = card; }}
            }}
            // Tier 3: partial word overlap
            else if ("{_js_escape(wt)}".length >= 6) {{
                const overlap = "{_js_escape(wt)}".substring(0, 12);
                if (title.includes(overlap)) {{
                    const score = overlap.length / title.length;
                    if (score > bestScore) {{ bestScore = score; best = card; }}
                }}
            }}
        }}
        if (best) {{ best.click(); return true; }}
        return false;
    }}
    """)
    if clicked:
        page.wait_for_timeout(3000)
        return True
    return False


def _js_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


# ─── list_works ───────────────────────────────────────────────────────────


def list_works() -> list[dict[str, Any]]:
    """List all works with scroll loading + publish-time validation."""
    p, context, page = _launch_session()
    if not page:
        return []
    works: list[dict[str, Any]] = []

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        select_btn = page.locator('button:has-text("选择作品"), [role="button"]:has-text("选择作品")').first
        try:
            select_btn.wait_for(state="visible", timeout=10000)
        except Exception:
            logger.warning("Douyin: '选择作品' button not found")
            context.close()
            p.stop()
            return []
        select_btn.click()
        page.wait_for_timeout(3000)

        # Scroll to load all works
        for _ in range(15):
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(600)
        page.wait_for_timeout(2000)

        # Extract with publish-time validation
        works = page.evaluate("""
        () => {
            const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();
            const panel = document.querySelector('.douyin-creator-interactive-sidesheet-body');
            if (!panel) return [];
            const cards = panel.querySelectorAll('[class*="work"], [class*="item"], [class*="card"]');
            const results = [], seen = new Set();
            for (const card of cards) {
                const text = normalize(card.innerText || card.textContent || '');
                const lines = text.split('\\n').map(l => normalize(l)).filter(Boolean);
                if (lines.length < 2) continue;
                const title = lines[0];
                const publishLine = lines.find(l => /发布于/.test(l) || /\\d{4}[/-]\\d/.test(l)) || '';
                if (title.length < 1 || title.length > 120) continue;
                const key = title + '|' + publishLine;
                if (seen.has(key)) continue;
                seen.add(key);
                results.push({ title, publishTime: publishLine });
            }
            return results;
        }
        """)
        logger.info(f"Douyin: Found {len(works)} works")
    except Exception as e:
        logger.warning(f"Douyin list_works failed: {e}")
    finally:
        context.close()
        p.stop()

    return works


# ─── export_comments ──────────────────────────────────────────────────────


def export_comments(work_title: str, limit: int = 200) -> dict[str, Any]:
    """Export comments with scroll collection, unreplied filter, and DB dedup."""
    p, context, page = _launch_session()
    if not page:
        return {"selectedWork": {"title": work_title}, "count": 0, "comments": []}
    result: dict[str, Any] = {"selectedWork": {"title": work_title}, "count": 0, "comments": []}

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Open work selector
        select_btn = page.locator('button:has-text("选择作品"), [role="button"]:has-text("选择作品")').first
        try:
            select_btn.wait_for(state="visible", timeout=10000)
        except Exception:
            logger.warning("Douyin: '选择作品' button not found")
            context.close()
            p.stop()
            return result
        select_btn.click()
        page.wait_for_timeout(3000)

        # Select target work
        if not _match_work_in_panel(page, work_title):
            logger.warning(f"Douyin: Work '{work_title[:30]}' not found in panel")
            context.close()
            p.stop()
            return result
        page.wait_for_timeout(4000)

        # Apply unreplied filter
        _apply_unreplied_filter(page)
        page.wait_for_timeout(2000)

        # Find and mark scroll container
        _find_comment_scroll_container(page)

        # Collect comments with scrolling
        all_comments = _collect_comments_scroll(page, limit=limit, timeout_s=90)

        # DB-based dedup: filter out comments already replied to
        reply_map = get_reply_count_map(work_title, all_comments)
        unreplied = []
        for c in all_comments:
            key = f"{c.get('username','')}|||{c.get('commentText','')}"
            if reply_map.get(key, 0) == 0:
                unreplied.append({
                    "username": c.get("username", ""),
                    "commentText": c.get("commentText", ""),
                    "imageUrls": c.get("imageUrls", []),
                    "replyMessage": "",
                })

        # Upsert to DB
        db_upsert(work_title, all_comments)

        # Attach user history
        usernames = list({c["username"] for c in unreplied if c.get("username")})
        histories = get_user_history(usernames)
        for c in unreplied:
            h = histories.get(c["username"], [])
            if h:
                c["history"] = h[:5]

        result["count"] = len(unreplied)
        result["comments"] = unreplied
        logger.info(f"Douyin: Exported {len(unreplied)} unreplied / {len(all_comments)} total from '{work_title[:30]}'")
    except Exception as e:
        logger.warning(f"Douyin export_comments failed: {e}")
    finally:
        context.close()
        p.stop()

    return result


# ─── Reply Matching + Reply Flow ──────────────────────────────────────────


def _match_reply_target(page, username: str, comment_text: str = "") -> bool:
    """Two-tier: username match → if ambiguous, username+commentText disambiguation."""
    un = _normalize_title(username)[:30]
    ct = _normalize_title(comment_text)[:100] if comment_text else ""
    found = page.evaluate(f"""
    () => {{
        const items = document.querySelectorAll('[comment-item]');
        const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();

        // Tier 1: exact username match → check if unique
        const matches = [];
        for (const item of items) {{
            if (item.innerText.includes("{_js_escape(un)}")) {{
                const btn = item.querySelector('button');
                const allBtns = item.querySelectorAll('button');
                const replyBtn = Array.from(allBtns).find(b => (b.textContent||'').trim() === '回复');
                if (replyBtn) matches.push(replyBtn);
            }}
        }}

        if (matches.length === 1) {{ matches[0].click(); return true; }}
        if (matches.length > 1 && "{_js_escape(ct)}") {{
            // Tier 2: disambiguate by comment text
            for (const item of items) {{
                const text = normalize(item.innerText || '');
                if (text.includes("{_js_escape(un)}") && (
                    text.includes("{_js_escape(ct)}") ||
                    "{_js_escape(ct)}".includes(text.substring(0, 30))
                )) {{
                    const replyBtn = Array.from(item.querySelectorAll('button'))
                        .find(b => (b.textContent||'').trim() === '回复');
                    if (replyBtn) {{ replyBtn.click(); return true; }}
                }}
            }}
        }}
        return false;
    }}
    """)
    return bool(found)


def _safe_reply_one(page, reply_msg: str) -> dict[str, str]:
    """Multi-stage reply: click reply → find input → type with delay → wait send → click send."""
    page.wait_for_timeout(800)

    # Find the reply input (after clicking reply button)
    try:
        inp = page.locator('[contenteditable="true"], textarea, input[type="text"]').first
        inp.wait_for(state="visible", timeout=8000)
    except Exception:
        return {"status": "input_not_found"}

    # Clear, then type with delay
    page.wait_for_timeout(300)
    try:
        inp.fill("")
        page.wait_for_timeout(200)
        inp.type(reply_msg[:400], delay=30)
        page.wait_for_timeout(500)
    except Exception:
        # Fallback: try keyboard typing
        try:
            inp.click()
            page.wait_for_timeout(200)
            page.keyboard.type(reply_msg[:400], delay=30)
        except Exception as e:
            return {"status": "type_failed", "error": str(e)}

    # Wait for send button to become enabled
    page.wait_for_timeout(300)
    try:
        send_btn = page.locator('button:has-text("发送"), button:has-text("发表"), [role="button"]:has-text("发送")').first
        send_btn.wait_for(state="visible", timeout=5000)
        # Small additional wait for button to become clickable
        page.wait_for_timeout(300)
        send_btn.click()
        page.wait_for_timeout(1200)
        return {"status": "replied"}
    except Exception as e:
        # Fallback: press Enter
        try:
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            return {"status": "replied_enter"}
        except Exception:
            return {"status": "send_failed", "error": str(e)}


# ─── reply_comments ───────────────────────────────────────────────────────


def reply_comments(reply_plan: list[dict[str, Any]], work_title: str) -> dict[str, Any]:
    """Batch reply with two-tier matching and DB tracking."""
    p, context, page = _launch_session()
    if not page:
        return {"total": 0, "replied": 0, "results": [], "error": "login_required"}
    results: list[dict] = []

    try:
        page.goto(COMMENT_PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        select_btn = page.locator('button:has-text("选择作品"), [role="button"]:has-text("选择作品")').first
        try:
            select_btn.wait_for(state="visible", timeout=10000)
        except Exception:
            logger.warning("Douyin: '选择作品' button not found")
            context.close()
            p.stop()
            return {"total": len(reply_plan), "replied": 0, "results": []}
        select_btn.click()
        page.wait_for_timeout(3000)

        if not _match_work_in_panel(page, work_title):
            logger.warning(f"Douyin: Work '{work_title[:30]}' not found for reply")
            context.close()
            p.stop()
            return {"total": len(reply_plan), "replied": 0, "results": []}
        page.wait_for_timeout(4000)

        # Apply unreplied filter
        _apply_unreplied_filter(page)
        page.wait_for_timeout(2000)

        # Reply loop
        for plan in reply_plan[:20]:
            username = plan.get("username", "")
            reply_msg = plan.get("replyMessage", "")
            comment_text = plan.get("commentText", "")
            if not reply_msg or len(reply_msg) > 400:
                continue

            # Match and click reply button
            if not _match_reply_target(page, username, comment_text):
                results.append({"username": username, "status": "not_found"})
                continue

            # Execute reply
            r = _safe_reply_one(page, reply_msg)
            r["username"] = username
            results.append(r)

            # Track in DB
            if r.get("status") in ("replied", "replied_enter"):
                increment_reply_count(work_title, username, comment_text)

        # Upsert reply results to DB
        for plan in reply_plan[:20]:
            un = plan.get("username", "")
            rm = plan.get("replyMessage", "")
            ct = plan.get("commentText", "")
            if un and ct and rm:
                db_upsert(work_title,
                          [{"username": un, "commentText": ct, "replyMessage": rm}])

    except Exception as e:
        logger.warning(f"Douyin reply_comments failed: {e}")
    finally:
        context.close()
        p.stop()

    return {"total": len(reply_plan), "replied": sum(1 for r in results if "replied" in r.get("status", "")),
            "results": results}


# ─── publish_article ──────────────────────────────────────────────────────


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

        for _ in range(3):
            dismiss = page.query_selector('text="我知道了"')
            if not dismiss:
                break
            try:
                dismiss.click()
                page.wait_for_timeout(500)
            except Exception:
                break

        title_input = page.get_by_placeholder("请输入文章标题").first
        title_input.fill(title[:30])
        page.wait_for_timeout(300)

        if subtitle:
            sub = page.get_by_placeholder("添加内容摘要").first
            sub.fill(subtitle[:30])
            page.wait_for_timeout(300)

        body = content[:8000] if content else ""
        if tags:
            body += "\n\n" + " ".join(f"#{t}" for t in tags[:5])
        editor = page.locator('[contenteditable="true"]').first
        editor.click()
        page.wait_for_timeout(300)
        editor.fill(body)
        page.wait_for_timeout(500)

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


# ─── publish_imagetext ────────────────────────────────────────────────────


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

        for _ in range(3):
            dismiss = page.query_selector('text="我知道了"')
            if not dismiss:
                break
            try:
                dismiss.click()
                page.wait_for_timeout(500)
            except Exception:
                break

        if image_paths:
            upload_btn = page.get_by_text("上传图文").first
            with page.expect_file_chooser(timeout=10000) as fc_info:
                upload_btn.click()
            fc_info.value.set_files(image_paths)
            try:
                page.wait_for_selector('img[src], [class*="upload"] img, [class*="image"]', timeout=15000)
            except Exception:
                page.wait_for_timeout(8000)

        if title:
            title_input = page.get_by_placeholder("添加作品标题").first
            title_input.fill(title[:20])
            page.wait_for_timeout(300)

        if description:
            desc_input = page.get_by_placeholder("添加描述").first
            try:
                desc_input.fill(description[:1000])
            except Exception:
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
