# ESP32 Mini Plane V1.4 Project Context

This workspace is for reproducing the OSHWHub project "ESP32 mini plane" V1.4.

Project page:
https://oshwhub.com/malagis/esp32-mini-plane

## Current Build Route

- PCB version: V1.4
- Main controller: ESP32 DevKit V1 / ESP-32 CH340 Type-C, with headers soldered
- IMU route: GY-521 MPU6050 module
- Do not use the MPU6500 firmware for this build
- Preferred control route: phone / QGroundControl over ESP32 Wi-Fi
- ESP32 AP expected by project firmware: `Drone_WIFI`, password `12345678`
- If the 5 V boost module is not installed, R12 must be shorted with 0 ohm / solder / short wire

## Firmware And Source To Keep

Priority files from the OSHWHub attachment area:

1. Firmware bin archive, 2026-03-25
   - Contains V1.4 firmware bins.
   - Use the MPU6050 firmware bin for this MPU6050 build.
2. Project-modified Flix v1.2 source archive, 2026-03-25
   - Author-modified Flix v1.2 source with Chinese comments/changes.
   - In `imu.ino`, only enable the MPU6050 line, not the MPU6500/MPU9250 line.
3. BOM spreadsheet, updated 2025-12-26
   - Keep as BOM reference even if some parts are already bought.
4. `flash_download_tool_3.9.9_R2.zip`
   - Optional if using Espressif Flash Download Tool instead of Arduino IDE upload.
5. Optional reference/modification packages:
   - Liu Zhensheng modified source: ELRS protocol, LED control, voltage telemetry
   - Liu Zhensheng modified source: barometer altitude hold, web-browser phone control

Upstream reference:

- Flix v1.2 release: https://github.com/okalachev/flix/releases/tag/v1.2
- Flix repository: https://github.com/okalachev/flix
- ESP-Drone reference: https://espressif-docs.readthedocs-hosted.com/projects/espressif-esp-drone/zh-cn/latest/gettingstarted.html

## Build Order

Recommended staged assembly and validation:

1. Power path
2. ESP32 module
3. MPU6050 module
4. Motor drive circuits
5. Motors
6. Propellers last

Before first power:

- Check BAT+ to GND is not shorted
- Check battery connector polarity matches PCB polarity
- Check 3.3 V rail behavior before plugging sensitive modules
- Do not install propellers during first power, flashing, or motor tests

## Known Risk Points

- Battery connector polarity reversal
- Missing R12 short when no 5 V boost module is used
- Wrong firmware variant, especially flashing MPU6500 firmware onto MPU6050 build
- Motor direction and propeller A/B orientation
- MPU6050 orientation and IMU selection in `imu.ino`

## Serial / Test Notes

- Serial monitor baud rate: 115200
- Motor test commands from project page:
  - `mfr`: front right motor
  - `mfl`: front left motor
  - `mrr`: rear right motor
  - `mrl`: rear left motor
- Accelerometer calibration command: `ca`
- Print status/attitude command mentioned by project page: `ps`
