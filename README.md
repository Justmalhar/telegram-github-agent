# Telegram GitHub Bot

<div align="center">

![Telegram GitHub Bot Logo](https://img.shields.io/badge/Telegram-GitHub-blue?style=for-the-badge&logo=telegram)

A Telegram bot that generates AI-powered project scaffolding and pushes it to GitHub.

[![Twitter: justmalhar](https://img.shields.io/twitter/follow/justmalhar?style=social)](https://twitter.com/justmalhar)
[![LinkedIn: justmalhar](https://img.shields.io/badge/-justmalhar-blue?style=flat-square&logo=Linkedin&logoColor=white&link=https://www.linkedin.com/in/justmalhar/)](https://www.linkedin.com/in/justmalhar/)
[![GitHub: Justmalhar](https://img.shields.io/github/followers/Justmalhar?label=follow&style=social)](https://github.com/Justmalhar)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/Justmalhar/telegram-github-agent)

</div>

## 🌟 Features

- Create new projects with a simple conversation flow
- Generate comprehensive documentation (PRD, HLD, API specs, DB schema)
- Generate code scaffolding for frontend and backend
- Automatically create GitHub repository with the generated files
- Package the project as a ZIP file
- Uses OpenRouter API for AI model access

## 🔄 How It Works

```mermaid
flowchart TD
    A[User] -->|/new command| B[Bot]
    B -->|Ask for project name| A
    A -->|Provide project name| B
    B -->|Ask for description| A
    A -->|Provide description| B
    B -->|Generate project| C[Project Generation]
    
    subgraph C[Project Generation Process]
        D[Create project folder] --> E[Generate PRD]
        E --> F[Generate HLD]
        F --> G[Generate API Specs]
        G --> H[Generate DB Schema]
        H --> I[Generate README]
        I --> J[Generate Code Files]
        J --> K[Create ZIP Archive]
        K --> L[Push to GitHub]
    end
    
    C -->|Send files & GitHub link| A
```

## 📂 Project Structure

```mermaid
flowchart TD
    A[telegram-github-bot] --> B[bot.py]
    A --> C[prompts.json]
    A --> D[requirements.txt]
    A --> E[.env]
    A --> F[projects/]
    
    F --> G[project_name/]
    
    subgraph G[Generated Project Structure]
        H[docs/] --> H1[PRD.md]
        H --> H2[HLD.md]
        H --> H3[API.md]
        H --> H4[DBSchema.md]
        
        I[backend/] --> I1[requirements.txt]
        
        J[frontend/] --> J1[package.json]
        
        K[docker/] --> K1[docker-compose.yml]
        
        L[README.md]
    end
```

## 🏗️ Architecture

```mermaid
graph TD
    A[Telegram Bot] <-->|Commands & Messages| B[User]
    A <--> C[Bot Logic]
    
    C --> D[Project Generator]
    D --> E[File Generator]
    
    E <-->|API Requests| F[OpenRouter API]
    F -->|GPT-4o| G[AI Model]
    
    D --> H[GitHub Integration]
    H -->|Create Repository| I[GitHub API]
    
    subgraph "Generated Files"
        J[Documentation]
        K[Code Scaffolding]
        L[Configuration Files]
    end
    
    E --> J
    E --> K
    E --> L
    
    J --> M[ZIP Archive]
    K --> M
    L --> M
```

## 🛠️ Requirements

- Python 3.8+
- Telegram Bot Token
- OpenRouter API Key
- GitHub Personal Access Token

## 📋 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Justmalhar/telegram-github-bot.git
   cd telegram-github-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   
   Copy the example environment file and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   
   Then edit the `.env` file with your actual API keys:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENROUTER_API_KEY=your_openrouter_api_key
   GITHUB_TOKEN=your_github_personal_access_token
   ```

## 🚀 Usage

1. Test the configuration:
   ```bash
   python bot.py --test
   ```

2. Start the bot:
   ```bash
   python bot.py
   ```

3. In Telegram, start a conversation with your bot
4. Use the `/new` command to create a new project
5. Follow the prompts to specify project name and description
6. The bot will generate all necessary files and create a GitHub repository

## 🐳 Docker

Build the image and run the bot in a container:

```bash
docker build -t telegram-github-bot .
docker run --env-file .env telegram-github-bot
```

## 🚄 One-Click Deploy on Railway

You can deploy this bot directly to Railway. Click the button at the top of this
README or use the link below:

<https://railway.app/new/template?template=https://github.com/Justmalhar/telegram-github-agent>

After the project is created, add the environment variables from `.env.example`
to the Railway dashboard and deploy.

## 📁 Project Structure

- `bot.py`: Main bot code
- `prompts.json`: Templates for AI generation prompts
- `requirements.txt`: Python dependencies
- `projects/`: Directory where generated projects are stored

## 🔧 Customization

You can customize the AI prompts by editing the `prompts.json` file. The following templates are available:

| Template | Description |
|----------|-------------|
| `prd_prompt` | Product Requirements Document |
| `hld_prompt` | High-Level Design |
| `api_prompt` | API Specification |
| `dbschema_prompt` | Database Schema |
| `readme_prompt` | Project README |
| `requirements_prompt` | Backend requirements.txt |
| `packagejson_prompt` | Frontend package.json |
| `docker_prompt` | Docker configuration |

## 🤖 OpenRouter Configuration

This bot uses OpenRouter to access various AI models. OpenRouter provides:

- Access to multiple AI models through a single API
- Competitive pricing
- Fallback options if a model is unavailable

You can get an API key from [OpenRouter](https://openrouter.ai/).

## 🔄 Bot Workflow

```mermaid
sequenceDiagram
    participant User
    participant Bot
    participant Thread
    participant OpenRouter
    participant GitHub
    
    User->>Bot: /new command
    Bot->>User: Ask for project name
    User->>Bot: Provide project name
    Bot->>User: Ask for description
    User->>Bot: Provide description
    
    Bot->>Thread: Start project generation
    
    Thread->>OpenRouter: Generate PRD
    OpenRouter->>Thread: PRD content
    Thread->>Bot: Send PRD to user
    Bot->>User: PRD document
    
    Thread->>OpenRouter: Generate HLD
    OpenRouter->>Thread: HLD content
    Thread->>Bot: Send HLD to user
    Bot->>User: HLD document
    
    Thread->>OpenRouter: Generate API Specs
    OpenRouter->>Thread: API content
    Thread->>Bot: Send API to user
    Bot->>User: API document
    
    Thread->>OpenRouter: Generate DB Schema
    OpenRouter->>Thread: DB Schema content
    Thread->>Bot: Send DB Schema to user
    Bot->>User: DB Schema document
    
    Thread->>OpenRouter: Generate README
    OpenRouter->>Thread: README content
    Thread->>Bot: Send README to user
    Bot->>User: README document
    
    Thread->>OpenRouter: Generate code files
    OpenRouter->>Thread: Code file contents
    Thread->>Bot: Send code files to user
    Bot->>User: Code files
    
    Thread->>Thread: Create ZIP archive
    Thread->>Bot: Send ZIP to user
    Bot->>User: ZIP archive
    
    Thread->>GitHub: Create repository
    GitHub->>Thread: Repository URL
    Thread->>Bot: Send GitHub link
    Bot->>User: GitHub repository link
```

## 📄 License

MIT

---

## Connect With Me 

<div align="center">
  <p>Created by <a href="https://twitter.com/justmalhar">@justmalhar</a> | <a href="https://www.linkedin.com/in/justmalhar/">LinkedIn</a></p>
</div>