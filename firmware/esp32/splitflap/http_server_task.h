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
#pragma once

#include <SPIFFS.h>
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>


#include "../core/logger.h"
#include "../core/splitflap_task.h"
#include "../core/task.h"

#include "display_task.h"

class HTTPServerTask : public Task<HTTPServerTask> {
    friend class Task<HTTPServerTask>; // Allow base Task to invoke protected run()

    public:
        HTTPServerTask(SplitflapTask& splitflap_task, DisplayTask& display_task, Logger& logger, uint8_t task_core);

    protected:
        void run();

    private:
        void connectWifi();
        void startServer();
        void handleRoot();
        void handleTextPost();
        void handleStatusGet();
        void handleCalibratePost();
        void handleOptions();
        void handleNotFound();
        void sendJson(uint16_t status_code, const String& payload);
        void updateWifiStatusDisplay();

        SplitflapTask& splitflap_task_;
        DisplayTask& display_task_;
        Logger& logger_;
        WebServer server_;
        bool routes_configured_ = false;
        bool server_running_ = false;
        wl_status_t last_wifi_status_ = WL_NO_SHIELD;
};