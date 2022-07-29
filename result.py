from bs4 import BeautifulSoup

class Result:
    def __init__(self, title: str, type: "", multiple: bool):
        self.title = title
        self.result = ""
        self.type = type
        self.multiple = multiple

    def parse(self, html, pattern):
        html = BeautifulSoup(html, "lxml")
        try:
            if(self.type != ""):
                if (self.type == "text"):
                    self.result = [a.text.strip() for a in html.select(pattern)]
                else:
                    self.result = [a.get(self.type) for a in html.select(pattern)]
            else:
                self.result = [str(a) for a in html.select(pattern)]

            print(self.result)
            if not self.multiple and self.result:
                self.result = self.result[0]
        except:
            self.result = "ERROR: Vzor nebyl zadán ve správném formátu"

        return self.result




