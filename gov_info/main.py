from scrapy import cmdline


def main():
    # cmdline.execute("scrapy crawl wxgzh_task".split())
    cmdline.execute("scrapy crawl wxgzh".split())


if __name__ == '__main__':
    main()

