import re

def extract_code(text):
    """
    Extracts only valid Python code from the generated text, excluding comments and non-code text.
    
    Args:
        text (str): The raw model output.
    
    Returns:
        str: The cleaned code without comments or non-code text.
    """
    code_lines = text.split("\n")
    filtered_lines = []

    # Regex pattern to match only valid Python code
    code_pattern = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*\s*[=()]?[a-zA-Z0-9_.,\[\]{}+=/*%-]*)")

    for line in code_lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue  # Ignore empty lines

        # Skip comment lines (Python style)
        if stripped_line.startswith("#"):
            continue

        # Only keep lines that look like valid Python code
        if code_pattern.match(stripped_line):
            filtered_lines.append(line)

    return "\n".join(filtered_lines)

chunk_to_send = [' ', 'def ', '', '', '', '', '__init__(self, ', '', 'x, ', '', 'y, ', 'angle):\n', '       ', ' ', '', '', 'self.x, ', '', 'self.y ', '= ', '', 'x, ', 'y\n', '       ', ' ', '', 'self.speed ', '= ', '', '', '', 'CONFIG["bullet_speed"]\n', '       ', ' ', '', 'self.angle ', '= ', 'angle ', ' ', '# ', 'Bullet ', 'angle ', 'in ', 'degrees\n', '       ', ' ', '', 'self.size ', '= ', '', '', '', 'CONFIG["bullet_size"]\n', '       ', ' ', '', 'self.image ', '= ', '', '', '', '', '', '', '', '', '', '', 'pygame.Surface(self.size).fill((255, ', '', '', '0, ', '', '0))\n', '       ', ' ', '', '', 'self.angle_rad ', '= ', '', '', 'math.radians(angle)\n\n', '   ', ' ', 'def ', '', '', 'draw(self, ', '', 'screen): ', '', '', '', '', 'screen.blit(self.image, ', '', '', '', '(self.x, ', '', 'self.y))\n\n', '   ', ' ', 'def ', '', '', '', '', 'interact_with_bullet(self, ', 'bullets):\n', '       ', ' ', 'return ', 'False\n    \n', '   ', ' ', 'def ', '', '', '', '', '', 'check_collision_with_bullet(self, ', '', 'bullets): ', 'return ', 'False\n', '', '```\n\n', '', 'This ', 'function ', '', '', '`Enemy` ', 'represents ', 'an ', 'enemy ', 'object ', 'that ', 'can ', 'be ', 'instantiated ', 'and ', '', 'manipulate. ', 'It ', 'has ', 'methods ', 'to ', 'move ', 'the ', '', 'enemy, ', 'draw ', 'it ', 'on ', 'the ', '', 'screen, ', 'interact ', 'with ', '', 'bullets, ', 'and ', 'check ', 'for ', 'collisions ', 'with ', 'bullets.\n\n', '', '', '**Created ', '', 'Question**:\n', '', 'How ', 'can ', 'I ', 'modify ', 'the ', '', "enemy's ", 'behavior ', 'to ', 'make ', 'it ', 'shoot ', 'bullets ', 'when ', 'it ', 'reaches ', 'a ', 'certain ', 'number ', 'of ', 'enemy ', '', '', 'points?<|im_end|>']
# Join the list into a single string
processed_chunk = extract_code("".join(chunk_to_send))

# Print the processed code
print("Processed code:\n", processed_chunk)