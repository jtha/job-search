# import uuid
# import urllib.parse
# from playwright.async_api import async_playwright
# from bs4 import BeautifulSoup
# from markdownify import markdownify as md
# import time

# from ..utilities import setup_logging, get_logger

# setup_logging()
# logger = get_logger(__name__)



# scrollable_pane_selector = 'ul.semantic-search-results-list'
# job_cards_selector = 'li.semantic-search-results-list__list-item'
# title_selector = 'div.artdeco-entity-lockup__title strong'
# company_selector = 'div.artdeco-entity-lockup__subtitle > div'
# location_selector = 'div.artdeco-entity-lockup__caption > div'
# url_selector = 'a.job-card-job-posting-card-wrapper__card-link'
# salary_selector = 'div.artdeco-entity-lockup__metadata > div.mt1'
# next_button_selector = 'button[aria-label="View next page"]'

# def generate_search_url(keywords: str, geo_id: str = "105080838", distance: str = "25") -> str:
#     """
#     Generates a LinkedIn job search URL based on the provided keywords, location, and distance.
#     """
#     url_base = "https://www.linkedin.com/jobs/search-results/"
#     keywords_stringifed = urllib.parse.quote(keywords)
#     return f"{url_base}?distance={distance}&geoId={geo_id}&keywords={keywords_stringifed}"

# async def scrape_linkedin_multi_page(keywords: str, max_pages: int =10) -> dict:
#     """
#     Scrapes multiple pages of LinkedIn job listings, up to a specified maximum.
#     """
#     logger.info("Initializing browser and navigating to LinkedIn Jobs...")
#     job_run_id = str(uuid.uuid4())
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         context = await browser.new_context(
#             storage_state="../playwright/.auth/auth_1.json"
#         ) 
#         page = await context.new_page()

#         search_url = generate_search_url(keywords)
#         await page.goto(search_url, wait_until="load", timeout=10000)

#         all_job_meta = []
#         all_job_listings = []
#         counter = 0

#         for page_num in range(1, max_pages + 1):
#             logger.info(f"Scraping Page {page_num} ---")
#             timestamp = int(time.time())
            
#             try:
#                 await page.wait_for_selector(scrollable_pane_selector, timeout=10000)
#             except Exception:
#                 logger.exception("Could not find the job listings pane. Ending scrape.")
#                 break
                
#             scrollable_element = page.locator(scrollable_pane_selector)

#             # --- Robust Scrolling Logic (for each page) ---
#             last_height = 0
#             no_change_count = 0
#             patience = 2
#             while no_change_count < patience:
#                 await scrollable_element.evaluate('(element) => { element.scrollBy(0, 400); }')
#                 try:
#                     await page.wait_for_load_state("networkidle", timeout=500)
#                 except Exception:
#                     await page.wait_for_timeout(500)

#                 current_height = await scrollable_element.evaluate('(element) => element.scrollHeight')
#                 if current_height == last_height:
#                     no_change_count += 1
#                     logger.info(f"Scroll height stable. Patience count: {no_change_count}/{patience}")
#                 else:
#                     no_change_count = 0
#                 last_height = current_height

#             # --- Parsing Logic (for each page) ---
#             logger.info("Finished scrolling page. Parsing results...")
#             pane_html = await scrollable_element.inner_html()
#             soup = BeautifulSoup(pane_html, "lxml")
            
#             job_cards = soup.select(job_cards_selector)
#             page_jobs_count = 0
#             for card in job_cards:
#                 if not card.select_one('div.job-card-job-posting-card-wrapper'):
#                     continue
#                 job_data = {}
#                 job_meta = {}
#                 counter += 1
#                 def get_text(selector):
#                     element = card.select_one(selector)
#                     return element.get_text(strip=True) if element else None
#                 def get_attribute(selector, attr):
#                     element = card.select_one(selector)
#                     return element[attr] if element and element.has_attr(attr) else None

#                 job_data['title'] = get_text(title_selector)
#                 job_data['company'] = get_text(company_selector)
#                 job_data['location'] = get_text(location_selector)
#                 job_data['url'] = get_attribute(url_selector, 'href')
#                 salary_element = card.select_one(salary_selector)
#                 job_data['salary'] = salary_element.get_text(strip=True) if salary_element and '$' in salary_element.get_text() else None
                
#                 job_id = None
#                 job_url_direct = None

#                 if job_data['url']:
#                     try:
#                         parsed_url = urllib.parse.urlparse(job_data['url']) # type: ignore
#                         query_params = urllib.parse.parse_qs(parsed_url.query)
#                         if 'currentJobId' in query_params:
#                             job_id = query_params['currentJobId'][0]
#                             job_url_direct = f"https://www.linkedin.com/jobs/view/{job_id}"
#                     except Exception as e:
#                         logger.exception(f"Could not parse job ID from URL: {job_data['url']}. Error: {e}")
                
#                 job_data['job_id'] = job_id
#                 job_data['job_url_direct'] = job_url_direct

#                 job_meta['job_run_id'] = job_run_id
#                 job_meta['job_run_timestamp'] = timestamp
#                 job_meta['job_run_keywords'] = keywords
#                 job_meta['job_run_page_num'] = page_num
#                 job_meta['job_run_rank'] = counter
#                 job_meta['job_id'] = job_id



#                 if job_data['title']:
#                     all_job_listings.append(job_data)
#                     page_jobs_count += 1
#                     all_job_meta.append(job_meta)
            
#             logger.info(f"Found {page_jobs_count} jobs on this page.")

#             # --- Navigate to the Next Page ---
#             if page_num == max_pages:
#                 logger.info("Reached max pages limit. Ending scrape.")
#                 break

#             logger.info("Attempting to navigate to the next page...")
#             try:
#                 # This is a very specific and reliable selector for the "Next" button
#                 await page.locator(next_button_selector).click(timeout=5000)
#                 await page.wait_for_load_state("domcontentloaded", timeout=10000)
#                 logger.info("Successfully clicked 'Next' page.")
#             except Exception as e:
#                 logger.info(f"Could not find or click the 'Next' page button. Assuming end of results. Error: {e}")
#                 break

#         await browser.close()
#         return {
#             "job_run_meta": all_job_meta,
#             "job_listings": all_job_listings
#         }

# async def scrape_linkedin_job_page(url: str, min_length:int=200) -> str | None:
#     """
#     Scrapes a single LinkedIn job page for detailed information,
#     returning the description in Markdown format.
#     """
#     logger.info("Launching browser...")
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True) 
        
#         try:
#             context = await browser.new_context(
#                 storage_state="../playwright/.auth/auth_1.json"
#             )
#         except FileNotFoundError:
#             logger.exception("Error: Authentication file not found. Please run the playwright script to log in and create 'auth_1.json' first.")
#             await browser.close()
#             return "Error: Auth file not found."

#         page = await context.new_page()
        
#         logger.info(f"Navigating to {url}...")
        
#         try:
#             await page.goto(url, wait_until="domcontentloaded", timeout=5000)

#             # Wait for the main description container to be visible
#             description_locator = page.locator("div.jobs-description__content")
#             await description_locator.wait_for(state="visible", timeout=3000)

#             # Click the "see more" button if it exists to expand the description
#             try:
#                 see_more_button = page.get_by_role("button", name="Click to see more description")
#                 if await see_more_button.is_visible():
#                     print("Clicking 'see more' to expand description...")
#                     await see_more_button.click()
#                     # Give it a moment to expand
#                     await page.wait_for_timeout(500) 
#             except Exception as e:
#                 # This is not a critical error; the button may not be present on shorter descriptions
#                 logger.info("Could not find or click 'see more' button (might not be necessary).")

#             logger.info("Extracting job description HTML...")
#             job_desc_html = await description_locator.inner_html(timeout=3000)

#             # The `heading_style="ATX"` option ensures that <h1> becomes #, <h2> becomes ##, etc.
#             soup = BeautifulSoup(job_desc_html, "lxml")
#             plain_text = soup.get_text()
#             text_length = len(plain_text)

#             if text_length < min_length:
#                 await browser.close()
#                 logger.error(f"Job description is too short ({text_length} characters). Skipping this job.")
#                 return None

#             logger.info("Converting HTML to Markdown...")
#             job_description_md = md(job_desc_html, heading_style="ATX").strip()
            
#             await browser.close()
#             logger.info("Scraping complete.")
#         except Exception as e:
#             await browser.close()
#             logger.error(f"Error while scraping LinkedIn job page: {e}")
#             return None

#     return job_description_md