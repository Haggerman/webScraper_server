from bs4 import BeautifulSoup
from pattern import Pattern


class Result:
    def __init__(self, pattern):
        self.__pattern = pattern
        self.__parsedData = ""

    def parse(self, html):
        html = BeautifulSoup(html, "lxml")
        try:
            if (self.__pattern.type != ""):
                if (self.__pattern.type == "text"):
                    self.__parsedData = [a.text.strip() for a in html.select(self.__pattern.strippedPattern)]
                else:
                    self.__parsedData = [a.get(self.__pattern.type) for a in
                                         html.select(self.__pattern.strippedPattern)]
            else:
                self.__parsedData = [str(a) for a in html.select(self.__pattern.strippedPattern)]

            if not self.__pattern.multiple and self.__parsedData:
                self.__parsedData = self.__parsedData[0]
        except Exception as ex:
            self.__parsedData = "ERROR: Vzor nebyl zadán ve správném formátu"

        print(self.__parsedData)

        return self.__parsedData

    @property
    def parsedData(self):
        return self.__parsedData

    @property
    def pattern(self):
        return self.__pattern

    @pattern.setter
    def pattern(self, value):
        self.__pattern = value
