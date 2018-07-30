from scrapy.cmdline import execute

spiders = [
    # 'scrapy crawl cdhrsip',
    # 'scrapy crawl cdht',
    # 'scrapy crawl cdibi',
    # 'scrapy crawl cdkjfw',
    # 'scrapy crawl cdmbc',
    # 'scrapy crawl cdsjxw',
    # 'scrapy crawl cdsme',
    # 'scrapy crawl cdst',
    # 'scrapy crawl csidc',
    # 'scrapy crawl innocom',
    # 'scrapy crawl scst',
    'scrapy crawl sczwfw',
    # 'scrapy crawl wxgzh_task',
    # 'scrapy crawl wxgzh',
    # 'scrapy crawl zgzzscxd',
]


def main():
    for i in spiders:
        execute(i.split())


if __name__ == '__main__':
    main()
