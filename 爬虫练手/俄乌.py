import asyncio
import json
from playwright.async_api import async_playwright
import time


class UkraineNewsScraper:
    def __init__(self):
        self.base_url = "https://www.bbc.com"
        self.total_pages = 12

    async def _click_pagination(self, page, page_num):
        await page.click(f'button:has-text("{page_num}")')

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            all_articles = []

            for current_page in range(1, self.total_pages + 1):
                if current_page == 1:
                    await page.goto(f"{self.base_url}/news/war-in-ukraine", timeout=60000)
                else:
                    await self._click_pagination(page, current_page)

                link_elements = await page.query_selector_all('a[data-testid="internal-link"]')
                news_urls = [
                    f"{self.base_url.rstrip('/')}{await link.get_attribute('href')}"
                    for link in link_elements
                    if "/news/articles/" in await link.get_attribute('href')
                ]

                news_urls = list(set(news_urls))

                for url in news_urls:
                    article_page = await browser.new_page()
                    retries = 3  # 设置重试次数
                    success = False

                    while retries > 0 and not success:
                        try:
                            await article_page.goto(url, timeout=60000)
                            await article_page.wait_for_selector('h1', timeout=20000)

                            article_data = {
                                "title": await article_page.text_content("h1"),
                                "author": await article_page.text_content("span.sc-b42e7a8f-7.khDNZq")
                                if await article_page.query_selector('span.sc-b42e7a8f-7.khDNZq')
                                else "Unknown",
                                "timestamp": await article_page.get_attribute("time", "datetime"),
                                "content": [await p.text_content()
                                            for p in await article_page.query_selector_all('p.sc-eb7bd5f6-0 fezwLZ')],
                                "url": url
                            }
                            all_articles.append(article_data)
                            print(f"第 {current_page} 页 | 已解析：{article_data['title'][:30]}...")
                            success = True

                        except Exception as e:
                            retries -= 1
                            print(f"解析失败，重试中 ({3 - retries}次重试): {e}")
                            time.sleep(3)  # 每次重试间隔3秒
                            if retries == 0:
                                print(f"多次尝试失败，跳过 {url}")

                        finally:
                            await article_page.close()


        with open("ukraine_news_full.json", "w", encoding="utf-8") as f:
                        json.dump(all_articles, f, ensure_ascii=False, indent=2)
                        print(f"全部完成！共爬取 {len(all_articles)} 篇文章")

        await browser.close()


if __name__ == "__main__":
    scraper = UkraineNewsScraper()
    asyncio.run(scraper.run())