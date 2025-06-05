# 📝 sumsnap

**sumsnap** is a powerful yet simple command-line tool that uses AI to generate concise or detailed summaries of files—including code, text documents, images, and PDFs.

> **Summarize anything, beautifully.**

---

## ✨ Features

- 📄 **Multi-format input:** Summarize code, text, images, and PDFs.
- 🧠 **AI-powered summaries:** Uses your preferred LLM (e.g., OpenAI) via API.
- 🎨 **Beautiful CLI output:** Leverages [Rich](https://github.com/Textualize/rich) for styled summaries.
- 💾 **Save summaries:** Optionally write summaries to Markdown files.
- ⚡ **Progress indication:** See a spinner while your summaries are generated.
- 🔒 **Secure config:** Set API keys and options securely via CLI config commands.

---

## 🚀 Quick Start

### 1. Install sumsnap

#### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/frinshhd/sumsnap/main/install/install-macos.sh | bash
```

#### Linux

```bash
curl -fsSL https://raw.githubusercontent.com/frinshhd/sumsnap/main/install/install-linux.sh | bash
```

#### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/frinshhd/sumsnap/main/install/install-windows.ps1 | iex
```

---

### 2. Configure your API credentials

Run the interactive setup command and follow the prompts:

```bash
sumsnap setup
```

You can also set or update individual values at any time:

```bash
sumsnap set-api-endpoint https://your-endpoint
sumsnap set-api-key your_api_key
sumsnap set-ai-model your_model_name
```

---

### 3. Summarize files

Run sumsnap from the CLI:

```bash
sumsnap summary path/to/file1.py path/to/file2.pdf
```

#### More options

- Add `--detailed` for longer, more comprehensive summaries.
- Use `--save-to-file` to write the summary as a Markdown file.

Example:

```bash
sumsnap summary --detailed --save-to-file my_code.py
```

---

## ⚙️ Configuration

Set these values using the CLI commands:

- `set-api-key` – Your API key for the chosen LLM provider.
- `set-api-endpoint` – The API endpoint using OpenAI's format.
- `set-ai-model` – The model to use.

Or use the interactive `setup` command to set all at once.

Your configuration is stored in a user-specific config file (e.g., on Windows: `C:\Users\<YourUsername>\AppData\Roaming\sumsnap\config.ini`).

---

**Note:**  
Replace `<your-username>` with your actual GitHub username in the above commands and scripts.
