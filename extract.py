from pypdf import PdfReader

def extract_head(filename):
    print(f"--- {filename} ---")
    try:
        reader = PdfReader(filename)
        text = reader.pages[0].extract_text()
        print(text[:1000])
        print("\n" + "="*50 + "\n")
    except Exception as e:
        print(f"Error: {e}")

extract_head('2407.11384v2.pdf')
extract_head('2503.03350v1.pdf')
