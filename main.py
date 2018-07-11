from scrapy.cmdline import execute

spiders = [
    # 'scrapy crawl cdhrsip',
    'scrapy crawl wxgzh_task',
    # 'scrapy crawl wxgzh',
]


def main():
    for i in spiders:
        execute(i.split())


if __name__ == '__main__':
    main()
