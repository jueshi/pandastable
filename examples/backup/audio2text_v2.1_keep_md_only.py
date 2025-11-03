import whisper
import os
import json
import subprocess
import sys
import threading
import traceback

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

    # Try to prepare lightweight Markdown rendering deps
    def ensure_md_preview_deps():
        md_mod = None
        html_label_cls = None
        try:
            import markdown as _md
            md_mod = _md
        except Exception:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"]) 
                import markdown as _md
                md_mod = _md
            except Exception:
                md_mod = None
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
        return md_mod, html_label_cls

    md_module, HTMLLabel = ensure_md_preview_deps()

    # Load Whisper model once
    print("Loading Whisper model (this may take a moment)...")
    model = whisper.load_model("small")  # memory: ~1 GB (CPU) / ~6 GB (GPU)

    # Build GUI
    root = tk.Tk()
    root.title("Audio to Text (Whisper)")
    root.geometry("900x600")

    # UI Elements
    status_var = tk.StringVar(value="Ready. Click 'Select Audio' to transcribe.")
    current_file_var = tk.StringVar(value="No file selected.")
    output_path_var = tk.StringVar(value="")

    header = tk.Label(root, text="Audio to Text Transcription", font=("Segoe UI", 14, "bold"))
    header.pack(pady=(12, 6))

    frame = tk.Frame(root)
    frame.pack(fill=tk.X, padx=12)

    select_btn = tk.Button(frame, text="Select Audio", width=16)
    select_btn.pack(side=tk.LEFT)

    browse_btn = tk.Button(frame, text="Browse Folder", width=16)
    browse_btn.pack(side=tk.LEFT, padx=(8, 0))

    transcribe_sel_btn = tk.Button(frame, text="Transcribe Selected", width=20)
    transcribe_sel_btn.pack(side=tk.LEFT, padx=(8, 0))

    auto_fit_btn = tk.Button(frame, text="Auto-fit Columns", width=18)
    auto_fit_btn.pack(side=tk.LEFT, padx=(8, 0))

    # Recent folders: dropdown + open button
    tk.Label(frame, text="Recent:").pack(side=tk.LEFT, padx=(12, 4))
    recent_var = tk.StringVar(value="")
    recent_combo = ttk.Combobox(frame, textvariable=recent_var, width=40, state="readonly")
    recent_combo.pack(side=tk.LEFT, padx=(0, 4))
    recent_open_btn = tk.Button(frame, text="Open", width=8)
    recent_open_btn.pack(side=tk.LEFT)

    quit_btn = tk.Button(frame, text="Quit", command=root.destroy)
    quit_btn.pack(side=tk.RIGHT)

    file_label = tk.Label(root, textvariable=current_file_var, anchor="w")
    file_label.pack(fill=tk.X, padx=12, pady=(8, 2))

    status_label = tk.Label(root, textvariable=status_var, anchor="w")
    status_label.pack(fill=tk.X, padx=12, pady=(2, 8))

    # Paned layout: upper file list, lower log
    paned = ttk.Panedwindow(root, orient=tk.VERTICAL)
    paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

    # Upper: file browser tree
    files_frame = tk.Frame(paned)
    cols = ("audio", "size", "modified", "transcript")
    tree = ttk.Treeview(files_frame, columns=cols, show="headings", height=10, selectmode="extended")
    header_labels = {
        "audio": "Audio File",
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
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    paned.add(files_frame, weight=1)

    # Lower: Notebook with Log, Preview, and Notes tabs
    nb = ttk.Notebook(paned)
    paned.add(nb, weight=1)

    # Log tab
    log_frame = tk.Frame(nb)
    log = tk.Text(log_frame, height=10, wrap="word")
    log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log.yview)
    log.configure(state=tk.DISABLED, yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    nb.add(log_frame, text="Log")

    # Preview tab
    preview_frame = tk.Frame(nb)
    preview = tk.Text(preview_frame, height=10, wrap="word")
    preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview.yview)
    preview.configure(state=tk.DISABLED, yscrollcommand=preview_scroll.set)
    preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    nb.add(preview_frame, text="Preview")

    # Notes (Markdown) tab
    notes_frame = tk.Frame(nb)
    notes_toolbar = tk.Frame(notes_frame)
    notes_toolbar.pack(fill=tk.X, padx=6, pady=(6, 4))
    current_md_path_var = tk.StringVar(value="")
    tk.Label(notes_toolbar, text="Notes file:").pack(side=tk.LEFT)
    notes_path_label = tk.Label(notes_toolbar, textvariable=current_md_path_var, anchor="w")
    notes_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
    notes_save_btn = tk.Button(notes_toolbar, text="Save Notes")
    notes_save_btn.pack(side=tk.RIGHT, padx=(6, 0))
    notes_reveal_btn = tk.Button(notes_toolbar, text="Reveal")
    notes_reveal_btn.pack(side=tk.RIGHT)

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
    if HTMLLabel is not None:
        md_preview = HTMLLabel(preview_container, html="", background="white")
        md_preview.pack(fill=tk.BOTH, expand=True)
    else:
        # Fallback to read-only text if HTML renderer unavailable
        md_preview = tk.Text(preview_container, height=10, wrap="word", state=tk.DISABLED)
        md_preview.pack(fill=tk.BOTH, expand=True)

    notes_split.add(editor_container, weight=1)
    notes_split.add(preview_container, weight=1)
    nb.add(notes_frame, text="Notes (Markdown)")

    out_frame = tk.Frame(root)
    out_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
    tk.Label(out_frame, text="Saved transcript:").pack(side=tk.LEFT)
    out_entry = tk.Entry(out_frame, textvariable=output_path_var)
    out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))

    # Context menu helpers
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
    MAX_RECENT = 10

    def load_recent_folders():
        try:
            if os.path.isfile(RECENT_FILE):
                with open(RECENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # Keep only existing directories
                    vals = [p for p in data if isinstance(p, str) and os.path.isdir(p)]
                    recent_combo["values"] = vals
                    return vals
        except Exception:
            pass
        recent_combo["values"] = []
        return []

    def save_recent_folders(values: list[str]):
        try:
            with open(RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump(values[:MAX_RECENT], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_recent_values(values: list[str]):
        recent_combo["values"] = values[:MAX_RECENT]
        # If current value not in list, clear selection
        if recent_var.get() not in values:
            recent_var.set("")

    def add_recent_folder(path: str):
        if not path or not os.path.isdir(path):
            return
        path = os.path.abspath(path)
        current_vals = list(recent_combo["values"]) if recent_combo["values"] else []
        # Move to front, remove duplicates
        new_vals = [path] + [p for p in current_vals if os.path.abspath(p) != path]
        new_vals = new_vals[:MAX_RECENT]
        set_recent_values(new_vals)
        save_recent_folders(new_vals)

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

    def append_log(text: str):
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, text + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    def set_preview_text(text: str):
        preview.configure(state=tk.NORMAL)
        preview.delete("1.0", tk.END)
        preview.insert(tk.END, text)
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

    def render_markdown_to_preview(text: str):
        # Convert markdown to HTML if possible, else just show plain text
        if 'HTMLLabel' in locals() and HTMLLabel is not None:
            try:
                html = text
                if 'md_module' in locals() and md_module is not None:
                    html = md_module.markdown(text, extensions=["fenced_code", "tables"])
                styled = f"""
                <div style='font-family: Segoe UI, Arial, sans-serif; font-size: 12pt; color: #222;'>
                {html}
                </div>
                """
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
                md_preview.insert(tk.END, text)
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

            # Transcribe with explicit device setting for CPU-friendliness
            result = model.transcribe(
                audio_path,
                fp16=False,   # Force FP32 for CPU
                verbose=True  # Show progress in console
            )

            transcript = result.get("text", "").strip()
            append_log("Transcription completed.")

            output_file = os.path.join(folder, f"{base}.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcript)

            # Update UI with result path and copy to clipboard
            output_path_var.set(output_file)
            root.clipboard_clear()
            root.clipboard_append(output_file)
            root.update()  # now it stays on the clipboard after the app exits

            set_status("Saved transcript and copied path to clipboard. You can select another file.")
            append_log(f"Saved transcript to: {output_file}")

            # If the file is in the current folder view, update its transcript column
            if current_folder_var.get() and os.path.dirname(audio_path) == current_folder_var.get():
                item_id = path_to_item.get(audio_path)
                if item_id:
                    tree.set(item_id, "transcript", output_file)
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
        paths = filedialog.askopenfilenames(
            title="Select audio file(s)",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return

        # Convert to list and normalize
        file_list = [p for p in paths if p]
        if not file_list:
            return

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
                        result = model.transcribe(
                            audio_path,
                            fp16=False,
                            verbose=True,
                        )
                        transcript = result.get("text", "").strip()
                        output_file = os.path.join(folder, f"{base}.txt")
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(transcript)

                        output_path_var.set(output_file)
                        root.clipboard_clear()
                        root.clipboard_append(output_file)
                        root.update()
                        set_status(f"[{idx}/{len(file_list)}] Saved transcript and copied path. Next...")
                        append_log(f"Saved transcript to: {output_file}")

                        # Update tree if folder matches current view
                        if current_folder_var.get() and os.path.dirname(audio_path) == current_folder_var.get():
                            item_id = path_to_item.get(audio_path)
                            if item_id:
                                tree.set(item_id, "transcript", output_file)
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
            set_preview_text("(No transcript available for this row)")

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
        # Determine md path: prefer deriving from transcript; if missing, derive from audio display name
        if isinstance(transcript_path, str) and transcript_path and os.path.isfile(transcript_path):
            md_path = md_path_for_transcript(transcript_path)
        else:
            # Handle md-only row like "<base> (md only)" or other cases
            audio_display = vals[0] if len(vals) > 0 else ""
            # Strip suffixes used for special rows
            base_name = audio_display.replace(" (md only)", "").replace(" (no audio)", "")
            folder = current_folder_var.get()
            md_path = os.path.join(folder, base_name + ".md") if folder and base_name else ""
        current_md_path_var.set(md_path)
        notes_editor.delete("1.0", tk.END)
        if md_path and os.path.isfile(md_path):
            try:
                with open(md_path, "r", encoding="utf-8", errors="replace") as f:
                    notes_editor.insert(tk.END, f.read())
            except Exception as e:
                notes_editor.insert(tk.END, f"Failed to load notes:\n{e}")
        else:
            if md_path:
                notes_editor.insert(tk.END, "# Notes\n\nWrite your notes here. Click 'Save Notes' to create the file.")
        # Update preview to match editor content
        try:
            content = notes_editor.get("1.0", tk.END)
        except Exception:
            content = ""
        render_markdown_to_preview(content)

    def on_save_notes():
        md_path = current_md_path_var.get().strip()
        if not md_path:
            messagebox.showwarning("No transcript selected", "Select a row with a transcript to associate notes.")
            return
        try:
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            content = notes_editor.get("1.0", tk.END)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            set_status(f"Saved notes to: {md_path}")
            # Refresh preview after save
            render_markdown_to_preview(content)
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

        audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}
        entries = []
        audio_bases = set()
        names = sorted(os.listdir(folder))
        # First, collect audio files
        for name in names:
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() in audio_exts:
                audio_bases.add(base)
                txt_path = os.path.join(folder, base + ".txt")
                transcript = txt_path if os.path.exists(txt_path) else "(missing)"

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
                entries.append((name, full, size_str, modified_str, transcript, True))

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
                transcript = full  # the .txt file path
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
        audio_path = os.path.join(folder, audio_name)
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
                file_list.append(os.path.join(folder, vals[0]))
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
                        result = model.transcribe(audio_path, fp16=False, verbose=True)
                        transcript = result.get("text", "").strip()
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
        audio_path = os.path.join(folder, audio_name) if folder else None
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
        audio_path = os.path.join(folder, audio_display_name)
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
            ap = os.path.join(folder, audio_display_name)
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
            audio_path = os.path.join(folder, audio_display_name)
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
        # Get selected audio and potential transcript
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select an audio file in the list.")
            return
        vals = tree.item(item, "values")
        if not vals:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        old_audio_name = vals[0]
        old_audio_path = os.path.join(folder, old_audio_name)
        base_old, ext_old = os.path.splitext(old_audio_name)
        old_txt_path = os.path.join(folder, base_old + ".txt")
        has_txt = os.path.exists(old_txt_path)

        # Ask for new base name
        new_base = simpledialog.askstring(
            "Rename",
            "New base name (without extension):",
            initialvalue=base_old,
            parent=root,
        )
        if new_base is None:
            return  # cancelled
        new_base = new_base.strip()
        # Disallow Windows-invalid filename characters
        invalid_chars = ['\\', '/', '\\r', '\\n', ':', '*', '?', '"', '<', '>', '|']
        if not new_base or any(ch in new_base for ch in invalid_chars):
            messagebox.showerror("Invalid name", "Please enter a valid file base name.")
            return

        if new_base == base_old:
            return  # nothing to do

        new_audio_name = new_base + ext_old
        new_audio_path = os.path.join(folder, new_audio_name)
        new_txt_path = os.path.join(folder, new_base + ".txt")

        # Overwrite prompt if targets exist
        conflicts = []
        if os.path.exists(new_audio_path):
            conflicts.append(new_audio_name)
        if has_txt and os.path.exists(new_txt_path):
            conflicts.append(os.path.basename(new_txt_path))
        if conflicts:
            names = "\n".join(conflicts)
            if not messagebox.askyesno(
                "Overwrite?",
                f"The following files already exist and will be overwritten:\n\n{names}\n\nProceed?",
                parent=root,
            ):
                return

        try:
            # Rename audio first
            os.replace(old_audio_path, new_audio_path)

            set_status("Renamed successfully.")
        except Exception as e:
            messagebox.showerror("Rename failed", f"Could not rename files.\n\n{e}")

    tree_menu.add_separator()
    tree_menu.add_command(label="Delete Audio Only", command=tree_delete_audio_only)
    tree_menu.add_command(label="Delete Audio + Transcript (keep .md)", command=tree_delete_audio_and_txt_keep_md)
    tree_menu.add_command(label="Delete Selected (audio/txt/md)…", command=tree_delete_selected_with_associated)
    tree_menu.add_command(label="Rename Audio + Transcript…", command=tree_rename_pair)
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
    transcribe_sel_btn.configure(command=on_transcribe_selected)
    auto_fit_btn.configure(command=on_autofit_columns)
    recent_open_btn.configure(command=open_recent_selected)
    notes_save_btn.configure(command=on_save_notes)
    notes_reveal_btn.configure(command=on_reveal_notes)
    tree.bind("<Double-1>", on_tree_double_click)
    tree.bind("<Button-3>", on_tree_right_click)
    tree.bind("<<TreeviewSelect>>", lambda e: (load_preview_for_item(tree.focus()), load_notes_for_item(tree.focus())))
    recent_combo.bind("<<ComboboxSelected>>", lambda e: open_recent_selected())

    # Debounced live preview while typing
    _md_preview_job = None
    def _on_notes_keypress(event=None):
        nonlocal _md_preview_job
        try:
            if _md_preview_job is not None:
                root.after_cancel(_md_preview_job)
        except Exception:
            pass
        def do_update():
            try:
                content = notes_editor.get("1.0", tk.END)
            except Exception:
                content = ""
            render_markdown_to_preview(content)
        _md_preview_job = root.after(300, do_update)
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
    # Load recent folders on startup
    try:
        set_recent_values(load_recent_folders())
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
