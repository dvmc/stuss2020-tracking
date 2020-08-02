#!/usr/bin/env python

from flask import Flask, render_template, request, send_from_directory
app = Flask(__name__)

@app.route("/")
def main():
    return render_template('index.html')

if __name__ == "__main__":
    app.run()