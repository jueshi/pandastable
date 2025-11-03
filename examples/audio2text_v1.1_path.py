import whisper
import os
import subprocess
import sys
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import simpledialog
from tkinter import ttk

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
    cols = ("audio", "transcript")
    tree = ttk.Treeview(files_frame, columns=cols, show="headings", height=10)
    tree.heading("audio", text="Audio File")
    tree.heading("transcript", text="Transcript .txt")
    tree.column("audio", width=420, anchor="w")
    tree.column("transcript", width=380, anchor="w")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    paned.add(files_frame, weight=1)

    # Lower: logs
    log_frame = tk.Frame(paned)
    log = tk.Text(log_frame, height=10, wrap="word")
    log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log.yview)
    log.configure(state=tk.DISABLED, yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    paned.add(log_frame, weight=1)
    log.configure(state=tk.DISABLED)

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

    # State for file browser
    current_folder_var = tk.StringVar(value="")
    path_to_item = {}

    def append_log(text: str):
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, text + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    def set_status(text: str):
        status_var.set(text)
        root.update_idletasks()

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
        # Ask for a file each time; model is reused
        audio_path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma"),
                ("All files", "*.*"),
            ],
        )
        if not audio_path:
            return

        current_file_var.set(audio_path)
        output_path_var.set("")
        set_status("Preparing transcription...")
        append_log("")

        # Disable while working
        select_btn.configure(state=tk.DISABLED, text="Transcribing...")

        # Run in background to keep UI responsive
        t = threading.Thread(target=do_transcribe, args=(audio_path,), daemon=True)
        t.start()

    def populate_tree(folder: str):
        # Clear existing
        for iid in tree.get_children():
            tree.delete(iid)
        path_to_item.clear()

        if not folder or not os.path.isdir(folder):
            return

        audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}
        entries = []
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            base, ext = os.path.splitext(name)
            if ext.lower() in audio_exts:
                txt_path = os.path.join(folder, base + ".txt")
                transcript = txt_path if os.path.exists(txt_path) else "(missing)"
                entries.append((name, full, transcript))

        for name, full, transcript in entries:
            iid = tree.insert("", tk.END, values=(name, transcript))
            path_to_item[full] = iid

    def on_browse_folder():
        folder = filedialog.askdirectory(title="Select a folder of audio files")
        if not folder:
            return
        current_folder_var.set(folder)
        append_log(f"Folder selected: {folder}")
        populate_tree(folder)

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
        item = tree.focus()
        if not item:
            messagebox.showwarning("No selection", "Please select an audio file in the list.")
            return
        values = tree.item(item, "values")
        if not values:
            return
        folder = current_folder_var.get()
        if not folder:
            return
        audio_path = os.path.join(folder, values[0])
        current_file_var.set(audio_path)
        output_path_var.set("")
        set_status("Preparing transcription...")
        select_btn.configure(state=tk.DISABLED, text="Transcribing...")
        t = threading.Thread(target=do_transcribe, args=(audio_path,), daemon=True)
        t.start()

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
        audio_name, transcript_val = vals[0], vals[1]
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
            # Rename transcript if present
            if has_txt:
                os.replace(old_txt_path, new_txt_path)

            # Update UI mapping and row
            if old_audio_path in path_to_item:
                iid = path_to_item.pop(old_audio_path)
                path_to_item[new_audio_path] = iid
                tree.item(iid, values=(new_audio_name, new_txt_path if os.path.exists(new_txt_path) else "(missing)"))
                tree.focus(iid)
                tree.selection_set(iid)

            # Update currently selected file/output fields if they match old paths
            if current_file_var.get() == old_audio_path:
                current_file_var.set(new_audio_path)
            if output_path_var.get() == old_txt_path:
                output_path_var.set(new_txt_path)

            set_status("Renamed successfully.")
        except Exception as e:
            messagebox.showerror("Rename failed", f"Could not rename files.\n\n{e}")

    tree_menu.add_separator()
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
    tree.bind("<Double-1>", on_tree_double_click)
    tree.bind("<Button-3>", on_tree_right_click)

    # Ready
    set_status("Model loaded. Ready to transcribe.")
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