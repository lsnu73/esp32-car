# -*- coding: utf-8 -*-
"""
@Author: Wang HaiRui
@Date: 2024-12-5
@Version: 3.0
@Description: ESP32小车控制程序,通过ESP32的Wi-Fi热点实现
                网页控制小车前后左右移动，启动和停止，前方避障功能。
"""

import network
import socket
import json
import ujson
from machine import UART, Pin, SoftI2C
from esp32_aw2013 import AW2013
import time
from time import sleep
 
# 配置UART 
uart = UART(2, 115200, rx=16, tx=17)

# RGB LED 初始化
DEFAULT_I2C_ADDR = 0x45
i2c = SoftI2C(sda=Pin(26), scl=Pin(27), freq=100000)
RGB = AW2013(i2c, DEFAULT_I2C_ADDR)

# 配置Wi-Fi热点 
ap = network.WLAN(network.AP_IF)
ap.active(True) 
ap.config(essid='ESP32_Car',  password='12345678')
 
# 定义控制命令
commands = {
    'forward': {"control": {"turn": "run", "pwm": {"L_Motor": 350, "R_Motor": 350}}},
    'backward': {"control": {"turn": "back", "pwm": {"L_Motor": 350, "R_Motor": 350}}},
    'left': {"control": {"turn": "left", "pwm": {"L_Motor": 200, "R_Motor": 400}}},
    'right': {"control": {"turn": "right", "pwm": {"L_Motor": 400, "R_Motor": 200}}},
    'stop': {"control": {"turn": "stop", "pwm": {"L_Motor": 0, "R_Motor": 0}}}
}

#从UART读取的数据中提取第一个distance的值。
def get_first_distance(uart):
    
    try:
        # 读取UART数据
        data = uart.read()
        # 检查是否读取到数据
        if data is not None:
            # 将读取到的字节字符串解码为普通字符串
            data_str = data.decode('utf-8')
            
            # 按照换行符分割字符串，获取单独的JSON字符串
            json_strings = data_str.split('\n')
            
            # 检查是否至少有一个JSON字符串
            if json_strings and json_strings[0]:
                # 解析第一个JSON字符串
                status = ujson.loads(json_strings[0])
                
                # 提取distance的值
                distance = status['status']['distance']
                return distance
            else:
                print("No JSON data found")
                return None
        else:
            print("No data read from UART")
            return None
    except ValueError:
        print("JSON decode error")
        return None
    except KeyError:
        print("Key error: 'distance' not found")
        return None

# HTML页面内容
html = """
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Car Control</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin-top: 50px;
        }
        button {
            width: 150px;
            height: 150px;
            font-size: 24px;
            margin: 10px;
        }
    </style>
</head>
<body>
    <h1>ESP32 Car Control</h1>
    <button onclick="location.href='/forward'">Forward</button><br> 
    <button onclick="location.href='/left'">Left</button> 
    <button onclick="location.href='/right'">Right</button><br> 
    <button onclick="location.href='/backward'">Backward</button><br> 
    <button onclick="location.href='/stop'">Stop</button> 
</body>
</html>
"""



# 创建Web服务器
def start_web_server():
    addr = socket.getaddrinfo('192.168.4.1',80)[0][-1]
    s = socket.socket() 
    s.bind(addr) 
    s.listen(1) 
    print('Listening on', addr)
 
    while True:
        cl, addr = s.accept() 
        print('Client connected from', addr)
        request = cl.recv(1024) 
        request = str(request)
        print('Request:', request)
        # 解析请求 
        if 'GET /forward' in request:
            RGB.set_value(0,255,0)
            control=True;
            #检测小车前方距离
            while control:
                distance = get_first_distance(uart)
                print(distance)
                command = commands['forward']
                json_data = json.dumps(command) 
                uart.write(json_data) 
                #距离小于250时，停止前进
                if distance < 250:
                    RGB.set_value(0, 0, 0)
                    command = commands['stop']
                    json_data = json.dumps(command) 
                    uart.write(json_data)
                    control=False  # 跳出循环
                sleep(0.1)
        elif 'GET /backward' in request:
            RGB.set_value(255,255,0)
            command = commands['backward']
        elif 'GET /left' in request:
            RGB.set_value(255,0,0)
            command = commands['left']
        elif 'GET /right' in request:
            RGB.set_value(0,0,255)
            command = commands['right']
        elif 'GET /stop' in request:
            RGB.set_value(0,0,0)
            command = commands['stop']
        else:
            RGB.set_value(0,0,0)
            command = commands['stop']
 
        # 发送命令
        json_data = json.dumps(command) 
        uart.write(json_data) 
        print('Sent:', json_data)
 
        # 发送响应
        response = 'HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n' + html
        cl.send(response) 
        cl.close()

 
# 启动Web服务器
start_web_server()


