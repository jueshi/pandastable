import whisper
import os
import json
import subprocess
import sys
import threading
import traceback
import base64
import tempfile
import shutil
import math
import urllib.parse

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import simpledialog
from tkinter import ttk
from tkinter import font as tkfont
from datetime import datetime

def install_ffmpeg():
    try:
        # Try to import ffmpeg-python
        import ffmpeg
    except ImportError:
        print("Installing ffmpeg-python...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ffmpeg-python"])
        import ffmpeg

def ensure_ffmpeg_in_path():
    """Ensure the ffmpeg executable is available by checking common Windows locations
    and prepending them to PATH at runtime. Also validates by invoking `ffmpeg -version`.
    """
    # If already available, return quickly
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return
    except Exception:
        pass

    candidates = []
    # Common Windows install locations
    candidates.append(r"C:\\ffmpeg\\bin")
    candidates.append(r"C:\\Program Files\\ffmpeg\\bin")
    candidates.append(r"C:\\Program Files (x86)\\ffmpeg\\bin")
    # Workspace-local `ffmpeg` folder if present
    workspace_ffmpeg_bin = os.path.join(os.getcwd(), "ffmpeg", "bin")
    candidates.append(workspace_ffmpeg_bin)

    for path in candidates:
        if path and os.path.isdir(path) and os.path.isfile(os.path.join(path, "ffmpeg.exe")):
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
            break

    # Validate again; if still missing, raise a clear message
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        print("\nError: FFmpeg executable not found.")
        print("I looked for ffmpeg in the following locations:")
        for p in candidates:
            print(f" - {p}")
        print("\nPlease ensure FFmpeg is installed and that C\\ffmpeg\\bin (or your install's bin folder) is added to your PATH.")
        print("Download: https://ffmpeg.org/download.html or a Windows build from https://www.gyan.dev/ffmpeg/builds/")
        sys.exit(1)

def ensure_yt_dlp_installed():
    try:
        import yt_dlp  # noqa: F401
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])  # actively maintained fork
            import yt_dlp  # noqa: F401
        except Exception:
            print("Failed to install yt-dlp. URL transcription for online videos may not work.")
            return False
    return True

def main():
    # Install required packages and ensure ffmpeg availability
    install_ffmpeg()
    ensure_ffmpeg_in_path()

    # Force-install Send2Trash so deletions go to Recycle Bin
    try:
        import send2trash  # noqa: F401
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Send2Trash"])  # canonical package name
            import send2trash  # noqa: F401
        except Exception:
            # Continue without hard-failing; deletion code will fall back if needed
            pass

    # Try to prepare Markdown rendering deps (markdown + tkhtmlview) and optional rich features
    def ensure_md_preview_deps():
        md_mod = None
        md_render = None
        html_label_cls = None
        try:
            import markdown as _md
            md_mod = _md
            try:
                md_render = _md.markdown
            except Exception:
                md_render = None
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"]) 
                import markdown as _md
                md_mod = _md
                try:
                    md_render = _md.markdown
                except Exception:
                    md_render = None
            except Exception:
                md_mod = None
                md_render = None
        try:
            from tkhtmlview import HTMLLabel as _HTMLLabel
            html_label_cls = _HTMLLabel
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "tkhtmlview"]) 
                from tkhtmlview import HTMLLabel as _HTMLLabel
                html_label_cls = _HTMLLabel
            except Exception:
                html_label_cls = None
        return md_mod, md_render, html_label_cls

    md_module, md_render, HTMLLabel = ensure_md_preview_deps()
    # Try to enable a richer HTML renderer if available
    HtmlFrame = None
    try:
        from tkinterweb import HtmlFrame as _HtmlFrame
        HtmlFrame = _HtmlFrame
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "tkinterweb"]) 
            from tkinterweb import HtmlFrame as _HtmlFrame
            HtmlFrame = _HtmlFrame
        except Exception:
            HtmlFrame = None
    # Optional richer Markdown features
    pygments_formatter = None
    has_pymdown = False
    try:
        # Syntax highlighting
        from pygments.formatters import HtmlFormatter as _HtmlFormatter
        pygments_formatter = _HtmlFormatter()
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pygments"]) 
            from pygments.formatters import HtmlFormatter as _HtmlFormatter
            pygments_formatter = _HtmlFormatter()
        except Exception:
            pygments_formatter = None
    try:
        import pymdownx  # noqa: F401
        has_pymdown = True
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pymdown-extensions"]) 
            import pymdownx  # noqa: F401
            has_pymdown = True
        except Exception:
            has_pymdown = False

    # Load Whisper model once with retry on checksum mismatch
    def _whisper_model_path(cache_dir: str, name: str) -> str:
        try:
            return os.path.join(cache_dir, f"{name}.pt")
        except Exception:
            return ""

    def _remove_cached_model(cache_dir: str, name: str):
        try:
            p = _whisper_model_path(cache_dir, name)
            if p and os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass

    def load_whisper_model_with_retry(name: str = "small"):
        print("Loading Whisper model (this may take a moment)...")
        primary_cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        alt_cache = os.path.join(os.getcwd(), "whisper_models_cache")
        try:
            os.makedirs(primary_cache, exist_ok=True)
        except Exception:
            pass
        try:
            os.makedirs(alt_cache, exist_ok=True)
        except Exception:
            pass
        # Attempt 1: use primary cache
        try:
            return whisper.load_model(name, download_root=primary_cache)
        except RuntimeError as e:
            if "checksum" not in str(e).lower():
                raise
            # Clear potentially corrupted file and try alt cache
            _remove_cached_model(primary_cache, name)
        # Attempt 2: alt cache, after clearing alt as well
        _remove_cached_model(alt_cache, name)
        return whisper.load_model(name, download_root=alt_cache)

    # Start with a lightweight model for quick startup; can be changed from UI
    model = load_whisper_model_with_retry("small")

    # Build GUI
    root = tk.Tk()
    root.title("Audio to Text (Whisper)")
    root.geometry("900x600")

    # UI Elements
    status_var = tk.StringVar(value="Ready. Click 'Select Audio' to transcribe.")
    current_file_var = tk.StringVar(value="No file selected.")
    output_path_var = tk.StringVar(value="")
    # Single status bar: file + status + model + legend
    status_bar_var = tk.StringVar(value="")
    def _refresh_status_bar(*_):
        try:
            cf = current_file_var.get() or ""
            st = status_var.get() or ""
            sep = "  —  " if cf and st else ""
            # Model
            try:
                mdl = f"  |  Model: {current_model_name.get()}"
            except Exception:
                mdl = ""
            legend = "  |  Legend: 🎥 video"
            status_bar_var.set(f"{cf}{sep}{st}{mdl}{legend}")
        except Exception:
            pass
    try:
        status_var.trace_add("write", _refresh_status_bar)
        current_file_var.trace_add("write", _refresh_status_bar)
    except Exception:
        pass

    # header = tk.Label(root, text="Audio to Text", font=("Segoe UI", 12, "bold"))
    # header.pack(pady=(6, 2))

    frame = tk.Frame(root)
    frame.pack(fill=tk.X, padx=8)

    select_btn = tk.Button(frame, text="Select Audio", width=12)
    select_btn.pack(side=tk.LEFT)

    transcribe_url_btn = tk.Button(frame, text="Transcribe URL", width=14)
    transcribe_url_btn.pack(side=tk.LEFT, padx=(6, 0))

    browse_btn = tk.Button(frame, text="Browse Folder", width=12)
    browse_btn.pack(side=tk.LEFT, padx=(6, 0))

    transcribe_sel_btn = tk.Button(frame, text="Transcribe Selected", width=20)
    transcribe_sel_btn.pack(side=tk.LEFT, padx=(8, 0))

    auto_fit_btn = tk.Button(frame, text="Auto-fit Columns", width=14)
    auto_fit_btn.pack(side=tk.LEFT, padx=(6, 0))

    add_md_btn = tk.Button(frame, text="Add MD Only", width=14)
    add_md_btn.pack(side=tk.LEFT, padx=(8, 0))

    # Move group (audio/txt/md) for selected row
    move_group_btn = tk.Button(frame, text="Move Group", width=12)
    move_group_btn.pack(side=tk.LEFT, padx=(6, 0))

    # Initialize Tk variables now that root exists
    current_model_name = tk.StringVar(value="small")
    # Model display stringvar available to both toolbar tab and status area
    model_display_var = tk.StringVar(value=f"Model: {current_model_name.get()}")

    # Model selection and load button
    model_label = tk.Label(frame, text="Model:")
    model_label.pack(side=tk.LEFT, padx=(8, 2))
    model_choices = ["small", "medium", "large-v2"]
    model_combo = ttk.Combobox(frame, textvariable=current_model_name, values=model_choices, width=10, state="readonly")
    model_combo.pack(side=tk.LEFT)
    try:
        current_model_name.trace_add("write", _refresh_status_bar)
    except Exception:
        pass
    # Bind Enter key to trigger model load
    try:
        model_combo.bind("<Return>", lambda e: on_load_model())
    except Exception:
        pass

    loading_model = {"value": False}

    def on_load_model():
        if loading_model["value"]:
            return
        name = current_model_name.get().strip() or "small"
        loading_model["value"] = True
        set_status(f"Loading model: {name}…")
        def worker():
            nonlocal model
            try:
                new_model = load_whisper_model_with_retry(name)
                model = new_model
                set_status(f"Loaded model: {name}")
                try:
                    model_display_var.set(f"Model: {name}")
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Load Model Failed", str(e))
                # revert selection on failure
                try:
                    current_model_name.set("small")
                except Exception:
                    pass
            finally:
                loading_model["value"] = False
        threading.Thread(target=worker, daemon=True).start()

    load_model_btn = tk.Button(frame, text="Load", width=6, command=on_load_model)
    load_model_btn.pack(side=tk.LEFT, padx=(4, 0))

    # Stop/Break button to cancel batch loops
    stop_event = threading.Event()
    def on_stop():
        stop_event.set()
        set_status("Stopping… will abort after current file.")
        try:
            transcribe_sel_btn.configure(text="Stopping…")
        except Exception:
            pass
    stop_btn = tk.Button(frame, text="Stop transcription", width=16, command=on_stop)
    stop_btn.pack(side=tk.LEFT, padx=(8, 0))

    # Language selector: Auto or pick a specific Whisper language
    language_label = tk.Label(frame, text="Language:")
    language_label.pack(side=tk.LEFT, padx=(8, 2))
    language_var = tk.StringVar(value="Auto")
    # Common Whisper-supported languages (label -> code)
    _LANG_OPTIONS = [
        ("Auto", None),
        ("English", "en"),
        ("Chinese", "zh"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("German", "de"),
        ("Japanese", "ja"),
        ("Korean", "ko"),
        ("Portuguese", "pt"),
        ("Italian", "it"),
        ("Russian", "ru"),
        ("Hindi", "hi"),
        ("Arabic", "ar"),
        ("Dutch", "nl"),
        ("Turkish", "tr"),
        ("Polish", "pl"),
        ("Swedish", "sv"),
        ("Danish", "da"),
        ("Norwegian", "no"),
        ("Finnish", "fi"),
        ("Greek", "el"),
        ("Czech", "cs"),
        ("Ukrainian", "uk"),
        ("Vietnamese", "vi"),
        ("Thai", "th"),
        ("Indonesian", "id"),
        ("Malay", "ms"),
        ("Hebrew", "he"),
    ]
    language_labels = [lbl for (lbl, _) in _LANG_OPTIONS]
    language_combo = ttk.Combobox(frame, textvariable=language_var, values=language_labels, width=14, state="readonly")
    language_combo.pack(side=tk.LEFT)

    def _selected_language_code() -> str | None:
        try:
            sel = language_var.get()
            for lbl, code in _LANG_OPTIONS:
                if lbl == sel:
                    return code
        except Exception:
            pass
        return None

    # Accent bias (helps with Indian English pronunciation and terms)
    indian_bias_var = tk.BooleanVar(value=True)
    indian_bias_chk = tk.Checkbutton(frame, text="Indian English bias", variable=indian_bias_var)
    indian_bias_chk.pack(side=tk.LEFT, padx=(8, 0))

    # Stability Mode: enable beam search for steadier output (slower)
    stability_var = tk.BooleanVar(value=False)
    stability_chk = tk.Checkbutton(frame, text="Stability Mode (beam)", variable=stability_var)
    stability_chk.pack(side=tk.LEFT, padx=(8, 0))

    # Fast decode: greedy, temperature=0 (overrides Stability when ON)
    fast_decode_var = tk.BooleanVar(value=False)
    fast_decode_chk = tk.Checkbutton(frame, text="Fast Decode", variable=fast_decode_var)
    fast_decode_chk.pack(side=tk.LEFT, padx=(8, 0))

    def _selected_initial_prompt() -> str | None:
        # Provide an English bias prompt only when English is explicitly selected; augment for Indian English
        try:
            base = None
            if _selected_language_code() == 'en':
                base = "Transcribe the following English speech."
                if indian_bias_var.get():
                    base += " The speaker has an Indian English accent; prefer standard English words, keep technical terms as spoken, and avoid filling repeated phrases."
            return base
        except Exception:
            return None

    # Output mode selector
    output_label = tk.Label(frame, text="Output:")
    output_label.pack(side=tk.LEFT, padx=(8, 2))
    output_mode_var = tk.StringVar(value="Same Language")
    output_mode_combo = ttk.Combobox(
        frame,
        textvariable=output_mode_var,
        values=["Same Language", "English (Translate)", "Chinese (Translate)"],
        width=20,
        state="readonly",
    )
    output_mode_combo.pack(side=tk.LEFT)

    # Install translator on demand
    def ensure_deep_translator_installed() -> bool:
        try:
            import deep_translator  # noqa: F401
            return True
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])  # lightweight Google Translate wrapper
                import deep_translator  # noqa: F401
                return True
            except Exception:
                append_log("Failed to install deep-translator; Chinese translation unavailable.")
                return False

    def translate_text(text: str, target_lang: str) -> str:
        try:
            from deep_translator import GoogleTranslator
            # Use auto source detection; target: 'zh-CN' for Chinese
            return GoogleTranslator(source='auto', target=target_lang).translate(text or "")
        except Exception as e:
            append_log(f"Translation failed: {e}")
            return text

    def compute_transcribe_args() -> dict:
        """Return kwargs for model.transcribe based on UI selections.
        Tuned to reduce repetitions and mis-detections.
        """
        lang = _selected_language_code()
        mode = output_mode_var.get()
        init_prompt = _selected_initial_prompt()

        # Base args: reduce variability + repetition
        args = dict(
            fp16=False,
            verbose=True,
            language=lang,
            task='transcribe',
            temperature=0,
            initial_prompt=init_prompt,
            # repetition/garble safeguards
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,   # drop overly repetitive segments
            logprob_threshold=-1.0,             # drop very low-confidence segments
            no_speech_threshold=0.3,            # be more willing to skip silence/music
        )

        # Beam search for stability when toggled (slower)
        if stability_var.get():
            args.update(beam_size=5, best_of=5)

        # Fast decode overrides beam search; enforce greedy
        if fast_decode_var.get():
            args['temperature'] = 0.0
            # Remove beam-related args if present
            try:
                args.pop('beam_size', None)
                args.pop('best_of', None)
            except Exception:
                pass

        # If we are specifically targeting English output, override to English
        if indian_bias_var.get() and (lang is None or lang != 'en'):
            # When biasing Indian English, force language to English if user hasn't explicitly chosen another
            args['language'] = 'en'

        if mode == "English (Translate)":
            # Whisper translate mode outputs English
            args.update(task='translate', language='en', initial_prompt=_selected_initial_prompt())
        elif mode == "Chinese (Translate)":
            # Keep task=transcribe in source language; we'll post-translate Chinese after
            pass
        return args

    # Recent folders: dropdown with auto-fit width and +/- adjusters + open button
    recent_label = tk.Label(frame, text="Recent:")
    recent_label.pack(side=tk.LEFT, padx=(8, 4))
    recent_var = tk.StringVar(value="")
    recent_width_var = tk.IntVar(value=30)
    recent_combo = ttk.Combobox(frame, textvariable=recent_var, width=recent_width_var.get(), state="readonly")
    recent_combo.pack(side=tk.LEFT, padx=(0, 4))
    # Change selection -> switch file list
    try:
        recent_combo.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())
    except Exception:
        pass

    def update_recent_combo_width(candidates: list[str] | None = None):
        try:
            # Choose primary widget (prefer the toolbar tab combobox if available)
            try:
                target_widget = recent_combo_tab  # defined later; safe if exists
            except Exception:
                target_widget = recent_combo
            # Determine the longest string width in pixels based on the chosen widget
            font_obj = tkfont.nametofont(str(target_widget.cget("font"))) if target_widget.cget("font") else tkfont.nametofont("TkDefaultFont")
        except Exception:
            font_obj = tkfont.nametofont("TkDefaultFont")
        try:
            # Use provided candidates, otherwise read from whichever widget currently holds values
            if candidates is not None:
                vals = candidates
            else:
                try:
                    vals = list(recent_combo_tab["values"]) if recent_combo_tab["values"] else []
                except Exception:
                    vals = list(recent_combo["values"]) if recent_combo["values"] else []
        except Exception:
            vals = []
        samples = [str(v) for v in vals if v]
        cur = recent_var.get()
        if cur:
            samples.append(str(cur))
        try:
            max_px = max([font_obj.measure(s) for s in samples], default=0)
        except Exception:
            max_px = 0
        try:
            avg_px = font_obj.measure("0") or 7
        except Exception:
            avg_px = 7
        # Convert pixels to approximate character width, add padding
        width_chars = int(math.ceil((max_px + 24) / max(1, avg_px)))
        width_chars = max(20, min(100, width_chars))
        try:
            recent_width_var.set(width_chars)
            # Apply to both widgets if present
            try:
                recent_combo_tab.configure(width=width_chars)
            except Exception:
                pass
            try:
                recent_combo.configure(width=width_chars)
            except Exception:
                pass
        except Exception:
            pass

    def adjust_recent_width(delta: int):
        try:
            w = int(recent_width_var.get()) + int(delta)
        except Exception:
            w = 30
        w = max(10, min(120, w))
        recent_width_var.set(w)
        try:
            recent_combo.configure(width=w)
        except Exception:
            pass

    # Provide small -/+ buttons to adjust combobox width
    dec_btn = tk.Button(frame, text="−", width=2, command=lambda: adjust_recent_width(-4))
    inc_btn = tk.Button(frame, text="+", width=2, command=lambda: adjust_recent_width(+4))
    dec_btn.pack(side=tk.LEFT, padx=(0, 2))
    inc_btn.pack(side=tk.LEFT, padx=(0, 6))

    # Double-click the combobox to auto-fit to current values
    try:
        recent_combo.bind("<Double-Button-1>", lambda e: update_recent_combo_width(None))
    except Exception:
        pass

    recent_open_btn = tk.Button(frame, text="Open", width=6)
    recent_open_btn.pack(side=tk.LEFT)

    # --- Grouped Toolbar (Notebook) ---
    # Create a tabbed toolbar for better organization: Model | Options | Folders
    toolbar_nb = ttk.Notebook(root)
    toolbar_nb.pack(fill=tk.X, padx=8, pady=(6, 2))

    # Model tab
    tab_model = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_model, text="Model")
    tk.Label(tab_model, text="Model:").pack(side=tk.LEFT, padx=(4, 2))
    model_combo_tab = ttk.Combobox(tab_model, textvariable=current_model_name, values=["small", "medium", "large-v2"], width=12, state="readonly")
    model_combo_tab.pack(side=tk.LEFT)
    try:
        model_combo_tab.bind("<Return>", lambda e: on_load_model())
    except Exception:
        pass
    tk.Button(tab_model, text="Load", width=8, command=on_load_model).pack(side=tk.LEFT, padx=(6, 2))
    # Show current model on the right side of the tab
    tk.Label(tab_model, textvariable=model_display_var, fg="#666").pack(side=tk.RIGHT, padx=(2, 4))

    # Options tab
    tab_options = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_options, text="Options")
    tk.Label(tab_options, text="Language:").pack(side=tk.LEFT, padx=(4, 2))
    language_combo_tab = ttk.Combobox(tab_options, textvariable=language_var, values=[lbl for (lbl, _) in _LANG_OPTIONS], width=16, state="readonly")
    language_combo_tab.pack(side=tk.LEFT)
    tk.Checkbutton(tab_options, text="Indian English bias", variable=indian_bias_var).pack(side=tk.LEFT, padx=(8, 0))
    tk.Checkbutton(tab_options, text="Stability Mode (beam)", variable=stability_var).pack(side=tk.LEFT, padx=(8, 0))
    tk.Checkbutton(tab_options, text="Fast Decode", variable=fast_decode_var).pack(side=tk.LEFT, padx=(8, 0))
    tk.Label(tab_options, text="Output:").pack(side=tk.LEFT, padx=(12, 2))
    output_mode_combo_tab = ttk.Combobox(
        tab_options,
        textvariable=output_mode_var,
        values=["Same Language", "English (Translate)", "Chinese (Translate)"],
        width=22,
        state="readonly",
    )
    output_mode_combo_tab.pack(side=tk.LEFT)

    # Folders tab
    tab_folders = tk.Frame(toolbar_nb)
    toolbar_nb.add(tab_folders, text="Folders")
    tk.Label(tab_folders, text="Recent:").pack(side=tk.LEFT, padx=(4, 4))
    recent_combo_tab = ttk.Combobox(tab_folders, textvariable=recent_var, width=recent_width_var.get(), state="readonly")
    recent_combo_tab.pack(side=tk.LEFT, padx=(0, 4))
    # Change selection in tab -> switch file list
    try:
        recent_combo_tab.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())
    except Exception:
        pass
    # Bind double-click to auto-fit
    try:
        recent_combo_tab.bind("<Double-Button-1>", lambda e: update_recent_combo_width(None))
    except Exception:
        pass
    # Width adjusters
    tk.Button(tab_folders, text="−", width=2, command=lambda: adjust_recent_width(-4)).pack(side=tk.LEFT, padx=(0, 2))
    tk.Button(tab_folders, text="+", width=2, command=lambda: adjust_recent_width(+4)).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(tab_folders, text="Open", width=8, command=lambda: open_recent_selected()).pack(side=tk.LEFT)

    # Hide legacy inline controls to declutter original single-row toolbar
    try:
        # Model controls
        model_label.pack_forget()
        model_combo.pack_forget()
        load_model_btn.pack_forget()
    except Exception:
        pass
    try:
        # Language and output controls
        language_label.pack_forget()
        indian_bias_chk.pack_forget()
        stability_chk.pack_forget()
        fast_decode_chk.pack_forget()
        language_combo.pack_forget()
        output_label.pack_forget()
        output_mode_combo.pack_forget()
    except Exception:
        pass
    try:
        # Recent controls and width buttons
        recent_label.pack_forget()
        recent_combo.pack_forget()
        dec_btn.pack_forget(); inc_btn.pack_forget(); recent_open_btn.pack_forget()
    except Exception:
        pass

    # Auto-fit soon after layout (after values may have been populated)
    try:
        root.after(300, lambda: update_recent_combo_width(None))
    except Exception:
        pass

    quit_btn = tk.Button(frame, text="Quit", command=root.destroy)
    quit_btn.pack(side=tk.RIGHT)

    # Files pane show/hide toggle
    files_toggle_btn = tk.Button(frame, text="Files ▼")
    files_toggle_btn.pack(side=tk.RIGHT, padx=(6, 0))

    # Single status bar label (file + status + model + legend)
    status_bar_label = tk.Label(root, textvariable=status_bar_var, anchor="w")
    status_bar_label.pack(fill=tk.X, padx=8, pady=(4, 6))
    _refresh_status_bar()

    # Paned layout: upper file list, lower log
    paned = ttk.Panedwindow(root, orient=tk.VERTICAL)
    paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

    # Upper: file browser tree
    files_frame = tk.Frame(paned)
    cols = ("audio", "size", "modified", "transcript")
    tree = ttk.Treeview(files_frame, columns=cols, show="headings", height=6, selectmode="extended")
    header_labels = {
        "audio": "Audio/Video File",
        "size": "Size",
        "modified": "Date Modified",
        "transcript": "Transcript .txt",
    }
    tree.heading("audio", text=header_labels["audio"], command=lambda c="audio": tree_sort_by(c), anchor="w")
    tree.heading("size", text=header_labels["size"], command=lambda c="size": tree_sort_by(c), anchor="center")
    tree.heading("modified", text=header_labels["modified"], command=lambda c="modified": tree_sort_by(c), anchor="center")
    tree.heading("transcript", text=header_labels["transcript"], command=lambda c="transcript": tree_sort_by(c), anchor="center")
    tree.column("audio", width=360, anchor="w")
    tree.column("size", width=90, anchor="center")
    tree.column("modified", width=160, anchor="center")
    tree.column("transcript", width=260, anchor="center")
    # Legend moved into the consolidated status bar above
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    paned.add(files_frame, weight=0)

    # Lower: Notebook with Log, Preview, and Notes tabs
    nb = ttk.Notebook(paned)
    paned.add(nb, weight=1)

    # Configure minimal size for files pane to allow near-collapse
    try:
        paned.paneconfigure(files_frame, minsize=24)
    except Exception:
        pass

    # Files pane collapse/expand behavior
    files_collapsed = {"value": False}
    def _set_files_collapsed(collapsed: bool):
        files_collapsed["value"] = collapsed
        try:
            total_h = root.winfo_height()
            if total_h <= 1:
                total_h = 600
            if collapsed:
                # Move sash to top to minimize files pane
                paned.sashpos(0, 0)
                files_toggle_btn.configure(text="Files ▲")
            else:
                # Give about 22% to files, 78% to bottom
                paned.sashpos(0, int(total_h * 0.22))
                files_toggle_btn.configure(text="Files ▼")
        except Exception:
            pass

    def on_files_toggle():
        _set_files_collapsed(not files_collapsed["value"])

    try:
        files_toggle_btn.configure(command=on_files_toggle)
    except Exception:
        pass

    # Set initial sash position after layout to favor lower pane
    def _init_sash():
        _set_files_collapsed(False)
    root.after(120, _init_sash)

    # Log tab
    log_frame = tk.Frame(nb)
    log = tk.Text(log_frame, height=10, wrap="word")
    log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log.yview)
    log.configure(state=tk.DISABLED, yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    nb.add(log_frame, text="Log")

    # Preview tab (zoomable)
    preview_frame = tk.Frame(nb)
    # Use a dedicated font so we can scale without affecting other widgets
    try:
        _base_preview_font = tkfont.nametofont("TkDefaultFont").copy()
    except Exception:
        _base_preview_font = tkfont.Font(family="Segoe UI", size=10)
    preview_font = tkfont.Font()
    try:
        preview_font.config(family=_base_preview_font.cget("family"), size=_base_preview_font.cget("size"))
    except Exception:
        preview_font.config(size=10)
    preview_zoom = {"size": preview_font.cget("size"), "min": 8, "max": 28, "base": preview_font.cget("size")}

    preview = tk.Text(preview_frame, height=10, wrap="word", font=preview_font)
    preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview.yview)
    preview.configure(state=tk.DISABLED, yscrollcommand=preview_scroll.set)
    preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _apply_preview_zoom(new_size: int):
        try:
            new_size = max(preview_zoom["min"], min(preview_zoom["max"], int(new_size)))
            preview_font.configure(size=new_size)
            preview_zoom["size"] = new_size
        except Exception:
            pass

    def _on_ctrl_mousewheel(event):
        # Windows: event.delta in multiples of 120; positive=up
        try:
            if (event.state & 0x4) == 0x4:  # Control pressed
                delta = event.delta if hasattr(event, "delta") else 0
                step = 1 if delta > 0 else -1
                _apply_preview_zoom(preview_zoom["size"] + step)
                return "break"
        except Exception:
            pass
        return None

    def _on_ctrl_plus(event):
        _apply_preview_zoom(preview_zoom["size"] + 1)
        return "break"

    def _on_ctrl_minus(event):
        _apply_preview_zoom(preview_zoom["size"] - 1)
        return "break"

    def _on_ctrl_zero(event):
        _apply_preview_zoom(preview_zoom["base"])
        return "break"

    # Bind zoom gestures
    try:
        preview.bind("<Control-MouseWheel>", _on_ctrl_mousewheel)      # Windows
        preview.bind("<Control-Button-4>", lambda e: (_apply_preview_zoom(preview_zoom["size"] + 1), "break"))  # Linux scroll up
        preview.bind("<Control-Button-5>", lambda e: (_apply_preview_zoom(preview_zoom["size"] - 1), "break"))  # Linux scroll down
        preview.bind("<Control-plus>", _on_ctrl_plus)
        preview.bind("<Control-KP_Add>", _on_ctrl_plus)
        preview.bind("<Control-minus>", _on_ctrl_minus)
        preview.bind("<Control-KP_Subtract>", _on_ctrl_minus)
        preview.bind("<Control-0>", _on_ctrl_zero)
        preview.bind("<Control-KP_0>", _on_ctrl_zero)
    except Exception:
        pass

    nb.add(preview_frame, text="Preview")

    # Notes (Markdown) tab
    notes_frame = tk.Frame(nb)
    notes_toolbar = tk.Frame(notes_frame)
    notes_toolbar.pack(fill=tk.X, padx=6, pady=(6, 4))
    current_md_path_var = tk.StringVar(value="")
    # Helper to shorten long paths with middle ellipsis
    def _shorten_middle(text: str, max_len: int = 80) -> str:
        try:
            t = text or ""
            if len(t) <= max_len:
                return t
            keep = max_len - 3
            left = keep // 2
            right = keep - left
            return f"{t[:left]}...{t[-right:]}"
        except Exception:
            return text
    display_md_path_var = tk.StringVar(value="")
    def _refresh_md_path(*_):
        display_md_path_var.set(_shorten_middle(current_md_path_var.get(), 100))
    try:
        current_md_path_var.trace_add("write", _refresh_md_path)
    except Exception:
        pass
    tk.Label(notes_toolbar, text="Notes file:").pack(side=tk.LEFT)
    notes_path_label = tk.Label(notes_toolbar, textvariable=display_md_path_var, anchor="w")
    notes_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
    autosave_enabled_var = tk.BooleanVar(value=True)
    autosave_delay_s_var = tk.DoubleVar(value=1.0)  # seconds
    tk.Label(notes_toolbar, text="Auto-save:").pack(side=tk.LEFT, padx=(6, 2))
    autosave_chk = tk.Checkbutton(notes_toolbar, text="Notes", variable=autosave_enabled_var)
    autosave_chk.pack(side=tk.LEFT)
    tk.Label(notes_toolbar, text="Delay:").pack(side=tk.LEFT, padx=(8, 2))
    autosave_delay_spin = tk.Spinbox(notes_toolbar, from_=0.2, to=10.0, increment=0.2, width=5, textvariable=autosave_delay_s_var)
    autosave_delay_spin.pack(side=tk.LEFT)
    tk.Label(notes_toolbar, text="s").pack(side=tk.LEFT, padx=(2, 6))
    # Right-aligned sub-toolbar to keep everything on one row
    notes_toolbar_right = tk.Frame(notes_toolbar)
    notes_toolbar_right.pack(side=tk.RIGHT)
    saved_at_var = tk.StringVar(value="")
    saved_at_label = tk.Label(notes_toolbar_right, textvariable=saved_at_var, anchor="e", fg="#0a7")
    saved_at_label.pack(side=tk.LEFT, padx=(0, 6))
    notes_reveal_btn = tk.Button(notes_toolbar_right, text="Reveal")
    notes_reveal_btn.pack(side=tk.LEFT)
    notes_save_btn = tk.Button(notes_toolbar_right, text="Save Notes")
    notes_save_btn.pack(side=tk.LEFT, padx=(6, 0))
    
    # Markdown formatting toolbar (above editor)
    md_format_toolbar = tk.Frame(notes_frame)
    md_format_toolbar.pack(fill=tk.X, padx=6, pady=(0, 4))
    # Left side: language dropdown for code blocks (remembers last used)
    md_lang_frame = tk.Frame(md_format_toolbar)
    md_lang_frame.pack(side=tk.LEFT)
    tk.Label(md_lang_frame, text="Lang:").pack(side=tk.LEFT, padx=(0, 4))
    common_langs = [
        "python", "bash", "sh", "powershell", "cmd", "bat",
        "json", "yaml", "markdown", "text",
        "javascript", "typescript", "html", "css",
        "c", "cpp", "java", "go", "rust", "sql",
        "matlab", "r"
    ]
    code_lang_var = tk.StringVar(value="python")
    code_lang_combo = ttk.Combobox(md_lang_frame, textvariable=code_lang_var, values=common_langs, width=12, state="normal")
    code_lang_combo.pack(side=tk.LEFT)
    # Right-aligned area for engine indicator
    md_toolbar_right = tk.Frame(md_format_toolbar)
    md_toolbar_right.pack(side=tk.RIGHT)
    preview_engine_var = tk.StringVar(value="")
    tk.Label(md_toolbar_right, textvariable=preview_engine_var, fg="#666").pack(side=tk.RIGHT, padx=(6, 0))

    def _get_selection_or_cursor():
        try:
            start = notes_editor.index("sel.first")
            end = notes_editor.index("sel.last")
            return start, end, True
        except Exception:
            # No selection; operate at cursor
            idx = notes_editor.index(tk.INSERT)
            return idx, idx, False

    def _refresh_after_edit():
        try:
            # Trigger existing preview/autosave debounce
            notes_editor.event_generate("<KeyRelease>")
        except Exception:
            try:
                content = notes_editor.get("1.0", tk.END)
                render_markdown_to_preview(content)
            except Exception:
                pass

    def _wrap_selection(prefix: str, suffix: str):
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            notes_editor.delete(s, e)
            notes_editor.insert(s, f"{prefix}{text}{suffix}")
        else:
            notes_editor.insert(s, f"{prefix}{suffix}")
            # Place cursor between
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(prefix)}c")
            except Exception:
                pass
        _refresh_after_edit()

    def _linewise_prefix(prefix: str):
        # Apply prefix to each selected line, or current line
        s, e, has_sel = _get_selection_or_cursor()
        start_line = int(float(s.split(".")[0]))
        end_line = int(float(e.split(".")[0])) if has_sel else start_line
        for ln in range(start_line, end_line + 1):
            line_start = f"{ln}.0"
            notes_editor.insert(line_start, prefix)
        _refresh_after_edit()

    def _heading(level: int):
        s, _, _ = _get_selection_or_cursor()
        line = int(float(s.split(".")[0]))
        line_start = f"{line}.0"
        # Remove existing hashes on this line, then add desired level
        try:
            line_text = notes_editor.get(line_start, f"{line}.end")
        except Exception:
            line_text = ""
        stripped = line_text.lstrip('# ').rstrip('\n')
        notes_editor.delete(line_start, f"{line}.end")
        notes_editor.insert(line_start, f"{'#'*level} {stripped}\n")
        _refresh_after_edit()

    def _make_link():
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            notes_editor.delete(s, e)
            notes_editor.insert(s, f"[{text}](https://)")
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(text)+3}c")
            except Exception:
                pass
        else:
            notes_editor.insert(s, "[link text](https://)")
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+1c")
            except Exception:
                pass
        _refresh_after_edit()

    def _inline_code():
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            if "\n" in text:
                # Multiline -> code block
                notes_editor.delete(s, e)
                notes_editor.insert(s, f"```\n{text}\n```\n")
            else:
                notes_editor.delete(s, e)
                notes_editor.insert(s, f"`{text}`")
        else:
            notes_editor.insert(s, "``")
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+1c")
            except Exception:
                pass
        _refresh_after_edit()

    def _code_block():
        # Prompt for language (optional)
        try:
            lang = simpledialog.askstring(
                "Code Block",
                "Language (e.g., python, bash) — optional:",
                initialvalue=(code_lang_var.get() or ""),
                parent=root,
            )
        except Exception:
            lang = None
        lang = (lang or "").strip()
        if lang:
            try:
                code_lang_var.set(lang)
            except Exception:
                pass
        s, e, has_sel = _get_selection_or_cursor()
        if has_sel:
            text = notes_editor.get(s, e)
            notes_editor.delete(s, e)
            notes_editor.insert(s, f"```{lang}\n{text}\n```\n")
            # Place cursor just after the closing fence
            try:
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(lang)+4+len(text)+5}c")
            except Exception:
                pass
        else:
            # Insert empty fenced block and position cursor on the blank line inside
            block = f"```{lang if lang else (code_lang_var.get() or '')}\n\n```\n"
            notes_editor.insert(s, block)
            try:
                # Move cursor one line down after opening fence
                effective_lang = lang if lang else (code_lang_var.get() or '')
                notes_editor.mark_set(tk.INSERT, f"{s}+{len(effective_lang)+4}c")  # after first line break
                notes_editor.mark_set(tk.INSERT, f"{tk.INSERT}+1l")
            except Exception:
                pass
        _refresh_after_edit()

    def _image():
        s, _, _ = _get_selection_or_cursor()
        notes_editor.insert(s, "![alt text](images/placeholder.png)")
        _refresh_after_edit()

    def _insert_image_action():
        # Pick an image and either copy it into notes images/ or link it directly, then insert markdown
        try:
            img_path = filedialog.askopenfilename(
                title="Insert image",
                filetypes=[
                    ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.svg"),
                    ("All files", "*.*"),
                ],
            )
            if not img_path:
                return
            img_path = os.path.abspath(img_path)
            # Determine target folder (images under current md, else under current folder)
            try:
                base_dir = os.path.dirname(current_md_path_var.get()) if current_md_path_var.get() else (current_folder_var.get() or os.getcwd())
            except Exception:
                base_dir = os.getcwd()
            images_dir = os.path.join(base_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # Ask whether to copy into images folder (recommended for portability)
            do_copy = messagebox.askyesno(
                "Insert Image",
                "Copy image into the notes 'images' folder?\n\nYes: copy into images/ and use a relative path.\nNo: link to the original absolute path.",
                parent=root,
            )

            if do_copy:
                target_name = os.path.basename(img_path)
                dest_path = os.path.join(images_dir, target_name)
                # Avoid overwriting: if exists, add numeric suffix
                if os.path.abspath(dest_path) != os.path.abspath(img_path) and os.path.exists(dest_path):
                    name, ext = os.path.splitext(target_name)
                    k = 2
                    while os.path.exists(os.path.join(images_dir, f"{name}-{k}{ext}")):
                        k += 1
                    dest_path = os.path.join(images_dir, f"{name}-{k}{ext}")
                try:
                    if os.path.abspath(dest_path) != os.path.abspath(img_path):
                        shutil.copy2(img_path, dest_path)
                    # Insert relative markdown path
                    rel = os.path.relpath(dest_path, start=base_dir).replace("\\", "/")
                    _wrap_selection(f"![alt text](", f"{rel})")
                except Exception as e:
                    messagebox.showerror("Insert Image", f"Failed to copy image. Linking instead.\n\n{e}")
                    _wrap_selection(f"![alt text](", f"{img_path})")
            else:
                # Link to original absolute path; preprocessing will turn into file:///
                _wrap_selection(f"![alt text](", f"{img_path})")
        except Exception as e:
            messagebox.showerror("Insert Image", f"Unexpected error: {e}")

    def _numbered():
        s, e, has_sel = _get_selection_or_cursor()
        start_line = int(float(s.split(".")[0]))
        end_line = int(float(e.split(".")[0])) if has_sel else start_line
        num = 1
        for ln in range(start_line, end_line + 1):
            notes_editor.insert(f"{ln}.0", f"{num}. ")
            num += 1
        _refresh_after_edit()

    # Buttons
    btn_specs = [
        ("B", lambda: _wrap_selection("**", "**")),
        ("I", lambda: _wrap_selection("*", "*")),
        ("H1", lambda: _heading(1)),
        ("H2", lambda: _heading(2)),
        ("•", lambda: _linewise_prefix("- ")),
        ("1.", _numbered),
        ("Link", _make_link),
        ("Code", _inline_code),
        ("Code Block", _code_block),
        (">", lambda: _linewise_prefix("> ")),
        ("Img", _image),
        ("Insert Image…", _insert_image_action),
        ("[ ]", lambda: _linewise_prefix("- [ ] ")),
    ]

    for text, cmd in btn_specs:
        tk.Button(md_format_toolbar, text=text, width=3, command=cmd).pack(side=tk.LEFT, padx=2)

    # Split view: editor | preview
    notes_split = ttk.Panedwindow(notes_frame, orient=tk.HORIZONTAL)
    notes_split.pack(fill=tk.BOTH, expand=True)
    # Left: editor with its own scroll
    editor_container = tk.Frame(notes_split)
    notes_editor = tk.Text(editor_container, height=10, wrap="word")
    notes_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    notes_scroll = ttk.Scrollbar(editor_container, orient=tk.VERTICAL, command=notes_editor.yview)
    notes_editor.configure(yscrollcommand=notes_scroll.set)
    notes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    # Right: rendered preview
    preview_container = tk.Frame(notes_split)
    if HtmlFrame is not None:
        md_preview = HtmlFrame(preview_container, horizontal_scrollbar="auto")
        md_preview.pack(fill=tk.BOTH, expand=True)
        preview_engine_var.set("Preview: tkinterweb")
    elif HTMLLabel is not None:
        md_preview = HTMLLabel(preview_container, html="", background="white")
        md_preview.pack(fill=tk.BOTH, expand=True)
        preview_engine_var.set("Preview: tkhtmlview")
    else:
        # Fallback to read-only text if HTML renderer unavailable
        md_preview = tk.Text(preview_container, height=10, wrap="word", state=tk.DISABLED)
        md_preview.pack(fill=tk.BOTH, expand=True)
        preview_engine_var.set("Preview: text (fallback)")
    notes_split.add(editor_container, weight=1)
    notes_split.add(preview_container, weight=1)
    nb.add(notes_frame, text="Notes (Markdown)")

    # --- Menubar with Tools -> Clear Cache & Reset Whisper Cache ---
    try:
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        # menubar.add_cascade(label="Tools", menu=tools_menu)

        def clear_cached_wavs():
            cache_dir = os.path.join(os.path.expanduser("~"), ".audio2text_cache")
            if not os.path.isdir(cache_dir):
                messagebox.showinfo("Clear Cache", "No cache directory found.")
            removed = 0
            errors = []
            try:
                for name in os.listdir(cache_dir):
                    if not name.lower().endswith(".wav"):
                        continue
                    p = os.path.join(cache_dir, name)
                    try:
                        os.remove(p)
                        removed += 1
                    except Exception as e:
                        errors.append(f"{name}: {e}")
                # Try to remove cache dir if empty (ignore errors)
                try:
                    if not os.listdir(cache_dir):
                        os.rmdir(cache_dir)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Clear Cache", f"Failed to enumerate cache directory:\n{e}")
                return
            if errors:
                messagebox.showerror("Clear Cache", f"Removed {removed} file(s), but some failed:\n" + "\n".join(errors))
            else:
                messagebox.showinfo("Clear Cache", f"Removed {removed} cached WAV file(s).")

        tools_menu.add_command(label="Clear Cached WAVs", command=clear_cached_wavs)

        def reset_whisper_cache():
            primary_cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
            alt_cache = os.path.join(os.getcwd(), "whisper_models_cache")
            removed = []
            errors = []
            for base in [primary_cache, alt_cache]:
                try:
                    if not os.path.isdir(base):
                        continue
                    for name in os.listdir(base):
                        p = os.path.join(base, name)
                        if os.path.isfile(p) and name.lower().endswith(".pt"):
                            try:
                                os.remove(p)
                                removed.append(p)
                            except Exception as e:
                                errors.append(f"{p}: {e}")
                except Exception as e:
                    errors.append(f"{base}: {e}")
            if errors:
                messagebox.showerror("Reset Whisper Cache", "Some files could not be removed:\n" + "\n".join(errors))
            else:
                messagebox.showinfo("Reset Whisper Cache", f"Removed {len(removed)} cached model file(s).")

        tools_menu.add_command(label="Reset Whisper Cache", command=reset_whisper_cache)
    except Exception:
        pass

    # Saved transcript entry row
    out_frame = tk.Frame(root)
    out_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
    tk.Label(out_frame, text="Saved transcript:").pack(side=tk.LEFT)
    out_entry = tk.Entry(out_frame, textvariable=output_path_var)
    out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))

    # Context menu helpers
    def _normpath(p: str) -> str:
        try:
            return os.path.normpath(p) if p else p
        except Exception:
            return p

    def copy_to_clipboard(text: str):
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        except Exception:
            pass

    def reveal_in_explorer(path: str):
        if not path:
            return
        # Normalize to absolute for Explorer
        abs_path = os.path.abspath(path)
        try:
            if os.path.isfile(abs_path):
                # Use separate args to avoid quoting issues with spaces
                subprocess.run(["explorer", "/select,", abs_path], check=False)
                return
            # If it's a directory, open it directly
            if os.path.isdir(abs_path):
                subprocess.run(["explorer", abs_path], check=False)
                return
            # If it doesn't exist, try opening its parent folder
            parent = os.path.dirname(abs_path)
            if parent and os.path.isdir(parent):
                subprocess.run(["explorer", parent], check=False)
        except Exception:
            pass

    def open_with_default_app(path: str):
        try:
            if path and os.path.isfile(path):
                os.startfile(path)  # Windows: open with default application
        except Exception:
            messagebox.showerror("Open Failed", f"Could not open file:\n{path}")

    # --- URL transcription helpers ---
    def _download_media_to_temp(url: str) -> tuple[str | None, str | None]:
        """Download media from URL into a unique temp directory using yt-dlp.
        Returns (media_path, temp_dir). Caller is responsible for cleaning temp_dir if desired.
        """
        tmpdir = tempfile.mkdtemp(prefix="a2t_url_")

        # 1) If the URL looks like a direct media file (e.g., googlevideo.com or ends with media extension),
        # try a simple HTTP download first without yt-dlp.
        def _looks_like_direct_media(u: str) -> bool:
            try:
                low = (u or "").lower()
                media_exts = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".mp4", ".webm", ".mkv", ".mov", ".avi")
                return low.endswith(media_exts) or ("googlevideo.com" in low)
            except Exception:
                return False

        if _looks_like_direct_media(url):
            try:
                import urllib.request
                # Guess a filename
                filename = "downloaded_media"
                # Try to infer extension from URL query if present
                if ".mp4" in url.lower():
                    filename += ".mp4"
                elif ".webm" in url.lower():
                    filename += ".webm"
                elif ".m4a" in url.lower():
                    filename += ".m4a"
                elif ".mp3" in url.lower():
                    filename += ".mp3"
                else:
                    # default to mp4 for video URLs like googlevideo
                    filename += ".mp4"
                dest = os.path.join(tmpdir, filename)
                set_status("Downloading media (direct)...")
                # Some hosts require a User-Agent
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
                    shutil.copyfileobj(r, f)
                if os.path.isfile(dest) and os.path.getsize(dest) > 0:
                    return dest, tmpdir
            except Exception as e:
                append_log(f"Direct download attempt failed, falling back to yt-dlp: {e}")

        # 2) Fallback to yt-dlp for complex URLs (watch pages, playlists, etc.)
        ok = ensure_yt_dlp_installed()
        if not ok:
            return None, tmpdir
        # Use yt-dlp via module invocation for compatibility
        out_tmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")
        cmd = [sys.executable, "-m", "yt_dlp", "-f", "bestaudio/best", "-o", out_tmpl, url]
        try:
            set_status("Downloading media...")
            completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if completed.returncode != 0:
                append_log("yt-dlp download failed. stderr:\n" + (completed.stderr or ""))
                return None, tmpdir
        except Exception as e:
            append_log(f"yt-dlp download failed: {e}")
            return None, tmpdir
        # Find the largest/newest file in tmpdir
        try:
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if os.path.isfile(os.path.join(tmpdir, f))]
            if not files:
                return None, tmpdir
            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return files[0], tmpdir
        except Exception:
            return None, tmpdir

    # --- Media helpers ---
    def is_video_file(path: str) -> bool:
        try:
            _, ext = os.path.splitext(path or "")
            return (ext or "").lower() in {
                ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v", ".webm", ".mts", ".m2ts", ".ts",
                ".3gp", ".flv", ".mpeg",
            }
        except Exception:
            return False

    def display_to_real_filename(name: str) -> str:
        # Strip our optional leading video emoji tag and optional trailing indicator
        try:
            if name.startswith("🎥 "):
                name = name[2:].lstrip()
            if name.endswith(" [video]"):
                name = name[:-8]
            return name
        except Exception:
            return name

    def _file_size_bytes(path: str) -> int:
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    def _cache_wav_path_for(src_path: str) -> str:
        import hashlib
        home = os.path.expanduser("~")
        cache_dir = os.path.join(home, ".audio2text_cache")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass
        try:
            stat = os.stat(src_path)
            key = f"{os.path.abspath(src_path)}|{stat.st_mtime_ns}|{stat.st_size}".encode("utf-8", errors="ignore")
        except Exception:
            key = os.path.abspath(src_path).encode("utf-8", errors="ignore")
        digest = hashlib.sha1(key).hexdigest()  # short enough for Windows paths
        return os.path.join(cache_dir, f"{digest}.wav")

    def get_or_make_cached_wav_for_large_video(input_path: str, threshold_mb: int = 200) -> str | None:
        """If input is a video and larger than threshold, extract audio to a cached WAV and return its path.
        Return None to use the original input file.
        """
        try:
            if not is_video_file(input_path):
                return None
            size_mb = _file_size_bytes(input_path) / (1024 * 1024.0)
            if size_mb < float(threshold_mb):
                return None
            out_wav = _cache_wav_path_for(input_path)
            if os.path.isfile(out_wav):
                return out_wav
            # Extract mono 16 kHz WAV using ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", out_wav,
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.isfile(out_wav):
                    return out_wav
            except Exception as e:
                append_log(f"FFmpeg extraction failed: {e}")
            return None
        except Exception:
            return None

    def human_readable_size(num_bytes: int) -> str:
        """Return human-readable file size (e.g., 1.23 MB)."""
        try:
            size = float(num_bytes)
        except Exception:
            return "-"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0 or unit == "TB":
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def human_readable_mtime(ts: float) -> str:
        """Return human-readable modified time (local)."""
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "-"

    def autofit_tree_columns(tree_widget: ttk.Treeview, columns: tuple[str, ...], min_widths=None, max_widths=None, padding: int = 18):
        """Auto-fit column widths to content and headers.
        - min_widths/max_widths are optional dicts mapping column id to pixel width constraints.
        - padding adds some extra space so text isn't cramped.
        """
        try:
            # Use the Treeview's current font (falls back to default if not found)
            tv_font = tkfont.nametofont(str(tree_widget.cget("font"))) if tree_widget.cget("font") else tkfont.nametofont("TkDefaultFont")
        except Exception:
            tv_font = tkfont.nametofont("TkDefaultFont")

        min_widths = min_widths or {}
        max_widths = max_widths or {}

        # Measure each column
        for col in columns:
            # Start with header label text
            header_text = tree_widget.heading(col).get("text", col)
            max_px = tv_font.measure(header_text)

            # Include all row values in that column
            for iid in tree_widget.get_children(""):
                vals = tree_widget.item(iid, "values")
                if not vals:
                    continue
                # Map column to index
                try:
                    idx = columns.index(col)
                except ValueError:
                    idx = 0
                cell = vals[idx] if idx < len(vals) else ""
                # Avoid very long paths in transcript from blowing up width; clip for measurement but keep full text shown with horizontal scroll if any
                display_sample = str(cell)
                px = tv_font.measure(display_sample)
                if px > max_px:
                    max_px = px

            # Apply padding and constraints
            max_px += padding
            if col in min_widths:
                max_px = max(max_px, int(min_widths[col]))
            if col in max_widths:
                max_px = min(max_px, int(max_widths[col]))

            # Set width
            try:
                tree_widget.column(col, width=max_px)
            except Exception:
                pass

    # State for file browser
    current_folder_var = tk.StringVar(value="")
    path_to_item = {}

    # Recent folders state and helpers
    RECENT_FILE = os.path.join(os.path.expanduser("~"), ".audio2text_recent_folders.json")
    STATE_FILE = os.path.join(os.path.expanduser("~"), ".audio2text_state.json")
    MAX_RECENT = 10

    def load_recent_folders():
        try:
            if os.path.isfile(RECENT_FILE):
                with open(RECENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # Keep only existing directories
                    vals = [p for p in data if isinstance(p, str) and os.path.isdir(p)]
                    # Update both recent widgets if available
                    try:
                        recent_combo["values"] = vals
                    except Exception:
                        pass
                    try:
                        recent_combo_tab["values"] = vals
                    except Exception:
                        pass
                    # Auto-fit to loaded values
                    try:
                        update_recent_combo_width(vals)
                    except Exception:
                        pass
                    return vals
        except Exception:
            pass
        try:
            recent_combo["values"] = []
        except Exception:
            pass
        try:
            recent_combo_tab["values"] = []
        except Exception:
            pass
        return []

    def save_recent_folders(values: list[str]):
        try:
            with open(RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump(values[:MAX_RECENT], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # --- Persist last-opened folder ---
    def load_last_folder() -> str:
        try:
            if os.path.isfile(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    p = data.get("last_folder", "")
                    if isinstance(p, str) and os.path.isdir(p):
                        return p
        except Exception:
            pass
        return ""

    def save_last_folder(path: str):
        try:
            data = {}
            if os.path.isfile(STATE_FILE):
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    if isinstance(existing, dict):
                        data.update(existing)
                except Exception:
                    pass
            data["last_folder"] = os.path.abspath(path)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_recent_values(values: list[str]):
        vals = values[:MAX_RECENT]
        # Update both widgets' values
        try:
            recent_combo["values"] = vals
        except Exception:
            pass
        try:
            recent_combo_tab["values"] = vals
        except Exception:
            pass
        # If current value not in list, clear selection
        if recent_var.get() not in vals:
            recent_var.set("")
        # Auto-fit to provided values
        try:
            update_recent_combo_width(vals)
        except Exception:
            pass

    def add_recent_folder(path: str):
        if not path or not os.path.isdir(path):
            return
        path = os.path.abspath(path)
        # Merge current values from both widgets
        try:
            vals_a = list(recent_combo["values"]) if recent_combo["values"] else []
        except Exception:
            vals_a = []
        try:
            vals_b = list(recent_combo_tab["values"]) if recent_combo_tab["values"] else []
        except Exception:
            vals_b = []
        current_vals = []
        seen = set()
        for v in vals_a + vals_b:
            av = os.path.abspath(v)
            if av not in seen:
                seen.add(av)
                current_vals.append(v)
        # Move to front, remove duplicates
        new_vals = [path] + [p for p in current_vals if os.path.abspath(p) != path]
        new_vals = new_vals[:MAX_RECENT]
        set_recent_values(new_vals)
        save_recent_folders(new_vals)
        try:
            update_recent_combo_width(new_vals)
        except Exception:
            pass

    def open_recent_selected():
        path = recent_var.get().strip()
        if not path:
            return
        if not os.path.isdir(path):
            messagebox.showerror("Folder Missing", f"The folder no longer exists:\n{path}")
            # Remove from recent
            vals = [p for p in (recent_combo["values"] or []) if p != path]
            set_recent_values(vals)
            save_recent_folders(vals)
            return
        current_folder_var.set(path)
        append_log(f"Folder selected: {path}")
        populate_tree(path)
        # Persist last-opened folder
        try:
            save_last_folder(path)
        except Exception:
            pass

    def append_log(text: str):
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, text + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    def set_preview_text(text: str):
        # Sanitize citation markers for display in the preview tab only
        t = sanitize_notes_markdown(text if isinstance(text, str) else "")
        preview.configure(state=tk.NORMAL)
        preview.delete("1.0", tk.END)
        preview.insert(tk.END, t)
        preview.see("1.0")
        preview.configure(state=tk.DISABLED)

    def set_status(text: str):
        status_var.set(text)
        root.update_idletasks()

    # Safer delete via Recycle Bin
    _trash_ready = False
    def ensure_send2trash_ready() -> bool:
        nonlocal _trash_ready
        if _trash_ready:
            return True
        try:
            import send2trash  # noqa: F401
            _trash_ready = True
            return True
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "Send2Trash"])  # package name capitalization
                import send2trash  # noqa: F401
                _trash_ready = True
                return True
            except Exception:
                return False

    def safe_delete_to_trash(path: str):
        if not path:
            return
        try:
            if ensure_send2trash_ready():
                from send2trash import send2trash
                send2trash(path)
            else:
                # Fallback to permanent removal if Send2Trash unavailable
                os.remove(path)
        except Exception as e:
            raise e

    def sanitize_notes_markdown(text: str) -> str:
        # Remove citation markers from preview (robust to case/whitespace/entity-escaping)
        try:
            import re, html as _py_html
            t = text or ""
            # Unescape entities so '&#91;cite_start]' also matches
            try:
                t = _py_html.unescape(t)
            except Exception:
                pass
            # Normalize common escaped patterns first (e.g., [cite\_start] -> [cite_start])
            t = re.sub(r"(?i)cite\\_start", "cite_start", t)
            t = re.sub(r"(?i)cite\\_end", "cite_end", t)
            # Remove [cite_start], [cite-end], [ cite start ], [cite_start:meta], \[cite_start]
            # Support separators _, -, or space; allow optional :suffix; and optional escape before '['
            t = re.sub(r"\\?\[\s*cite(?:[\s_\-])*start\s*(?::[^\]]*)?\]", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\\?\[\s*cite(?:[\s_\-])*end\s*\]", "", t, flags=re.IGNORECASE)
            # Remove inline [cite: ...] references as well
            t = re.sub(r"\\?\[\s*cite\s*:[^\]]*\]", "", t, flags=re.IGNORECASE)
            # Also remove any leftover empty lines that were only markers
            t = re.sub(r"^(\s*)$", r"\1", t, flags=re.MULTILINE)
            return t
        except Exception:
            return text

    def render_markdown_to_preview(text: str):
        # Convert markdown to HTML if possible, else just show plain text
        sanitized_input = sanitize_notes_markdown(text if isinstance(text, str) else "")

        # --- Pre-process image links in Markdown to valid file:/// URLs (Windows safe) ---
        def _to_file_url(path: str, base_dir: str | None) -> str:
            try:
                p = path.strip().strip('"\'')
                # Ignore web URLs and data URIs
                lower = p.lower()
                if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:"):
                    return p
                # Resolve relative paths against base_dir
                if base_dir and not os.path.isabs(p):
                    p_abs = os.path.abspath(os.path.join(base_dir, p))
                else:
                    p_abs = os.path.abspath(p)
                # Normalize to forward slashes and add file:/// scheme
                p_abs = p_abs.replace('\\', '/')
                # URL-encode path segments but keep slashes and colon
                quoted = urllib.parse.quote(p_abs, safe=':/')
                if not quoted.lower().startswith('file:///'):
                    quoted = 'file:///' + quoted
                return quoted
            except Exception:
                return path

        def _preprocess_markdown_images(md_text: str) -> str:
            try:
                import re
                base_dir = ''
                try:
                    # Prefer folder of current markdown file; else current folder
                    base_dir = os.path.dirname(current_md_path_var.get()) if current_md_path_var.get() else (current_folder_var.get() or '')
                except Exception:
                    base_dir = ''

                def repl(m):
                    alt = m.group(1)
                    url = m.group(2)
                    fixed = _to_file_url(url, base_dir)
                    return f"![{alt}]({fixed})"

                # Match standard markdown image: ![alt](url)
                return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, md_text)
            except Exception:
                return md_text

        # Track missing local images to display a small warning in preview
        missing_list = []
        try:
            import re
            # Determine base_dir for resolving relative paths
            try:
                base_dir_detect = os.path.dirname(current_md_path_var.get()) if current_md_path_var.get() else (current_folder_var.get() or '')
            except Exception:
                base_dir_detect = ''

            def _resolve_to_fs(path_str: str) -> str:
                p = path_str.strip().strip('"\'')
                low = p.lower()
                if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
                    return ""  # not a local file
                if base_dir_detect and not os.path.isabs(p):
                    p = os.path.abspath(os.path.join(base_dir_detect, p))
                return p

            for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", sanitized_input):
                candidate = _resolve_to_fs(m.group(1))
                if candidate and not os.path.isfile(candidate):
                    missing_list.append(candidate)
        except Exception:
            missing_list = []

        sanitized_input = _preprocess_markdown_images(sanitized_input)
        # Determine whether to show placeholder for empty input:
        # Only show placeholder if a real .md file exists for the current path.
        file_exists_for_notes = False
        try:
            p = current_md_path_var.get().strip()
            file_exists_for_notes = bool(p and os.path.isfile(p))
        except Exception:
            file_exists_for_notes = False

        if 'HtmlFrame' in locals() and HtmlFrame is not None:
            try:
                # Show placeholder only when an existing md is open; else keep empty
                has_text = bool(sanitized_input.strip())
                display_text = sanitized_input if has_text else ("# Notes\n\nWrite your notes here. Click 'Save Notes' to create the file." if file_exists_for_notes else "")
                exts = [
                    "extra", "toc", "sane_lists", "smarty", "nl2br", "fenced_code", "tables", "codehilite",
                ]
                ext_configs = {
                    'codehilite': {'noclasses': False, 'linenums': False, 'guess_lang': False}
                }
                if has_pymdown:
                    exts.extend([
                        "pymdownx.superfences", "pymdownx.highlight", "pymdownx.tasklist", "pymdownx.tilde", "pymdownx.caret", "pymdownx.emoji",
                    ])
                html = display_text
                if md_render is not None:
                    try:
                        html = md_render(display_text, extensions=exts, extension_configs=ext_configs)
                    except Exception:
                        try:
                            # Second pass minimal fallback
                            html = md_render(display_text, extensions=["fenced_code", "tables"]) 
                        except Exception:
                            html = display_text
                # Ensure code/pre have visible formatting even without Pygments
                if "<pre" in html:
                    html = html.replace("<pre>", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;">')
                    html = html.replace("<pre ", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;" ')
                if "<code" in html:
                    html = html.replace("<code>", '<code style="font-family:Consolas, \"Courier New\", monospace;">')
                    html = html.replace("<code ", '<code style="font-family:Consolas, \"Courier New\", monospace;" ')

                # Do not force a full-document <pre> fallback for HtmlFrame; let Markdown output stand

                # Use full HTML with a style block (HtmlFrame supports it)
                css = ""
                try:
                    from pygments.formatters import HtmlFormatter as _HtmlFormatter2
                    css = _HtmlFormatter2().get_style_defs('.codehilite')
                except Exception:
                    css = ""
                warn_html = ""
                if missing_list:
                    items = ''.join(f"<li>{os.path.basename(p)}</li>" for p in missing_list[:8])
                    more = "" if len(missing_list) <= 8 else f"<li>… and {len(missing_list)-8} more</li>"
                    warn_html = f"<div style='background:#fff3cd;border:1px solid #ffeeba;padding:6px 8px;border-radius:6px;margin-bottom:8px;color:#8a6d3b;'>Missing image file(s):<ul style='margin:4px 0 0 18px'>{items}{more}</ul></div>"
                # If there is truly no text and no warning, push a minimal blank page to clear old content
                if not display_text.strip() and not warn_html:
                    try:
                        md_preview.load_html("<html><head><meta charset='utf-8'></head><body></body></html>")
                    except Exception:
                        try:
                            md_preview.set_html("<div></div>")
                        except Exception:
                            pass
                    return
                full = f"""
                <html><head><meta charset='utf-8'>
                <style>
                body, div, p, li {{ font-family: Segoe UI, Arial, sans-serif; color: #222; }}
                table {{ border-collapse: collapse; }}
                table, th, td {{ border: 1px solid #999; }}
                th, td {{ padding: 6px 8px; }}
                pre {{ background: #f6f8fa; padding: 10px; border-radius: 6px; overflow-x: auto; }}
                code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}
                {css}
                </style></head><body>
                {warn_html}{html}
                </body></html>
                """
                try:
                    md_preview.load_html(full)
                except Exception:
                    # Some versions use set_html
                    md_preview.set_html(full)
            except Exception:
                try:
                    md_preview.load_html("<pre>Failed to render markdown.</pre>")
                except Exception:
                    pass
        elif 'HTMLLabel' in locals() and HTMLLabel is not None:
            try:
                # Show placeholder only when an existing md is open; else keep empty
                has_text = bool(sanitized_input.strip())
                display_text = sanitized_input if has_text else ("# Notes\n\nWrite your notes here. Click 'Save Notes' to create the file." if file_exists_for_notes else "")
                html = display_text
                if md_render is not None:
                    # Build extension set for richer formatting, with inline styles for codehilite
                    exts = [
                        "extra",
                        "toc",
                        "sane_lists",
                        "smarty",
                        "nl2br",
                        "fenced_code",
                        "tables",
                        "codehilite",
                    ]
                    ext_configs = {
                        'codehilite': {
                            'noclasses': True,   # use inline styles so we don't need a <style> block
                            'linenums': False,
                            'guess_lang': False,
                        }
                    }
                    if has_pymdown:
                        exts.extend([
                            "pymdownx.superfences",
                            "pymdownx.highlight",
                            "pymdownx.tasklist",
                            "pymdownx.tilde",
                            "pymdownx.caret",
                            "pymdownx.emoji",
                        ])
                        # prefer inline styles for pymdown highlight as well
                        ext_configs['pymdownx.highlight'] = {
                            'use_pygments': True,
                            'noclasses': True,
                        }
                    try:
                        html = md_render(display_text, extensions=exts, extension_configs=ext_configs)
                    except Exception:
                        # Fallback to basic
                        try:
                            html = md_render(display_text, extensions=["fenced_code", "tables"]) 
                        except Exception:
                            html = display_text

                # Post-process to force table borders via attributes/styles for tkhtmlview
                try:
                    if "<table" in html:
                        # Simplify sections that tkhtmlview may ignore
                        html = html.replace("<thead>", "").replace("</thead>", "")
                        html = html.replace("<tbody>", "").replace("</tbody>", "")
                        # Convert headers to regular cells (boldness is less important than borders showing)
                        html = html.replace("<th ", "<td ").replace("</th>", "</td>")
                        html = html.replace("<th>", "<td>")
                        html = html.replace(
                            "<table>",
                            '<table border="1" rules="all" frame="box" cellspacing="0" cellpadding="6" style="border-collapse:collapse;border:1px solid #999;">'
                        )
                        html = html.replace(
                            "<table ",
                            '<table border="1" rules="all" frame="box" cellspacing="0" cellpadding="6" style="border-collapse:collapse;border:1px solid #999;" '
                        )
                        html = html.replace(
                            "<td>",
                            '<td border="1" style="border:1px solid #999; padding:6px 8px;">'
                        )
                        # Also handle tags with attributes
                        html = html.replace(
                            "<td ",
                            '<td border="1" style="border:1px solid #999; padding:6px 8px;" '
                        )
                        # Add borders to table rows as well
                        html = html.replace(
                            "<tr>",
                            '<tr style="border:1px solid #999;">'
                        )
                        html = html.replace(
                            "<tr ",
                            '<tr style="border:1px solid #999;" '
                        )
                except Exception:
                    pass

                # Ensure code/pre have visible formatting with inline styles
                if "<pre" in html:
                    html = html.replace("<pre>", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;">')
                    html = html.replace("<pre ", '<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;" ')
                if "<code" in html:
                    html = html.replace("<code>", '<code style="font-family:Consolas, \"Courier New\", monospace;">')
                    html = html.replace("<code ", '<code style="font-family:Consolas, \"Courier New\", monospace;" ')

                # Fallback: if fenced markers present but no <pre>, convert only fenced blocks via regex
                if "<pre" not in html and ("```" in display_text or "~~~" in display_text):
                    import re, html as _py_html
                    def _fence_to_pre(m):
                        code = m.group(2) if m.group(2) is not None else m.group(1)
                        return f'<pre style="background:#f6f8fa;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre;">{_py_html.escape(code)}</pre>'
                    # ```lang\ncode\n``` or ```\ncode\n```
                    html = re.sub(r"```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```", lambda m: _fence_to_pre(m), display_text)
                    # ~~~ variant
                    html = re.sub(r"~~~[a-zA-Z0-9_-]*\n([\s\S]*?)\n~~~", lambda m: _fence_to_pre(m), html)

                # Wrap with minimal inline styling accepted by tkhtmlview (no <style> tag)
                container_style = (
                    "font-family: Segoe UI, Arial, sans-serif; color: #222;"
                )
                # Inline pre/code/table styling by wrapping in a div
                warn_html = ""
                if missing_list:
                    items = ''.join(f"<li>{os.path.basename(p)}</li>" for p in missing_list[:8])
                    more = "" if len(missing_list) <= 8 else f"<li>… and {len(missing_list)-8} more</li>"
                    warn_html = f"<div style='background:#fff3cd;border:1px solid #ffeeba;padding:6px 8px;border-radius:6px;margin-bottom:8px;color:#8a6d3b;'>Missing image file(s):<ul style='margin:4px 0 0 18px'>{items}{more}</ul></div>"
                # If there is no text and no warning, push a minimal blank container to clear old content
                if not has_text and not warn_html:
                    try:
                        md_preview.set_html("<div></div>")
                    except Exception:
                        pass
                else:
                    styled = f"<div style=\"{container_style}\">{warn_html}{html}</div>"
                    md_preview.set_html(styled)
            except Exception:
                try:
                    md_preview.set_html("<pre>Failed to render markdown.</pre>")
                except Exception:
                    pass
        else:
            try:
                md_preview.configure(state=tk.NORMAL)
                md_preview.delete("1.0", tk.END)
                md_preview.insert(tk.END, sanitized_input if sanitized_input.strip() else "(Empty notes)")
                md_preview.configure(state=tk.DISABLED)
            except Exception:
                pass

    def md_path_for_transcript(txt_path: str) -> str:
        try:
            if not txt_path:
                return ""
            folder = os.path.dirname(txt_path)
            base, _ = os.path.splitext(os.path.basename(txt_path))
            return os.path.join(folder, base + ".md")
        except Exception:
            return ""

    def do_transcribe(audio_path: str):
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"File not found: {audio_path}")

            folder = os.path.dirname(audio_path)
            file_name = os.path.basename(audio_path)
            base, _ = os.path.splitext(file_name)

            set_status("Starting transcription...")
            append_log(f"Processing file: {file_name}")

            # If this is a large video, extract/cached WAV for faster repeated runs
            cached = get_or_make_cached_wav_for_large_video(audio_path, threshold_mb=200)
            input_for_whisper = cached if cached else audio_path

            # Build args and transcribe
            args = compute_transcribe_args()
            result = model.transcribe(input_for_whisper, **args)
            transcript = result.get("text", "").strip()
            # Post-translate to Chinese if requested
            if output_mode_var.get() == "Chinese (Translate)" and transcript:
                if ensure_deep_translator_installed():
                    transcript = translate_text(transcript, target_lang='zh-CN')
            append_log("Transcription completed.")

            output_file = os.path.join(folder, f"{base}.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcript)

            # Update UI with result path and copy to clipboard
            out_norm = _normpath(output_file)
            output_path_var.set(out_norm)
            root.clipboard_clear()
            root.clipboard_append(out_norm)
            root.update()  # now it stays on the clipboard after the app exits

            set_status("Saved transcript and copied path to clipboard. You can select another file.")
            append_log(f"Saved transcript to: {output_file}")

            # If the file is in the current folder view, update its transcript column
            if current_folder_var.get() and os.path.dirname(audio_path) == current_folder_var.get():
                item_id = path_to_item.get(audio_path)
                if item_id:
                    tree.set(item_id, "transcript", _normpath(output_file))
                    # Auto-fit transcript column after update
                    try:
                        autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
                    except Exception:
                        pass

            # Optional: show a message box
            try:
                messagebox.showinfo("Transcription Saved", f"Transcript saved to:\n{output_file}\n\nPath copied to clipboard.")
            except Exception:
                # In case messagebox cannot be shown in some environments
                pass

        except FileNotFoundError as e:
            set_status("Error: Required file not found.")
            append_log(str(e))
            append_log("1) The audio file was moved or deleted\n2) FFmpeg is not properly installed")
        except Exception as e:
            set_status("Unexpected error. See log.")
            append_log(f"Unexpected error: {e}")
            append_log(traceback.format_exc())
        finally:
            # Re-enable the button
            select_btn.configure(state=tk.NORMAL, text="Select Audio")

    def on_select_audio():
        # Allow multiple selection; model is reused
        # Support common video files as well (decoded via FFmpeg for Whisper)
        paths = filedialog.askopenfilenames(
            title="Select media file(s)",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma"),
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.wmv *.m4v *.webm *.mts *.m2ts *.ts *.3gp *.flv *.mpeg"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return

        # Convert to list and normalize
        file_list = [p for p in paths if p]
        if not file_list:
            return

        # Add the parent folder of the first selected file to Recent
        try:
            first_dir = os.path.dirname(os.path.abspath(file_list[0]))
            if first_dir and os.path.isdir(first_dir):
                add_recent_folder(first_dir)
        except Exception:
            pass

        # Disable while working
        select_btn.configure(state=tk.DISABLED, text="Transcribing...")
        transcribe_sel_btn.configure(state=tk.DISABLED)

        def run_batch():
            try:
                for idx, audio_path in enumerate(file_list, start=1):
                    current_file_var.set(audio_path)
                    output_path_var.set("")
                    set_status(f"[{idx}/{len(file_list)}] Starting transcription...")
                    append_log("")

                    # Perform transcription (same settings as single)
                    try:
                        if not os.path.exists(audio_path):
                            raise FileNotFoundError(f"File not found: {audio_path}")
                        folder = os.path.dirname(audio_path)
                        file_name = os.path.basename(audio_path)
                        base, _ = os.path.splitext(file_name)

                        append_log(f"Processing file: {file_name}")
                        args = compute_transcribe_args()
                        result = model.transcribe(
                            audio_path,
                            **args,
                        )

                        transcript = result.get("text", "").strip()
                        if output_mode_var.get() == "Chinese (Translate)" and transcript:
                            if ensure_deep_translator_installed():
                                transcript = translate_text(transcript, target_lang='zh-CN')
                        output_file = os.path.join(folder, f"{base}.txt")
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(transcript)

                        out_norm = _normpath(output_file)
                        output_path_var.set(out_norm)
                        root.clipboard_clear()
                        root.clipboard_append(out_norm)
                        root.update()
                        set_status(f"[{idx}/{len(file_list)}] Saved transcript and copied path. Next...")
                        append_log(f"Saved transcript to: {output_file}")

                        # Update tree if folder matches current view
                        if current_folder_var.get() and os.path.dirname(audio_path) == current_folder_var.get():
                            item_id = path_to_item.get(audio_path)
                            if item_id:
                                tree.set(item_id, "transcript", _normpath(output_file))
                                try:
                                    autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
                                except Exception:
                                    pass
                    except Exception as e:
                        append_log(f"Error transcribing {audio_path}: {e}")
                        append_log(traceback.format_exc())
                        continue
            finally:
                select_btn.configure(state=tk.NORMAL, text="Select Audio")
                transcribe_sel_btn.configure(state=tk.NORMAL)
                set_status("Batch complete.")

        threading.Thread(target=run_batch, daemon=True).start()

    def load_preview_for_item(iid: str):
        if not iid:
            set_preview_text("")
            return
        vals = tree.item(iid, "values")
        if not vals or len(vals) < 4:
            set_preview_text("")
            return
        transcript_path = vals[3]
        if transcript_path and isinstance(transcript_path, str) and os.path.isfile(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                set_preview_text(content)
                nb.select(preview_frame)
            except Exception as e:
                set_preview_text(f"Failed to load transcript:\n{e}")
        else:
            # No transcript: show empty preview
            set_preview_text("")

    def load_notes_for_item(iid: str):
        # Load notes editor based on the transcript path of the selected row
        if not iid:
            current_md_path_var.set("")
            notes_editor.delete("1.0", tk.END)
            render_markdown_to_preview("")
            return
        vals = tree.item(iid, "values")
        if not vals or len(vals) < 4:
            current_md_path_var.set("")
            notes_editor.delete("1.0", tk.END)
            render_markdown_to_preview("")
            return
        transcript_path = vals[3]
        # Compute audio-based and transcript-based candidates
        audio_display = vals[0] if len(vals) > 0 else ""
        if isinstance(audio_display, str) and audio_display.startswith("🎥 "):
            audio_display = audio_display[2:].lstrip()
        base_name = audio_display.replace(" (md only)", "").replace(" (no audio)", "").strip()
        folder = current_folder_var.get()
        audio_md = os.path.join(folder, base_name + ".md") if folder and base_name else ""
        txt_md = md_path_for_transcript(transcript_path) if (isinstance(transcript_path, str) and transcript_path and os.path.isfile(transcript_path)) else ""

        # Choose MD to show: prefer existing audio_md, then existing txt_md; else plan to write to audio_md
        chosen_md = audio_md if (audio_md and os.path.isfile(audio_md)) else (txt_md if (txt_md and os.path.isfile(txt_md)) else audio_md)
        current_md_path_var.set(chosen_md)
        notes_editor.delete("1.0", tk.END)
        if chosen_md and os.path.isfile(chosen_md):
            try:
                with open(chosen_md, "r", encoding="utf-8", errors="replace") as f:
                    notes_editor.insert(tk.END, f.read())
            except Exception as e:
                notes_editor.insert(tk.END, f"Failed to load notes:\n{e}")
        else:
            # No markdown file: show empty notes editor
            pass
        # Update preview to match editor content
        try:
            content = notes_editor.get("1.0", tk.END)
        except Exception:
            content = ""
        render_markdown_to_preview(content)

        # Diagnostics to log selection mapping (helps investigate mismatches)
        try:
            a_disp = vals[0] if len(vals) > 0 else ""
            t_disp = transcript_path if isinstance(transcript_path, str) else ""
            append_log(f"Notes selection: audio='{a_disp}' | transcript='{t_disp}' | audio_md='{audio_md}' | txt_md='{txt_md}' | chosen='{chosen_md}'")
        except Exception:
            pass

    def on_save_notes():
        md_path = current_md_path_var.get().strip()
        if not md_path:
            # Try to derive a sensible target from the current selection
            try:
                sel = tree.selection()
                iid = sel[0] if sel else ""
            except Exception:
                iid = ""
            target_folder = (current_folder_var.get() or "").strip()
            audio_base = ""
            transcript_dir = ""
            if iid:
                try:
                    vals = tree.item(iid, "values") or []
                    audio_disp = str(vals[0]) if len(vals) > 0 else ""
                    if audio_disp.startswith("🎥 "):
                        audio_disp = audio_disp[2:].lstrip()
                    audio_base = audio_disp.replace(" (md only)", "").replace(" (no audio)", "").strip()
                    if len(vals) >= 4 and isinstance(vals[3], str) and os.path.isfile(vals[3]):
                        transcript_dir = os.path.dirname(vals[3])
                except Exception:
                    pass
            if not target_folder:
                target_folder = transcript_dir
            if not target_folder:
                # As a last resort, ask the user for a folder to save notes
                try:
                    target_folder = filedialog.askdirectory(title="Select folder to save notes")
                except Exception:
                    target_folder = ""
            if target_folder and audio_base:
                md_path = os.path.join(target_folder, audio_base + ".md")
                current_md_path_var.set(md_path)
            else:
                messagebox.showwarning("No target path", "Please select a row or choose a folder before saving notes.")
                return
        try:
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            content = notes_editor.get("1.0", tk.END)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            set_status(f"Saved notes to: {md_path}")
            # Refresh preview after save
            render_markdown_to_preview(content)
            # Update saved-at label
            try:
                saved_at_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save notes:\n{e}")

    def on_reveal_notes():
        md_path = current_md_path_var.get().strip()
        if md_path:
            reveal_in_explorer(md_path)

    # Manual auto-fit trigger
    def on_autofit_columns():
        try:
            root.update_idletasks()
            autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
            set_status("Columns auto-fitted.")
        except Exception:
            pass

    def on_add_md_only():
        # Ensure we have a target folder
        folder = current_folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            folder = filedialog.askdirectory(title="Select a folder to create the Markdown file")
            if not folder:
                return
            current_folder_var.set(folder)
            append_log(f"Folder selected: {folder}")

        # Prompt for base name
        base = simpledialog.askstring(
            "Add Markdown Only",
            "File base name (without extension):",
            parent=root,
        )
        if base is None:
            return
        base = base.strip()
        invalid_chars = ['\\', '/', '\\r', '\\n', ':', '*', '?', '"', '<', '>', '|']
        if not base or any(ch in base for ch in invalid_chars):
            messagebox.showerror("Invalid name", "Please enter a valid file base name.")
            return

        md_path = os.path.join(folder, base + ".md")
        # Create or overwrite
        try:
            os.makedirs(folder, exist_ok=True)
            # Prepare images folder and a tiny placeholder image
            images_dir = os.path.join(folder, "images")
            os.makedirs(images_dir, exist_ok=True)
            placeholder_name = f"{base}.png"
            placeholder_path = os.path.join(images_dir, placeholder_name)
            # 1x1 transparent PNG
            _PNG_1x1_TRANSPARENT = (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
            )
            try:
                with open(placeholder_path, "wb") as imgf:
                    imgf.write(base64.b64decode(_PNG_1x1_TRANSPARENT))
            except Exception:
                # Non-fatal; continue without blocking creation
                pass
            # Write initial markdown template (with hyperlink example)
            initial = (
                f"# {base}\n\n"
                f"![Add image here](images/{placeholder_name})\n\n"
                f"Write your notes here.\n\n"
                f"## Example: Hyperlink\n"
                f"You can add a link like this: [OpenAI](https://www.openai.com).\n"
            )
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(initial)
        except Exception as e:
            messagebox.showerror("Create Failed", f"Could not create markdown file.\n\n{e}")
            return

        # Refresh UI and select the new row
        try:
            populate_tree(folder)
            add_recent_folder(folder)
            # Try to locate the inserted md-only row
            target_display = f"{base} (md only)"
            found_iid = None
            for iid in tree.get_children(""):
                vals = tree.item(iid, "values")
                if vals and len(vals) > 0 and str(vals[0]) == target_display:
                    found_iid = iid
                    break
            if found_iid:
                tree.focus(found_iid)
                tree.selection_set(found_iid)
                nb.select(notes_frame)
                # Load notes editor to this md file
                current_md_path_var.set(md_path)
                try:
                    notes_editor.delete("1.0", tk.END)
                    with open(md_path, "r", encoding="utf-8", errors="replace") as f:
                        notes_editor.insert(tk.END, f.read())
                except Exception:
                    pass
                # Render preview too
                try:
                    content = notes_editor.get("1.0", tk.END)
                except Exception:
                    content = ""
                render_markdown_to_preview(content)
            set_status(f"Created notes: {md_path}")
        except Exception:
            pass

    # Transcribe directly from a URL (e.g., YouTube) by downloading audio first
    def on_transcribe_url():
        try:
            # Ask for URL
            url = simpledialog.askstring(
                "Transcribe URL",
                "Enter media URL (YouTube, etc.):",
                parent=root,
            )
            if not url:
                return

            # Choose destination folder for transcript
            dest_folder = current_folder_var.get().strip()
            if not dest_folder or not os.path.isdir(dest_folder):
                dest_folder = filedialog.askdirectory(title="Select a folder to save the transcript")
                if not dest_folder:
                    return
                current_folder_var.set(dest_folder)
                append_log(f"Folder selected: {dest_folder}")
            # Add to Recent
            try:
                add_recent_folder(dest_folder)
            except Exception:
                pass

            # Disable buttons while we work
            try:
                transcribe_url_btn.configure(state=tk.DISABLED, text="Downloading...")
                select_btn.configure(state=tk.DISABLED)
                transcribe_sel_btn.configure(state=tk.DISABLED)
            except Exception:
                pass

            def worker():
                temp_dir = None
                media_path = None
                try:
                    set_status("Downloading media...")
                    media_path, temp_dir = _download_media_to_temp(url)
                    if not media_path:
                        set_status("Download failed. See log.")
                        return

                    # Determine base name to use for output
                    file_name = os.path.basename(media_path)
                    base, _ = os.path.splitext(file_name)

                    append_log(f"Processing URL -> file: {file_name}")
                    set_status("Transcribing...")

                    # Run Whisper directly so we can control the destination folder
                    try:
                        # Optionally extract cached WAV for large video files
                        cached = get_or_make_cached_wav_for_large_video(media_path, threshold_mb=200)
                    except Exception:
                        cached = None
                    input_for_whisper = cached if cached else media_path

                    args = compute_transcribe_args()
                    result = model.transcribe(
                        input_for_whisper,
                        **args,
                    )

                    transcript = result.get("text", "").strip()
                    if output_mode_var.get() == "Chinese (Translate)" and transcript:
                        if ensure_deep_translator_installed():
                            transcript = translate_text(transcript, target_lang='zh-CN')

                    output_file = os.path.join(dest_folder, f"{base}.txt")
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(transcript)

                    out_norm = _normpath(output_file)
                    output_path_var.set(out_norm)
                    try:
                        root.clipboard_clear()
                        root.clipboard_append(out_norm)
                        root.update()
                    except Exception:
                        pass

                    set_status("Saved transcript and copied path to clipboard.")
                    append_log(f"Saved transcript to: {output_file}")

                    # If the destination matches current view, refresh and try to reflect transcript
                    try:
                        if current_folder_var.get() and os.path.abspath(dest_folder) == os.path.abspath(current_folder_var.get()):
                            populate_tree(dest_folder)
                            # Attempt to locate the just-saved transcript row to show preview
                            for iid in tree.get_children(""):
                                vals = tree.item(iid, "values")
                                if vals and len(vals) > 3 and str(vals[3]) == out_norm:
                                    tree.focus(iid)
                                    tree.selection_set(iid)
                                    nb.select(preview_frame)
                                    break
                    except Exception:
                        pass
                except Exception as e:
                    append_log(f"URL transcription failed: {e}")
                    append_log(traceback.format_exc())
                    set_status("Unexpected error. See log.")
                finally:
                    # Cleanup temp dir
                    try:
                        if temp_dir and os.path.isdir(temp_dir):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                    except Exception:
                        pass
                    # Re-enable buttons
                    try:
                        transcribe_url_btn.configure(state=tk.NORMAL, text="Transcribe URL")
                        select_btn.configure(state=tk.NORMAL)
                        transcribe_sel_btn.configure(state=tk.NORMAL)
                    except Exception:
                        pass

            threading.Thread(target=worker, daemon=True).start()
        except Exception:
            # Non-fatal UI errors
            pass

    # Sorting state and helper
    sort_state = {}

    def tree_sort_by(col: str):
        # Toggle sort order for the column
        reverse = sort_state.get(col, False)
        items = list(tree.get_children(""))

        def key_for(iid):
            vals = tree.item(iid, "values")
            if not vals:
                return ""
            if col == "audio":
                return (vals[0] or "").lower()
            elif col == "size":
                folder = current_folder_var.get()
                try:
                    return os.path.getsize(os.path.join(folder, vals[0]))
                except Exception:
                    return -1
            elif col == "modified":
                folder = current_folder_var.get()
                try:
                    return os.path.getmtime(os.path.join(folder, vals[0]))
                except Exception:
                    return 0.0
            elif col == "transcript":
                return (vals[3] if len(vals) > 3 else "").lower()
            return (vals[0] or "").lower()

        items.sort(key=key_for, reverse=reverse)
        for idx, iid in enumerate(items):
            tree.move(iid, "", idx)
        # Update indicator on headers
        current_ascending = not reverse
        for c in cols:
            label = header_labels.get(c, c)
            if c == col:
                indicator = " ▲" if current_ascending else " ▼"
                tree.heading(c, text=label + indicator, command=lambda cc=c: tree_sort_by(cc))
            else:
                tree.heading(c, text=label, command=lambda cc=c: tree_sort_by(cc))
        sort_state[col] = not reverse
        # Auto-fit to account for header indicator and any content impact
        try:
            autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
        except Exception:
            pass

    def populate_tree(folder: str):
        # Clear existing
        for iid in tree.get_children():
            tree.delete(iid)
        path_to_item.clear()

        if not folder or not os.path.isdir(folder):
            return

        # Treat common video extensions as transcribable media (audio extracted by FFmpeg)
        audio_exts = {
            ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma",
            ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v", ".webm", ".mts", ".m2ts", ".ts",
            ".3gp", ".flv", ".mpeg",
        }
        entries = []
        audio_bases = set()
        names = sorted(os.listdir(folder))
        # First, collect audio/video files
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() in audio_exts:
                audio_bases.add(base)
                txt_path = os.path.join(folder, base + ".txt")
                transcript = _normpath(txt_path) if os.path.exists(txt_path) else "(missing)"

                try:
                    size_bytes = os.path.getsize(full)
                except Exception:
                    size_bytes = 0
                try:
                    mtime = os.path.getmtime(full)
                except Exception:
                    mtime = 0.0
                size_str = human_readable_size(size_bytes)
                modified_str = human_readable_mtime(mtime)
                display_name = ("🎥 " + name) if is_video_file(full) else name
                entries.append((display_name, full, size_str, modified_str, transcript, True))

        # Then, include standalone .txt transcripts without audio
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() == ".txt" and base not in audio_bases:
                # Represent as "<base> (no audio)" in the audio column
                display_audio_name = f"{base} (no audio)"
                try:
                    size_bytes = os.path.getsize(full)
                except Exception:
                    size_bytes = 0
                try:
                    mtime = os.path.getmtime(full)
                except Exception:
                    mtime = 0.0
                size_str = human_readable_size(size_bytes)
                modified_str = human_readable_mtime(mtime)
                transcript = _normpath(full)  # the .txt file path
                # Use a placeholder full path for mapping? We skip mapping since there's no audio
                entries.append((display_audio_name, None, size_str, modified_str, transcript, False))

        # Finally, include standalone .md notes without audio/.txt
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() == ".md" and base not in audio_bases:
                # Only include if there's no .txt alongside (pure md-only case)
                if not os.path.isfile(os.path.join(folder, base + ".txt")):
                    display_audio_name = f"{base} (md only)"
                    try:
                        size_bytes = os.path.getsize(full)
                    except Exception:
                        size_bytes = 0
                    try:
                        mtime = os.path.getmtime(full)
                    except Exception:
                        mtime = 0.0
                    size_str = human_readable_size(size_bytes)
                    modified_str = human_readable_mtime(mtime)
                    transcript = "(missing)"  # no transcript .txt
                    entries.append((display_audio_name, None, size_str, modified_str, transcript, False))

        # Insert rows
        for audio_name, full_audio_path, size_str, modified_str, transcript, has_audio in entries:
            iid = tree.insert("", tk.END, values=(audio_name, size_str, modified_str, transcript))
            if has_audio and full_audio_path:
                path_to_item[full_audio_path] = iid
        # Auto-fit after population
        try:
            autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
        except Exception:
            pass

    def on_browse_folder():
        folder = filedialog.askdirectory(title="Select a folder of audio files")
        if not folder:
            return
        current_folder_var.set(folder)
        append_log(f"Folder selected: {folder}")
        populate_tree(folder)
        add_recent_folder(folder)
        try:
            save_last_folder(folder)
        except Exception:
            pass

    def _update_status_for_selection(iid: str | None):
        try:
            if not iid:
                return
            vals = tree.item(iid, "values")
            if not vals:
                return
            sel_name = str(vals[0]) if len(vals) > 0 else ""
            # Only update the current file portion; keep the rest via status_var
            current_file_var.set(sel_name)
        except Exception:
            pass

    def _derive_md_path_from_row(iid: str) -> str:
        try:
            vals = tree.item(iid, "values") or []
            if len(vals) < 1:
                return ""
            # Derive audio-based candidate from display name and current folder
            audio_display = str(vals[0])
            # Strip UI adornments: video emoji and special suffixes
            if audio_display.startswith("🎥 "):
                audio_display = audio_display[2:].lstrip()
            base_name = audio_display.replace(" (md only)", "").replace(" (no audio)", "").strip()
            folder = current_folder_var.get().strip()
            audio_md = os.path.join(folder, base_name + ".md") if (folder and base_name) else ""

            # Transcript-based candidate
            txt_path = vals[3] if len(vals) >= 4 else ""
            txt_md = md_path_for_transcript(txt_path) if (isinstance(txt_path, str) and os.path.isfile(txt_path)) else ""

            # Prefer existing audio-based MD; else existing transcript-based MD
            if audio_md and os.path.isfile(audio_md):
                return audio_md
            if txt_md and os.path.isfile(txt_md):
                return txt_md
            # If neither exists, return audio-based target (for future saves)
            return audio_md or txt_md or ""
        except Exception:
            pass
        return ""

    def on_tree_select(event):
        try:
            sel = tree.selection()
            if not sel:
                return
            iid = sel[0]
            # Update status bar current file portion
            _update_status_for_selection(iid)

            # Determine preferred display: Markdown > TXT > Log
            md_path = _derive_md_path_from_row(iid)
            if md_path and os.path.isfile(md_path):
                # Load notes editor + preview, switch to Notes tab
                load_notes_for_item(iid)
                try:
                    nb.select(notes_frame)
                except Exception:
                    pass
                return

            # Fallback to transcript preview if present
            vals = tree.item(iid, "values") or []
            txt_path = str(vals[3]) if len(vals) >= 4 else ""
            if txt_path and os.path.isfile(txt_path):
                load_preview_for_item(iid)
                # Clear Notes context to avoid showing stale markdown from previous selection
                try:
                    current_md_path_var.set("")
                    notes_editor.delete("1.0", tk.END)
                except Exception:
                    pass
                try:
                    nb.select(preview_frame)
                except Exception:
                    pass
                return

            # Otherwise, show Log tab
            try:
                # Also clear Notes context for rows without md/txt
                current_md_path_var.set("")
                notes_editor.delete("1.0", tk.END)
            except Exception:
                pass
            try:
                nb.select(log_frame)
            except Exception:
                pass
        except Exception:
            pass

    def on_tree_double_click(event):
        item = tree.focus()
        if not item:
            return
        values = tree.item(item, "values")
        if not values:
            return
        audio_name = values[0]
        folder = current_folder_var.get()
        if not folder:
            return
        audio_path = os.path.join(folder, display_to_real_filename(audio_name))
        current_file_var.set(audio_path)
        output_path_var.set("")
        set_status("Preparing transcription...")
        select_btn.configure(state=tk.DISABLED, text="Transcribing...")
        t = threading.Thread(target=do_transcribe, args=(audio_path,), daemon=True)
        t.start()

    def on_transcribe_selected():
        # Transcribe all selected rows in the visual order
        sel = list(tree.selection())
        if not sel:
            messagebox.showwarning("No selection", "Please select one or more audio files in the list.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        # Order selected items by their current display order
        order = []
        selected_set = set(sel)
        for iid in tree.get_children(""):
            if iid in selected_set:
                order.append(iid)

        file_list = []
        for iid in order:
            vals = tree.item(iid, "values")
            if vals:
                file_list.append(os.path.join(folder, display_to_real_filename(vals[0])))
        if not file_list:
            return

        # Disable while working
        select_btn.configure(state=tk.DISABLED)
        transcribe_sel_btn.configure(state=tk.DISABLED, text="Transcribing...")

        def run_batch():
            try:
                for idx, audio_path in enumerate(file_list, start=1):
                    current_file_var.set(audio_path)
                    output_path_var.set("")
                    set_status(f"[{idx}/{len(file_list)}] Starting transcription...")
                    append_log("")
                    try:
                        if not os.path.exists(audio_path):
                            raise FileNotFoundError(f"File not found: {audio_path}")
                        folder_local = os.path.dirname(audio_path)
                        file_name = os.path.basename(audio_path)
                        base, _ = os.path.splitext(file_name)
                        append_log(f"Processing file: {file_name}")
                        cached = get_or_make_cached_wav_for_large_video(audio_path, threshold_mb=200)
                        input_for_whisper = cached if cached else audio_path
                        args = compute_transcribe_args()
                        result = model.transcribe(
                            input_for_whisper,
                            **args,
                        )
                        transcript = result.get("text", "").strip()
                        if output_mode_var.get() == "Chinese (Translate)" and transcript:
                            if ensure_deep_translator_installed():
                                transcript = translate_text(transcript, target_lang='zh-CN')
                        output_file = os.path.join(folder_local, f"{base}.txt")
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(transcript)
                        output_path_var.set(output_file)
                        root.clipboard_clear()
                        root.clipboard_append(output_file)
                        root.update()
                        set_status(f"[{idx}/{len(file_list)}] Saved transcript and copied path. Next...")
                        append_log(f"Saved transcript to: {output_file}")
                        # Update row
                        item_id = path_to_item.get(audio_path)
                        if item_id:
                            tree.set(item_id, "transcript", output_file)
                    except Exception as e:
                        append_log(f"Error transcribing {audio_path}: {e}")
                        append_log(traceback.format_exc())
                        continue
            finally:
                select_btn.configure(state=tk.NORMAL)
                transcribe_sel_btn.configure(state=tk.NORMAL, text="Transcribe Selected")
                set_status("Batch complete.")

        threading.Thread(target=run_batch, daemon=True).start()

    # --- Right-click menu for the transcript entry ---
    entry_menu = tk.Menu(root, tearoff=0)
    def entry_copy_full_path():
        path = output_path_var.get().strip()
        if path:
            copy_to_clipboard(path)
            set_status("Copied full path to clipboard.")
    def entry_copy_file_name():
        path = output_path_var.get().strip()
        if path:
            copy_to_clipboard(os.path.basename(path))
            set_status("Copied file name to clipboard.")
    def entry_reveal():
        path = output_path_var.get().strip()
        if path:
            reveal_in_explorer(path)

    entry_menu.add_command(label="Copy Full Path", command=entry_copy_full_path)
    entry_menu.add_command(label="Copy File Name", command=entry_copy_file_name)
    def entry_copy_folder_path():
        path = output_path_var.get().strip()
        if path:
            copy_to_clipboard(os.path.dirname(path))
            set_status("Copied folder path to clipboard.")
    def entry_open():
        path = output_path_var.get().strip()
        if path and os.path.isfile(path):
            open_with_default_app(path)

    entry_menu.add_separator()
    entry_menu.add_command(label="Copy Folder Path", command=entry_copy_folder_path)
    entry_menu.add_command(label="Open Transcript", command=entry_open)
    entry_menu.add_command(label="Reveal in Explorer", command=entry_reveal)

    def show_entry_menu(event):
        try:
            entry_menu.tk_popup(event.x_root, event.y_root)
        finally:
            entry_menu.grab_release()

    out_entry.bind("<Button-3>", show_entry_menu)  # Right-click on Windows

    # --- Right-click menu for the file list (uses transcript column) ---
    tree_menu = tk.Menu(root, tearoff=0)
    def tree_get_selected_paths():
        item = tree.focus()
        if not item:
            return None, None
        vals = tree.item(item, "values")
        if not vals:
            return None, None
        # vals: [audio_name, size_str, modified_str, transcript_val]
        audio_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None
        folder = current_folder_var.get()
        audio_path = os.path.join(folder, display_to_real_filename(audio_name)) if folder else None
        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" else None
        return audio_path, transcript_path

    def tree_copy_full_path():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            copy_to_clipboard(transcript_path)
            set_status("Copied transcript full path to clipboard.")

    def tree_copy_file_name():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            copy_to_clipboard(os.path.basename(transcript_path))
            set_status("Copied transcript file name to clipboard.")

    def tree_reveal():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            reveal_in_explorer(transcript_path)

    tree_menu.add_command(label="Copy Transcript Full Path", command=tree_copy_full_path)
    tree_menu.add_command(label="Copy Transcript File Name", command=tree_copy_file_name)
    def tree_copy_folder_path():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path:
            copy_to_clipboard(os.path.dirname(transcript_path))
            set_status("Copied transcript folder path to clipboard.")

    def tree_open():
        _, transcript_path = tree_get_selected_paths()
        if transcript_path and os.path.isfile(transcript_path):
            open_with_default_app(transcript_path)

    # --- Move Group (audio/txt/md) support ---
    def _unique_dest_path(dest_dir: str, base_name: str) -> str:
        try:
            candidate = os.path.join(dest_dir, base_name)
            if not os.path.exists(candidate):
                return candidate
            root_name, ext = os.path.splitext(base_name)
            n = 1
            while True:
                alt = os.path.join(dest_dir, f"{root_name} ({n}){ext}")
                if not os.path.exists(alt):
                    return alt
                n += 1
        except Exception:
            return os.path.join(dest_dir, base_name)

    def _get_associated_paths_for_item(item) -> list[tuple[str, str]]:
        # Returns list of (path, friendly_name) for audio, txt, md if present
        out: list[tuple[str, str]] = []
        vals = tree.item(item, "values") or []
        if not vals:
            return out
        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None
        folder = current_folder_var.get()
        # transcript
        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" else None
        if transcript_path and os.path.isfile(transcript_path):
            out.append((transcript_path, os.path.basename(transcript_path)))
        # md derived from transcript
        md_path = md_path_for_transcript(transcript_path) if transcript_path else None
        if md_path and os.path.isfile(md_path):
            out.append((md_path, os.path.basename(md_path)))
        # audio unless this is a standalone row
        if audio_display_name and not audio_display_name.endswith(" (no audio)"):
            try:
                audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
                if os.path.isfile(audio_path):
                    out.append((audio_path, os.path.basename(audio_path)))
            except Exception:
                pass
        return out

    def on_move_group_selected():
        # Move audio/txt/md associated with the focused row
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row to move.")
            return
        folder = current_folder_var.get()
        if not folder:
            return
        paths = _get_associated_paths_for_item(item)
        if not paths:
            messagebox.showinfo("Nothing to move", "No associated files (audio/txt/md) exist on disk.")
            return
        # Ask destination
        dest = filedialog.askdirectory(title="Select destination folder for group move")
        if not dest:
            return
        dest = os.path.abspath(dest)
        if os.path.abspath(dest) == os.path.abspath(folder):
            messagebox.showinfo("Same folder", "Destination is the same as the current folder.")
            return
        errors = []
        moved = []
        for p, name in paths:
            try:
                target = _unique_dest_path(dest, name)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.move(p, target)
                moved.append((p, target))
            except Exception as e:
                errors.append(f"{name}: {e}")
        # Update UI: remove row from current list
        try:
            tree.delete(item)
        except Exception:
            pass
        # Add destination to recent
        try:
            add_recent_folder(dest)
        except Exception:
            pass
        if errors:
            messagebox.showerror("Move completed with errors", "Some files could not be moved:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Move complete", f"Moved {len(moved)} file(s) to:\n{dest}")
        set_status("Group move finished.")

    # Add context menu entry for Move Group
    tree_menu.add_separator()
    tree_menu.add_command(label="Move Group (audio/txt/md)...", command=on_move_group_selected)

    def tree_delete_audio_only():
        # Delete only the audio file for the selected row; keep .txt and .md
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_display_name = vals[0]
        if not audio_display_name or audio_display_name.endswith(" (no audio)") or audio_display_name.endswith(" (md only)"):
            messagebox.showinfo("No audio", "This row has no audio file to delete.")
            return
        audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
        if not os.path.isfile(audio_path):
            messagebox.showinfo("Missing file", "Audio file does not exist on disk.")
            return
        if not messagebox.askyesno("Delete Audio", f"Move audio to Recycle Bin?\n\n{os.path.basename(audio_path)}", parent=root):
            return
        try:
            safe_delete_to_trash(audio_path)
            # Remove row or update it? Keep row but audio gone; better to remove row and re-populate
            tree.delete(item)
            set_status("Audio deleted.")
        except Exception as e:
            messagebox.showerror("Delete failed", str(e))

    def tree_delete_audio_and_txt_keep_md():
        # Delete audio and associated .txt, keep .md (notes)
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None
        candidate_paths = []
        friendly = []
        # audio
        if audio_display_name and not audio_display_name.endswith(" (no audio)") and not audio_display_name.endswith(" (md only)"):
            ap = os.path.join(folder, display_to_real_filename(audio_display_name))
            if os.path.isfile(ap):
                candidate_paths.append(ap)
                friendly.append(os.path.basename(ap))
        # txt
        tp = transcript_val if transcript_val and transcript_val != "(missing)" else None
        if tp and os.path.isfile(tp):
            candidate_paths.append(tp)
            friendly.append(os.path.basename(tp))
        if not candidate_paths:
            messagebox.showinfo("Nothing to delete", "No audio or transcript files found to delete.")
            return
        names = "\n".join(friendly)
        if not messagebox.askyesno("Delete Audio + Transcript", f"Move the following to Recycle Bin (notes .md will be kept):\n\n{names}\n\nProceed?", parent=root):
            return
        errors = []
        for p in candidate_paths:
            try:
                safe_delete_to_trash(p)
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")
        try:
            tree.delete(item)
        except Exception:
            pass
        if errors:
            messagebox.showerror("Some deletions failed", "\n".join(errors))
        set_status("Audio and transcript deleted; notes kept.")
    def tree_delete_selected_with_associated():
        # Delete the selected row and any associated files: audio, transcript (.txt), and notes (.md)
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row to delete.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None

        # Determine actual file paths
        candidate_paths = []
        friendly_list = []

        # Transcript (.txt)
        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" else None
        if transcript_path and os.path.isfile(transcript_path):
            candidate_paths.append(transcript_path)
            friendly_list.append(os.path.basename(transcript_path))

        # Notes (.md) derived from transcript
        md_path = md_path_for_transcript(transcript_path) if transcript_path else None
        if md_path and os.path.isfile(md_path):
            candidate_paths.append(md_path)
            friendly_list.append(os.path.basename(md_path))

        # Audio file (skip if this is a standalone transcript row shown as "(no audio)")
        if audio_display_name and not audio_display_name.endswith(" (no audio)"):
            audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
            if os.path.isfile(audio_path):
                candidate_paths.append(audio_path)
                friendly_list.append(os.path.basename(audio_path))

        if not candidate_paths:
            # Nothing to delete on disk; just remove the row after confirmation
            if not messagebox.askyesno("Delete Row", "No associated files found on disk. Remove the row from the list?", parent=root):
                return
            try:
                tree.delete(item)
                set_status("Row removed.")
            except Exception:
                pass
            return

        # Confirm deletion
        names = "\n".join(friendly_list)
        prompt = "move to Recycle Bin" if ensure_send2trash_ready() else "be permanently deleted"
        if not messagebox.askyesno("Delete Files", f"The following files will {prompt}:\n\n{names}\n\nProceed?", parent=root):
            return

        # Attempt deletion (to Recycle Bin when possible)
        errors = []
        for p in candidate_paths:
            try:
                safe_delete_to_trash(p)
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        # Update UI
        try:
            tree.delete(item)
        except Exception:
            pass
        # Clear preview/notes if they were showing the deleted transcript
        try:
            if transcript_path and output_path_var.get().strip() == transcript_path:
                set_preview_text("")
                current_md_path_var.set("")
                notes_editor.delete("1.0", tk.END)
        except Exception:
            pass

        if errors:
            messagebox.showerror("Some deletions failed", "\n".join(errors))
            set_status("Delete completed with errors.")
        else:
            set_status("Selected files deleted and row removed.")

    def tree_rename_pair():
        # Rename audio/video, .txt, and .md associated with the selected row
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select a row in the list.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return

        audio_display_name = vals[0]
        transcript_val = vals[3] if len(vals) > 3 else None

        # Resolve existing associated paths
        audio_path = None
        if audio_display_name and not audio_display_name.endswith(" (no audio)") and not audio_display_name.endswith(" (md only)"):
            try:
                audio_path = os.path.join(folder, display_to_real_filename(audio_display_name))
                if not os.path.isfile(audio_path):
                    audio_path = None
            except Exception:
                audio_path = None

        transcript_path = transcript_val if transcript_val and transcript_val != "(missing)" and os.path.isfile(transcript_val) else None
        md_path = md_path_for_transcript(transcript_path) if transcript_path else None
        if md_path and not os.path.isfile(md_path):
            md_path = None
        # If there is no transcript-derived MD, try deriving MD directly from the display name (handles 'md only' rows)
        if md_path is None:
            try:
                disp = display_to_real_filename(audio_display_name)
                # Strip UI suffixes
                base_guess = disp.replace(" (md only)", "").replace(" (no audio)", "")
                base_guess = os.path.splitext(base_guess)[0]
                candidate_md = os.path.join(folder, base_guess + ".md")
                if os.path.isfile(candidate_md):
                    md_path = candidate_md
            except Exception:
                pass

        # Determine current base name to propose
        if transcript_path:
            base_current = os.path.splitext(os.path.basename(transcript_path))[0]
        elif audio_path:
            base_current = os.path.splitext(os.path.basename(audio_path))[0]
        else:
            # Standalone rows: derive from display name (strip UI suffixes and extension)
            name = audio_display_name
            if name.endswith(" (no audio)"):
                name = name[:-11]
            if name.endswith(" (md only)"):
                name = name[:-10]
            base_current = os.path.splitext(name)[0]

        new_base = simpledialog.askstring(
            "Rename",
            "New base name (without extension):",
            initialvalue=base_current,
            parent=root,
        )
        if new_base is None:
            return
        new_base = new_base.strip()
        invalid_chars = ['\\', '/', '\\r', '\\n', ':', '*', '?', '"', '<', '>', '|']
        if not new_base or any(ch in new_base for ch in invalid_chars):
            messagebox.showerror("Invalid name", "Please enter a valid file base name.")
            return
        if new_base == base_current:
            return  # nothing to do

        # Compute target paths preserving audio extension
        new_audio_path = None
        new_audio_display_name = None
        if audio_path:
            ext = os.path.splitext(audio_path)[1]
            new_audio_display_name = new_base + ext
            new_audio_path = os.path.join(folder, new_audio_display_name)
        elif audio_display_name.endswith(" (no audio)"):
            new_audio_display_name = f"{new_base} (no audio)"
        elif audio_display_name.endswith(" (md only)"):
            new_audio_display_name = f"{new_base} (md only)"

        new_txt_path = os.path.join(folder, new_base + ".txt") if transcript_path else None
        new_md_path = os.path.join(folder, new_base + ".md") if (md_path or transcript_path) else None

        # Check conflicts
        conflicts = []
        if new_audio_path and os.path.exists(new_audio_path):
            conflicts.append(os.path.basename(new_audio_path))
        if new_txt_path and os.path.exists(new_txt_path):
            conflicts.append(os.path.basename(new_txt_path))
        if new_md_path and os.path.exists(new_md_path):
            conflicts.append(os.path.basename(new_md_path))
        if conflicts:
            names = "\n".join(conflicts)
            if not messagebox.askyesno("Overwrite?", f"The following files already exist and will be overwritten:\n\n{names}\n\nProceed?", parent=root):
                return

        # Execute renames
        try:
            if audio_path and new_audio_path and audio_path != new_audio_path:
                os.replace(audio_path, new_audio_path)
            if transcript_path and new_txt_path and transcript_path != new_txt_path:
                try:
                    os.replace(transcript_path, new_txt_path)
                    transcript_path = new_txt_path
                except Exception as e:
                    messagebox.showwarning("Partial rename", f"Audio renamed but transcript could not be renamed.\n\n{e}")
            if (md_path or (transcript_path and new_md_path)):
                # If md exists, rename it; if not, leave it missing
                if md_path and new_md_path and md_path != new_md_path and os.path.isfile(md_path):
                    try:
                        os.replace(md_path, new_md_path)
                        md_path = new_md_path
                    except Exception as e:
                        messagebox.showwarning("Partial rename", f"Markdown could not be renamed.\n\n{e}")

            # Update UI row
            try:
                if audio_path:
                    # Decide emoji for video types
                    disp_name = new_audio_display_name
                    try:
                        if is_video_file(new_audio_path):
                            disp_name = "🎥 " + new_audio_display_name
                    except Exception:
                        pass
                    tree.set(item, "audio", disp_name)
                else:
                    # Standalone rows retain suffix
                    if new_audio_display_name:
                        tree.set(item, "audio", new_audio_display_name)

                if transcript_path:
                    tree.set(item, "transcript", new_txt_path or transcript_path)
                else:
                    tree.set(item, "transcript", "(missing)")
            except Exception:
                pass

            # Update mapping for path_to_item (audio)
            try:
                if audio_path and new_audio_path and audio_path in path_to_item:
                    iid_ref = path_to_item.pop(audio_path)
                    path_to_item[new_audio_path] = iid_ref
            except Exception:
                pass

            # Update Notes tab to new md (if any) and refresh preview
            try:
                if new_md_path and os.path.isfile(new_md_path):
                    current_md_path_var.set(new_md_path)
                else:
                    current_md_path_var.set("")
            except Exception:
                pass
            try:
                notes_editor.delete("1.0", tk.END)
                if new_md_path and os.path.isfile(new_md_path):
                    with open(new_md_path, "r", encoding="utf-8", errors="replace") as f:
                        notes_editor.insert(tk.END, f.read())
                content = notes_editor.get("1.0", tk.END)
                render_markdown_to_preview(content)
            except Exception:
                pass

            set_status("Renamed associated files.")
        except Exception as e:
            messagebox.showerror("Rename failed", f"Could not rename files.\n\n{e}")

    tree_menu.add_separator()
    tree_menu.add_command(label="Delete Audio Only", command=tree_delete_audio_only)
    tree_menu.add_command(label="Delete Audio + Transcript (keep .md)", command=tree_delete_audio_and_txt_keep_md)
    tree_menu.add_command(label="Delete Selected (audio/txt/md)…", command=tree_delete_selected_with_associated)
    tree_menu.add_command(label="Rename Associated Files (audio/txt/md)…", command=tree_rename_pair)
    tree_menu.add_command(label="Copy Transcript Folder Path", command=tree_copy_folder_path)
    tree_menu.add_command(label="Open Transcript", command=tree_open)
    tree_menu.add_command(label="Reveal Transcript in Explorer", command=tree_reveal)

    def on_tree_right_click(event):
        # Select the item under cursor first
        iid = tree.identify_row(event.y)
        if iid:
            tree.selection_set(iid)
            tree.focus(iid)
        try:
            tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            tree_menu.grab_release()

    select_btn.configure(command=on_select_audio)
    browse_btn.configure(command=on_browse_folder)
    transcribe_url_btn.configure(command=on_transcribe_url)
    transcribe_sel_btn.configure(command=on_transcribe_selected)
    auto_fit_btn.configure(command=on_autofit_columns)
    add_md_btn.configure(command=on_add_md_only)
    recent_open_btn.configure(command=open_recent_selected)
    notes_save_btn.configure(command=on_save_notes)
    notes_reveal_btn.configure(command=on_reveal_notes)
    move_group_btn.configure(command=on_move_group_selected)
    tree.bind("<Double-1>", on_tree_double_click)
    tree.bind("<Button-3>", on_tree_right_click)
    # Single selection handler: prefer Markdown > TXT > Log
    tree.bind("<<TreeviewSelect>>", on_tree_select)
    recent_combo.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())

    # Debounced live preview and auto-save while typing
    _md_preview_job = None
    _md_autosave_job = None
    def _on_notes_keypress(event=None):
        nonlocal _md_preview_job, _md_autosave_job
        # Debounce preview update
        try:
            if _md_preview_job is not None:
                root.after_cancel(_md_preview_job)
        except Exception:
            pass
        def do_update_preview():
            try:
                content = notes_editor.get("1.0", tk.END)
            except Exception:
                content = ""
            render_markdown_to_preview(content)
        _md_preview_job = root.after(300, do_update_preview)

        # Debounce auto-save to disk (respect toggle and delay)
        try:
            if _md_autosave_job is not None:
                root.after_cancel(_md_autosave_job)
        except Exception:
            pass
        def do_autosave():
            md_path = current_md_path_var.get().strip()
            if not md_path:
                return
            try:
                os.makedirs(os.path.dirname(md_path), exist_ok=True)
                content = notes_editor.get("1.0", tk.END)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(content)
                # Light-touch status update without interrupting flow
                try:
                    set_status(f"Auto-saved notes: {os.path.basename(md_path)}")
                    saved_at_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
                except Exception:
                    pass
            except Exception:
                # Silent fail for autosave to avoid modal interruptions while typing
                pass
        # Only schedule autosave if enabled
        try:
            if autosave_enabled_var.get():
                delay_ms = int(max(0.0, float(autosave_delay_s_var.get())) * 1000)
                if delay_ms < 50:
                    delay_ms = 50
                _md_autosave_job = root.after(delay_ms, do_autosave)
        except Exception:
            # Fallback to default 1000 ms if something goes wrong reading the delay
            _md_autosave_job = root.after(1000, do_autosave)
    notes_editor.bind("<KeyRelease>", _on_notes_keypress)

    # Auto-fit on window resize with debounce
    resize_job_id = None

    def on_root_resize(event):
        nonlocal resize_job_id
        # Only respond to root window resize events
        if event.widget is not root:
            return
        if resize_job_id is not None:
            try:
                root.after_cancel(resize_job_id)
            except Exception:
                pass
        # Debounce: run after 150 ms
        def do_fit():
            try:
                autofit_tree_columns(tree, cols, min_widths={"size": 80, "modified": 140}, padding=18)
            except Exception:
                pass
        resize_job_id = root.after(150, do_fit)

    root.bind("<Configure>", on_root_resize)

    # Ready
    set_status("Model loaded. Ready to transcribe.")
    # Bind selection event handler already set above
    # Load recent folders on startup
    try:
        set_recent_values(load_recent_folders())
    except Exception:
        pass
    # Auto-open last folder if available
    try:
        last = load_last_folder()
        if last:
            current_folder_var.set(last)
            populate_tree(last)
            # Reflect in Recent dropdown and selection
            add_recent_folder(last)
            recent_var.set(last)
            open_recent_selected()
    except Exception:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()

# choco install ffmpeg
# ffmpeg -version
# pip install torch
# python -c "import torch; print(torch.cuda.is_available())"
# pip install -U openai-whisper
# whisper --help
# python "C:\\Users\\JueShi\\OneDrive - Astera Labs, Inc\\Documents\\windsurf\\audio2text.py"

# working
# & 'c:\Program Files\Python311\python.exe' 'c:\Users\juesh\.windsurf\extensions\ms-python.debugpy-2025.10.0-win32-x64\bundled\libs\debugpy\launcher' '64312' '--' 'c:\Users\juesh\OneDrive\Documents\windsurf\stock_charts_10k10q\audio2ext_v1.1_path.py' 

# not working
# & 'c:\Users\juesh\AppData\Local\Programs\Python\Python313\python.exe' 'c:\Users\juesh\.windsurf\extensions\ms-python.debugpy-2025.10.0-win32-x64\bundled\libs\debugpy\launcher' '53222' '--' 'c:\Users\juesh\OneDrive\Documents\pandastable\examples\audio2ext_v1.1_path.py' 
