import os

with open("README.template.md", "r") as f:
    main_readme = f.read()

main_folder = "streamlitextras"
module_folders = [f for f in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, f))]

def process_readme(readme):
    """
    """
    sections = readme.split("\n#")

    sections_processed = []
    for section in sections:
        sub_sections = section.split("\n")
        section_title = sub_sections[0].strip()
        section_body = sub_sections[1:]
        section_body = "\n".join(section_body).strip()
        code_snippet = section_body.split("``") if "```" in section_body else None
        out_snippet = None
        if code_snippet:
            for i, part in enumerate(code_snippet):
                if part.startswith("`Python"):
                    out_snippet = f"""``{"".join(code_snippet[i:i+1])}```"""
                    break
        sections_processed.append((section_title, section_body, out_snippet, sub_sections, section))

    return sections_processed

for module_folder in module_folders:
    module_readme_file = os.path.join(str(main_folder), module_folder, "README.md")
    print(module_readme_file)
    if not os.path.exists(module_readme_file):
        continue
    with open(module_readme_file, "r") as f:
        readme = f.read()
    sections = process_readme(readme)
    inserted_title = sections[0][0].replace("# Streamlit Extras ", "")
    inserted_description = sections[0][0]
    inserted_usage = sections[1][1]
    inserted_usage = sections[1][2]

    title_match = f"@@{inserted_title.upper()}".replace(" ", "").strip()
    footer = f"\n\nSee the [package readme]({module_readme_file}) or API docs for more details.\n"
    print(module_readme_file, title_match, inserted_usage[:20])
    main_readme = main_readme.replace(title_match, inserted_usage+footer)

with open("README.md", "w") as f:
    f.write(main_readme)