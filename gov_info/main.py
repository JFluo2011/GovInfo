from scrapy import cmdline


def main():
    # cmdline.execute("scrapy crawl wxgzh_task".split())
    cmdline.execute("scrapy crawl wxgzh".split())
    # cmdline.execute("scrapy crawl cdht".split())
    # cmdline.execute("scrapy crawl cdsjxw".split())
    # cmdline.execute("scrapy crawl scst".split())


if __name__ == '__main__':
    main()

