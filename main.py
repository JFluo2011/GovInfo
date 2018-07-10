from scrapy.cmdline import execute

spiders = [
    'scrapy crawl cdhrsip',
]


def main():
    for i in spiders:
        execute(i.split())


if __name__ == '__main__':
    main()
