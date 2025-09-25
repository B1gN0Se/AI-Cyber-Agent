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
MODEL_NAME = "anthropic/claude-3.7-sonnet"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_OUTPUT_LENGTH = 30000

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

    def call_llm(self, prompt_messages):
        headers = { "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json" }
        data = { "model": MODEL_NAME, "messages": prompt_messages }
        max_retries = 3
        backoff_factor = 5

        for attempt in range(max_retries):
            try:
                response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=180)
                response.raise_for_status()
                content = response.json()['choices'][0]['message']['content']
                # Remove markdown wrappers from JSON responses
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif content.strip().startswith("```") and content.strip().endswith("```"):
                     content = content.strip()[3:-3].strip()
                return content
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    print(f"{Colors.RED}[!] Error: 400 Bad Request. The API request was likely too large or malformed.{Colors.RESET}")
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
        """Formats the mission history into a text string for the AI."""
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
        
        # Only generate a detailed report if the mission was a success and had steps
        if not self.history or self.history[-1]['command'] != "FINISH_SUCCESS" or len(self.history) < 2:
            last_status = self.history[-1]['command'] if self.history else "UNKNOWN"
            result_status = f"{Colors.RED}FAILURE ({last_status}){Colors.RESET}"
            print(f"{Colors.BOLD}**Target:**{Colors.RESET} {self.target}")
            print(f"{Colors.BOLD}**Objective:**{Colors.RESET} {self.objective}")
            print(f"{Colors.BOLD}**Final Result:**{Colors.RESET} {result_status}")
            print(f"{Colors.YELLOW}Mission did not complete successfully. Skipping narrative report.{Colors.RESET}")
            return

        mission_log = self._summarize_history_for_report()
        
        # The Proof of Concept (PoC) is the result of the penultimate step
        final_evidence = self.history[-2].get('result', 'No direct evidence captured.').strip()
        if not final_evidence and self.history[-2].get('result_summary'):
             final_evidence = f"Evidence is located in the file: {self.history[-2]['result_summary'].split(' ')[-1]}"

        # Create the prompt for the AI to generate the final report, requiring Markdown format
        report_prompt = f"""
        You are a senior penetration tester summarizing the results of an engagement.
        Based on the following mission log and final evidence, write a final report for the client.

        The report must be clear, concise, and professional. You MUST strictly follow the Markdown formatting rules below:
        - The main title MUST start with a single hashtag (e.g., `# Penetration Test Report`).
        - Each section title MUST start with two hashtags (e.g., `## Executive Summary`).
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
        
        messages = [{"role": "user", "content": report_prompt}]
        
        print(f"{Colors.CYAN}[*] Asking AI to synthesize the final report... This may take a moment.{Colors.RESET}")
        
        # Call the AI to generate the report in Markdown format
        narrative_report = self.call_llm(messages)
        
        # Print the generated report, applying colors based on formatting
        print("\n" + f"{Colors.BOLD}{Colors.GREEN}" + "="*80 + "\nFINAL MISSION REPORT\n" + "="*80 + f"{Colors.RESET}")
        
        in_code_block = False
        for line in narrative_report.splitlines():
            # Check for the start/end of a code block
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                print(f"{Colors.DIM}{line}{Colors.RESET}") # Print the ``` in dim
            elif in_code_block:
                # Lines inside the code block (PoC) are green
                print(f"{Colors.GREEN}{line}{Colors.RESET}")
            elif line.startswith('# '):
                # Main title in Bold Cyan
                print(f"{Colors.BOLD}{Colors.CYAN}{line}{Colors.RESET}")
            elif line.startswith('## '):
                # Section titles in Bold Yellow
                print(f"{Colors.BOLD}{Colors.YELLOW}{line}{Colors.RESET}")
            else:
                # Normal text (no special color)
                print(line)
        
        print("\n" + f"{Colors.BOLD}{Colors.CYAN}" + "="*80 + "\nEND OF REPORT\n" + "="*80 + f"{Colors.RESET}")

    def create_system_prompt(self):
        return """
        You are 'Cortex', an autonomous cybersecurity agent.

        CRITICAL RULES:
        1. You are operating with root privileges (superuser). You will receive the full, raw output of all commands.
        2. You are using Kali Linux, so feel free to use any kali linux tool to achieve your goal easier and faster
        3. INSTALLATION ABILITY: If a command fails with 'command not found', install the missing tool using `apt-get update && apt-get install -y <package_name>`.
        4. Think step-by-step, analyzing the full result to inform your next action.
        5. Your response MUST be valid JSON with the keys "thought" and "command".
        6. Use "FINISH_SUCCESS" or "FINISH_FAILURE" to end the mission.
        7. HANDLING LARGE OUTPUTS: If you are told that a command's output was too large and has been saved to a file (e.g., 'output_step_X.log'), you MUST use file-reading commands (`cat`, `less`, `grep`, `head`, `tail`) to inspect the file's contents to determine your next action. Do not ignore the file.
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
