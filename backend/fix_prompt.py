path = r'y:\Yash\Adlers Den\Part B v2\backend\pitches.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

normalized = content.replace('\r\n', '\n')

old = '6. Include a compelling subject line.\n\nReturn ONLY a valid JSON object with exactly two keys: "subject" and "body". No markdown, no explanations."""'
new = '6. Include a compelling subject line.\n7. Sign off EXACTLY as: "Best regards,\\nAdler\'s Den" -- do NOT use "[Your Name]", "[Name]", or any placeholder.\n\nReturn ONLY a valid JSON object with exactly two keys: "subject" and "body". No markdown, no explanations."""'

if old in normalized:
    normalized = normalized.replace(old, new, 1)
    print("Replaced successfully")
else:
    print("Pattern NOT found")
    idx = normalized.find("Include a compelling subject line")
    print(repr(normalized[idx-5:idx+200]))

result = normalized.replace('\n', '\r\n') if '\r\n' in content else normalized
with open(path, 'w', encoding='utf-8') as f:
    f.write(result)

print("File written")
