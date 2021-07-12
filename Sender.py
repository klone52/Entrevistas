import http.client
import urllib
import base64
import yaml
import cv2
import datetime

HOST = 'localhost'
URL =  '/api/v1/set_alarm'
HEADERS = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
        }

class Sender:

    def __init__(self, host = HOST, url = URL):
        self.host = host
        self.url = url

    def sendpackage(self, image, idx, alarm, sco_number, date, time):
        jpg_image = cv2.imencode('.jpg', image)[1]
        b64_image = base64.b64encode(jpg_image).decode('ascii')

        params = urllib.parse.urlencode({ 
            'image': b64_image,
            'cam_id': idx,
            'alarm': alarm,
            'paydesk': sco_number,
            'datetime': date+' '+time,
            'idx': idx,
            'sco_number': sco_number,
            'date': date,
            'time': time

            })
        try:
            conn = http.client.HTTPConnection(self.host)
        except Exception as e:
            print("Error1 ", end="")
            print(e)
        try:
            conn.request('POST', self.url, params, HEADERS)
        except Exception as e:
            print("Error2 ", end="")
            print(e)
        return conn.getresponse().read().decode('utf-8')

    def sendregister(self, image, idx, alarm, sco_number, date, time):
        jpg_image = cv2.imencode('.jpg', image)[1]
        b64_image = base64.b64encode(jpg_image).decode('ascii')

        params = urllib.parse.urlencode({ 
            'image': b64_image,
            'paydesk': sco_number,
            'datetime': date+' '+time
            })
        try:
            conn = http.client.HTTPConnection(self.host)
        except Exception as e:
            print("Error1 ", end="")
            print(e)
        try:
            conn.request('POST', self.url, params, HEADERS)
        except Exception as e:
            print("Error2 ", end="")
            print(e)
        return conn.getresponse().read().decode('utf-8')


if __name__ == '__main__':
    # carga del archivo de configuración
    yaml.warnings({'YAMLLoadWarning': False})
    yaml_file = open("../config.yaml", 'r')
    config = yaml.load(yaml_file)
    yaml_file.close()

    img = cv2.imread('test.png')
    sender = Sender(host=config['App']['ip'], url=config['App']['URL_TO_APPWEB'])
    print(sender.sendpackage(img, 1, 1, 1, '2020-05-11', '22:30:00'))

