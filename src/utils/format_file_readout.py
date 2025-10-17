READOUT_FORMAT_EXPAND_HEADER=1.5

def format_file_readout(name, text):
    """
    Normalizes to \n, strips leading/trailing whitespace,


    Creates a header with row of stars and file path, like


    *******************************
         my/important/file.txt
    *******************************

    The number of stars is equal to READOUT_FORMAT_EXPAND_HEADER * len(name)

    Attempts to center the name in the header (round to nearest integer)

    Then, it puts on more blank line, then the contents of the file

    """
    # Normalize newlines and strip outer whitespace of contents
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Determine header width (at least the name length)
    raw_width = int(round(READOUT_FORMAT_EXPAND_HEADER * len(name)))
    width = max(len(name), raw_width)

    # Build star lines
    stars = "*" * width

    # Center the name by left-padding with spaces to the nearest center
    left_pad = (width - len(name)) // 2
    name_line = " " * left_pad + name

    # Assemble final string
    return f"{stars}\n{name_line}\n{stars}\n\n{normalized}"
