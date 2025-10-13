import os
import requests
import json
import argparse
import subprocess
import sys
import time

# --- NEW: Tee class to redirect stdout/stderr to multiple streams ---
class Tee:
    """A helper class to redirect output to multiple file-like objects (e.g., terminal and a file)."""
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            try:
                f.write(obj)
                f.flush()  # Ensure output is written immediately
            except IOError:
                # Handle cases where one of the streams might be closed
                pass

    def flush(self):
        for f in self.files:
            try:
                f.flush()
            except IOError:
                pass


# --- Color management class for the terminal ---
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    DIM = '\033[2m'

# --- Default Configurations ---
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
MAX_OUTPUT_LENGTH = 30000

class AIAgent:
    """
    USE ONLY IN A DISPOSABLE VM WITH 'sudo'.
    """
    def __init__(self, target, objective, provider, model=None, base_url=None, api_key=None):
        if not target or not objective:
            raise ValueError("Target and objective are required.")
        
        self.target = target
        self.objective = objective
        self.history = []
        
        # LLM provider setup (OpenRouter or Ollama)
        self.provider = provider
        if self.provider == 'openrouter':
            if not api_key:
                raise ValueError("API key is required for OpenRouter.")
            self.api_key = api_key
            self.model = model or DEFAULT_OPENROUTER_MODEL
            self.api_url = OPENROUTER_API_URL
            print(f"{Colors.BOLD}{Colors.CYAN}Using Provider: OpenRouter ({self.model}){Colors.RESET}")
        elif self.provider == 'ollama':
            if not model:
                 raise ValueError("A model name must be specified for the Ollama provider (--model).")
            self.model = model
            self.base_url = base_url or DEFAULT_OLLAMA_BASE_URL
            self.api_url = f"{self.base_url.rstrip('/')}/api/chat"
            print(f"{Colors.BOLD}{Colors.CYAN}Using Provider: Ollama ({self.model} at {self.base_url}){Colors.RESET}")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Choose 'openrouter' or 'ollama'.")

        print(f"{Colors.BOLD}{Colors.MAGENTA}--- AI CYBER AGENT FRAMEWORK ---{Colors.RESET}")
        print("\n" + "="*60)
        print(f"{Colors.RED}This script is in the testing phase. If you encounter bugs, please open an issue on GitHub.")
        print(f"PROCEED ONLY IF YOU ARE USING A VIRTUAL MACHINE.{Colors.RESET}")
        print("="*60 + "\n")
        try:
            input(f"{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")
        except EOFError:
            print("\nExecution cancelled.")
            sys.exit(1)

    def execute_command(self, command, timeout=600):
        if not command: return "Error: No command to execute."
        print(f"\n{Colors.BOLD}{Colors.YELLOW}[>>] EXECUTING AS ROOT:{Colors.RESET} {command}")
        try:
            process = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout, 
                encoding='utf-8', 
                errors='ignore'
            )
            return process.stdout + process.stderr
        except subprocess.TimeoutExpired:
            return f"Error: The command timed out after {timeout} seconds."
        except Exception as e:
            return f"Error executing command: {e}"

    def _call_openrouter(self, prompt_messages):
        headers = { "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json" }
        data = { "model": self.model, "messages": prompt_messages }
        response = requests.post(self.api_url, headers=headers, json=data, timeout=180)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return content

    def _call_ollama(self, prompt_messages):
        headers = { "Content-Type": "application/json" }
        # The "format": "json" parameter forces Ollama to return valid JSON
        data = { "model": self.model, "messages": prompt_messages, "stream": False, "format": "json" }
        response = requests.post(self.api_url, data=json.dumps(data), timeout=180)
        response.raise_for_status()
        content = response.json()['message']['content']
        return content

    def call_llm(self, prompt_messages):
        max_retries = 3
        backoff_factor = 5

        for attempt in range(max_retries):
            try:
                content = ""
                if self.provider == 'openrouter':
                    content = self._call_openrouter(prompt_messages)
                elif self.provider == 'ollama':
                    content = self._call_ollama(prompt_messages)

                # Remove markdown wrappers (```json ... ```) from the response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif content.strip().startswith("```") and content.strip().endswith("```"):
                     content = content.strip()[3:-3].strip()
                return content
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    print(f"{Colors.RED}[!] Error: 400 Bad Request. The request might be too large or malformed.{Colors.RESET}")
                    print(f"{Colors.DIM}Response body: {e.response.text[:500]}...{Colors.RESET}")
                    return f'{{"thought": "The previous API request failed with a 400 error, likely because the context was too large. I need to proceed with a different approach, perhaps by summarizing previous findings or trying a less verbose command.", "command": "echo \'API request failed, retrying with a different strategy.\'"}}'
                print(f"{Colors.YELLOW}[!] Warning: API connection failed (attempt {attempt + 1}/{max_retries}): {e}{Colors.RESET}")
            except requests.exceptions.RequestException as e:
                print(f"{Colors.YELLOW}[!] Warning: API connection failed (attempt {attempt + 1}/{max_retries}): {e}{Colors.RESET}")

            if attempt < max_retries - 1:
                wait_time = backoff_factor * (attempt + 1)
                print(f"{Colors.CYAN}[*] Retrying in {wait_time} seconds...{Colors.RESET}")
                time.sleep(wait_time)
            else:
                print(f"{Colors.RED}[!] Error: Maximum connection retries reached.{Colors.RESET}")
                return f'{{"thought": "Critical API connection error. Check internet/DNS.", "command": "FINISH_FAILURE"}}'
        return f'{{"thought": "Unexpected failure in API retry loop.", "command": "FINISH_FAILURE"}}'

    @staticmethod
    def parse_llm_response(response_text):
        try:
            return json.loads(response_text)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"{Colors.RED}[!] Error decoding JSON: {e}\n[!] Received response: {response_text}{Colors.RESET}")
            return {"thought": "The AI's response was not valid JSON. I will try again, ensuring my output is perfectly formatted.", "command": "echo 'AI response has invalid format.'"}

    def run_mission(self):
        print(f"\n{Colors.BOLD}{Colors.CYAN}--- STARTING MISSION ---{Colors.RESET}")
        print(f"{Colors.BOLD}Target:{Colors.RESET} {self.target}\n{Colors.BOLD}Objective:{Colors.RESET} {self.objective}\n--------------------------\n")

        system_prompt = self.create_system_prompt()
        user_prompt = f"The target is '{self.target}' and the objective is '{self.objective}'. Please begin."
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

        step = 1
        while True:
            print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- STEP {step} ---{Colors.RESET}")
            print(f"{Colors.CYAN}[*] Thinking...{Colors.RESET}")
            
            llm_response_text = self.call_llm(messages)
            action = self.parse_llm_response(llm_response_text)
            
            thought = action.get("thought", "No thought recorded.")
            command = action.get("command", "")
            print(f"{Colors.GREEN}{Colors.BOLD}[+] THOUGHT:{Colors.RESET}{Colors.GREEN} {thought}{Colors.RESET}")
            
            current_history = {"step": step, "thought": thought, "command": command, "result": "", "result_summary": ""}
            self.history.append(current_history)

            if command in ["FINISH_SUCCESS", "FINISH_FAILURE"]:
                status_color = Colors.GREEN if command == "FINISH_SUCCESS" else Colors.RED
                print(f"\n{Colors.BOLD}{status_color}--- MISSION COMPLETE --- \nFinal Status: {command}{Colors.RESET}")
                break
            
            result = self.execute_command(command)
            current_history["result"] = result

            if len(result) > MAX_OUTPUT_LENGTH:
                filename = f"output_step_{step}.log"
                with open(filename, "w", encoding='utf-8', errors='ignore') as f:
                    f.write(result)
                
                print(f"{Colors.BLUE}{Colors.BOLD}[<<] RESULT IS TOO LARGE ({len(result)} chars). Saved to '{filename}'. Informing AI.{Colors.RESET}")
                
                user_feedback = (f"The command output was too large to display directly. "
                                 f"It has been saved to the file '{filename}'.\n"
                                 f"You MUST analyze this file using file-reading commands (like 'head', 'tail', 'grep', 'cat') "
                                 f"to find the relevant information and decide your next step.")
                current_history["result_summary"] = f"Output too large, saved to {filename}"
            else:
                print(f"{Colors.BLUE}{Colors.BOLD}[<<] FULL RESULT SENT TO AI ({len(result)} characters):{Colors.RESET}")
                user_feedback = f"The result of your last command was:\n---\n{result}\n---\nBased on this full result, what is your next step?"

            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append({"role": "user", "content": user_feedback})
            
            step += 1

        self.generate_report()
    
    def _summarize_history_for_report(self):
        summary = []
        for record in self.history:
            command = record['command']
            if command in ["FINISH_SUCCESS", "FINISH_FAILURE"]:
                summary.append(f"Step {record['step']}: Mission finished with status: {command}.")
                continue

            thought = record['thought']
            summary.append(f"Step {record['step']}:\n- Thought: {thought}\n- Command Executed: {command}")
        return "\n".join(summary)

    def generate_report(self):
        print("\n\n" + f"{Colors.BOLD}{Colors.CYAN}" + "="*80 + "\nGenerating Final Narrative Report...\n" + "="*80 + f"{Colors.RESET}")
        
        if not self.history or self.history[-1]['command'] != "FINISH_SUCCESS" or len(self.history) < 2:
            last_status = self.history[-1]['command'] if self.history else "UNKNOWN"
            result_status = f"{Colors.RED}FAILURE ({last_status}){Colors.RESET}"
            print(f"{Colors.BOLD}**Target:**{Colors.RESET} {self.target}")
            print(f"{Colors.BOLD}**Objective:**{Colors.RESET} {self.objective}")
            print(f"{Colors.BOLD}**Final Result:**{Colors.RESET} {result_status}")
            print(f"{Colors.YELLOW}Mission did not complete successfully. Skipping narrative report.{Colors.RESET}")
            return

        mission_log = self._summarize_history_for_report()
        final_evidence = self.history[-2].get('result', 'No direct evidence captured.').strip()
        if not final_evidence and self.history[-2].get('result_summary'):
             final_evidence = f"Evidence is located in the file: {self.history[-2]['result_summary'].split(' ')[-1]}"

        report_prompt = f"""
        You are a senior penetration tester summarizing the results of an engagement.
        Based on the following mission log and final evidence, write a final report for the client.

        The report must be clear, concise, and professional. You MUST strictly follow the Markdown formatting rules below:
        - The main title MUST start with a single hashtag (#).
        - Each section title MUST start with two hashtags (##).
        - The two required section titles are EXACTLY: `## Executive Summary` and `## Proof of Concept (PoC)`.
        - The evidence in the PoC section MUST be enclosed in a single fenced code block (using ```).

        **Mission Details:**
        - **Target:** {self.target}
        - **Objective:** {self.objective}

        **Execution Log (for your context only):**
        ---
        {mission_log}
        ---

        **Final Proof of Concept (PoC) Data:**
        ---
        {final_evidence}
        ---

        Now, generate the final report based on these instructions.
        """
        
        print(f"{Colors.CYAN}[*] Asking AI ({self.model}) to synthesize the final report... This may take a moment.{Colors.RESET}")
        
        messages = [{"role": "user", "content": report_prompt}]
        
        narrative_report = self.call_llm(messages)
        
        print("\n" + f"{Colors.BOLD}{Colors.GREEN}" + "="*80 + "\nFINAL MISSION REPORT\n" + "="*80 + f"{Colors.RESET}")
        
        in_code_block = False
        for line in narrative_report.splitlines():
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                print(f"{Colors.DIM}{line}{Colors.RESET}")
            elif in_code_block:
                print(f"{Colors.GREEN}{line}{Colors.RESET}")
            elif line.startswith('# '):
                print(f"{Colors.BOLD}{Colors.CYAN}{line}{Colors.RESET}")
            elif line.startswith('## '):
                print(f"{Colors.BOLD}{Colors.YELLOW}{line}{Colors.RESET}")
            else:
                print(line)
        
        print("\n" + f"{Colors.BOLD}{Colors.CYAN}" + "="*80 + "\nEND OF REPORT\n" + "="*80 + f"{Colors.RESET}")

    def create_system_prompt(self):
        # --- MODIFICATION IS HERE ---
        return """
        You are 'Cortex', an autonomous cybersecurity agent.

        CRITICAL RULES:
        1. You are operating with root privileges (superuser). You will receive the full, raw output of all commands.
        2. NON-INTERACTIVE EXECUTION: All commands you issue MUST be non-interactive and designed to terminate on their own without user input. You MUST NOT use commands that start an interactive session (e.g., `nc`, `telnet` without piping input) or run indefinitely (e.g., `ping host.com`). Always use finite parameters, for example: `ping -c 4 host.com`.
        3. You are using Kali Linux, so feel free to use any Kali Linux tool to achieve your goal easier and faster.
        4. INSTALLATION ABILITY: If a command fails with 'command not found', install the missing tool using `apt update && apt install -y <package_name>`.
        5. Think step-by-step, analyzing the full result to inform your next action.
        6. Your response MUST be a valid JSON with the keys "thought" and "command".
        7. Use "FINISH_SUCCESS" or "FINISH_FAILURE" to end the mission.
        8. HANDLING LARGE OUTPUTS: If you are told that a command's output was too large and has been saved to a file (e.g., 'output_step_X.log'), you MUST use file-reading commands (`cat`, `less`, `grep`, `head`, `tail`) to inspect the file's contents to determine your next action. Do not ignore the file.
        """

def check_root():
    if os.name != 'nt' and os.geteuid() != 0:
        print(f"{Colors.RED}\n[!] ERROR: Please run with 'sudo python3 {sys.argv[0]} ...'{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    check_root()
    parser = argparse.ArgumentParser(description="AI Cyber Agent.")
    parser.add_argument("--target", required=True, help="The mission's target.")
    parser.add_argument("--objective", required=True, help="The mission's objective.")
    
    # --- NEW: Added -o/--output argument ---
    parser.add_argument(
        "-o", "--output",
        help="File to save the entire session log to."
    )

    parser.add_argument(
        "--provider", 
        choices=['openrouter', 'ollama'], 
        default='openrouter', 
        help="The LLM provider to use (default: openrouter)."
    )
    parser.add_argument(
        "--model", 
        help="The model name to use. E.g., 'google/gemini-flash-1.5' for OpenRouter or 'llama3' for Ollama."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_OLLAMA_BASE_URL,
        help=f"The base URL for the local LLM provider (Ollama) (default: {DEFAULT_OLLAMA_BASE_URL})."
    )
    
    args = parser.parse_args()

    # --- NEW: Setup logging to file if --output is provided ---
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    log_file = None

    if args.output:
        try:
            log_file = open(args.output, 'w', encoding='utf-8', errors='ignore')
            # Redirect both stdout and stderr to the Tee object
            tee = Tee(original_stdout, log_file)
            sys.stdout = tee
            sys.stderr = tee
            print(f"[{Colors.CYAN}*{Colors.RESET}] Logging all output to '{args.output}'")
        except IOError as e:
            # If we can't open the file, print to the original stderr and exit
            original_stderr.write(f"{Colors.RED}[!] Error: Could not open output file '{args.output}': {e}{Colors.RESET}\n")
            sys.exit(1)
    
    try:
        api_key = None
        if args.provider == 'openrouter':
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("For the 'openrouter' provider, the 'OPENROUTER_API_KEY' environment variable is not set.")

        agent = AIAgent(
            target=args.target, 
            objective=args.objective, 
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            api_key=api_key
        )
        agent.run_mission()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Operation interrupted by user.{Colors.RESET}")
    except ValueError as e:
        print(f"\n{Colors.RED}[!] Configuration Error: {e}{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}[!!!] A fatal application error occurred: {e}{Colors.RESET}")
    finally:
        # --- NEW: Cleanup block to ensure the log file is closed and streams are restored ---
        if log_file:
            print(f"\n[{Colors.CYAN}*{Colors.RESET}] Session log saved to '{args.output}'")
            log_file.close()
            # Restore original stdout and stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
