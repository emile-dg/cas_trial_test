import time
import os.path

from flask import Flask, send_file, render_template

# I will be using a library I built myself to ease my web scraping related projects
# You can check the author at https://pypi.org/project/titanscraper/
from titanscraper import TitanScraper
from titanscraper.processors import ReplaceWith, StringStripper

TARGET_SITE = "https://www.coursera.org"

CATEGORY_LINKS = [
    "/browse/data-science",
    "/browse/business",
    "/browse/computer-science",
    "/browse/personal-development",
    "/browse/information-technology",
    "/browse/language-learning",
    "/browse/health",
    "/browse/math-and-logic",
    "/browse/social-sciences",
    "/browse/physical-science-and-engineering",
    "/browse/arts-and-humanities",
]
CATEGORIES_PAGE_MAP = {}

application = Flask(__name__)


def convert_to_csv(headers: list[str], scraped_data: list[dict]) -> str:
    """convert the list of scraped data into a csv string"""
    result = f"{','.join(headers)}\n"  # the header line

    # write all the lines
    for item in scraped_data:
        line = ','.join(map(lambda v: f"\"{v}\"", [
            item.get('category_name', ""),
            item.get('course_name', ""),
            item.get('first_instructor', ""),
            item.get('course_description', ""),
            item.get('number_of_students', ""),
            item.get('number_of_ratings', ""),
        ]))  # create a comma seperated line with quotes
        result += f"{line}\n"

    return result


def write_to_file(file_path: str, data: str):
    """Used to save the csv file"""
    with open(file_path, "w+", encoding="utf-8") as file:
        file.write(data)


def get_category_courses(category_page: str) -> list:
    """Scraps a given category page to"""
    course_links_selector = "a.CardText-link"

    # rules define how the scraper will fetch and name the data from the pages
    course_scraping_rules = [
        {
            "name": "category_name",
            "selector": "a[aria-current=page][data-track-component=breadcrumb_link]",
        },
        {
            "name": "course_name",
            "selector": "h1.banner-title",
        },
        {
            "name": "first_instructor",
            "selector": ".instructor-count-display>span",
            "default": ""
        },
        {
            "name": "course_description",
            "selector": "div.description",
        },
        {
            "name": "number_of_students",
            "selector": ".rc-ProductMetrics strong>span",
            "postprocessors": [ReplaceWith(',', '')],  # just to remove the comma
        },
        {
            "name": "number_of_ratings",
            "selector": "[data-test=ratings-count-without-asterisks]>span",
            "postprocessors": [
                ReplaceWith(",", ""),
                ReplaceWith("ratings", ""),
                StringStripper,
            ],
        },
    ]

    scraper = TitanScraper()

    # for a given course category, get all the course links on the page
    page_courses = scraper.get_links_from_page(TARGET_SITE, category_page, course_links_selector)

    # then scrap all the data from the course pages
    data = scraper.scrap(page_courses, course_scraping_rules)

    return data


def init_category_page_map():
    """Initialize a dictionary of categories with their names and respective urls"""
    global CATEGORIES_PAGE_MAP, CATEGORY_LINKS

    for link in CATEGORY_LINKS:
        category_id = link.split("/browse/")[1]  # get the 2nd item which we
        CATEGORIES_PAGE_MAP[category_id] = {
            "name": category_id.replace("-", " ").title(),
            "page_url": link,
        }


# The following are the controllers of the api

@application.route("/")
def get_categories_route():
    categories = []
    for cat_key in CATEGORIES_PAGE_MAP.keys():
        value = CATEGORIES_PAGE_MAP[cat_key]
        categories.append({
            "id": cat_key,
            "name": value['name'],
        })

    return render_template("index.html", categories=categories)


@application.route("/categories/<category_id>/courses")
def get_category_course_route(category_id: str):
    if not category_id or category_id not in CATEGORIES_PAGE_MAP.keys():
        return "Page not Found", 404

    target_page = CATEGORIES_PAGE_MAP[category_id]
    courses = get_category_courses(target_page['page_url'])

    csv_headers = ["Category Name", "Course Name", "First Instructor Name", "Course Description",
                   "# of Students Enrolled", "# of Ratings"]
    csv_content = convert_to_csv(csv_headers, courses)

    # now let's export the csv
    export_file_name = f"{category_id}-{time.time()}.csv"
    export_file_path = f"./exports/{export_file_name}"
    write_to_file(export_file_path, csv_content)

    # send the file for download
    return send_file(export_file_path, download_name=export_file_name)


# Here starts the api
init_category_page_map()

# make sure the 'export' folder exists
if not os.path.exists('./exports'):
    os.mkdir('./exports')

# if we run the file directly
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=1880, debug=True)
