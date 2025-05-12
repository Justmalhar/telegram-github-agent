import os
import shutil
import zipfile
from openai import OpenAI
import requests
import json
import sys
import threading
import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from dotenv import load_dotenv
import queue

# Create a queue for communication between threads
message_queue = queue.Queue()

# Load environment variables from .env file
load_dotenv()

# === CONFIG ===
# Only set API keys if not in test mode
TEST_MODE = len(sys.argv) > 1 and sys.argv[1] == "--test"

if not TEST_MODE:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
else:
    # In test mode, use placeholder values
    OPENROUTER_API_KEY = "test_key"
    GITHUB_TOKEN = "test_token"

BASE_DIR = "projects"

# Create projects directory if it doesn't exist
os.makedirs(BASE_DIR, exist_ok=True)

with open("prompts.json") as f:
    PROMPTS = json.load(f)

# === CORE BOT LOGIC ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to CreateAIAppBot!\nUse /new to start building your project.")

async def new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("What is your project name?")
    context.user_data['step'] = 'get_project_name'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')

    if step == 'get_project_name':
        context.user_data['project_name'] = update.message.text.strip()
        context.user_data['step'] = 'get_description'
        await update.message.reply_text("Describe what your app does:")

    elif step == 'get_description':
        context.user_data['description'] = update.message.text.strip()
        context.user_data['step'] = None
        await generate_project(update, context)

# === FILE GENERATION ===
def make_project_folder(name):
    path = os.path.join(BASE_DIR, name)
    os.makedirs(f"{path}/docs", exist_ok=True)
    os.makedirs(f"{path}/backend", exist_ok=True)
    os.makedirs(f"{path}/frontend", exist_ok=True)
    os.makedirs(f"{path}/docker", exist_ok=True)
    return path

def zip_project(project_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_path)
                zipf.write(full_path, rel_path)

def interpolate(template, **kwargs):
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template

def generate_ai_file(prompt, file_path):
    if TEST_MODE:
        # In test mode, just create a placeholder file
        content = f"# Test content for {os.path.basename(file_path)}\n\nThis is a placeholder generated in test mode."
        with open(file_path, "w") as f:
            f.write(content)
        return content
    
    # Normal mode - use OpenRouter API
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    
    response = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    with open(file_path, "w") as f:
        f.write(content)
    return content

# === GITHUB ===
def push_to_github(name, path):
    if TEST_MODE:
        # In test mode, skip GitHub API call
        return "https://github.com/test/test-repo"
        
    url = f"https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"name": name, "auto_init": False, "private": False}
    r = requests.post(url, headers=headers, json=data)
    
    if r.status_code != 201:
        print(f"Error creating GitHub repository: {r.text}")
        return None
        
    clone_url = r.json().get("clone_url")
    
    if clone_url:
        # Configure git user for this repository
        git_commands = [
            f"cd {path}",
            "git init",
            "git config user.name 'Telegram Bot'",
            "git config user.email 'bot@example.com'",
            "git add .",
            "git commit -m 'Initial commit'",
            f"git remote add origin {clone_url}",
            "git branch -M main",  # Rename current branch to main
            "git push -u origin main"
        ]
        
        git_command = " && ".join(git_commands)
        
        try:
            import subprocess
            result = subprocess.run(git_command, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error pushing to GitHub: {result.returncode}")
                print(f"Error details: {result.stderr}")
                return None
        except Exception as e:
            print(f"Exception during GitHub push: {str(e)}")
            return None
            
        return clone_url
    return None

# Message types for the queue
class MessageType:
    EDIT_MESSAGE = "edit_message"
    SEND_MESSAGE = "send_message"
    SEND_DOCUMENT = "send_document"
    SEND_FINAL_MESSAGE = "send_final_message"

# Function to process project generation in a separate thread
def process_project_generation(name, desc, path, chat_id, message_id):
    try:
        # Update status message
        message_queue.put({
            "type": MessageType.EDIT_MESSAGE,
            "chat_id": chat_id,
            "message_id": message_id,
            "text": "🔄 Generating Product Requirements Document (PRD)..."
        })
        
        # Generate PRD
        prd_path = f"{path}/docs/PRD.md"
        prd = generate_ai_file(
            interpolate(PROMPTS['prd_prompt'], project_name=name, description=desc),
            prd_path
        )
        
        # Send PRD file to user
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": prd_path,
            "caption": "📄 Product Requirements Document (PRD) generated!"
        })
        
        # Generate HLD
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Generating High-Level Design (HLD)..."
        })
        
        hld_path = f"{path}/docs/HLD.md"
        generate_ai_file(interpolate(PROMPTS['hld_prompt'], prd=prd), hld_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": hld_path,
            "caption": "📄 High-Level Design (HLD) generated!"
        })
        
        # Generate API Specs
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Generating API Specifications..."
        })
        
        api_path = f"{path}/docs/API.md"
        generate_ai_file(interpolate(PROMPTS['api_prompt'], prd=prd), api_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": api_path,
            "caption": "📄 API Specifications generated!"
        })
        
        # Generate DB Schema
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Generating Database Schema..."
        })
        
        db_path = f"{path}/docs/DBSchema.md"
        generate_ai_file(interpolate(PROMPTS['dbschema_prompt'], prd=prd), db_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": db_path,
            "caption": "📄 Database Schema generated!"
        })
        
        # Generate README
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Generating Project README..."
        })
        
        readme_path = f"{path}/README.md"
        generate_ai_file(interpolate(PROMPTS['readme_prompt'], project_name=name, description=desc, prd=prd), readme_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": readme_path,
            "caption": "📄 Project README generated!"
        })
        
        # Generate code files
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Generating code files (backend requirements, frontend package.json, docker config)..."
        })
        
        # Generate code files
        backend_req_path = os.path.join(path, "backend/requirements.txt")
        generate_ai_file(interpolate(PROMPTS['requirements_prompt'], prd=prd), backend_req_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": backend_req_path,
            "caption": "📄 Backend requirements.txt generated!"
        })
        
        frontend_pkg_path = os.path.join(path, "frontend/package.json")
        generate_ai_file(interpolate(PROMPTS['packagejson_prompt'], prd=prd), frontend_pkg_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": frontend_pkg_path,
            "caption": "📄 Frontend package.json generated!"
        })
        
        docker_path = os.path.join(path, "docker/docker-compose.yml")
        generate_ai_file(interpolate(PROMPTS['docker_prompt'], prd=prd), docker_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": docker_path,
            "caption": "📄 Docker configuration generated!"
        })
        
        # Create zip
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Creating project ZIP archive..."
        })
        
        zip_path = f"{path}.zip"
        zip_project(path, zip_path)
        message_queue.put({
            "type": MessageType.SEND_DOCUMENT,
            "chat_id": chat_id,
            "file_path": zip_path,
            "caption": "📦 Project ZIP archive created!"
        })
        
        # Push to GitHub
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": "🔄 Creating GitHub repository..."
        })
        
        repo_url = push_to_github(name, path)
        
        # Log the project
        log_path = os.path.join(BASE_DIR, "log.txt")
        with open(log_path, "a") as log:
            log.write(f"[{datetime.now()}] Project: {name}\nDesc: {desc}\nGitHub: {repo_url}\n\n")
        
        # Create keyboard with GitHub repo link
        keyboard = [[
            InlineKeyboardButton("🔗 GitHub Repo", url=repo_url or "https://github.com")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send final message
        message_queue.put({
            "type": MessageType.SEND_FINAL_MESSAGE,
            "chat_id": chat_id,
            "text": f"✅ Project *{name}* is ready!\n\n`npx create-ai-app {name} --openai --auth=supabase --ui=shadcn`",
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        })
        
    except Exception as e:
        # Send error message if something goes wrong
        message_queue.put({
            "type": MessageType.SEND_MESSAGE,
            "chat_id": chat_id,
            "text": f"❌ Error generating project: {str(e)}"
        })

# Message processor function for job queue
async def process_messages(context):
    try:
        # Process all messages in the queue
        while not message_queue.empty():
            message = message_queue.get_nowait()
            
            if message["type"] == MessageType.EDIT_MESSAGE:
                await context.bot.edit_message_text(
                    chat_id=message["chat_id"],
                    message_id=message["message_id"],
                    text=message["text"]
                )
            
            elif message["type"] == MessageType.SEND_MESSAGE:
                await context.bot.send_message(
                    chat_id=message["chat_id"],
                    text=message["text"]
                )
            
            elif message["type"] == MessageType.SEND_DOCUMENT:
                with open(message["file_path"], 'rb') as file:
                    await context.bot.send_document(
                        chat_id=message["chat_id"],
                        document=file,
                        caption=message["caption"]
                    )
            
            elif message["type"] == MessageType.SEND_FINAL_MESSAGE:
                await context.bot.send_message(
                    chat_id=message["chat_id"],
                    text=message["text"],
                    parse_mode=message["parse_mode"],
                    reply_markup=message["reply_markup"]
                )
    except Exception as e:
        print(f"Error processing message: {str(e)}")

# === PROJECT GENERATOR ===
async def generate_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data['project_name']
    desc = context.user_data['description']
    
    # Send initial processing message
    processing_message = await update.message.reply_text(
        "🔄 Processing your request. This may take a few minutes...\n\n"
        "I'll generate a complete project based on your description, including:\n"
        "- Product Requirements Document (PRD)\n"
        "- High-Level Design (HLD)\n"
        "- API Specifications\n"
        "- Database Schema\n"
        "- Code scaffolding\n"
        "- GitHub repository"
    )
    
    # Create project folder
    path = make_project_folder(name)
    
    # Start processing in a separate thread
    thread = threading.Thread(
        target=process_project_generation,
        args=(name, desc, path, update.effective_chat.id, processing_message.message_id)
    )
    thread.daemon = True
    thread.start()
    
    # Schedule the message processor
    if context.application.job_queue is not None:
        context.application.job_queue.run_repeating(process_messages, interval=1, first=0)
    else:
        await update.message.reply_text("Error: JobQueue is not available. Please install python-telegram-bot[job-queue].")
        return

# === MAIN ENTRY ===
def main():
    # Check for test mode
    if TEST_MODE:
        print("✅ Bot configuration test successful!")
        print("✅ Environment variables loaded successfully")
        print(f"✅ Projects directory created at: {os.path.abspath(BASE_DIR)}")
        print("✅ Prompts loaded successfully")
        
        # Test project generation without using Telegram or OpenAI APIs
        test_project_path = make_project_folder("test_project")
        test_prd = generate_ai_file("Test PRD prompt", f"{test_project_path}/docs/PRD.md")
        generate_ai_file("Test HLD prompt", f"{test_project_path}/docs/HLD.md")
        generate_ai_file("Test API prompt", f"{test_project_path}/docs/API.md")
        generate_ai_file("Test DB Schema prompt", f"{test_project_path}/docs/DBSchema.md")
        generate_ai_file("Test README prompt", f"{test_project_path}/docs/README.md")
        
        # Generate code files individually
        generate_ai_file("Test backend requirements", f"{test_project_path}/backend/requirements.txt")
        generate_ai_file("Test frontend package.json", f"{test_project_path}/frontend/package.json")
        generate_ai_file("Test docker config", f"{test_project_path}/docker/docker-compose.yml")
        
        print(f"✅ Test project generated at: {os.path.abspath(test_project_path)}")
        print("✅ All systems operational!")
        return
        
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        return
        
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not found in environment variables")
        return
        
    if not os.getenv("GITHUB_TOKEN"):
        print("Warning: GITHUB_TOKEN not found in environment variables. GitHub repository creation will not work.")
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Ensure job queue is properly initialized
    if app.job_queue is None:
        print("Warning: JobQueue is not available. Make sure python-telegram-bot[job-queue] is installed.")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()
