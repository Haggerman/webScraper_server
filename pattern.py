import re


class Pattern:
    def __init__(self, text: str):
        self.__text = text
        self.__name = ""
        self.__type = ""
        self.__strippedPattern = ""
        self.__multiple = True
        self.__findName()
        self.__findType()
        self.__createStrippedPattern()

    def __findName(self):
        if self.__text.find("==>") > -1:
            self.__name = self.__text.split('==>', 1)[1].strip()
            self.__multiple = False
        elif self.__text.find("===") > -1:
            self.__name = self.__text.split('===', 1)[1].strip()
            self.__multiple = True
        else:
            self.__name = "ERROR: Vzor nebyl zadán ve správném formátu"

    def __findType(self):
        if self.__text.find('>>>') > -1:
            self.__type = re.search(">>>(.*[^==])==", self.__text).group(1).strip()
            if self.__type.find('atr') > -1:
                self.__type = re.search("atr\((.*)\)", self.__text).group(1).strip()
            else:
                self.__type = "text"

    def __createStrippedPattern(self):
        if self.__text.find(">>>") > -1:
            self.__strippedPattern = re.search("select:(.*)>>>", self.__text).group(1).strip()

        else:
            self.__strippedPattern = re.search("select:(.*[^==])==", self.__text).group(1).strip()

        self.__strippedPattern = self.__strippedPattern.replace(" ", "")

        if self.__strippedPattern.find("tbody") > -1:
            self.__strippedPattern = self.__strippedPattern.replace("tbody>", "")

    @property
    def name(self):
        return self.__name

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, value):
        self.__name = value

    @property
    def type(self):
        return self.__type

    @property
    def multiple(self):
        return self.__multiple

    @property
    def strippedPattern(self):
        return self.__strippedPattern
