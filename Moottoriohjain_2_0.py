# Moottoriohjain device using a web browser UI
# Moottoriohjain also is connected to Azure SQL database via IoT Hub

import time
import network
import socket
from machine import Pin, PWM
from umqtt.simple import MQTTClient

# Set motor running ON/OFF
SetMotor = Pin(15, Pin.OUT)
# Read motor running status
ReadMotor = Pin(14, Pin.IN, Pin.PULL_UP)
# Read motor manual request running speed
ReadRunningSpeed = machine.ADC(28)
# Read motor manual start or stop request
ReadMotorManualStartStop = Pin(16, Pin.IN, Pin.PULL_DOWN)
# Set motor running speed
SetMotorRunningSpeed = PWM(Pin(13))
SetMotorRunningSpeed.freq(1000)

ssid = '<SSID>'
password = '<Password>'

hostname = '<IoT Hub>.azure-devices.net'
clientid = '<Device>'
user_name = '<IoT Hub>.azure-devices.net/<Device>/?api-version=2021-04-12'
passw = '<password>'
topic_pub = b'devices/<Device>/messages/events/'
port_no = 8883
subscribe_topic = "devices/<Device>/messages/devicebound/#"

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Connecting to motor control unit...')
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected via {ip}')
    return ip

def open_socket(ip):
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return(connection)

def mqtt_connect():
    certificate_path = "baltimore.cer"
    print('Loading Blatimore Certificate')
    with open(certificate_path, 'r') as f:
        cert = f.read()
    print('Obtained Baltimore Certificate')
    sslparams = {'cert':cert}
    
    AzureClient = MQTTClient(client_id=clientid, server=hostname, port=port_no, user=user_name, password=passw, keepalive=3600, ssl=True, ssl_params=sslparams)
    AzureClient.connect()
    print('Connected to IoT Hub MQTT Broker')
    return AzureClient

def callback_handler(topic, message_receive):
    print("Received message")
    print(message_receive)
    
def webpage(SetMotorStatus, ReadMotorStatus, RunningSpeed, ReadMotorManualStatus, SetMotorManualSpeed, RunningSpeedPercent):
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Moottoriohjain</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="3">
        <!-- Latest compiled and minified CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.1/dist/css/bootstrap.min.css" rel="stylesheet">
        <!-- Latest compiled JavaScript -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.1/dist/js/bootstrap.bundle.min.js"></script>
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-12">
                    <center><h1>Moottoriohjain</h1>
                    <br><br>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-6">
                    <h5>Moottorin käynnistys</h5>
                    <p>
                    <form>
                        <div class="btn-group">
                            <button type="submit" class="btn btn-success" name="led" value="on">Käynnistys</button>
                            <button type="submit" class="btn btn-danger active" name="led" value="off">Pysäytys</button>
                        </div>
                    </form>
                    </p>
                    <br><br>
                    <h5>Moottorin käyntinopeus</h5>
                    <p>
                    <form>
                        <input type= "range" name= "resistor" id= "ageInputId" value="{SetMotorManualSpeed}" min="1" max="100" oninput="ageOutputId.value = ageInputId.value">
                        <output name= "ageOutputName" id= "ageOutputId">{SetMotorManualSpeed}</output>%
                        <br><br>
                        <button type = "submit" class = "btn btn-primary">Aseta käyntinopeus</button>
                    </form>
                    </p>
                </div>
                <div class="col-sm-6">
                    <table class="table table-striped text-left">
                        <thead>
                            <tr>
                                <th scope="col">Asetukset</th>
                                <th> </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">Moottorin tila</th>
                                <td>{SetMotorStatus}<br>
                                    {ReadMotorStatus}</td>
                            </tr>
                            <tr>
                                <th scope="row">Moottorin asetettu<br>käyntinopeus</th>
                                <td>{SetMotorManualSpeed}%</td>
                            </tr>
                        <tbody>
                    </table>
                    <table class="table table-striped text-left">
                        <thead>
                            <tr>
                                <th scope="col">Mittaukset</th>
                                <th> </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">Käsikäytön ohjausjännite</th>
                                <td>{RunningSpeed}V<br>
                                {RunningSpeedPercent}%</td>
                            </tr>
                            <tr>
                                <th scope="row">Hätäpysäytyksen tila</th>
                                <td>{ReadMotorManualStatus}</td>
                            </tr>
                        <tbody>
                    </table>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <p class="text-left">
                        <br><br>
                        <a href="https://www.devicetwin.net" target="_blank">www.DeviceTwin.net</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return str(html)
    
def serve(connection):
    #Start web server
    SetMotor.value(0)
    SetMotorStatus = ' '
    ReadMotor.value(0)
    ReadMotorStatus = 'Moottori ei ole käynnissä'
    RunningSpeed = 0
    RunningSpeedPercent = 0
    ReadMotorManualStartStop.value(0)
    ReadMotorManualStatus = ' '
    SetMotorManualSpeed = 0
    
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
            requestResistor = request[2:10]
            requestResistorVal = request[11:13]
        except IndexError:
            pass
        
        # Set Motor ON/OFF
        if request == '/?led=on':
            SetMotor.value(1)
            SetMotorStatus = 'Moottori käynnistetty'
        elif request == '/?led=off':
            SetMotor.value(0)
            SetMotorStatus = 'Moottori pysäytetty'
            
        # Set Motor manual speed
        if requestResistor == 'resistor':
            SetMotorManualSpeed = requestResistorVal
            DimmerValue = float(requestResistorVal)
            TempValue = (DimmerValue * 65536)/100
            DimmerValue = int (TempValue)
            SetMotorRunningSpeed.duty_u16(DimmerValue)
            
        if ReadMotor.value() == 1:
            ReadMotorStatus = "Moottori käynnissä"
        else:
            ReadMotorStatus = "Moottori pysähtynyt"
            
        RunningSpeed = ((ReadRunningSpeed.read_u16()) * (3.3/65536))
        RunningSpeed = round(RunningSpeed,2)
        
        RunningSpeedPercent = (RunningSpeed * 100) / 3.3
        RunningSpeedPercent = round(RunningSpeedPercent,1)
        
        if ReadMotorManualStartStop.value() == 1:
            ReadMotorManualStatus = "Moottorin hätäpysäytys aktivoitunut"
        else:
            ReadMotorManualStatus = "Moottorin hätäpysäytys ei aktiivisena"

        html = webpage(SetMotorStatus, ReadMotorStatus, RunningSpeed, ReadMotorManualStatus, SetMotorManualSpeed, RunningSpeedPercent)
        client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        client.send(html)
        
        MQTTSetMotor = str(SetMotor.value())
        MQTTReadMotor = str(ReadMotor.value())
        MQTTSetMotorManualSpeed = str(SetMotorManualSpeed)
        MQTTRunningSpeed = str(RunningSpeed)
        MQTTRunningSpeedPercent = str(RunningSpeedPercent)
        MQTTReadMotorEStop = str(ReadMotorManualStartStop.value())
        
        AzureClient.check_msg()
        topic_msg = '{"SetMotor": "{0}", "ReadMotor": "{1}", "SetMotorManualSpeed": "{2}", "RunningSpeed": "{3}", "RunningSpeedPercent": "{4}", "ReadMotorEStop": "{5}"}'
        topic_msg = topic_msg.replace("{0}", MQTTSetMotor).replace("{1}", MQTTReadMotor).replace("{2}", MQTTSetMotorManualSpeed).replace("{3}", MQTTRunningSpeed).replace("{4}", MQTTRunningSpeedPercent).replace("{5}", MQTTReadMotorEStop)
        AzureClient.publish(topic_pub, topic_msg)
        
        client.close()
        
try:
    ip = connect()
    connection = open_socket(ip)
    AzureClient = mqtt_connect()
    AzureClient.set_callback(callback_handler)
    AzureClient.subscribe(topic=subscribe_topic)
    serve(connection)
except KeyboardInterrupt:
    machine.reset()
    