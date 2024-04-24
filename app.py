import json
import secrets
import string

from flask import Flask, g, request, jsonify, render_template, session, redirect
from flask_mail import Mail, Message

import test1
from test1 import find_lcu_prot_and_token

app = Flask(__name__, static_folder='static')
app.secret_key = '@'  # 设置密钥用于会话加密
app.config['MAIL_SERVER'] = 'smtp.163.com'  # 邮件服务器地址
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True  # 是否使用 TLS 加密
app.config['MAIL_USERNAME'] = ''  # 邮箱用户名
app.config['MAIL_PASSWORD'] = ''  # 邮箱密码

mail = Mail(app)


def get_gamemode(queue_id, game_modes_data):
    for mode in game_modes_data:
        if str(mode.get("queueId")) == queue_id:
            return mode.get("description", "未知描述")  # 处理缺少 description 的情况
    return "未知游戏模式"  # 如果未找到匹配的 queueId


def load_gamemodes(file_path="gamemodes.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            gamemodes = json.load(f)
        return gamemodes
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return str(e)


@app.route('/api/self_game')
def self_game():
    if in_check_login():
        return redirect('/login')
    summoner_name = request.args.get('summonerName')  # 从查询参数获取 summonerName
    if not summoner_name:
        return jsonify({"error": "缺少 summonerName 参数"}), 400
    data = test1.get_data(find_lcu_prot_and_token(), summoner_name)
    return data


@app.route('/api/Gamedetail')
def game_detail():
    if in_check_login():
        return redirect('/login')
    data = test1.get_game_detail(g.lol_PT, "8906861131")
    return data


@app.route("/api/gamemode")
def gamemodeid():
    if in_check_login():
        return redirect('/login')
    """根据 gamemode ID 获取游戏模式数据的 API 端点。"""
    gamemode_id = request.args.get('gameModeId')

    if not gamemode_id:
        return jsonify({"error": "缺少 gamemode ID"}), 400  # 返回错误消息
    data = get_gamemode(gamemode_id, load_gamemodes())
    if data:
        return jsonify(data)  # 返回游戏模式数据
    else:
        return jsonify("未知游戏模式")  # 如果未找到匹配的 queueId


@app.route("/api/champion")
def championId():
    if in_check_login():
        return redirect('/login')
    """根据 champion ID 获取角色数据的 API 端点。"""
    championId = request.args.get('championId')
    if not championId:
        return jsonify({"error": "缺少 championId ID"}), 400  # 返回错误消息
    data = test1.get_grid_champions(find_lcu_prot_and_token(), championId)
    if data:
        return jsonify(data)  # 返回游戏模式数据
    else:
        return jsonify({"error": "找不到 championId ID"}), 404  # 返回错误消息


@app.route('/api/rank')
def get_rank():
    if in_check_login():
        return redirect('/login')
    summoner_name = request.args.get('summonerName')  # 从查询参数获取 summonerName
    if not summoner_name:
        return jsonify({"error": "缺少 summonerName 参数"}), 400
    data = test1.get_ranks(find_lcu_prot_and_token(), summoner_name)
    return data


@app.route('/api/rank1')
def get_rank1():
    if in_check_login():
        return redirect('/login')
    summoner_name = request.args.get('summonerName')  # 从查询参数获取 summonerName
    if not summoner_name:
        return jsonify({"error": "缺少 summonerName 参数"}), 400
    data = test1.get_rank1(find_lcu_prot_and_token(), summoner_name)
    return data


@app.route('/api/extractdata')
def get_extractdata():
    if in_check_login():
        return redirect('/login')
    summoner_name = request.args.get('summonerName')
    if not summoner_name:
        return jsonify({"error": "缺少 summonerName 参数"}), 400
    data = test1.get_extract_data(find_lcu_prot_and_token(), summoner_name)
    return data


@app.route('/api/AllGameId')
def get_AllGameId():
    if in_check_login():
        return redirect('/login')
    summoner_name = request.args.get('summonerName')
    if not summoner_name:
        return jsonify({"error": "缺少 summonerName 参数"}), 400
    data = test1.get_All_Game_Id(find_lcu_prot_and_token(), summoner_name)
    return data


@app.route('/search')
def search():
    summoner_name = request.args.get('summonerName')
    user_agent = request.user_agent.string.lower()  # Get user-agent and lowercase
    is_mobile = False
    if in_check_login():
        return redirect('/login')

    mobile_keywords = ['iphone', 'ipad', 'android', 'mobile', 'tablet']
    for keyword in mobile_keywords:
        if keyword in user_agent:
            is_mobile = True
            break
    if is_mobile:
        template_name = 'msearch.html'
    else:
        template_name = 'search.html'

    return render_template(template_name, summoner_name=summoner_name)


@app.route('/')
def index():
    return render_template('index.html')


@app.before_request
def get_lol_pt():
    g.lol_PT = find_lcu_prot_and_token()


@app.route('/check_login')
def check_login():
    logged_in = session.get('logged_in')
    if logged_in:
        return jsonify({'status': True})
    else:
        return jsonify({'status': False})


@app.route('/send_verification_email', methods=['POST'])
def send_verification_code_email():
    email = request.form.get('email')
    verification_code = generate_verification_code()
    session['verification_code'] = verification_code
    try:
        msg = Message('战绩查询验证码', sender='验证码 <ooyy_2@163.com>', recipients=[email])
        msg.body = f'您的验证码是：{verification_code}'
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Verification code sent'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to send verification code'}), 500


def generate_verification_code(length=6):
    """生成指定长度的验证码，包含数字和字母 (更安全)"""
    characters = string.digits + string.ascii_letters
    code = ''.join(secrets.choice(characters) for _ in range(length))
    return code


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input_code = request.form['verification_code']
        correct_code = session.get('verification_code')
        if user_input_code == correct_code:
            session['logged_in'] = True
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '验证码错误'})
    else:
        return render_template('login.html')


def in_check_login():
    logged_in = session.get('logged_in')
    if not logged_in or logged_in is None:
        return True
    else:
        return False


if __name__ == '__main__':
    app.run(debug=True)
