# -*- coding: utf-8 -*-
import logging

from gov_info.common.utils import WXInfo
# Scrapy settings for gov_info project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'gov_info'

SPIDER_MODULES = ['gov_info.spiders']
NEWSPIDER_MODULE = 'gov_info.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'gov_info (+http://www.yourdomain.com)'

# Obey robots.txt rules
# ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'gov_info.middlewares.GovInfoSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'gov_info.middlewares.GovInfoDownloaderMiddleware': 543,
#}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'gov_info.pipelines.GovInfoPipeline': 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
# log
LOG_ENABLED = True
# LOG_FILE = 'logs/youku.log'
# LOG_FILE = 'logs/weixin_ergeng.log'
LOG_ENCODING = 'utf-8'
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
LOG_STDOUT = False
LOG_SHORT_NAMES = False

WXINFOS = [
    WXInfo(name='成都高新', wx_id='oIWsFtzdz_uTS1UC9PKpVWMvDyS4', origin='cdht_wx', tag='区', location='成都市高新区',
           referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0'
                    '&tsn=0&ft=&et=&interation=&wxid=oIWsFtzdz_uTS1UC9PKpVWMvDyS4'
                    '&usip=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0')),
    WXInfo(name='成都工业和信息化', wx_id='oIWsFt_3i5qYBzUSy7UK7vm3EjpA', origin='cdgyhxxh_wx',
           tag='市', location='成都市',
           referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8'
                    '&query=%E6%88%90%E9%83%BD%E5%B7%A5%E4%B8%9A%E5%92%8C%E4%BF%A1%E6%81%AF%E5%8C%96'
                    '&tsn=0&ft=&et=&interation=&wxid=oIWsFt_3i5qYBzUSy7UK7vm3EjpA'
                    '&usip=%E6%88%90%E9%83%BD%E5%B7%A5%E4%B8%9A%E5%92%8C%E4%BF%A1%E6%81%AF%E5%8C%96')),
    WXInfo(name='企邦帮', wx_id='oIWsFt5bBYFhqeLQbPdiR_BYnIo0', origin='qbb_wx',
           tag='企邦帮', location='企邦帮',
           referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E4%BC%81%E9%82%A6%E5%B8%AE&tsn=0'
                    '&ft=&et=&interation=&wxid=oIWsFt5bBYFhqeLQbPdiR_BYnIo0&usip=%E4%BC%81%E9%82%A6%E5%B8%AE'))
]

try:
    from gov_info.common.config import *
except Exception as err:
    raise err
