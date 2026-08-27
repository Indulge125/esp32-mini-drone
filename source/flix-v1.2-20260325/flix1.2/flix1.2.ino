// Copyright (c) 2023 Oleg Kalachev <okalachev@gmail.com>
// Repository代码仓库: https://github.com/okalachev/flix
// Main firmware file 主程序文件Releases V1.2 20260108
// 源代码使用Arduino IDE 2.3.x以上版本编译，不支持老版本的1.8.19！
// 必须安装ESP32开发板核心库（即esp32 by Espressif Systems）
// 必须安装MAVLINK，FlixPeriph库文件！
// 开发板可选择ESP32 Dev Module或WeMOS D1 MINI ESP32；
// 嘉立创开源项目：ESP32迷你无人机 https://oshwhub.com/malagis/esp32-mini-plane
// B站微辣火龙果 https://space.bilibili.com/544479100

#include "vector.h"
#include "quaternion.h"
#include "util.h"

#define WIFI_ENABLED 1

extern float t, dt;
extern float controlRoll, controlPitch, controlYaw, controlThrottle, controlMode;
extern Vector gyro, acc;
extern Vector rates;
extern Quaternion attitude;
extern bool landed;
extern float motors[4];

void setup() {
	Serial.begin(115200);
	print("程序初始化！\n");
	disableBrownOut();
	setupParameters();
	setupLED();
	setupMotors();
	setLED(true);
#if WIFI_ENABLED
	setupWiFi();
#endif
	setupIMU();
	setupRC();
	setLED(false);
	print("初始化完成\n");
}

void loop() {
	readIMU();
	step();
	readRC();
	estimate();
	control();
	sendMotors();
	handleInput();
#if WIFI_ENABLED
	processMavlink();
#endif
	logData();
	syncParameters();
}
