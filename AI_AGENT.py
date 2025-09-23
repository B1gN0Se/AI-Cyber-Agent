import os
import requests
import json
import argparse
import subprocess
import sys
import time

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

# --- Configuration ---
MODEL_NAME = "deepseek/deepseek-chat-v3.1"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class AIAgent:
    """
    USE ONLY IN A DISPOSABLE VM WITH 'sudo'.
    """
    def __init__(self, target, objective, api_key):
        if not target or not objective or not api_key:
            raise ValueError("Target, objective, and API key are required.")
        
        self.target = target
        self.objective = objective
        self.api_key = api_key
        self.history = []
        
        print(f"{Colors.BOLD}{Colors.MAGENTA}--- AI CYBER AGENT FRAMEWORK ---{Colors.RESET}")
        print("\n" + "="*60)
        print(f"{Colors.RED}This script is still in the testing phase. If you encounter any bugs, please open an issue on GitHub.")
        print(f"PROCEED ONLY IF YOU ARE IN A USING A VIRTUAL MACHINE.{Colors.RESET}")
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
            process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='ignore')
            return process.stdout + process.stderr
        except subprocess.TimeoutExpired:
            return f"Error: The command timed out after {timeout} seconds."
        except Exception as e:
            return f"Error executing command: {e}"

    def call_llm(self, prompt_messages):
        headers = { "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json" }
        data = { "model": MODEL_NAME, "messages": prompt_messages }
        max_retries = 3
        backoff_factor = 5

        for attempt in range(max_retries):
            try:
                response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=180)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
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
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            return json.loads(response_text)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"{Colors.RED}[!] Error decoding JSON: {e}\n[!] Received response: {response_text}{Colors.RESET}")
            return {"thought": "The AI's response was not valid JSON.", "command": "echo 'AI response has invalid format.'"}

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

            self.history.append({"step": step, "thought": thought, "command": command, "result": ""})
            
            if command in ["FINISH_SUCCESS", "FINISH_FAILURE"]:
                status_color = Colors.GREEN if command == "FINISH_SUCCESS" else Colors.RED
                print(f"\n{Colors.BOLD}{status_color}--- MISSION COMPLETE --- \nFinal Status: {command}{Colors.RESET}")
                break
            
            result = self.execute_command(command)
            print(f"{Colors.BLUE}{Colors.BOLD}[<<] FULL RESULT SENT TO AI ({len(result)} characters):{Colors.RESET}")
            print(f"{Colors.DIM}{result.strip()[:1000]}...{Colors.RESET}") # Shows a preview in dim color

            self.history[-1]["result"] = result

            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append({"role": "user", "content": f"The result of your last command was:\n---\n{result}\n---\nBased on this full result, what is your next step?"})
            
            step += 1

        self.generate_report()
    
    def generate_report(self):
        print("\n\n" + f"{Colors.BOLD}{Colors.CYAN}" + "="*80 + "\nFINAL MISSION REPORT - AI AGENT\n" + "="*80 + f"{Colors.RESET}")
        last_status = self.history[-1]['command']
        
        if last_status == "FINISH_SUCCESS":
            result_status = f"{Colors.GREEN}SUCCESS{Colors.RESET}"
        else:
            result_status = f"{Colors.RED}FAILURE{Colors.RESET}"
            
        print(f"{Colors.BOLD}**Target:**{Colors.RESET} {self.target}\n{Colors.BOLD}**Objective:**{Colors.RESET} {self.objective}\n{Colors.BOLD}**Final Result:**{Colors.RESET} {result_status}\n" + "-" * 80)
        print(f"\n{Colors.BOLD}**Execution Summary (Log):**{Colors.RESET}\n")
        
        for record in self.history:
            print(f"{Colors.MAGENTA}--- Step {record['step']} ---{Colors.RESET}")
            print(f"  - {Colors.GREEN}Thought:{Colors.RESET} {record['thought']}")
            print(f"  - {Colors.YELLOW}Command:{Colors.RESET} {record['command']}")
            if record['command'] not in ["FINISH_SUCCESS", "FINISH_FAILURE"]:
                result_preview = record['result'].strip().replace('\n', ' ')[:150]
                print(f"  - {Colors.DIM}Result (preview):{Colors.RESET} {result_preview}...")
            print(f"{Colors.DIM}" + "-" * 20 + f"{Colors.RESET}")
            
        if last_status == "FINISH_SUCCESS" and len(self.history) > 1:
            print(f"\n{Colors.BOLD}**Proof of Concept (Evidence):**{Colors.RESET}\n")
            final_evidence = self.history[-2]['result']
            print(f"{Colors.GREEN}```\n" + final_evidence.strip() + f"\n```{Colors.RESET}")
        
        print("\n" + f"{Colors.BOLD}{Colors.CYAN}" + "="*80 + "\nEND OF REPORT\n" + "="*80 + f"{Colors.RESET}")

    def create_system_prompt(self):
        return """
        You are 'Cortex', an autonomous cybersecurity agent.

        CRITICAL RULES:
        1. You are operating with root privileges (superuser). You will receive the full, raw output of all commands.
        2. INSTALLATION ABILITY: If a command fails with 'command not found', install the missing tool using `apt-get update && apt-get install -y <package_name>`.
        3. Think step-by-step, analyzing the full result to inform your next action.
        4. Your response MUST be valid JSON with the keys "thought" and "command".
        5. Use "FINISH_SUCCESS" or "FINISH_FAILURE" to end the mission.
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
    args = parser.parse_args()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print(f"{Colors.RED}[!] Error: The 'OPENROUTER_API_KEY' environment variable is not set.{Colors.RESET}")
        sys.exit(1)
    try:
        agent = AIAgent(target=args.target, objective=args.objective, api_key=api_key)
        agent.run_mission()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Operation interrupted by user.{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}[!!!] A fatal application error occurred: {e}{Colors.RESET}")
