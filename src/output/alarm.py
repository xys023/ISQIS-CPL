"""
报警输出管理模块
支持多种报警方式：
- console: 控制台打印（所有平台可用，默认）
- gpio: RK3588 GPIO 控制声光报警器
- serial: 串口输出（连接PLC/报警灯）
- http: HTTP 回调（对接 MES/质量追溯系统）

可同时启用多种方式。
"""
import time
import threading
import json
import urllib.request
import urllib.error


class AlarmManager:
    """报警管理器"""

    def __init__(self, config):
        self.config = config
        methods_str = config.get("alarm.methods", "console")
        self.methods = [m.strip() for m in methods_str.split(",") if m.strip()]
        self.duration = config.get("alarm.duration", 3)
        self.gpio_pin = config.get("alarm.gpio_pin", 18)
        self.serial_port = config.get("alarm.serial.port", "/dev/ttyS0")
        self.serial_baud = config.get("alarm.serial.baudrate", 9600)
        self.http_url = config.get("alarm.http_url", "")

        self._gpio_available = False
        self._serial_available = False
        self._gpio = None
        self._serial = None
        self._alarm_active = False
        self._alarm_thread = None

        self._init_gpio()
        self._init_serial()

    def _init_gpio(self):
        """初始化 GPIO（仅 RK3588/Linux 硬件可用）"""
        if "gpio" not in self.methods:
            return
        try:
            # 优先使用 gpiozero（跨平台兼容）
            from gpiozero import LED
            self._gpio = LED(self.gpio_pin)
            self._gpio_available = True
            print(f"[信息] GPIO 报警初始化成功，引脚: {self.gpio_pin}")
        except Exception as e:
            # 回退到 sysfs 方式
            try:
                import os
                gpio_path = f"/sys/class/gpio/gpio{self.gpio_pin}"
                if not os.path.exists(gpio_path):
                    with open("/sys/class/gpio/export", "w") as f:
                        f.write(str(self.gpio_pin))
                with open(f"{gpio_path}/direction", "w") as f:
                    f.write("out")
                self._gpio_available = True
                self._gpio = "sysfs"
                print(f"[信息] GPIO(sysfs) 报警初始化成功，引脚: {self.gpio_pin}")
            except Exception as e2:
                print(f"[警告] GPIO 不可用（非 RK3588 硬件或无权限）: {e2}")
                print("[提示] 已自动降级为 console 报警")

    def _init_serial(self):
        """初始化串口"""
        if "serial" not in self.methods:
            return
        try:
            import serial
            self._serial = serial.Serial(self.serial_port, self.serial_baud, timeout=1)
            self._serial_available = True
            print(f"[信息] 串口报警初始化成功: {self.serial_port}@{self.serial_baud}")
        except ImportError:
            print("[警告] 未安装 pyserial，串口报警不可用")
        except Exception as e:
            print(f"[警告] 串口打开失败: {e}")

    def trigger(self, detection_result):
        """触发报警"""
        if self._alarm_active:
            return  # 已在报警中，避免重复

        defect_labels = [d.label_cn for d in detection_result.defects]
        message = f"[报警] 检测到不合格品！缺陷类型: {', '.join(defect_labels)}"

        # console 报警
        if "console" in self.methods:
            print(message)

        # GPIO 报警
        if "gpio" in self.methods and self._gpio_available:
            self._alarm_active = True
            self._alarm_thread = threading.Thread(
                target=self._gpio_alarm_worker, daemon=True
            )
            self._alarm_thread.start()

        # 串口报警
        if "serial" in self.methods and self._serial_available:
            try:
                # 发送报警指令（可根据PLC协议调整）
                cmd = f"ALARM,{','.join(defect_labels)}\n".encode()
                self._serial.write(cmd)
            except Exception as e:
                print(f"[错误] 串口报警发送失败: {e}")

        # HTTP 回调
        if "http" in self.methods and self.http_url:
            self._http_callback(detection_result)

    def _gpio_alarm_worker(self):
        """GPIO 报警闪烁线程"""
        end_time = time.time() + self.duration
        try:
            while time.time() < end_time and self._alarm_active:
                self._gpio_on()
                time.sleep(0.3)
                self._gpio_off()
                time.sleep(0.3)
        finally:
            self._gpio_off()
            self._alarm_active = False

    def _gpio_on(self):
        if self._gpio == "sysfs":
            try:
                with open(f"/sys/class/gpio/gpio{self.gpio_pin}/value", "w") as f:
                    f.write("1")
            except Exception:
                pass
        elif self._gpio is not None:
            try:
                self._gpio.on()
            except Exception:
                pass

    def _gpio_off(self):
        if self._gpio == "sysfs":
            try:
                with open(f"/sys/class/gpio/gpio{self.gpio_pin}/value", "w") as f:
                    f.write("0")
            except Exception:
                pass
        elif self._gpio is not None:
            try:
                self._gpio.off()
            except Exception:
                pass

    def _http_callback(self, result):
        """HTTP 回调上报检测结果"""
        try:
            data = json.dumps(result.to_dict()).encode("utf-8")
            req = urllib.request.Request(
                self.http_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass  # 静默处理
        except Exception as e:
            print(f"[警告] HTTP 回调失败: {e}")

    def stop(self):
        """停止报警"""
        self._alarm_active = False
        self._gpio_off()
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
