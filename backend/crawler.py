import urllib.parse
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .utilities import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

async def manual_extract(html_content: str, url: str):
    soup = BeautifulSoup(html_content, 'lxml')

    def get_text(selector):
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None

    try:
            if url.startswith("https://www.linkedin.com/jobs/view/"):
                # Extract job_id from the path
                parsed_url = urllib.parse.urlparse(url)
                path_parts = parsed_url.path.strip('/').split('/')
                if len(path_parts) >= 3 and path_parts[0] == "jobs" and path_parts[1] == "view":
                    job_id = path_parts[2]
                elif len(path_parts) >= 2 and path_parts[0] == "jobs" and path_parts[1] == "view":
                    job_id = path_parts[-1]
                else:
                    job_id = path_parts[-1]
                job_url_direct = url
            else:
                parsed_url = urllib.parse.urlparse(url) # type: ignore
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if 'currentJobId' in query_params:
                    job_id = query_params['currentJobId'][0]
                    job_url_direct = f"https://www.linkedin.com/jobs/view/{job_id}"
    except Exception as e:
        logger.exception(f"Could not parse job ID from URL: {url}. Error: {e}")

    job_data = {}

    buttons = soup.select("div.job-details-fit-level-preferences button")

    try:
        primary_container = get_text("div.job-details-jobs-unified-top-card__primary-description-container")
        location = primary_container.split("·")[0] # type: ignore
    except Exception:
        location = None

    if len(buttons) == 3:
        salary = buttons[0].get_text(strip=True)
        # Get visible span text from second button
        location_type_span = buttons[1].select_one("span.tvm__text")
        location_type = location_type_span.get_text(strip=True) if location_type_span else None
    else:
        salary = None
        location_type_span = buttons[0].select_one("span.tvm__text")
        location_type = location_type_span.get_text(strip=True) if location_type_span else None

    location_final = f"{location} ({location_type})"

    html_description = soup.select_one(".jobs-description__content")
    job_data['job_description'] = md(str(html_description), heading_style="ATX").strip()
    job_data['job_company'] = get_text(".job-details-jobs-unified-top-card__company-name")
    job_data['job_title'] = get_text("div.t-24.job-details-jobs-unified-top-card__job-title")
    job_data['job_url'] = url
    job_data['job_url_direct'] = job_url_direct
    job_data['job_salary'] = salary
    job_data['job_location'] = location_final
    job_data['job_id'] = job_id

    return job_data

