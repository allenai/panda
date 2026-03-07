
import json
import re
from html.parser import HTMLParser
import unicodedata
from .logger import logger

# New version, courtesy of Claude
def extract_json_from_string(text: str) -> any:
    """
    Robustly parse JSON from a Claude API response string.
    Handles:
      - Raw JSON strings
      - JSON wrapped in ```json ... ``` code fences
      - JSON wrapped in ``` ... ``` code fences (no language tag)
      - Surrounding text before/after the fenced block
    """
    if not text or not text.strip():
        raise ValueError("Empty response")

    # 1. Try to extract from a code fence (```json or ``` with optional language tag)
    fence_pattern = re.compile(
        r'```(?:json)?\s*\n(.*?)\n\s*```',
        re.DOTALL | re.IGNORECASE
    )
    matches = fence_pattern.findall(text)
    for match in matches:
        candidate = match.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue  # try next match if multiple fences

    # 2. Try parsing the whole string as-is
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 3. Heuristic: find the first { or [ and try to parse from there
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No valid JSON found in response: {text[:200]!r}")    

# ----------    

def extract_html_from_string(text):
    """Extracts the HTML portion from a given text."""
    match = re.search(r"```html\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        logger.info("Yikes! Couldn't find any HTML in string! Returning it directly...")
        return text

# ----------    

def extract_txt_from_string(text):
    """Extracts an explicit text block (if annotated) """
    match = re.search(r"```text\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        match = re.search(r"```txt\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1)    
        else:
            return text

### ======================================================================
###	Courtesy Gemini
### ======================================================================

def extract_first_code_block(text):
  """
  Extracts a single code block enclosed in triple backticks (```) from a given text.
  Args:
    text: The input text containing a single code block.
  Returns:
    The extracted code block as a string, or None if no code block is found.
  """
  pattern = r"```(?:\w*\n)?(.*?)```"
  match = re.search(pattern, text, re.DOTALL)

  if match:
    return match.group(1).strip()
  else:
    return None

# --------------------

def extract_code_blocks(text):
  """
  Extracts code blocks enclosed in triple backticks (```) from a given text.
  Args:
    text: The input text containing potential code blocks.
  Returns:
    A list of strings, where each string is a extracted code block.
    Returns an empty list if no code blocks are found.
  """
  code_blocks = []
  pattern = r"```(?:\w*\n)?(.*?)```"  # Matches ``` with optional language specifier
  matches = re.findall(pattern, text, re.DOTALL)

  for match in matches:
      code_blocks.append(match.strip()) #remove leading and trailing whitespace.

  return code_blocks

### ======================================================================

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_data(self):
        return ''.join(self.text)

def remove_html_markup(html):
    """Remove HTML markup from the given string."""
    stripper = HTMLStripper()
    stripper.feed(html)
    return normalize_newlines(stripper.get_data())

# ------------------------------

def normalize_newlines(text):
    # Replace multiple blank lines (lines with only whitespace or newlines) with a single newline
    return re.sub(r'(\n\s*\n)+', '\n\n', text.strip())
 
## replace triple, 4x, .. newlines with a double newline
#def normalize_newlines(text):
#    return re.sub(r'\n{3,}', '\n\n', text)

# ----------------------------------------------------------------------

def multiline_input(prompt="Enter your text (end with a blank line): "):
    print(prompt, end="")
    lines = []
    while True:
        line = input()
        if line.strip().lower() == 'q':  # Check for 'q' as an end signal
            return 'q'
        elif line.strip() == "": 
            if lines:  # Check if any lines have been entered
                break
            else:
                print("Please enter something!")
                print(prompt, end="")                
                continue  # Retry input
        lines.append(line)
    return "\n".join(lines)

# ======================================================================
#	GET RID OF SPECIAL CHARACTERS
# ======================================================================
    
# o1 version

CUSTOM_REPLACEMENTS = {
    8212: ' - ',   # Em dash
    8211: '-',     # En dash
    8220: '"',     # Left double quotation mark
    8221: '"',     # Right double quotation mark
    8216: "'",     # Left single quotation mark
    8217: "'",     # Right single quotation mark
    8230: '...'    # Ellipsis
    # Add more replacements as needed
}

def replace_special_chars_with_ascii(text):
    global CUSTOM_REPLACEMENTS
    result = []

    for char in text:
        code_point = ord(char)
        if code_point in CUSTOM_REPLACEMENTS:
            result.append(CUSTOM_REPLACEMENTS[code_point])
        else:
            normalized_char = unicodedata.normalize('NFKD', char)
            ascii_bytes = normalized_char.encode('ascii', 'ignore')
            ascii_char = ascii_bytes.decode('ascii')
            result.append(ascii_char)
    ascii_text = ''.join(result)
    return ascii_text

### ======================================================================

import string

## e.g., similar_strings("Hello, World!", "hello world") -> True
def similar_strings(str1, str2):

    # Convert both strings to lowercase
    str1_lower = str1.lower()
    str2_lower = str2.lower()

    # Remove punctuation from both strings
    table = str.maketrans('', '', string.punctuation)
    str1_no_punct = str1_lower.translate(table)
    str2_no_punct = str2_lower.translate(table)

    # Compare the strings
    return str1_no_punct == str2_no_punct

# Shorthand for pretty-printing JSON objects (or lists of JSON objects)
def jprint(json_item):
    logger.info(json.dumps(json_item,indent=2))

# printf() instead of print() is a repeated  misconception of GPT4.1 so let's define it to reduce trivial errors
# or could simply do printf = print, apparently, as functions are first-class objects    
#def printf(format_str, *args):
#    print(format_str % args)

# logger automatically adds a newline when printing    
def remove_trailing_newline(s: str) -> str:
    """Remove a single trailing newline (\\n or \\r\\n) from the end of the string, if present."""
    if s.endswith("\r\n"):
        return s[:-2]
    elif s.endswith("\n") or s.endswith("\r"):
        return s[:-1]
    else:
        return s

# ------------------------------

def strip_trailing_question(text: str) -> str:
    """
    Removes the final trailing question (including Markdown formatting) 
    if the final sentence is a question. Returns the cleaned text.
    """
    original = text.rstrip()

    # Pattern to capture a trailing question sentence (optionally wrapped in markdown)
    # Handles cases like:
    #   What do you want to do next?
    #   **What do you want to do next?**
    #   *What do you want to do next?*
    #   ## What do you want to do next?
    md_opt = r'(?:[*_#\s]*)'   # Optional markdown stars, underscores, headers, spaces
    question_pattern = (
        rf"{md_opt}"           # Leading markdown
        r"([^\n]*\?)"          # The question sentence
        rf"{md_opt}$"          # Optional markdown after
    )

    # Try to find a final question at the end
    match = re.search(question_pattern, original)

    if match:
        # Remove the entire matched question block
        cleaned = original[:match.start()].rstrip()
        return cleaned

    # If no terminal question found, return original text
    return original

