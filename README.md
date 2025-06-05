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
- 🔒 **Environment-based config:** Set API keys and options securely.

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your environment

Copy the example environment file and update it with your API credentials:

```bash
cp .example.env .env
# Edit .env to add your AI_API_KEY, AI_API_ENDPOINT, and AI_MODEL
```

### 3. Summarize files

Run sumsnap from the CLI:

```bash
python -m src.main summary path/to/file1.py path/to/file2.pdf
```

#### More options

- Add `--detailed` for longer, more comprehensive summaries.
- Use `--save-to-file` to write the summary as a Markdown file.

Example:

```bash
python -m src.main summary --detailed --save-to-file my_code.py
```

---

## ⚙️ Configuration

Set these variables in your `.env` file:

- `AI_API_KEY` – Your API key for the chosen LLM provider.
- `AI_API_ENDPOINT` – The API endpoint using Openai's format.
- `AI_MODEL` – The model to use.
