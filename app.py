import io
import json
import os
import random
import pandas as pd
from pandas.io.json import json_normalize
from flask import Flask, jsonify, session, request
from flask_session import Session
from flask_restful import Api, Resource, reqparse
from pattern import Pattern
from result import Result
import headerRotation
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import time
from flask_cors import CORS, cross_origin
from bs4 import BeautifulSoup
import requests
import sys
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "12345"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CORS(app, support_credentials=True)

api = Api(app)
htmls = []

#Overuje, ze je request spravne
url_put_args = reqparse.RequestParser()
url_put_args.add_argument("url", type=str, help="URL" )
url_put_args.add_argument("mail", type=str, help="mail" )
url_put_args.add_argument("pattern", type=str, help="Parsing pattern" )
url_put_args.add_argument("id", type=str, help="URL id" )
url_put_args.add_argument("proxys", type=list, help="Proxy URLs" )

class URL(Resource):
    @cross_origin(supports_credentials=True)
    def delete(self):
        args = url_put_args.parse_args()
        id = int(args["id"])
        if "htmls" in session:
            newList = [html for html in session["htmls"] if int(html["id"]) != id]
            session["htmls"] = newList
        else:
            session["htmls"] = []

        return jsonify(session["htmls"]), 200

    @cross_origin(supports_credentials=True)
    def get(self):
        if "htmls" in session and len(session["htmls"]) > 0:
            session["htmls"]
        else:
            addSampleData()

        response = session["htmls"]
        return jsonify(response)

    @cross_origin(supports_credentials=True)
    def post(self):
        args = url_put_args.parse_args()
        url = args["url"]
        id = args["id"]
        header = headerRotation.rotateHeaders()
        try:
            result = requests.get(url, headers=header)
            html = BeautifulSoup(result.text, "lxml")
            html = html.prettify()
            if "htmls" in session:
                session["htmls"].append({"html": html, "id": id, "url": url})
            else:
                session["htmls"] = []
                session["htmls"].append({"html": html, "id": id, "url": url})
            response = jsonify(str(html))
        except:
            response = "Adresa neodpovídá", 500

        return response

api.add_resource(URL, "/url")


class Parser(Resource):
    @cross_origin(supports_credentials=True)
    def post(self):
        results = []
        args = url_put_args.parse_args()
        pattern = args["pattern"]
        session["patterns"] = pattern
        if "htmls" in session:
           try:
                patterns = getAllPatterns(pattern)
                if len(patterns)>0:
                    for p in patterns:
                        for html in session["htmls"]:
                            result = Result(p.name, p.type, p.multiple)
                            r = result.parse(html["html"],p.strippedPattern)
                            results.append({"title": p.name, "result": r, "id":html["id"]})
                else:
                    results.append({"title": "error", "result": "ERROR: Vzor nebyl zadán ve správném formátu", "id": -1})

           except:
               results.append({"title": "error", "result" : "ERROR: Vzor nebyl zadán ve správném formátu", "id": -1})

        return jsonify(results)

api.add_resource(Parser, "/parser")


class Patterns(Resource):
    @cross_origin(supports_credentials=True)
    def get(self):
        if "patterns" in session and len(session["patterns"]) > 0:
            print("patterns")
            print(session["patterns"])
        else:
           addSamplePatterns()

        response = session["patterns"]
        return jsonify(response)

api.add_resource(Patterns, "/getPatterns")

class File(Resource):
    @cross_origin(supports_credentials=True)
    def post(self):
        f = request.files['file']
        mail = request.form['mail']
        type = request.form['type']
        patterns = []
        proxys = []
        df=""
        if "patterns" in session:
            patterns = getAllPatterns(session["patterns"])
        if "proxys" in session:
            proxys = session["proxys"]

        try:
            df = pd.read_csv(f.stream)
            response = jsonify("Data uspesne predana")
        except:
            response = jsonify("Soubor je ve spatnem formatu")

        def bulkExtraction(df, e, patt, proxy,type):
            df_list = df.values.tolist()
            results = getAllResutlts(df_list, patt,proxy)
            try:
                newMail(results, e, type)
            except IOError:
                print("mail error")

        if len(df) > 0:
            thread = Thread(target=bulkExtraction, args=(df,mail,patterns,proxys,type))
            thread.start()

        return response


api.add_resource(File, "/uploadFile")


class Proxy(Resource):
    @cross_origin(supports_credentials=True)
    def post(self):
        proxys = request.json['proxys']
        if "proxys" in session:
            session["proxys"] = proxys

        else:
            session["proxys"] = []
            session["proxys"] = proxys

        return jsonify(str(proxys))

    @cross_origin(supports_credentials=True)
    def get(self):
        response = ""
        if "proxys" in session and len(session["proxys"]) > 0:
            response = session["proxys"]

        return jsonify(response)

api.add_resource(Proxy, "/proxy")

def getAllPatterns(pattern):
    namedPatterns = set()
    patterns = pattern.split(";")
    for subPattern in patterns:
        if subPattern.find('==') > -1:
            namedPatterns.add(Pattern(subPattern))

    return namedPatterns

def getAllResutlts(addressList, patterns, proxys):
    results = []
    if len(patterns)>0:
        for i,a in enumerate(addressList):
            patternResult = {'url':a[0]}
            header = headerRotation.rotateHeaders()
            a=a[0]
            if len(proxys)>0:
                proxy = proxys[random.randint(len(proxys))]["url"]
                response = requests.get(a, proxies={"http": proxy, "https": proxy}, headers=header)
                for p in patterns:
                        result = Result(p.name, p.type, p.multiple)
                        r = result.parse(response.text,p.strippedPattern)
                        patternResult[p.name]=r
            else:
                response = requests.get(a, headers=header)
                for p in patterns:
                        result = Result(p.name, p.type, p.multiple)
                        r = result.parse(response.text, p.strippedPattern)
                        patternResult[p.name] = r
            time.sleep(0.5)
            results.append(patternResult)
    return results

def addSampleData():
    session["htmls"] = []
    session["htmls"].append({
        "html": """<!DOCTYPE html>
<html>
<head>
<title>Page Title</title>
</head>
<body>

<h1>My First Heading</h1>
<p>My first paragraph.</p>
<p>My second paragraph.</p>
<p>My third paragraph.</p>
<div class="block">
    <p>Block of code</p>
    <a href="127.0.0.1">Link</a>
</div>
</body>
</html> """,
        "id": 0,
        "url": "ukazkova adresa"})

def addSamplePatterns():
    session["patterns"] = """select: title >>> text === titulek;
select: body > h1 >>> text === nadpis;
select: body > div >>> atr(class) ==> trida;
select: body > p === odstavce;
    """

def newMail(df, mail, type):
    message = MIMEMultipart()
    message['Subject'] = "Web scraping data"
    message['From'] = os.getenv("MAIL")
    message['To'] = mail

    if type=="CSV":
        bio = io.BytesIO()
        df = json_normalize(df)
        df.to_csv(bio,mode="wb")
        bio.seek(0)
        attachement = MIMEApplication(bio.getvalue(),Name="Results")
        attachement.add_header("Content-Disposition", "attachement", filename="Results.csv")
    else:
        json_payload = json.dumps(df,ensure_ascii=False).encode('utf8')
        attachement = MIMEApplication(json_payload,Name="Results")
        attachement.add_header("Content-Disposition", "attachement", filename="Results.json")
        attachement.add_header('Content-Type','application/json')

    body = MIMEText("Here is your data", 'plain')
    message.attach(body)
    message.attach(attachement)
    with smtplib.SMTP("smtp-relay.sendinblue.com", 587) as server:
        server.starttls()
        server.login(os.getenv("MAIL"),os.getenv("PASSWORD"))
        server.sendmail(os.getenv("MAIL"),mail, message.as_string())


if __name__ == "__main__":
    app.run(debug=True)



