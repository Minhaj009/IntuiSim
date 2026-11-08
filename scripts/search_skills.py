import json

with open("F:/AntigravitySkills/skills_index.json", "r", encoding="utf-8-sig") as f:
    skills = json.load(f)

keywords = ["manim", "three", "youtube", "storytelling", "educational", "explainer", "animation", "pedagogy", "blue1brown"]
results = []
for s in skills:
    text = (s.get("name", "") + " " + s.get("description", "")).lower()
    for kw in keywords:
        if kw in text:
            results.append((kw, s["name"], s.get("description", "")))
            break

print(f"Total matching skills found: {len(results)}")
for kw, name, desc in results[:20]:
    print(f"[{kw}] {name}: {desc[:90]}...")
