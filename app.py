import io
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
    def get(self):
        args = url_put_args.parse_args()
        url = args
        return jsonify(url.text)

    @cross_origin(supports_credentials=True)
    def put(self):
        args = url_put_args.parse_args()
        url = args["url"]
        id = args["id"]
        header = headerRotation.rotateHeaders()
        result = requests.get(url, headers=header)
        print(result.text)
        html = BeautifulSoup(result.text, "lxml")
        html = html.prettify()
        if "htmls" in session:
            print("session existuje")
            session["htmls"].append({"html": html, "id": id, "url": url})

        else:
            print("session neexistuje")
            session["htmls"] = []
            session["htmls"].append({"html": html, "id": id, "url": url})


        print(session["htmls"])
        return jsonify(str(html)), 200

api.add_resource(URL, "/url")

class DeleteURL(Resource):
    def delete(self):
        args = url_put_args.parse_args()
        id = int(args["id"])
        if "htmls" in session:
            newList = [html for html in session["htmls"] if int(html["id"]) != id]
            session["htmls"] = newList

        return "Done", 200


api.add_resource(DeleteURL, "/deleteUrl")


class Parser(Resource):
    @cross_origin(supports_credentials=True)
    def get(self):
        args = url_put_args.parse_args()
        url = args
        return jsonify(url.text), 200

    @cross_origin(supports_credentials=True)
    def put(self):
        results = []
        args = url_put_args.parse_args()
        pattern = args["pattern"]
        session["patterns"] = pattern
        if "htmls" in session:
           print("toto jsou sessions")
           print(session["htmls"])
           try:
                patterns = getAllPatterns(pattern)
                for p in patterns:
                    for html in session["htmls"]:
                        result = Result(p.name, p.type, p.multiple)
                        r = result.parse(html["html"],p.strippedPattern)
                        results.append({"title": p.name, "result": r, "id":html["id"]})
           except:
               results.append({"title": "error", "result" : "ERROR: Vzor nebyl zadán ve správném formátu", "id": -1})

        return jsonify(results), 200

api.add_resource(Parser, "/parser")


class ExistingPatterns(Resource):
    @cross_origin(supports_credentials=True)
    def get(self):
        if "patterns" in session and len(session["patterns"]) > 0:
            print("patterns")
            print(session["patterns"])
        else:
           addSamplePatterns()

        response = session["patterns"]
        return jsonify(response), 200

api.add_resource(ExistingPatterns, "/getPatterns")


class ExistingUrls(Resource):
    @cross_origin(supports_credentials=True)
    def get(self):
        if "htmls" in session and len(session["htmls"]) > 0:
            print("htmls")
            print(session["htmls"])
        else:
            addSampleData()

        response = session["htmls"]
        return jsonify(response), 200

api.add_resource(ExistingUrls, "/getURLs")

class UploadFile(Resource):
    @cross_origin(supports_credentials=True)
    def post(self):
        f = request.files['file']
        mail = request.form['mail']
        patterns = []
        proxys = []
        if "patterns" in session:
            patterns = getAllPatterns(session["patterns"])
        if "proxys" in session:
            proxys = session["proxys"]

        def bulkExtraction(f, e, patt, proxy):
            df = pd.read_csv(f.stream)
            df_list = df.values.tolist()
            results = getAllResutlts(df_list, patt,proxy)
            try:
                newMail(results, e)
            except IOError:
                print("mail error")

        thread = Thread(target=bulkExtraction, args=(f,mail,patterns,proxys))
        thread.start()

        return jsonify("Data predana")


api.add_resource(UploadFile, "/uploadFile")


class AddProxy(Resource):
    @cross_origin(supports_credentials=True)
    def put(self):
        proxys = request.json['proxys']
        print(proxys)
        if "proxys" in session:
            session["proxys"] = proxys

        else:
            session["proxys"] = []
            session["proxys"] = proxys

        return jsonify(str(proxys)), 200


api.add_resource(AddProxy, "/addProxy")



class SessionCreate(Resource):
    @cross_origin(supports_credentials=True)
    def get(self):
        session["test"] = "Toto je test"
        return f'Obsah session: {session.get("test")}', 200

api.add_resource(SessionCreate, "/sessionCreate")

class SessionClear(Resource):
    @cross_origin(supports_credentials=True)
    def get(self):
        session.clear()
        return 'Smazano', 200

api.add_resource(SessionClear, "/sessionClear")

def getAllPatterns(pattern):
    namedPatterns = set()
    patterns = pattern.split(";")
    for subPattern in patterns:
        print(subPattern)
        if subPattern.find('==') > -1:
            namedPatterns.add(Pattern(subPattern))
    if len(namedPatterns) > 0:
        for p in namedPatterns:
            print(p.name)

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
    return json_normalize(results)

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




def newMail(df, mail):
    message = MIMEMultipart()
    message['Subject'] = "Web scraping data"
    message['From'] = os.getenv("MAIL")
    message['To'] = mail

    bio = io.BytesIO()
    df.to_csv(bio,mode="wb")
    bio.seek(0)
    attachement = MIMEApplication(bio.getvalue(),Name="Results")
    attachement.add_header("Content-Disposition", "attachement", filename="Results.csv")

    body = MIMEText("Here is your data", 'plain')
    message.attach(body)
    message.attach(attachement)
    with smtplib.SMTP("smtp-relay.sendinblue.com", 587) as server:
        server.starttls()
        server.login(os.getenv("MAIL"),os.getenv("PASSWORD"))
        server.sendmail(os.getenv("MAIL"),mail, message.as_string())

def bulkExtraction(f,mail):
    df = pd.read_csv(f.stream)
    df_list = df.values.tolist()
    results = getAllResutlts(df_list)
    newMail(results, mail)



if __name__ == "__main__":
    app.run(debug=True)
    print(sys.prefix)



