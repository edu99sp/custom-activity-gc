import requests, jwt
from flask import Flask, request, jsonify, render_template
from jwt.algorithms import RSAAlgorithm

app = Flask(__name__)

# Ajuste com suas infos do SFMC
CLIENT_ID = 'SEU_CLIENT_ID'
CLIENT_SECRET = 'SEU_CLIENT_SECRET'
AUTH_BASE_URL = 'https://SEU_SUBDOMAIN.auth.marketingcloudapis.com'
DE_EXTERNAL_KEY = 'EXTERNAL_KEY_DA_SUA_DE'

# Validação JWT SFMC
def validate_jwt(token):
    jwk_url = f'{AUTH_BASE_URL}/v2/token/publickey'
    jwk = requests.get(jwk_url).json()['publicKey']
    public_key = RSAAlgorithm.from_jwk(jwk)
    decoded = jwt.decode(token, public_key, algorithms=['RS256'], audience=CLIENT_ID)
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
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        validate_jwt(token)
    except Exception as e:
        return jsonify({'error': 'JWT invalid', 'detail': str(e)}), 401

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