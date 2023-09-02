import subprocess


def execute_command(command):
    try:
        output = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: Command '{command}' returned non-zero exit status {e.returncode}\n{e.output.strip()}"
