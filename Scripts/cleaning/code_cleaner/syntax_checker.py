import sys

def check_syntax(code: str) -> bool:
    """Check if Python code is syntactically correct."""
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError:
        return False
    except Exception:
        return False

def main():
    """Reads input from stdin and checks syntax efficiently."""
    buffer = ""
    while True:
        line = sys.stdin.readline()
        if not line:
            continue  # Avoid processing empty input
        
        buffer += line
        if line.strip() == "END":  # Use a custom delimiter to mark end of snippet
            buffer = buffer[:-4]  # Remove "END"
            print(1 if check_syntax(buffer) else 0, flush=True)
            buffer = ""  # Reset buffer for the next snippet

if __name__ == "__main__":
    main()
