from flask import Flask, render_template_string, jsonify, request
import requests
import colorsys

app = Flask(__name__)

class NanoleafController:
    def __init__(self, name, ip, auth_token):
        self.name = name
        self.ip = ip
        self.auth_token = auth_token
        self.base_url = f"http://{ip}:16021/api/v1/{auth_token}"

    def _put(self, path, payload):
        url = f"{self.base_url}/{path}"
        try:
            return requests.put(url, json=payload)
        except Exception as e:
            print(f"[{self.name}] PUT error: {e}")

    def _get(self, path):
        url = f"{self.base_url}/{path}"
        try:
            response = requests.get(url, timeout=3)
            return response.json()
        except Exception as e:
            print(f"[{self.name}] GET error or invalid JSON from {path}: {e}")
            return {}

    def turn_on(self):
        self._put("state", {"on": {"value": True}})

    def turn_off(self):
        self._put("state", {"on": {"value": False}})

    def set_brightness(self, value):
        self._put("state", {"brightness": {"value": value}})

    def set_color(self, r, g, b):
        r_norm, g_norm, b_norm = r / 255, g / 255, b / 255
        h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)

        hue = int(h * 360)
        saturation = int(s * 100)
        brightness = int(v * 100)

        self._put("state", {
            "hue": {"value": hue},
            "sat": {"value": saturation},
            "brightness": {"value": brightness}
        })

    def get_effects(self):
        data = self._get("effects/effectsList")
        return data if isinstance(data, list) else []

    def set_effect(self, effect_name):
        self._put("effects", {"select": effect_name})

    def get_state(self):
        return self._get("state")

    def get_current_effect(self):
        data = self._get("effects")
        return data.get("select", "") if data else ""



NANO1_IP = ""
NANO1_TOKEN = ""

NANO2_IP = ""
NANO2_TOKEN = ""

controller1 = NanoleafController("Panel 1", NANO1_IP, NANO1_TOKEN)
controller2 = NanoleafController("Panel 2", NANO2_IP, NANO2_TOKEN)

syncing = False


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Nanoleaf Controller</title>
    <style>
        body { background: black; color: white; font-family: Arial, sans-serif; }
        .panel { background: #222; padding: 15px; margin: 10px; border-radius: 8px; }
        button { margin: 5px; padding: 8px 12px; font-size: 16px; cursor: pointer; }
        .fav-button { width: 40px; height: 40px; border: none; margin: 2px; border-radius: 5px; cursor: pointer; }
        .fav-purple { background: #b383e9; }
        .fav-green { background: #9ce59c; }
        .fav-blue { background: #628ae2; }
        select { font-size: 16px; padding: 4px; margin: 5px 0; }
        #sync-btn { background: #88cc88; border: none; border-radius: 5px; }
        #sync-btn.syncing { background: #cc8888; }
    </style>
</head>
<body>
    <h1>Nanoleaf Controller</h1>

    <div id="panel1" class="panel">
        <h2>Panel 1</h2>
        <button onclick="powerToggle(1)">Toggle Power</button>
        <button onclick="brightnessChange(1, 10)">Brightness +</button>
        <button onclick="brightnessChange(1, -10)">Brightness -</button>
        <span id="brightness1"></span><br/>
        <select id="scene1" onchange="sceneChange(1)">
            <option>Loading...</option>
        </select><br/>
        <button class="fav-button fav-purple" title="Purple" onclick="setFavoriteScene(1, 'Purple')"></button>
        <button class="fav-button fav-green" title="Greener" onclick="setFavoriteScene(1, 'Greener')"></button>
        <button class="fav-button fav-blue" title="Thunder" onclick="setFavoriteScene(1, 'Thunder')"></button><br/>
        <button onclick="pickColor(1)">Pick Color</button>
    </div>

    <div id="panel2" class="panel">
        <h2>Panel 2</h2>
        <button onclick="powerToggle(2)" id="power-btn-2">Toggle Power</button>
        <button onclick="brightnessChange(2, 10)">Brightness +</button>
        <button onclick="brightnessChange(2, -10)">Brightness -</button>
        <span id="brightness2"></span><br/>
        <select id="scene2" onchange="sceneChange(2)">
            <option>Loading...</option>
        </select><br/>
        <button class="fav-button fav-purple" title="Purple" onclick="setFavoriteScene(2, 'Purple')"></button>
        <button class="fav-button fav-green" title="Greener" onclick="setFavoriteScene(2, 'Greener')"></button>
        <button class="fav-button fav-blue" title="Thunder" onclick="setFavoriteScene(2, 'Thunder')"></button><br/>
        <button onclick="pickColor(2)">Pick Color</button>
    </div>

    <button id="sync-btn" onclick="toggleSync()">Start Syncing</button>

    <input type="color" id="color-picker" style="display:none" onchange="colorPicked(event)"/>

<script>
let syncing = false;
let colorPanel = null;

async function fetchState(panel) {
    let resp = await fetch(`/api/${panel}/state`);
    return resp.json();
}

async function fetchScenes(panel) {
    let resp = await fetch(`/api/${panel}/scenes`);
    return resp.json();
}

async function updatePanelUI(panel) {
    let state = await fetchState(panel);
    let brightness = state.brightness?.value || 50;
    document.getElementById(`brightness${panel}`).textContent = "Brightness: " + brightness;

    let sceneSelect = document.getElementById(`scene${panel}`);
    let scenes = await fetchScenes(panel);

    sceneSelect.innerHTML = "";
    scenes.forEach(s => {
        let opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s;
        sceneSelect.appendChild(opt);
    });

    let currentEffectResp = await fetch(`/api/${panel}/current_effect`);
    let currentEffect = await currentEffectResp.json();
    if (scenes.includes(currentEffect.effect)) {
        sceneSelect.value = currentEffect.effect;
    } else {
        sceneSelect.selectedIndex = 0;
    }
}

async function powerToggle(panel) {
    let state = await fetchState(panel);
    let isOn = state.on?.value;
    let url = `/api/${panel}/power`;
    let newState = !isOn;
    await fetch(url, {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({on: newState})
    });
    updatePanelUI(panel);
    if(syncing && panel === 1){
        syncToPanel2();
    }
}

async function brightnessChange(panel, delta) {
    let state = await fetchState(panel);
    let brightness = state.brightness?.value || 50;
    brightness = Math.min(100, Math.max(0, brightness + delta));
    await fetch(`/api/${panel}/brightness`, {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({brightness: brightness})
    });
    updatePanelUI(panel);
    if(syncing && panel === 1){
        syncToPanel2();
    }
}

async function sceneChange(panel) {
    let sceneSelect = document.getElementById(`scene${panel}`);
    let scene = sceneSelect.value;
    await fetch(`/api/${panel}/scene`, {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scene: scene})
    });
    if(syncing && panel === 1){
        syncToPanel2();
    }
}

async function setFavoriteScene(panel, scene) {
    await fetch(`/api/${panel}/scene`, {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scene: scene})
    });
    updatePanelUI(panel);
    if(syncing && panel === 1){
        syncToPanel2();
    }
}

function pickColor(panel) {
    colorPanel = panel;
    document.getElementById("color-picker").click();
}

async function colorPicked(event) {
    if (!colorPanel) return;
    let color = event.target.value; 
    let r = parseInt(color.slice(1,3), 16);
    let g = parseInt(color.slice(3,5), 16);
    let b = parseInt(color.slice(5,7), 16);

    await fetch(`/api/${colorPanel}/color`, {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({r: r, g: g, b: b})
    });
    updatePanelUI(colorPanel);
    if(syncing && colorPanel === 1){
        syncToPanel2();
    }
    colorPanel = null;
}

async function toggleSync() {
    syncing = !syncing;
    let btn = document.getElementById("sync-btn");
    if(syncing){
        btn.textContent = "Stop Syncing";
        btn.classList.add("syncing");
        setPanel2Enabled(false);
        await syncToPanel2();
    } else {
        btn.textContent = "Start Syncing";
        btn.classList.remove("syncing");
        setPanel2Enabled(true);
    }
}

async function syncToPanel2(){
    let resp = await fetch('/api/sync');
    let result = await resp.json();
    if(result.status !== 'ok'){
        alert('Sync failed: ' + result.error);
    }
}

function setPanel2Enabled(enabled) {
    let panel2 = document.getElementById("panel2");
    let buttons = panel2.querySelectorAll("button, select");
    buttons.forEach(b => b.disabled = !enabled);
}

window.onload = function(){
    updatePanelUI(1);
    updatePanelUI(2);
};
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# API routes for panel actions
@app.route("/api/<int:panel>/power", methods=["GET", "POST"])
def panel_power(panel):
    controller = get_controller(panel)
    if request.method == "POST":
        data = request.get_json()
        if data.get("on") is True:
            controller.turn_on()
        else:
            controller.turn_off()
        return jsonify({"status": "ok"})
    else:
        state = controller.get_state()
        return jsonify({"on": state.get("on", {}).get("value", False)})

@app.route("/api/<int:panel>/brightness", methods=["GET", "POST"])
def panel_brightness(panel):
    controller = get_controller(panel)
    if request.method == "POST":
        data = request.get_json()
        brightness = data.get("brightness")
        if brightness is not None:
            controller.set_brightness(int(brightness))
        return jsonify({"status": "ok"})
    else:
        state = controller.get_state()
        return jsonify({"brightness": state.get("brightness", {}).get("value", 50)})

@app.route("/api/<int:panel>/scenes", methods=["GET"])
def panel_scenes(panel):
    controller = get_controller(panel)
    scenes = controller.get_effects()
    return jsonify(scenes)

@app.route("/api/<int:panel>/scene", methods=["POST"])
def panel_scene(panel):
    controller = get_controller(panel)
    data = request.get_json()
    scene = data.get("scene")
    if scene:
        controller.set_effect(scene)
    return jsonify({"status": "ok"})

@app.route("/api/<int:panel>/color", methods=["POST"])
def panel_color(panel):
    controller = get_controller(panel)
    data = request.get_json()
    r = data.get("r")
    g = data.get("g")
    b = data.get("b")
    if None not in (r, g, b):
        controller.set_color(int(r), int(g), int(b))
    return jsonify({"status": "ok"})

@app.route("/api/<int:panel>/state", methods=["GET"])
def panel_state(panel):
    controller = get_controller(panel)
    return jsonify(controller.get_state())

@app.route("/api/<int:panel>/current_effect", methods=["GET"])
def panel_current_effect(panel):
    controller = get_controller(panel)
    effect = controller.get_current_effect()
    return jsonify({"effect": effect})

@app.route("/api/sync", methods=["POST", "GET"])
def sync_panels():
    try:
        state = controller1.get_state()
        effect = controller1.get_current_effect()
        if state.get("on", {}).get("value", True):
            controller2.turn_on()
        else:
            controller2.turn_off()

        controller2.set_brightness(state.get("brightness", {}).get("value", 50))

        if effect:
            controller2.set_effect(effect)
        controller2_state = controller2.get_state()
        return jsonify({"status": "ok", "panel2_state": controller2_state})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


def get_controller(panel):
    if panel == 1:
        return controller1
    elif panel == 2:
        return controller2
    else:
        raise ValueError("Invalid panel number")

if __name__ == "__main__":
    app.run(debug=True)
