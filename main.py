import requests, jwt
from flask import Flask, request, jsonify, render_template
from jwt.algorithms import RSAAlgorithm

app = Flask(__name__)

# Ajuste com suas infos do SFMC
import os

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
AUTH_BASE_URL = os.environ.get('AUTH_BASE_URL')
DE_EXTERNAL_KEY = os.environ.get('DE_EXTERNAL_KEY')


# Validação JWT SFMC
def validate_jwt(token):
    import base64
    jwt_secret = os.environ.get("JWT_SECRET")
    if not jwt_secret:
        raise ValueError("JWT_SECRET não configurado.")

    decoded = jwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        audience=CLIENT_ID
    )
    return decoded


# Obter Token OAuth SFMC
def get_oauth_token():
    url = f'{AUTH_BASE_URL}/v2/token'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    r = requests.post(url, json=payload)
    return r.json()['access_token']

# Inserir dados na DE
def insert_into_de(data):
    token = get_oauth_token()
    url = f'https://{AUTH_BASE_URL.replace("auth", "rest")}/hub/v1/dataevents/key:{DE_EXTERNAL_KEY}/rowset'
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(url, json=[data], headers=headers)
    return response.status_code == 200

@app.route('/execute', methods=['POST'])
def execute():
    # token = request.headers.get('Authorization', '').replace('Bearer ', '')
    #try:
     #   validate_jwt(token)
    #except Exception as e:
     #   return jsonify({'error': 'JWT invalid', 'detail': str(e)}), 401

    args = request.json.get('inArguments', [{}])[0]
    contact_key = args.get('ContactKey', '')
    percentual_gc = float(args.get('PercentualGC', 10))
    nome_campanha = args.get('NomeCampanha', '')

    hash_val = sum(ord(c) for c in contact_key)
    grupo = 'GC' if (hash_val % 100) < percentual_gc else 'ACAO'

    data = {
        "keys": {"ContactKey": contact_key, "NomeCampanha": nome_campanha},
        "values": {"GrupoControle": grupo, "PercentualGC": percentual_gc}
    }

    success = insert_into_de(data)

    return jsonify({
        "outArguments": [
            {"grupoControle": grupo},
            {"NomeCampanha": nome_campanha},
            {"insertSuccess": success}
        ],
        "execute": True
    })

@app.route('/save', methods=['POST'])
@app.route('/publish', methods=['POST'])
@app.route('/validate', methods=['POST'])
def simple_response():
    return jsonify({"success": True})

@app.route('/ui', methods=['GET'])
def config_ui():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
