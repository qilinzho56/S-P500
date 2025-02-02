import requests
import lxml.html
import pandas as pd
import re
from datetime import date


def headlines(headers, company_list, max_days):
    """
    Scrape the stock page of each company and reformat the date information
    from http://finviz.com.

    Parameters
    ----------
    headers: HTTP header
    company_list: a list of companies of interest
    max_days: days that the user want to scrape util the current date

    Returns
    -------
    news_df: a dataframe including the date as index, time, company, headline and and url link
    """
    data = []
    date_pattern = re.compile(r"[A-Za-z]+")

    for company in company_list:
        company_url = headers["Referer"] + company
        response = requests.get(company_url, headers=headers)
        print(response)
        root = lxml.html.fromstring(response.text)
        news_rows = root.xpath("//table[@id='news-table']/tr")

        cur_date = None
        cur_time = None
        days_visited = 0

        for row in news_rows:
            time_extract = row.xpath("./td")[0].text_content()
            if re.match(date_pattern, time_extract.split()[0]):
                if "Today" in time_extract:
                    cur_date = date.today()
                    cur_date = cur_date.strftime("%b-%d-%y")
                    cur_time = time_extract.split()[1]
                else:
                    cur_date = time_extract.split()[0]
                    cur_time = time_extract.split()[1]

                days_visited += 1
            else:
                if not time_extract.split()[0]:
                    cur_time = time_extract.split()[1]
                else:
                    cur_time = time_extract.split()[0]

                if days_visited > max_days:
                    print(f"Maximum Days Reached For {company}")
                    break

            headline = row.xpath(".//a[@target='_blank']/text()")

            if headline:
                headline = headline[0]
                url = row.xpath(".//a[@target='_blank']/@href")
                data.append([cur_date, cur_time, company, headline, url[0]])
            else:
                print("Private News")

        news_df = pd.DataFrame(
            data, columns=["Date", "Time", "Company", "Headline", "URL"]
        )
        news_df = news_df.set_index("Date")
        news_df.index = pd.to_datetime(news_df.index, format="%b-%d-%y")

    return news_df


if __name__ == "__main__":
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://finviz.com/quote.ashx?t=",
    }
    print(headlines(headers, ["AAPL"], max_days=5))
