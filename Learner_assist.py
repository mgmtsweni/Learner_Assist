import requests
import pdfplumber
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time




# Step 1: Collect User Input
def get_user_input():
    print("Enter up to 3 courses you'd like to apply for:")
    courses = [input(f"Course {i+1}: ").strip() for i in range(3)]


    print("\nEnter your matric results (subject and percentage). Type 'done' to finish:")
    matric_results = {}
    while True:
        subject = input("Subject: ")
        if subject.lower() == 'done':
            break
        try:
            percentage = int(input("Percentage: "))
            matric_results[subject.strip()] = percentage
        except ValueError:
            print("Invalid percentage. Please try again.")


    return courses, matric_results


# Step 2: Search for course admission requirements
def search_pdf_keyword(pdf_url, keyword):
    try:
        # Download the PDF
        response = requests.get(pdf_url)
        response.raise_for_status()
        with open("temp.pdf", "wb") as f:
            f.write(response.content)
       
        # Extract text from all pages
        text = ""
        with pdfplumber.open("temp.pdf") as pdf:
            for page in pdf.pages:
                text += page.extract_text() or "" + "\n"
       
        # Search for keyword
        count = text.lower().count(keyword.lower())
       
        # Extract APS score (looking for patterns like "APS of X" or "minimum APS of X")
        aps_match = re.search(r"(?:APS of|minimum APS of)\s*(\d+)", text, re.IGNORECASE)
        aps_score = aps_match.group(1) if aps_match else "Not found"
       
       
        # Compile results
        results = {
            "keyword": keyword,
            "occurrences": f"'{keyword}' found {count} time(s)",
            "aps_score": aps_score,
        }
       
        return results
   
    except Exception as e:
        return f"Error: {e}"




# Step 4: Calculate APS from results
def calculate_aps(results):
    total = 0
    for score in results.values():
        if score >= 80:
            total += 7
        elif score >= 70:
            total += 6
        elif score >= 60:
            total += 5
        elif score >= 50:
            total += 4
        elif score >= 40:
            total += 3
        elif score >= 30:
            total += 2
        elif score >= 0:
            total += 1
    return total




# Main function to run the agent
def run_agent():
    courses, matric_results = get_user_input()


    universities = "https://tut.ac.za/images/prospectus/Part2_Arts-and-Design_Prospectus.pdf"
    keywords = [course for course in courses if course]  # ignore empty strings


    all_results = {}


    for keyword in keywords:
        result = search_pdf_keyword(universities, keyword)
        if isinstance(result, dict):
            all_results[keyword] = result
        else:
            print(f"Error while searching for '{keyword}': {result}")


    # Print results
    for key, value in all_results.items():
        for subkey, subval in value.items():
            print(f"{subkey}: {subval}")
        print()


    # Use one course's APS for comparison (assume the first one for now)
    first_result = list(all_results.values())[0] if all_results else None
    if first_result:
        aps_str = first_result.get("occurrences", "")
        aps_score = first_result.get("aps_score", "Not found")
        try:
            course_aps = int(aps_score)
        except ValueError:
            print("Could not extract APS requirement.")
            return
        user_aps = calculate_aps(matric_results)
        print(f"\nYour APS: {user_aps}\n")
        if user_aps >= course_aps:
            print("You qualify for the course.")
        else:  
            print("You do not qualify for the course.")
    else:
        print("No valid results found.")




if __name__ == "__main__":
    run_agent()
