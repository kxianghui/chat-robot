# Dify Chat Desktop Application
import tkinter as tk
from tkinter import messagebox

from config import Config
from api import DifyClient
from gui import ChatWindow


def main():
    """Main entry point for Dify Chat application."""
    # Load configuration
    config = Config()
    config.load()

    # Check if configuration is complete
    if not config.is_configured():
        # Need to get configuration from user
        root = tk.Tk()
        root.withdraw()  # Hide main window initially

        from gui.chat_window import SettingsDialog

        dialog = SettingsDialog(root, config.api_key or "", config.base_url or "", config.user_id or "", config.endpoint_path or "")
        result = dialog.show()

        if result:
            config.save(result["api_key"], result["base_url"], result["user_id"], result.get("endpoint_path"))
        else:
            # User cancelled, exit
            messagebox.showinfo("Configuration Required", "API configuration is required to use this application.")
            return

        root.destroy()

    # Create main window
    root = tk.Tk()

    # Initialize Dify client with configuration
    dify_client = DifyClient(
        api_key=config.api_key,
        base_url=config.base_url,
        user_id=config.user_id or "desktop-client-user",
        endpoint_path=config.endpoint_path or "chat-messages"
    )

    # Create and show chat window
    app = ChatWindow(root, dify_client)

    # Display welcome message
    app.append_message(
        "System:",
        "Welcome to Dify Chat! Click ⚙ Config to set up your API key if not configured.",
        "system_tag"
    )

    # Start the main loop
    root.mainloop()


if __name__ == '__main__':
    main()