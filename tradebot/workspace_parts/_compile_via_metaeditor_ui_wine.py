from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _compile_via_metaeditor_ui_wine(runtime: Mt5RuntimePaths) -> None:
    """Compile `live.mq5` via MetaEditor UI automation under Wine/X11."""

    if shutil.which("xdotool") is not None:
        _compile_via_metaeditor_ui_wine_xdotool(runtime)
        return

    try:
        from Xlib import X, XK, display, protocol
        from Xlib.ext import xtest
    except ImportError as exc:
        raise RuntimeError("MetaEditor UI fallback on Linux/Wine requires python-xlib.") from exc

    def keycode(dpy, keysym_name: str) -> int:
        keysym = XK.string_to_keysym(keysym_name)
        if not keysym:
            raise RuntimeError(f"Unsupported X11 keysym for MetaEditor fallback: {keysym_name}")
        code = dpy.keysym_to_keycode(keysym)
        if code == 0:
            raise RuntimeError(f"Could not resolve X11 keycode for MetaEditor fallback: {keysym_name}")
        return code

    def activate_window(dpy, win) -> None:
        root = dpy.screen().root
        try:
            net_active_window = dpy.intern_atom("_NET_ACTIVE_WINDOW")
            event = protocol.event.ClientMessage(
                window=win,
                client_type=net_active_window,
                data=(32, [1, X.CurrentTime, 0, 0, 0]),
            )
            root.send_event(
                event,
                event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
            )
        except Exception:
            pass
        try:
            win.configure(stack_mode=X.Above)
        except Exception:
            pass
        dpy.sync()

    def send_key(dpy, keysym_name: str, modifiers: tuple[str, ...] = ()) -> None:
        modifier_codes = [keycode(dpy, modifier) for modifier in modifiers]
        main_code = keycode(dpy, keysym_name)
        for modifier_code in modifier_codes:
            xtest.fake_input(dpy, X.KeyPress, modifier_code)
        xtest.fake_input(dpy, X.KeyPress, main_code)
        xtest.fake_input(dpy, X.KeyRelease, main_code)
        for modifier_code in reversed(modifier_codes):
            xtest.fake_input(dpy, X.KeyRelease, modifier_code)
        dpy.sync()

    def find_metaeditor_window(dpy):
        root = dpy.screen().root
        for win in root.query_tree().children:
            try:
                wm_class = win.get_wm_class() or ()
                wm_name = win.get_wm_name() or ""
            except Exception:
                continue
            if any("metaeditor" in str(item).lower() for item in wm_class):
                return win
            if "metaeditor" in str(wm_name).lower() or "live.mq5" in str(wm_name).lower():
                return win
        return None

    subprocess.run(
        ["pkill", "-f", "MetaEditor64.exe"],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_env(runtime),
    )

    source_value = to_windows_path(runtime, runtime.deployed_live_mq5)
    previous_ex5_mtime = runtime.deployed_live_ex5.stat().st_mtime if runtime.deployed_live_ex5.exists() else 0.0
    previous_ex5_size = runtime.deployed_live_ex5.stat().st_size if runtime.deployed_live_ex5.exists() else -1
    process = subprocess.Popen(
        ["wine", str(runtime.metaeditor_path), source_value],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        env=runtime_env(runtime),
        start_new_session=True,
    )

    dpy = None
    compiled = False
    try:
        dpy = display.Display()
        deadline = time.time() + 30.0
        window = None
        while time.time() < deadline:
            window = find_metaeditor_window(dpy)
            if window is not None:
                break
            time.sleep(0.5)
        if window is None:
            raise RuntimeError("MetaEditor window did not appear on the X11 display.")

        time.sleep(0.7)
        activate_window(dpy, window)
        time.sleep(0.3)
        send_key(dpy, "F7")

        compile_deadline = time.time() + 60.0
        while time.time() < compile_deadline:
            if runtime.deployed_live_ex5.exists():
                ex5_stat = runtime.deployed_live_ex5.stat()
                if ex5_stat.st_mtime > previous_ex5_mtime or ex5_stat.st_size != previous_ex5_size:
                    compiled = True
                    break
            time.sleep(0.5)

        activate_window(dpy, window)
        time.sleep(0.3)
        send_key(dpy, "F4", modifiers=("Alt_L",))
        time.sleep(1.0)
    finally:
        if dpy is not None:
            try:
                dpy.close()
            except Exception:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)

    if not compiled:
        raise RuntimeError("MetaEditor UI fallback did not update live.ex5.")
