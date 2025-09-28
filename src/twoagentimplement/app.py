# app.py
import streamlit as st
from researcher.crew import RESEARCHER
import warnings
from datetime import datetime
import os
import time
import re
import openai
from dotenv import load_dotenv
import shutil

# --- Page Setup & Constants ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="Conversational FEM Coder", page_icon="🧑‍💻", layout="wide")

# --- Environment Setup ---
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY not found in .env file. Please add it to run the application.")
    st.stop()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("🧑‍💻 FEniCS Assistant")
st.markdown("Enter your initial Finite Element Method (FEM) problem, then you can conversationally refine and approve the generated code.")

# --- Helper Functions ---

def get_new_output_path(chat_id: str) -> tuple[str, str]:
    safe_chat_id = chat_id.replace(":", "-").replace(" ", "_")
    timestamp = str(int(time.time()))
    host_path = os.path.join("output", safe_chat_id, timestamp)
    os.makedirs(host_path, exist_ok=True)
    docker_path = f"/workspace/output/{safe_chat_id}/{timestamp}"
    return host_path, docker_path

def get_chat_title(chat_id: str) -> str:
    return st.session_state.chats[chat_id].get("title", chat_id.replace("chat_", ""))

def format_chat_for_export(chat_data: dict) -> str:
    export_string = f"# Chat History: {chat_data.get('title', 'Untitled')}\n\n"
    for message in chat_data["messages"]:
        role = "👤 User" if message['role'] == 'user' else "🤖 Assistant"
        export_string += f"### {role}\n"
        content_str = str(message.get('content', ''))
        export_string += content_str.replace("### ✅ Final Code:", "#### ✅ Final Code:").replace("```", "\n```\n")
        export_string += "\n\n---\n\n"
    return export_string

def extract_python_code(markdown_text: str) -> str:
    match = re.search(r"```python\s*([\s\S]*?)\s*```", markdown_text)
    return match.group(1).strip() if match else ""

# --- Session State Initialization ---
if "chats" not in st.session_state:
    st.session_state.chats = {}
if "active_chat_id" not in st.session_state:
    first_chat_id = f"chat_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    st.session_state.chats[first_chat_id] = {
        "title": f"Chat from {datetime.now().strftime('%H:%M')}",
        "messages": [],
        "last_code": ""
    }
    st.session_state.active_chat_id = first_chat_id

# --- Sidebar for Chat Management ---
with st.sidebar:
    st.header("🗂️ Conversations")
    if st.button("➕ New Chat"):
        new_chat_id = f"chat_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        st.session_state.chats[new_chat_id] = {
            "title": f"Chat from {datetime.now().strftime('%H:%M')}",
            "messages": [], "last_code": ""
        }
        st.session_state.active_chat_id = new_chat_id
        st.rerun()

    st.write("---")
    chat_ids = sorted(st.session_state.chats.keys(), reverse=True)
    for chat_id in chat_ids:
        title = get_chat_title(chat_id)
        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
        with col1:
            if st.button(title, key=f"switch_{chat_id}", use_container_width=True, type="primary" if st.session_state.active_chat_id == chat_id else "secondary"):
                st.session_state.active_chat_id = chat_id
                st.rerun()
        with col2:
            if st.button("✏️", key=f"rename_{chat_id}", help="Rename Chat"):
                 st.session_state.renaming_chat_id = chat_id
                 st.rerun()
        with col3:
            if st.button("🗑️", key=f"delete_{chat_id}", help="Delete Chat"):
                if chat_id in st.session_state.chats:
                    del st.session_state.chats[chat_id]
                    if st.session_state.active_chat_id == chat_id:
                        remaining_chats = sorted(st.session_state.chats.keys(), reverse=True)
                        st.session_state.active_chat_id = remaining_chats[0] if remaining_chats else None
                    st.rerun()
        
        if st.session_state.get("renaming_chat_id") == chat_id:
            new_title = st.text_input("New name:", value=title, key=f"text_rename_{chat_id}")
            if st.button("Save", key=f"save_rename_{chat_id}"):
                st.session_state.chats[chat_id]["title"] = new_title
                del st.session_state.renaming_chat_id
                st.rerun()

# --- Main Chat Interface ---
active_chat_id = st.session_state.active_chat_id
if not active_chat_id or active_chat_id not in st.session_state.chats:
    st.info("👋 Welcome! Start a new chat from the sidebar.")
    st.stop()
    
active_chat = st.session_state.chats[active_chat_id]

col_title, col_export = st.columns([0.8, 0.2])
with col_title:
    st.markdown(f"### 💬 {get_chat_title(active_chat_id)}")
with col_export:
    export_data = format_chat_for_export(active_chat)
    st.download_button(
        label="📥 Export Chat",
        data=export_data,
        file_name=f"{get_chat_title(active_chat_id).replace(' ', '_')}.md",
        mime='text/markdown',
    )

for message in active_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "thinking_log" in message and message["thinking_log"]:
             with st.expander("🔬 View Agents' Thinking Process", expanded=False):
                    st.code(message["thinking_log"], language='json')
        if message["role"] == "assistant" and "files" in message:
            with st.expander("📄 View & Download Generated Files", expanded=True):
                for file_info in message["files"]:
                    file_path = file_info["path"]
                    file_name = file_info["name"]
                    if os.path.exists(file_path):
                        if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(file_path, caption=file_name)
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"Download {file_name}",
                                data=f.read(),
                                file_name=file_name,
                                key=f"dl_{message['timestamp']}_{file_name}"
                            )

def run_crew_and_get_results(full_prompt):
    try:
        crewai_path = os.path.join(os.getenv('LOCALAPPDATA'), 'CrewAI', 'researcher')
        if os.path.exists(crewai_path):
            shutil.rmtree(crewai_path)
            print(f"Successfully deleted old memory cache: {crewai_path}")
    except Exception as e:
        print(f"Could not delete old memory cache (this is usually not critical): {e}")

    crew_instance = RESEARCHER().crew()
    result = crew_instance.kickoff(inputs={'problem_description': full_prompt})
    return result

# --- User Input Handling ---
if prompt := st.chat_input("Describe your problem or request a change..."):
    if not active_chat["messages"]:
        active_chat["title"] = " ".join(prompt.split()[:5]) + "..."

    active_chat["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    host_output_path, docker_output_path = get_new_output_path(active_chat_id)
    
    image_instruction = (
        f"**CRITICAL INSTRUCTIONS FOR OUTPUT:**\n"
        f"1.  Your final response MUST be a detailed Markdown report that INCLUDES the complete, runnable Python code within a ```python code block.\n"
        f"2.  The Python code itself MUST generate visual plots of the results using `matplotlib.pyplot`.\n"
        f"3.  The code MUST save each plot as a separate, descriptively named PNG file (e.g., `x_displacement.png`).\n"
        f"4.  The code MUST save ALL output files (PNGs, .pvd, .xdmf, etc.) to this absolute path inside the container: `{docker_output_path}/`.\n"
        f"--- USER REQUEST ---\n"
        f"{prompt}"
    )

    full_prompt = image_instruction
    if active_chat["last_code"]:
        full_prompt = (
             f"User's new request: {prompt}\n\n"
             f"Please modify the following Python code based on the user's new request. Do not start from scratch. "
             f"Your final response MUST be a new Markdown report that includes the complete, updated Python code. "
             f"The code must save all new output files to `{docker_output_path}/`.\n\n"
             f"Previous Code to Modify:\n```python\n{active_chat['last_code']}\n```"
        )
        
    with st.chat_message("assistant"):
        try:
            with st.spinner("🤖 Agents are working on your request... This may take a while."):
                crew_output = run_crew_and_get_results(full_prompt)
            
            final_report = str(crew_output.raw) if crew_output and hasattr(crew_output, 'raw') else "Agent did not return a valid report."

            if final_report:
                log_content = ""
                try:
                    with open("my_crew_log.json", "r", encoding="utf-8") as f:
                        log_content = f.read()
                    with st.expander("🔬 View Agents' Thinking Process", expanded=False):
                        st.code(log_content, language='json')
                except (FileNotFoundError, UnicodeDecodeError):
                    st.warning("Could not read the agent thinking log file.")
                
                # extracte code
                # 1. frome final report
                extracted_code = extract_python_code(final_report)
                
                # 2. search in output of each tasks
                if not extracted_code and crew_output.tasks_output:
                    st.toast("Code not in final report. Searching intermediate steps for the last version...")
                    found_code_in_tasks = False
                    for task_output in crew_output.tasks_output:
                        code_from_task = extract_python_code(task_output.raw)
                        # ensures that the remaining code is the last code 
                        if code_from_task:
                            extracted_code = code_from_task
                            found_code_in_tasks = True
                    
                    if found_code_in_tasks:
                        st.success("Successfully extracted the latest code from agent's workflow!")

                
                st.markdown("### 📝 Agent's Report")
                st.markdown(final_report)

                if extracted_code:
                    active_chat["last_code"] = extracted_code
                    st.markdown("### ✅ Final Code")
                    st.code(extracted_code, language='python')
                    
                    # add download button
                    st.download_button(
                        label="📥 Download Python Code",
                        data=extracted_code.encode("utf-8"),
                        file_name="generated_script.py",
                        mime="text/x-python"
                    )

                else:
                    st.warning("Could not extract a Python code block from any agent's report.")
                
                time.sleep(1)
                
                generated_files = []
                if os.path.exists(host_output_path):
                    st.markdown("---")
                    with st.expander("📄 View & Download Generated Files", expanded=True):
                        for filename in sorted(os.listdir(host_output_path)):
                            file_path = os.path.join(host_output_path, filename)
                            generated_files.append({"name": filename, "path": file_path})
                            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                st.image(file_path, caption=filename)
                            with open(file_path, "rb") as f:
                                st.download_button(
                                    label=f"Download {filename}",
                                    data=f.read(),
                                    file_name=filename,
                                    key=f"dl_new_{filename}_{int(time.time())}"
                                )

                assistant_message = {
                    "role": "assistant", 
                    "content": final_report,
                    "files": generated_files,
                    "thinking_log": log_content,
                    "timestamp": int(time.time())
                }
                active_chat["messages"].append(assistant_message)
                st.rerun()

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            active_chat["messages"].append({"role": "assistant", "content": str(e)})
            st.rerun()