# VRPhoto Checker

VRPhoto Checker is a standalone Python application that monitors your VRChat photo directory and uses a local AI (Ollama) to audit screenshots for NSFW content, copyright infringement, and hate symbols.

Unlike cloud-based solutions, this tool runs entirely locally, ensuring your privacy.

## Features

- **Automated Monitoring**: Watches your VRChat photo folder for new screenshots.
- **Local AI Analysis**: Uses Ollama with vision-capable models (e.g., Gemma 2, LLaVA, MiniCPM-V) to analyze images.
- **Policy Enforcement**: Checks against defined rules for:
  - **NSFW**: Nudity, sexual acts.
  - **Copyright**: Unauthorized characters (e.g., Pokémon, Disney).
  - **Hate Symbols**: Prohibited iconography.
- **Web Dashboard**: View audit logs and images via a local web interface.
- **Desktop Notifications**: Receive Windows alerts for policy violations.
- **Privacy**: No images are uploaded to the cloud.

## Requirements

- **OS**: Windows 10 or 11
- **Python**: 3.10 or newer
- **Ollama**: Must be installed and running. [Download Ollama](https://ollama.com/)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/akiRAM2/vrphoto-checker.git
    cd vrphoto-checker
    ```

2.  **Install & Setup Ollama**:
    -   Download and install Ollama from the official website.
    -   Pull a vision-capable model. Recommended models:
        ```bash
        ollama pull gemma2:9b      # Good balance (requires ~6GB VRAM)
        # OR
        ollama pull llava:13b      # Standard vision model
        # OR
        ollama pull minicpm-v      # High performance small model
        ```
    -   Update `config.json` with your chosen model name (e.g., `"ai_model": "gemma2:9b"`).

3.  **Run the Application**:
    ```bash
    python main.py
    ```
    -   The application will start monitoring your default VRChat photo directory (`Pictures/VRChat`).
    -   A web dashboard will automatically open at `http://localhost:8080`.

## Configuration

Edit `config.json` to customize behavior:

```json
{
    "watch_path": "C:\\Users\\YourName\\Pictures\\VRChat",
    "ai_api_url": "http://localhost:11434/api/generate",
    "ai_model": "gemma2:9b",
    "ai_timeout": 60,
    "poll_interval": 5,
    "port": 8080
}
```

## Third-Party Libraries

This project uses the following open-source libraries via Python Standard Library or external tools:

-   **Ollama**: Local LLM runner.
-   **Python Standard Library**: `urllib`, `json`, `sqlite3`, `http.server`, `threading`, `subprocess`.

No external PIP packages are required for the core functionality.

## Disclaimer

This tool provides automated analysis based on AI models, which may produce errors or hallucinations. It should be used as an assistant, not a definitive legal judgment.
