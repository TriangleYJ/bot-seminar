import json

from flask import Flask, request, send_from_directory, redirect, render_template, session
from flask_cors import CORS, cross_origin
from flask_wtf.csrf import CSRFProtect
from flask_seasurf import SeaSurf
import requests
import os

import credentials


app = Flask(__name__)
# SECRET_KEY = os.urandom(32)
# app.config['SECRET_KEY'] = SECRET_KEY
FB_API_URL = 'https://graph.facebook.com/v2.6/me/messages'


app.config['DEBUG'] = True
CORS(app, supports_credentials=True)
# csrf = SeaSurf(app)


def send_message(recipient_id, text):
    """Send a response to Facebook"""
    payload = {
        'message': {
            'text': text
        },
        'recipient': {
            'id': recipient_id
        },
        'notification_type': 'regular'
    }

    auth = {
        'access_token': credentials.PAGE_ACCESS_TOKEN
    }

    response = requests.post(
        FB_API_URL,
        params=auth,
        json=payload
    )

    return response.json()


#사용자의 응답을 받고 메시지를 형성하는 부분
def respond(sender, message):

    credentials.DB["fb"].add(sender)

    if message == "id":
        send_message(sender, "Your id is")
        send_message(sender, sender)
    elif message == "/off":
        send_message(sender, "새글 알림이 꺼졌습니다.")
        credentials.DB["fb"].remove(sender)
    elif message == "/on":
        send_message(sender, "새글 알림이 켜졌습니다.")
        credentials.DB["fb"].add(sender)
    # elif message == "hello":
    #     send_reply(MY_ID, message)
    else:
        response = "This is a dummy response to '{}'".format(message)
        send_message(sender, response)



def is_user_message(message):
    return (message.get('message') and
            message['message'].get('text') and
            not message['message'].get("is_echo"))


#
# @app.route('/send/<id>/<message>')
# def send_reply(id, message):
#     data = {
#         'parent_article': None,
#         'parent_comment': id,
#         'content': message,
#         'is_anonymous': False,
#         'attachment': None
#     }
#     res = requests.post("https://newara.dev.sparcs.org/api/comments/", data=json.dumps(data))
#     print(res.content.decode('utf8'))
#     return "ok"

@app.route("/webhook", methods=['GET'])
def listen():
    if request.method == 'GET':
        return verify_webhook(request)

@app.route("/webhook", methods=['POST'])
def talk():
    payload = request.get_json()
    event = payload['entry'][0]['messaging']
    for x in event:
        if is_user_message(x):
            text = x['message']['text']
            sender_id = x['sender']['id']
            respond(sender_id, text)

    return "ok"

# @app.route("/login")
# def login():
#     return redirect("https://newara.dev.sparcs.org/api/users/sso_login/?next=http://127.0.0.1:3000/login-handler")
#
# @app.route("/login-handler")
# def login_handle():
#     return redirect("/")

@app.route("/")
def post_test():
    return "Hello world!"


def verify_webhook(req):
    if req.args.get("hub.verify_token") == credentials.VERIFY_TOKEN:
        return req.args.get("hub.challenge")
    else:
        return "incorrect"


@app.route('/<target>/<message>')
def test_echo_target(target, message):
    send_message(target, message)
    return message


@app.route('/bot/alert/<target>', methods=['POST'])
@cross_origin()
def ara_alert(target):
    payload = request.get_json()

    if target != "all":
        if target in credentials.DB["ara"]:
            id = credentials.DB["ara"][target]
            if payload["type"] == "reply":
                #print(payload["target_id"])
                reply_message = '[내 {}글 : {}]\n{} 님이 {}댓글을 달았어요. \n{} \n\n본문 보러 가기 :\nhttp://localhost:8080/post/{}'
                reply_message = reply_message.format("댓" if payload["reply_type"] == "re" else "", payload["my_content"], payload["sender"], "대" if payload["reply_type"] == "re" else "", payload["content"], payload["post_id"])
                send_message(id, reply_message)

    elif payload["type"] == "new_post":
        reply_message = '[{}]\n새로운 글이 올라왔어요.'
        reply_message = reply_message.format(payload["content"])
        for i in credentials.DB["fb"]:
            send_message(i, reply_message)

    return 'ok'
        

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'favicon.ico',mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(threaded=True, port=3000)