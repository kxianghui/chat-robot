# Tkinter GUI for Dify Chat application
import httpx
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk
import threading
from typing import Optional


class SettingsDialog:
    """Settings dialog for API configuration."""

    def __init__(self, parent, api_key: str = "", base_url: str = "", user_id: str = "desktop-client-user", endpoint_path: str = ""):
        self.parent = parent
        self.api_key = api_key
        self.base_url = base_url
        self.user_id = user_id
        self.endpoint_path = endpoint_path
        self.result = None

    def show(self) -> Optional[dict]:
        """Show settings dialog.

        Returns:
            Dictionary with api_key, base_url, user_id if saved, None otherwise.
        """
        dialog = tk.Toplevel(self.parent)
        dialog.title("Dify API Configuration")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()

        # Center dialog relative to parent
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 250
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")

        # Create form
        padding = {"padx": 20, "pady": 10}

        tk.Label(dialog, text="API Key:").grid(row=0, column=0, sticky="w", **padding)
        api_key_entry = tk.Entry(dialog, show="*", width=40)
        api_key_entry.insert(0, self.api_key)
        api_key_entry.grid(row=0, column=1, **padding)

        tk.Label(dialog, text="Base URL:").grid(row=1, column=0, sticky="w", **padding)
        base_url_entry = tk.Entry(dialog, width=40)
        base_url_entry.insert(0, self.base_url or "https://api.dify.ai/v1")
        base_url_entry.grid(row=1, column=1, **padding)

        tk.Label(dialog, text="User ID (optional):").grid(row=2, column=0, sticky="w", **padding)
        user_id_entry = tk.Entry(dialog, width=40)
        user_id_entry.insert(0, self.user_id)
        user_id_entry.grid(row=2, column=1, **padding)

        tk.Label(dialog, text="Endpoint Path (optional):").grid(row=3, column=0, sticky="w", **padding)
        endpoint_path_entry = tk.Entry(dialog, width=40)
        endpoint_path_entry.insert(0, self.endpoint_path or "chat-messages")
        endpoint_path_entry.grid(row=3, column=1, **padding)

        # Add help text
        help_text = "Default: chat-messages. Change if your Dify uses custom endpoint."
        tk.Label(dialog, text=help_text, font=("Arial", 8), fg="gray").grid(row=4, column=0, columnspan=2, pady=(0, 10))

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        def on_save():
            api_key = api_key_entry.get().strip()
            base_url = base_url_entry.get().strip()
            user_id = user_id_entry.get().strip() or "desktop-client-user"
            endpoint_path = endpoint_path_entry.get().strip() or "chat-messages"

            # Validation
            if not api_key:
                messagebox.showerror("Validation Error", "API Key is required")
                return
            if not base_url:
                messagebox.showerror("Validation Error", "Base URL is required")
                return
            if not base_url.startswith(("http://", "https://")):
                messagebox.showerror("Validation Error", "Base URL must start with http:// or https://")
                return

            self.result = {"api_key": api_key, "base_url": base_url, "user_id": user_id, "endpoint_path": endpoint_path}
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        tk.Button(button_frame, text="Save", command=on_save, width=12).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=on_cancel, width=12).pack(side="left", padx=10)

        # Wait for dialog to close
        self.parent.wait_window(dialog)
        return self.result


class ChatWindow:
    """Main chat window using Tkinter."""

    def __init__(self, root, dify_client):
        """Initialize chat window.

        Args:
            root: Tkinter root window
            dify_client: DifyClient instance
        """
        self.root = root
        self.dify_client = dify_client
        self.current_conversation_id = ""
        self.streaming = False

        self.root.title("Dify Chat")
        self.root.geometry("600x500")

        # Build UI
        self._build_ui()

        # Bind Enter key to send
        self.input_entry.bind("<Return>", lambda e: self.on_send())

    def _build_ui(self):
        """Build the main UI components."""
        # Top toolbar with settings button
        toolbar = tk.Frame(self.root, height=30)
        toolbar.pack(fill="x", padx=10, pady=5)

        tk.Label(toolbar, text="Dify Chat", font=("Arial", 14, "bold")).pack(side="left")
        tk.Button(toolbar, text="⚙ Config", command=self.open_settings).pack(side="right")

        # Chat display area with scrollbar
        chat_frame = tk.Frame(self.root)
        chat_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(chat_frame)
        scrollbar.pack(side="right", fill="y")

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Arial", 11),
            state="disabled",
        )
        self.chat_display.pack(fill="both", expand=True)

        scrollbar.config(command=self.chat_display.yview)

        # Configure text tags
        self.chat_display.tag_config("user_tag", foreground="blue", justify="right", font=("Arial", 11, "bold"))
        self.chat_display.tag_config("ai_tag", foreground="gray", justify="left")
        self.chat_display.tag_config("system_tag", foreground="darkgreen", justify="center", font=("Arial", 9, "italic"))

        # Input area
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", padx=10, pady=10)

        self.input_entry = tk.Entry(input_frame, font=("Arial", 11))
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.send_button = tk.Button(input_frame, text="Send", command=self.on_send, width=12)
        self.send_button.pack(side="right")

    def append_message(self, sender: str, text: str, tag: str = None):
        """Add a message to the chat display.

        Args:
            sender: Message sender label (e.g., "You:", "Dify:")
            text: Message text
            tag: Optional tag for styling
        """
        self.chat_display.config(state="normal")

        # Add message with sender label
        self.chat_display.insert("end", f"{sender} ", tag)
        self.chat_display.insert("end", text + "\n\n")

        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def append_streaming_chunk(self, text: str):
        """Append streaming text chunk to current AI message.

        Args:
            text: Text chunk to append
        """
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", text, "ai_tag")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def start_streaming(self):
        """Start a new AI streaming message."""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", "Dify: ", "ai_tag")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def end_streaming(self):
        """End the current AI streaming message."""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", "\n\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def on_send(self):
        """Handle send button click."""
        if self.streaming:
            return

        message = self.input_entry.get().strip()

        if not message:
            return

        # Clear input
        self.input_entry.delete(0, "end")

        # Display user message
        self.append_message("You:", message, "user_tag")

        # Disable input during streaming
        self.streaming = True
        self.input_entry.config(state="disabled")
        self.send_button.config(state="disabled")

        # Start streaming response in background thread
        thread = threading.Thread(target=self._stream_response, args=(message,), daemon=True)
        thread.start()

    def _stream_response(self, message: str):
        """Stream response from Dify API in background thread.

        Args:
            message: User message
        """
        try:
            self.root.after(0, self.start_streaming)

            for chunk in self.dify_client.stream_chat(message, self.current_conversation_id):
                # UI update must happen in main thread
                self.root.after(0, lambda c=chunk: self.append_streaming_chunk(c))

            self.root.after(0, self.end_streaming)

        except httpx.HTTPError as e:
            error_msg = f"Network error: {e}"
            self.root.after(0, lambda: self.append_message("System:", error_msg, "system_tag"))
        except Exception as e:
            error_msg = f"Error: {e}"
            self.root.after(0, lambda: self.append_message("System:", error_msg, "system_tag"))
        finally:
            # Re-enable input
            self.root.after(0, self._enable_input)
            self.streaming = False

    def _enable_input(self):
        """Re-enable input controls."""
        self.input_entry.config(state="normal")
        self.send_button.config(state="normal")
        self.input_entry.focus_set()

    def open_settings(self):
        """Open settings dialog to configure API."""
        # Get current config
        api_key = self.dify_client.api_key
        base_url = self.dify_client.base_url
        user_id = self.dify_client.user_id
        endpoint_path = getattr(self.dify_client, "endpoint_path", "chat-messages")

        # Show dialog
        dialog = SettingsDialog(self.root, api_key, base_url, user_id, endpoint_path)
        result = dialog.show()

        if result:
            # Update client
            self.dify_client.api_key = result["api_key"]
            self.dify_client.base_url = result["base_url"]
            self.dify_client.user_id = result["user_id"]
            self.dify_client.endpoint_path = result["endpoint_path"]

            # Save to config
            from config import Config

            config = Config()
            config.load()
            config.save(result["api_key"], result["base_url"], result["user_id"], result["endpoint_path"])

            messagebox.showinfo("Success", "Configuration saved successfully!")
            self.append_message("System:", "Configuration updated", "system_tag")