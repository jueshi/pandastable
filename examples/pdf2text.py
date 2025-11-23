import PyPDF2

def pdf_to_text(pdf_path, txt_path):
    """
    Convert a PDF file to a text file.

    Args:
        pdf_path (str): The path to the source PDF file.
        txt_path (str): The path to the destination text file.
    """
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        with open(txt_path, 'w', encoding='utf-8') as text_file:
            for page in reader.pages:
                text_file.write(page.extract_text())

# Example usage (commented out to avoid error on import)
# pdf_to_text(r"C:\Users\juesh\Downloads\Operator's Manual SDAIISoftware.pdf",
# "Operator's Manual SDAIISoftware.txt")