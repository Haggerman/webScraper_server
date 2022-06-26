import re

class Pattern:
    def __init__(self, text: str):
        self.text = text
        self.name = ""
        self.type = ""
        self.strippedPattern = ""
        self.multiple = True
        self.setName()
        self.setType()
        self.setStrippedPattern()

    def setName(self):
        if self.text.find("==>") > -1:
            self.name = self.text.split('==>',1)[1].strip()
            self.multiple = False
        elif self.text.find("===") > -1:
            self.name = self.text.split('===', 1)[1].strip()
            self.multiple = True
        else:
            self.name = "Incorrect pattern format"

    def setType(self):
        if self.text.find('>>>') > -1:
            self.type = re.search(">>>(.*[^==])==", self.text).group(1).strip()
            if self.type.find('atr') > -1:
                self.type = re.search("atr\((.*)\)", self.text).group(1).strip()
            else:
                self.type = "text"

        print(self.type)


    def setStrippedPattern(self):
        if self.text.find(">>>") > -1:
            self.strippedPattern = re.search("select:(.*)>>>", self.text).group(1).strip()

        else:
            self.strippedPattern = re.search("select:(.*[^==])==", self.text).group(1).strip()

        self.strippedPattern = self.strippedPattern.replace(" ","")

        if self.strippedPattern.find("tbody") > -1:
            self.strippedPattern = self.strippedPattern.replace("tbody>", "")


