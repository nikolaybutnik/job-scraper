import scrapy


class LinkedInJobsSpider(scrapy.Spider):
    name = "linkedin_jobs"
    api_url = "https://www.linkedin.com/jobs/search?keywords=angular&location=canada"

    def start_requests(self):
        first_job_on_page = 0
        first_url = self.api_url + "&start=" + str(first_job_on_page)

        yield scrapy.Request(
            url=first_url,
            callback=self.parse_job,
            meta={"first_job_on_page": first_job_on_page},
        )

    def parse_job(self, response):
        first_job_on_page = response.meta["first_job_on_page"]
        job_item = {}
        jobs = response.css("li")

        num_jobs_returned = len(jobs)
        print("-------")
        print("first_job_on_page", first_job_on_page)
        print("-------")

        for job in jobs:
            job_item = {}

            job_item["job_title"] = job.css("h3::text").get(default="not-found").strip()
            job_item["job_detail_url"] = (
                job.css(".base-card__full-link::attr(href)")
                .get(default="not-found")
                .strip()
            )
            job_item["job_listed"] = (
                job.css("time::text").get(default="not-found").strip()
            )

            job_item["company_name"] = (
                job.css("h4 a::text").get(default="not-found").strip()
            )
            job_item["company_link"] = job.css("h4 a::attr(href)").get(
                default="not-found"
            )
            job_item["company_location"] = (
                job.css(".job-search-card__location::text")
                .get(default="not-found")
                .strip()
            )

            yield job_item

        if num_jobs_returned > 0:
            first_job_on_page = int(first_job_on_page) + 25
            next_url = self.api_url + "&start=" + str(first_job_on_page)

            yield scrapy.Request(
                url=next_url,
                callback=self.parse_job,
                meta={"first_job_on_page": first_job_on_page},
            )
