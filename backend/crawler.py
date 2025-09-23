import urllib.parse
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .utilities import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

async def manual_extract(html_content: str, url: str):
    soup = BeautifulSoup(html_content, 'lxml')

    def get_text(selector, field_name: str | None = None):
        element = soup.select_one(selector)
        if not element:
            if field_name:
                logger.warning("Missing element for %s (selector: %s)", field_name, selector)
            else:
                logger.warning("Missing element for selector: %s", selector)
            return None
        return element.get_text(strip=True)

    job_id = None
    job_url_direct = None
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
                job_id = path_parts[-1] if path_parts else None
            job_url_direct = url
        else:
            parsed_url = urllib.parse.urlparse(url)  # type: ignore
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'currentJobId' in query_params:
                job_id = query_params['currentJobId'][0]
                job_url_direct = f"https://www.linkedin.com/jobs/view/{job_id}"
    except Exception as e:
        logger.exception(f"Could not parse job ID from URL: {url}. Error: {e}")
    finally:
        if not job_id:
            logger.error("Missing required job_id; could not be determined from url: %s", url)
            raise ValueError(f"Missing required element: job_id from url: {url}")
        if not job_url_direct:
            logger.error("Missing required job_url_direct; could not be determined from url: %s", url)
            raise ValueError(f"Missing required element: job_url_direct from url: {url}")

    job_data = {}

    buttons = soup.select("div.job-details-fit-level-preferences button")
    if not buttons:
        logger.warning("No 'div.job-details-fit-level-preferences button' elements found")

    try:
        primary_container = get_text(
            "div.job-details-jobs-unified-top-card__primary-description-container",
            "primary_description_container",
        )
        location = primary_container.split("·")[0] if primary_container else None
    except Exception:
        logger.warning("Unable to parse location from primary description container")
        location = None

    salary = None
    location_type = None
    if len(buttons) == 3:
        salary = buttons[0].get_text(strip=True)
        # Get visible span text from second button
        location_type_span = buttons[1].select_one("span.tvm__text")
        if location_type_span:
            location_type = location_type_span.get_text(strip=True)
        else:
            logger.warning("Missing 'span.tvm__text' inside second fit-level button for location_type")
    elif len(buttons) > 0:
        logger.warning("Unexpected number of fit-level buttons: %d (expected 3)", len(buttons))
        location_type_span = buttons[0].select_one("span.tvm__text")
        if location_type_span:
            location_type = location_type_span.get_text(strip=True)
        else:
            logger.warning("Missing 'span.tvm__text' inside first fit-level button for location_type")
    # else already logged when no buttons

    if location and location_type:
        location_final = f"{location} ({location_type})"
    elif location:
        logger.warning("location_type not found; only location available")
        location_final = location
    elif location_type:
        logger.warning("location not found; only location_type available")
        location_final = f"({location_type})"
    else:
        logger.warning("Both location and location_type are missing")
        location_final = None

    html_description = soup.select_one(".jobs-description__content")
    if not html_description:
        logger.error("Missing required '.jobs-description__content' element for job_description")
        raise ValueError("Missing required element: job_description (.jobs-description__content)")
    job_data['job_description'] = md(str(html_description), heading_style="ATX").strip()

    job_company = get_text(
        ".job-details-jobs-unified-top-card__company-name",
        "job_company",
    )
    if not job_company:
        logger.error("Missing required element for job_company (selector: .job-details-jobs-unified-top-card__company-name)")
        raise ValueError("Missing required element: job_company (.job-details-jobs-unified-top-card__company-name)")
    job_data['job_company'] = job_company

    job_title = get_text(
        "div.t-24.job-details-jobs-unified-top-card__job-title",
        "job_title",
    )
    if not job_title:
        logger.error("Missing required element for job_title (selector: div.t-24.job-details-jobs-unified-top-card__job-title)")
        raise ValueError("Missing required element: job_title (div.t-24.job-details-jobs-unified-top-card__job-title)")
    job_data['job_title'] = job_title
    job_data['job_url'] = url
    job_data['job_url_direct'] = job_url_direct
    job_data['job_salary'] = salary
    job_data['job_location'] = location_final
    job_data['job_id'] = job_id

    return job_data

