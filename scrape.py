import scrapelib
import lxml.html

from typing import Dict, Any, Optional, Generator
from typing_extensions import Literal


class ASPXScraper(scrapelib.Scraper):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:74.0) Gecko/20100101 Firefox/74.0"

    def session_secrets(self, page: lxml.html.HtmlElement) -> Dict[str, Any]:

        payload: Dict[str, Any] = {}
        payload['__EVENTARGUMENT'] = None
        payload['__VIEWSTATE'] = page.xpath(
            "//input[@name='__VIEWSTATE']/@value")[0]
        try:
            payload['__EVENTVALIDATION'] = page.xpath(
                "//input[@name='__EVENTVALIDATION']/@value")[0]
        except IndexError:
            pass

        try:
            payload['__VIEWSTATEGENERATOR'] = page.xpath(
                "//input[@name='__VIEWSTATEGENERATOR']/@value")[0]
        except IndexError:
            pass

        return(payload)

    def lxmlize(self,
                url: str,
                payload: Optional[Dict[str, Any]] = None) -> lxml.html.HtmlElement:
        '''
        Gets page and returns as XML
        '''
        if payload:
            response = self.post(url, payload)
        else:
            response = self.get(url)
        entry = response.text
        page = lxml.html.fromstring(entry)
        page.make_links_absolute(url)
        return page


class TaxAgencyScraper(ASPXScraper):

    REPORT_TYPE = {'agency rate': '1',
                   'agency eav': '2',
                   'new property': '3',
                   'exemption detail': '4'}

    def search(self,
               year: int,
               report_type: Literal['agency rate',
                                    'agency eav',
                                    'new property',
                                    'exemption detail']):
        search_url = 'https://taxreportsearch.cookcountyclerk.com/RevisedTaxReportSearch.aspx'

        # visit search page in order to get intialize aspx state
        page = self.lxmlize(search_url)

        for prefix in ('0', '1', '9'):

            payload = {'ctl00$content$ddlReportYear': str(year),
                       'ctl00$content$ddlReportType': self.REPORT_TYPE[report_type],
                       'ctl00$content$txtAgencyNum1': prefix,
                       'ctl00$content$btnSearch': 'Search'}
            payload.update(self.session_secrets(page))

            # search for year and report_type and prefix
            page = self.lxmlize(search_url,
                                payload)

            num_results_str, = page.xpath("//span[@id='ctl00_content_recordCount']/text()")
            num_results = int(num_results_str.split()[0])

            # get ready to iterate through results
            payload = {'ctl00$content$btnTextSelected': 'View Selected as Text'}
            payload.update(self.session_secrets(page))

            self.post(search_url, payload)

            yield from self.text_results(num_results)

    def text_results(self, num_results: int) -> Generator[str, None, None]:

        report_url = 'https://taxreportsearch.cookcountyclerk.com/ReportContent.aspx?index={}'

        for i in range(num_results):

            page = self.lxmlize(report_url.format(i))

            text, = page.xpath('//pre/text()')
            yield text

    def scrape(self) -> Generator[str, None, None]:

        for year in range(2018, 2005, -1):
            for report_type in self.REPORT_TYPE:
                yield from self.search(year, report_type)  # type: ignore


if __name__ == '__main__':

    scraper = TaxAgencyScraper()
    for report in scraper.search(2018, 'agency rate'):
        print(report)
        input()
