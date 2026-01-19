/*
   Copyright 2025 Scott Bezek and the splitflap contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
#if HTTP_SERVER

#include "http_server_task.h"

#include <json11.hpp>

#include "secrets.h"

using namespace json11;

namespace {
    constexpr uint16_t kHttpServerPort = 80;

    const char* ModeToString(SplitflapMode mode) {
        switch (mode) {
            case SplitflapMode::MODE_RUN:
                return "run";
            case SplitflapMode::MODE_SENSOR_TEST:
                return "sensor_test";
            default:
                return "unknown";
        }
    }

    const char* ModuleStateToString(State state) {
        switch (state) {
            case NORMAL:
                return "normal";
            case LOOK_FOR_HOME:
                return "look_for_home";
            case SENSOR_ERROR:
                return "sensor_error";
            case PANIC:
                return "panic";
            case STATE_DISABLED:
                return "disabled";
            default:
                return "unknown";
        }
    }
}

HTTPServerTask::HTTPServerTask(SplitflapTask& splitflap_task, DisplayTask& display_task, Logger& logger, uint8_t task_core) :
        Task("HTTP_SERVER", 8192, 1, task_core),
        splitflap_task_(splitflap_task),
        display_task_(display_task),
        logger_(logger),
        server_(kHttpServerPort) {
}

void HTTPServerTask::connectWifi() {
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    // Disable WiFi sleep as it causes glitches on pin 39; see https://github.com/espressif/arduino-esp32/issues/4903#issuecomment-793187707
    WiFi.setSleep(WIFI_PS_NONE);
    
    char buf[256];

    logger_.log("Establishing connection to WiFi..");
    snprintf(buf, sizeof(buf), "Wifi connecting to %s", WIFI_SSID);
    display_task_.setMessage(1, String(buf));
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
    }

    snprintf(buf, sizeof(buf), "Wifi IP: %s", WiFi.localIP().toString().c_str());
    logger_.log(buf);
    updateWifiStatusDisplay();
}

void HTTPServerTask::startServer() {
    if (!routes_configured_) {
        server_.on("/", HTTP_GET, [this]() { handleRoot(); });
        server_.on("/text", HTTP_POST, [this]() { handleTextPost(); });
        server_.on("/text", HTTP_OPTIONS, [this]() { handleOptions(); });
        server_.on("/status", HTTP_GET, [this]() { handleStatusGet(); });
        server_.on("/status", HTTP_OPTIONS, [this]() { handleOptions(); });
        server_.on("/calibrate", HTTP_POST, [this]() { handleCalibratePost(); });
        server_.on("/calibrate", HTTP_OPTIONS, [this]() { handleOptions(); });
        server_.onNotFound([this]() { handleNotFound(); });
        routes_configured_ = true;
    }

    if (server_running_ || WiFi.status() != WL_CONNECTED) {
        return;
    }

    server_.begin();
    server_running_ = true;

    char buf[192];
    snprintf(buf, sizeof(buf), "HTTP server ready: http://%s:%u/text", WiFi.localIP().toString().c_str(), kHttpServerPort);
    logger_.log(buf);
    display_task_.setMessage(1, String(buf));
}

void HTTPServerTask::handleRoot() {
    Json response = Json::object {
        {"status", "ok"},
        {"message", "POST JSON to /text to update the display"},
        {"max_length", NUM_MODULES}
    };
    sendJson(200, String(response.dump().c_str()));
}

void HTTPServerTask::handleTextPost() {
    if (!server_.hasArg("plain")) {
        sendJson(400, "{\"error\":\"empty_body\"}");
        return;
    }

    String body = server_.arg("plain");
    std::string err;
    Json json = Json::parse(body.c_str(), err);
    if (!err.empty() || !json.is_object()) {
        sendJson(400, "{\"error\":\"invalid_json\"}");
        return;
    }

    auto text_json = json["text"];
    if (!text_json.is_string()) {
        sendJson(400, "{\"error\":\"text_required\"}");
        return;
    }
    std::string text = text_json.string_value();

    bool force_full_rotation = false;
    auto force_json = json["force_full_rotation"];
    if (force_json.is_bool()) {
        force_full_rotation = force_json.bool_value();
    }

    bool default_unspecified_home = true;
    auto default_json = json["default_unspecified_home"];
    if (default_json.is_bool()) {
        default_unspecified_home = default_json.bool_value();
    }

    size_t requested_length = text.length();
    uint8_t length = requested_length > NUM_MODULES ? NUM_MODULES : requested_length;
    std::string truncated = text.substr(0, length);

    splitflap_task_.showString(truncated.c_str(), length, force_full_rotation, default_unspecified_home);

    char buf[128];
    snprintf(buf, sizeof(buf), "HTTP text update (%u chars)", length);
    logger_.log(buf);

    Json response = Json::object {
        {"status", "ok"},
        {"display_length", length},
        {"text", truncated}
    };
    sendJson(200, String(response.dump().c_str()));
}

void HTTPServerTask::handleOptions() {
    server_.sendHeader("Access-Control-Allow-Origin", "*");
    server_.sendHeader("Access-Control-Allow-Headers", "Content-Type");
    server_.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server_.send(204);
}

void HTTPServerTask::handleNotFound() {
    sendJson(404, "{\"error\":\"not_found\"}");
}

void HTTPServerTask::handleStatusGet() {
    SplitflapState state = splitflap_task_.getState();

    Json::array modules_json;
    for (uint8_t i = 0; i < NUM_MODULES; i++) {
        const auto& module = state.modules[i];
        char flap_char = (module.flap_index < NUM_FLAPS) ? static_cast<char>(flaps[module.flap_index]) : '?';

        modules_json.push_back(Json::object {
            {"index", i},
            {"state", ModuleStateToString(module.state)},
            {"flap_index", module.flap_index},
            {"flap", std::string(1, flap_char)},
            {"moving", module.moving},
            {"home_state", module.home_state},
            {"count_missed_home", module.count_missed_home},
            {"count_unexpected_home", module.count_unexpected_home}
        });
    }

    Json::object payload {
        {"status", "ok"},
        {"mode", ModeToString(state.mode)},
        {"uptime_ms", Json(static_cast<double>(millis()))},
        {"modules", modules_json}
    };

#ifdef CHAINLINK
    payload["loopbacks_ok"] = state.loopbacks_ok;
#endif

    sendJson(200, String(Json(payload).dump().c_str()));
}

void HTTPServerTask::handleCalibratePost() {
    splitflap_task_.resetAll();
    logger_.log("HTTP calibration requested");

    Json response = Json::object {
        {"status", "queued"},
        {"action", "calibrate"}
    };
    sendJson(202, String(response.dump().c_str()));
}

void HTTPServerTask::sendJson(uint16_t status_code, const String& payload) {
    server_.sendHeader("Access-Control-Allow-Origin", "*");
    server_.sendHeader("Access-Control-Allow-Headers", "Content-Type");
    server_.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server_.send(status_code, "application/json", payload);
}

void HTTPServerTask::updateWifiStatusDisplay() {
    wl_status_t status = WiFi.status();
    if (status == last_wifi_status_) {
        return;
    }
    last_wifi_status_ = status;

    String line0 = "Wifi: ";
    switch (status) {
        case WL_IDLE_STATUS:
            line0 += "Idle";
            break;
        case WL_NO_SSID_AVAIL:
            line0 += "No SSID";
            break;
        case WL_CONNECTED:
            line0 += String(WIFI_SSID) + " " + WiFi.localIP().toString();
            break;
        case WL_CONNECT_FAILED:
            line0 += "Connect failed";
            break;
        case WL_CONNECTION_LOST:
            line0 += "Connection lost";
            break;
        case WL_DISCONNECTED:
            line0 += "Disconnected";
            break;
        default:
            line0 += "Unknown";
            break;
    }
    display_task_.setMessage(0, line0);

    if (status == WL_CONNECTED && server_running_) {
        char buf[192];
        snprintf(buf, sizeof(buf), "HTTP: http://%s:%u/text", WiFi.localIP().toString().c_str(), kHttpServerPort);
        display_task_.setMessage(1, String(buf));
    } else {
        display_task_.setMessage(1, "HTTP: waiting...");
    }
}

void HTTPServerTask::run() {
    display_task_.setMessage(0, "");
    display_task_.setMessage(1, "HTTP: starting...");

    connectWifi();

    if (WiFi.status() == WL_CONNECTED) {
        startServer();
    } else if (server_running_) {
        server_running_ = false;
    }

    while (true) {
        updateWifiStatusDisplay();

        if (server_running_) {
            server_.handleClient();
        }
    }
}

#endif