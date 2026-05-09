"""
Persistent Edge browser manager — launches Edge once, keeps it alive.
All spiders share the same browser via CDP (Chrome DevTools Protocol).

Usage:
    manager = BrowserManager()
    await manager.start()
    page = await manager.new_page()
    # ... do work ...
    await page.close()
    # browser stays alive
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

_EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_CDP_PORT = 9222
_CDP_URL = f"http://localhost:{_CDP_PORT}"


class BrowserManager:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._browser: Any = None
        self._playwright: Any = None
        self._started = False

    async def start(self) -> None:
        """Launch Edge and connect Playwright via CDP."""
        if self._started:
            return

        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        # Try connecting first (Edge might already be running with CDP)
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(_CDP_URL)
            logger.info(f"Browser: Connected to existing Edge on port {_CDP_PORT}")
            self._started = True
            return
        except Exception:
            pass

        # Launch Edge like a user double-clicking the desktop shortcut
        from app.config import settings

        cmd = [
            _EDGE_EXE,
            f"--profile-directory={settings.edge_profile_dir}",
            f"--remote-debugging-port={_CDP_PORT}",
        ]
        logger.info(f"Browser: Launching Edge: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # Try alternative path
            alt_exe = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            cmd[0] = alt_exe
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Wait for CDP port to become available
        for i in range(30):
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(_CDP_URL)
                logger.info(f"Browser: Edge started and connected (CDP port {_CDP_PORT})")
                self._started = True
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise RuntimeError(f"Edge failed to start within 15s on port {_CDP_PORT}")

    async def new_page(self):
        """Create a new tab in the persistent browser."""
        if not self._started:
            await self.start()
        # Use the first context (there's always one with persistent/profile)
        contexts = self._browser.contexts
        if not contexts:
            contexts = [await self._browser.new_context()]
        ctx = contexts[0]
        page = await ctx.new_page()
        return page

    async def shutdown(self):
        """Close browser connection (Edge stays alive)."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._started = False
        logger.info("Browser: Playwright disconnected (Edge still running)")

    async def kill(self):
        """Force-kill the Edge process."""
        await self.shutdown()
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        logger.info("Browser: Edge process terminated")


# Singleton
_browser_instance: BrowserManager | None = None


async def get_browser() -> BrowserManager:
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = BrowserManager()
        await _browser_instance.start()
    return _browser_instance
