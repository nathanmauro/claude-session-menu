"""rumps-based menu bar: list sessions, smart open/focus on click."""
from __future__ import annotations

import rumps

from claude_session_menu import launcher, processes, sessions

REFRESH_SECS = 15
MAX_RUNNING_ITEMS = 20
MAX_RECENT_ITEMS = 20


class ClaudeSessionApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("CC", quit_button=None)
        self._build_menu()
        self._timer = rumps.Timer(self._on_tick, REFRESH_SECS)
        self._timer.start()

    def _on_tick(self, _: rumps.Timer) -> None:
        self._build_menu()

    def _build_menu(self) -> None:
        all_sess = sessions.list_sessions()
        running = processes.list_running()
        running_map = {r.session_id: r for r in running}

        running_sessions = [s for s in all_sess if s.session_id in running_map]
        running_sessions.sort(key=lambda s: s.mtime, reverse=True)
        recent = [s for s in all_sess if s.session_id not in running_map][:MAX_RECENT_ITEMS]

        self.title = f"CC{len(running_sessions)}" if running_sessions else "CC"

        self.menu.clear()
        if running_sessions:
            self.menu.add(rumps.MenuItem(f"— Running ({len(running_sessions)}) —", callback=None))
            for s in running_sessions[:MAX_RUNNING_ITEMS]:
                self.menu.add(self._session_item(s, running=True))
            self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("— Recent —", callback=None))
        for s in recent:
            self.menu.add(self._session_item(s, running=False))

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Refresh", callback=self._refresh))
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    def _session_item(self, s: sessions.Session, running: bool) -> rumps.MenuItem:
        proj = s.project_name
        title = sessions.session_display_title(s, maxlen=48)
        bullet = "● " if running else "  "
        label = f"{bullet}[{proj}] {title}"
        item = rumps.MenuItem(label, callback=self._on_session_click)
        item._sid = s.session_id  # type: ignore[attr-defined]
        item._cwd = s.cwd  # type: ignore[attr-defined]
        return item

    def _on_session_click(self, sender: rumps.MenuItem) -> None:
        sid = getattr(sender, "_sid", None)
        cwd = getattr(sender, "_cwd", None)
        if not sid or not cwd:
            return
        running = processes.find_running(sid)
        if running and running.terminal_pid:
            launcher.focus_pid(running.terminal_pid)
            return
        if running and running.terminal_app:
            launcher.focus_app(running.terminal_app)
            return
        launcher.open_new(cwd, sid)

    def _refresh(self, _: rumps.MenuItem) -> None:
        self._build_menu()


def main() -> None:
    ClaudeSessionApp().run()


if __name__ == "__main__":
    main()
