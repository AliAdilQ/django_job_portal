"""A tiny valid PDF generator for fictional seed resumes; no extra dependency."""
def resume_pdf(name, headline):
    def escape(value):
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = [name, headline, "Fictional demonstration resume - Django Job Portal", "Skills: Python, collaboration, problem solving", "Experience: Building thoughtful digital products", "Contact details are available in the applicant profile."]
    stream = "BT /F1 18 Tf 50 760 Td "
    for index, line in enumerate(lines):
        if index:
            stream += "0 -32 Td /F1 11 Tf "
        stream += f"({escape(line)}) Tj "
    stream += "ET"
    stream_bytes = stream.encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream_bytes)).encode() + b" >>\nstream\n" + stream_bytes + b"\nendstream",
    ]
    result = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(result)
    result += b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        result += f"{offset:010d} 00000 n \n".encode()
    result += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return result
