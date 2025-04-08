import requests
import re
from uagents import Agent, Context, Protocol, Model
from uagents.setup import fund_agent_if_low
from typing import Dict, List
import subprocess
import sys




def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


install("pdfplumber")
import pdfplumber


# Define input data model for DeltaV
class CourseQualificationRequest(Model):
    courses: List[str]  # List of up to 3 course names
    matric_results: Dict[str, int]  # Dictionary of subject: percentage


# Define output data model for DeltaV
class CourseQualificationResponse(Model):
    results: Dict[str, dict]  # Course search results
    user_aps: int  # User's calculated APS
    qualification_status: Dict[str, str]  # Qualification status per course


# Initialize the agent
agent = Agent(
    name="CourseQualificationAgent",
    seed="course_qualification_seed",
    endpoint=["http://127.0.0.1:8000/submit"],  # Adjust endpoint as needed
)


# Fund the agent if low on funds (Fetch.ai requirement)
fund_agent_if_low(agent.wallet.address())


# Define the protocol
qualification_protocol = Protocol("CourseQualificationProtocol")


# Search for course admission requirements in the PDF
def search_pdf_keyword(pdf_url: str, keyword: str) -> dict:
    try:
        response = requests.get(pdf_url, timeout=10)
        response.raise_for_status()
        with open("temp.pdf", "wb") as f:
            f.write(response.content)
       
        text = ""
        with pdfplumber.open("temp.pdf") as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
       
        count = text.lower().count(keyword.lower())
        aps_match = re.search(r"(?:APS of|minimum APS of)\s*(\d+)", text, re.IGNORECASE)
        aps_score = int(aps_match.group(1)) if aps_match else None
       
        return {
            "keyword": keyword,
            "occurrences": f"'{keyword}' found {count} time(s)",
            "aps_score": aps_score if aps_score else "Not found"
        }
    except Exception as e:
        return {"error": f"Error searching for '{keyword}': {str(e)}"}


# Calculate APS from matric results
def calculate_aps(matric_results: Dict[str, int]) -> int:
    total = 0
    for score in matric_results.values():
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


# Protocol handler for DeltaV requests
@qualification_protocol.on_message(model=CourseQualificationRequest, replies=CourseQualificationResponse)
async def handle_qualification_request(ctx: Context, sender: str, msg: CourseQualificationRequest):
    ctx.logger.info(f"Received request from {sender} for courses: {msg.courses}")
   
    # Filter out empty course names
    keywords = [course for course in msg.courses if course.strip()]
    pdf_url = "https://tut.ac.za/images/prospectus/Part2_Arts-and-Design_Prospectus.pdf"
    all_results = {}
    qualification_status = {}


    # Search for each course in the PDF
    for keyword in keywords:
        result = search_pdf_keyword(pdf_url, keyword)
        if "error" not in result:
            all_results[keyword] = result
        else:
            all_results[keyword] = {"error": result["error"]}


    # Calculate user's APS
    user_aps = calculate_aps(msg.matric_results)


    # Determine qualification status for each course
    for keyword, result in all_results.items():
        if "aps_score" in result and isinstance(result["aps_score"], int):
            course_aps = result["aps_score"]
            qualification_status[keyword] = (
                "You qualify" if user_aps >= course_aps else "You do not qualify"
            )
        else:
            qualification_status[keyword] = "APS requirement not found"


    # Prepare and send response
    response = CourseQualificationResponse(
        results=all_results,
        user_aps=user_aps,
        qualification_status=qualification_status
    )
    await ctx.send(sender, response)


# Include the protocol in the agent and publish the manifestw
agent.include(qualification_protocol, publish_manifest=True)


# Run the agent
if __name__ == "__main__":
    agent.run()

